#!/usr/bin/env python3
"""Bronze layer ingestion for the medallion rebuild (specs/medallion_architecture.md, section 2).

Modes:
  --full    discovery + full historical pull (2014 floor re-check + 2015->present, 3 series, 6 feeds)
  --update  weekly increment: refresh current/next-year index, revision-window re-fetch, retry failed
  --verify  re-hash stored/imported files against the manifest's recorded sha256

Run from src/ (data paths resolve from the repo root via __file__, per repo convention).
"""
import argparse, glob, gzip, hashlib, json, os, random, threading, time, urllib.error, urllib.request, uuid
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRONZE_DIR = os.path.join(REPO_ROOT, 'data', 'bronze')
TMP_DIR = os.path.join(BRONZE_DIR, '.tmp')
MANIFEST_PATH = os.path.join(BRONZE_DIR, 'manifest.jsonl')
LEGACY_IMPORT_DIR = os.path.join(BRONZE_DIR, 'legacy_import')
LEGACY_RACES_GLOB = os.path.join(REPO_ROOT, 'src', 'data', 'races', '*.json')
LEGACY_EXTRA_FILES = [os.path.join(REPO_ROOT, 'src', 'data', 'race_list_2026.json')]

BASE_URL = 'https://cf.nascar.com/cacher'
USER_AGENT = 'nascar-cup-model/1.0 (personal research archive)'
TOTAL_TIMEOUT = 60  # urllib exposes one socket timeout; this is the binding (larger) of the spec's 30s/60s pair

MIN_INDEX_YEAR = 2015
DEFAULT_WORKERS = 4
MAX_WORKERS = 6
RATE_CAP_PER_SEC = 5.0
JITTER_MS = 250

RETRY_SLEEPS = [2, 4, 8, 16, 32]
MAX_ATTEMPTS = 5

CIRCUIT_WINDOW = 30
CIRCUIT_403_THRESHOLD = 8
CIRCUIT_PAUSE_SECONDS = 120
CIRCUIT_RECOVERY_THRESHOLD = 1  # <=1/30 recent 403s -> restore full concurrency (2026-07-19 amendment, see spec 2.4 note)

# 2026-07-19 dated amendment (spec 2.4, "amendable pre-B2 by dated note" -- owner-directed mid-B2):
# once the circuit has tripped, a shorter ladder resolves confirmed-absent URLs faster and sends
# FEWER total requests at an endpoint already showing sustained 403s -- strictly more polite, not
# less. Pre-trip behavior (5 attempts, 2/4/8/16/32s) is unchanged, matching the original spec text.
CIRCUIT_TRIPPED_MAX_ATTEMPTS = 2
CIRCUIT_TRIPPED_RETRY_SLEEPS = [2]

REVISION_WINDOW_DAYS = 21

FEEDS_YEARED = ['weekend-feed', 'lap-times', 'live-pit-data', 'lap-notes']
FEEDS_LIVE = ['live-flag-data', 'live-feed']
ALL_FEEDS = FEEDS_YEARED + FEEDS_LIVE


# --------------------------------------------------------------------------
# Paths, URLs, atomic storage
# --------------------------------------------------------------------------

def race_dir(series_id, year, race_id):
    return os.path.join(BRONZE_DIR, f'series_{series_id}', str(year), str(race_id))


def feed_url(feed, series_id, year, race_id):
    if feed in FEEDS_LIVE:
        return f'{BASE_URL}/live/series_{series_id}/{race_id}/{feed}.json'
    return f'{BASE_URL}/{year}/{series_id}/{race_id}/{feed}.json'


def index_url(year):
    return f'{BASE_URL}/{year}/race_list_basic.json'


def utc_ts():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def ensure_dirs():
    os.makedirs(BRONZE_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(LEGACY_IMPORT_DIR, exist_ok=True)


def clean_tmp():
    if os.path.isdir(TMP_DIR):
        for name in os.listdir(TMP_DIR):
            try:
                os.remove(os.path.join(TMP_DIR, name))
            except OSError:
                pass


def store_atomic(raw_bytes, final_path):
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_path = os.path.join(TMP_DIR, f'{uuid.uuid4().hex}.json.gz.tmp')
    with gzip.GzipFile(tmp_path, mode='wb', mtime=0) as gz:
        gz.write(raw_bytes)
    os.replace(tmp_path, final_path)


def latest_stored_path(dirpath, feed):
    basename = 'race_list_basic' if feed == 'race_list' else feed
    matches = sorted(glob.glob(os.path.join(dirpath, f'{basename}.*.json.gz')))
    return matches[-1] if matches else None


def sha256_of_gz(path):
    with gzip.open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def load_manifest_state():
    """key -> latest outcome, for resumability skip checks."""
    state = {}
    if not os.path.exists(MANIFEST_PATH):
        return state
    with open(MANIFEST_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            key = (entry.get('feed'), entry.get('series_id'), entry.get('year'), entry.get('race_id'))
            state[key] = entry.get('outcome')
    return state


def record(manifest_lock, manifest_state, run_id, url, feed, series_id, year, race_id,
           outcome, http_status, sha256_hex, bytes_raw, bytes_gz, path, attempts, error):
    entry = {
        'run_id': run_id,
        'fetch_utc': datetime.now(timezone.utc).isoformat(),
        'url': url,
        'feed': feed,
        'series_id': series_id,
        'year': year,
        'race_id': race_id,
        'outcome': outcome,
        'http_status': http_status,
        'sha256': sha256_hex,
        'bytes_raw': bytes_raw,
        'bytes_gz': bytes_gz,
        'path': os.path.relpath(path, REPO_ROOT) if path else None,
        'attempts': attempts,
        'error': error,
    }
    line = json.dumps(entry)
    key = (feed, series_id, year, race_id)
    with manifest_lock:
        with open(MANIFEST_PATH, 'a') as f:
            f.write(line + '\n')
        manifest_state[key] = outcome


# --------------------------------------------------------------------------
# HTTP: politeness, retry ladder, circuit breaker
# --------------------------------------------------------------------------

class Throttle:
    """Aggregate rate cap + dynamic concurrency cap (shrinks to 1 when the circuit trips,
    restores to `workers` once the recent-request window looks healthy again -- 2026-07-19
    amendment, spec 2.4 note)."""

    def __init__(self, workers):
        self.default_cap = workers
        self.cond = threading.Condition()
        self.cap = workers
        self.active = 0
        self.recent = deque(maxlen=CIRCUIT_WINDOW)
        self.tripped = False
        self.last_dispatch = 0.0

    def _acquire(self):
        with self.cond:
            while self.active >= self.cap:
                self.cond.wait()
            self.active += 1

    def _release(self):
        with self.cond:
            self.active -= 1
            self.cond.notify_all()

    def _pace(self):
        with self.cond:
            interval = 1.0 / RATE_CAP_PER_SEC
            now = time.monotonic()
            wait = self.last_dispatch + interval - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self.last_dispatch = now
        time.sleep(random.uniform(0, JITTER_MS / 1000))

    @contextmanager
    def slot(self):
        self._acquire()
        try:
            self._pace()
            yield
        finally:
            self._release()

    def record_status(self, status):
        """Returns 'tripped' / 'recovered' on a state transition, else None. Can trip again
        after a recovery if a later stretch goes bad too."""
        with self.cond:
            self.recent.append(status)
            if len(self.recent) < CIRCUIT_WINDOW:
                return None
            n403 = sum(1 for s in self.recent if s == 403)
            if not self.tripped and n403 >= CIRCUIT_403_THRESHOLD:
                self.tripped = True
                self.cap = 1
                self.cond.notify_all()
                return 'tripped'
            if self.tripped and n403 <= CIRCUIT_RECOVERY_THRESHOLD:
                self.tripped = False
                self.cap = self.default_cap
                self.cond.notify_all()
                return 'recovered'
        return None


def do_request(url):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TOTAL_TIMEOUT) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as e:
        return e.code, None, f'HTTP {e.code}'
    except Exception as e:
        return None, None, repr(e)


def fetch_with_ladder(url, throttle):
    """Returns (outcome_kind, body, last_status, attempts, error).
    outcome_kind in {'success', 'absent_candidate', 'failed'}."""
    max_attempts = CIRCUIT_TRIPPED_MAX_ATTEMPTS if throttle.tripped else MAX_ATTEMPTS
    sleeps = CIRCUIT_TRIPPED_RETRY_SLEEPS if throttle.tripped else RETRY_SLEEPS
    last_status, last_err = None, None
    for attempt in range(1, max_attempts + 1):
        with throttle.slot():
            status, body, err = do_request(url)
        last_status, last_err = status, err
        transition = throttle.record_status(status if isinstance(status, int) else 0)
        if transition == 'tripped':
            print('[bronze_fetch] circuit breaker tripped (>=8/30 recent 403s): pausing 120s, '
                  'dropping to 1 worker + shorter ladder until the recent window looks healthy again')
            time.sleep(CIRCUIT_PAUSE_SECONDS)
        elif transition == 'recovered':
            print(f'[bronze_fetch] circuit recovered (<={CIRCUIT_RECOVERY_THRESHOLD}/{CIRCUIT_WINDOW} '
                  f'recent 403s): restoring full concurrency + ladder')
        if status == 200:
            try:
                json.loads(body)
                return 'success', body, status, attempt, None
            except Exception as e:
                last_err = f'unparseable JSON: {e}'
                last_status = 'unparseable'
        if attempt < max_attempts:
            time.sleep(sleeps[attempt - 1] + random.uniform(0, 1))
    if last_status in (403, 404):
        return 'absent_candidate', None, last_status, attempt, last_err
    return 'failed', None, last_status, attempt, last_err


def race_has_run(r):
    """True iff the index entry reflects a completed race, not just a scheduled one.

    winner_driver_id alone (spec 2.2's literal completion gate) is unset for every 2015-2019
    race and 12/41 of 2022's -- an older index schema variant that never populated it even
    for long-settled races. average_speed/total_race_time are 0/empty pre-race across every
    observed year (verified against 2026 race 5618, not yet run as of this session) and
    populated post-race even where winner_driver_id is missing, so they close the gap."""
    return bool(r.get('winner_driver_id')) or bool(r.get('average_speed')) \
        or bool((r.get('total_race_time') or '').strip())


def parse_race_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(s[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except Exception:
            return None


# --------------------------------------------------------------------------
# Index fetch (needs its body synchronously to build the race-task list,
# so its absent/throttled disambiguation is an inline single re-check
# rather than the batched end-of-run sweep used for feed tasks)
# --------------------------------------------------------------------------

def index_year_matches(idx_json, year):
    """cf.nascar.com quirk verified 2026-07-19: the year=2017 index URL 200s with the exact
    2018 season's races (race_season=2018 throughout) instead of 403ing like the genuinely
    absent 2013/2014. Every other year 2015-2026 is self-consistent. Detect any recurrence by
    majority vote on race_season across all three series rather than hardcoding 2017."""
    seasons = [r.get('race_season') for sid in (1, 2, 3)
               for r in (idx_json.get(f'series_{sid}') or []) if r.get('race_season') is not None]
    if not seasons:
        return True
    return sum(1 for s in seasons if s == year) > len(seasons) / 2


def fetch_index(year, throttle, manifest_lock, manifest_state, run_id):
    url = index_url(year)
    dirpath = os.path.join(BRONZE_DIR, 'race_list', str(year))
    existing_path = latest_stored_path(dirpath, 'race_list')
    existing_sha = sha256_of_gz(existing_path) if existing_path else None

    outcome_kind, body, status, attempts, err = fetch_with_ladder(url, throttle)
    if outcome_kind == 'absent_candidate':
        time.sleep(2)
        status, body, err = do_request(url)
        attempts += 1
        if status == 200:
            try:
                json.loads(body)
                outcome_kind = 'success'
            except Exception as e:
                err = f'unparseable JSON: {e}'
                outcome_kind = 'failed'
        else:
            outcome_kind = 'absent' if status in (403, 404) else 'failed'

    if outcome_kind == 'success':
        parsed = json.loads(body)
        if not index_year_matches(parsed, year):
            record(manifest_lock, manifest_state, run_id, url, 'race_list', None, year, None,
                   'absent', status, None, None, None, None, attempts,
                   f'index content year-mismatch: server returned another year\'s data for '
                   f'year={year} (cf.nascar.com quirk, verified 2026-07-19); treated as no '
                   f'distinct index exists for this year')
            return None
        sha = hashlib.sha256(body).hexdigest()
        if existing_sha == sha:
            record(manifest_lock, manifest_state, run_id, url, 'race_list', None, year, None,
                   'unchanged', status, sha, len(body), None, existing_path, attempts, None)
        else:
            final_path = os.path.join(dirpath, f'race_list_basic.{utc_ts()}.json.gz')
            store_atomic(body, final_path)
            record(manifest_lock, manifest_state, run_id, url, 'race_list', None, year, None,
                   'stored', status, sha, len(body), os.path.getsize(final_path), final_path, attempts, None)
        return parsed

    final_outcome = 'absent' if outcome_kind == 'absent' else 'failed'
    record(manifest_lock, manifest_state, run_id, url, 'race_list', None, year, None,
           final_outcome, status, None, None, None, None, attempts, err)
    return None


# --------------------------------------------------------------------------
# Feed tasks: fetch, atomic write / unchanged / defer-to-sweep / failed
# --------------------------------------------------------------------------

def process_task(task, throttle, manifest_lock, manifest_state, tentative_absents, lock_absents, run_id):
    feed, sid, year, race_id, force = task
    dirpath = race_dir(sid, year, race_id)
    url = feed_url(feed, sid, year, race_id)
    key = (feed, sid, year, race_id)

    existing_path = latest_stored_path(dirpath, feed)
    if not force:
        if existing_path:
            return
        if manifest_state.get(key) == 'absent':
            return

    outcome_kind, body, status, attempts, err = fetch_with_ladder(url, throttle)

    if outcome_kind == 'success':
        sha = hashlib.sha256(body).hexdigest()
        existing_sha = sha256_of_gz(existing_path) if existing_path else None
        if existing_sha == sha:
            record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                   'unchanged', status, sha, len(body), None, existing_path, attempts, None)
        else:
            final_path = os.path.join(dirpath, f'{feed}.{utc_ts()}.json.gz')
            store_atomic(body, final_path)
            record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                   'stored', status, sha, len(body), os.path.getsize(final_path), final_path, attempts, None)
    elif outcome_kind == 'absent_candidate':
        with lock_absents:
            tentative_absents.append((feed, sid, year, race_id, url))
    else:
        record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
               'failed', status, None, None, None, None, attempts, err)


def run_tasks(tasks, throttle, manifest_lock, manifest_state, tentative_absents, run_id, workers):
    if not tasks:
        return
    lock_absents = threading.Lock()
    total = len(tasks)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(process_task, t, throttle, manifest_lock, manifest_state,
                           tentative_absents, lock_absents, run_id) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            exc = f.exception()
            if exc:
                print(f'[bronze_fetch] task error: {exc!r}')
            if i % 200 == 0 or i == total:
                print(f'[bronze_fetch] {i}/{total} tasks processed')


def sweep_tentative(tentatives, manifest_lock, manifest_state, run_id):
    for feed, sid, year, race_id, url in tentatives:
        time.sleep(2)
        status, body, err = do_request(url)
        dirpath = race_dir(sid, year, race_id)
        existing_path = latest_stored_path(dirpath, feed)
        if status == 200:
            try:
                json.loads(body)
            except Exception as e:
                record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                       'failed', 'unparseable', None, None, None, None, 1, f'unparseable JSON: {e}')
                continue
            sha = hashlib.sha256(body).hexdigest()
            existing_sha = sha256_of_gz(existing_path) if existing_path else None
            if existing_sha == sha:
                record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                       'unchanged', status, sha, len(body), None, existing_path, 1, None)
            else:
                final_path = os.path.join(dirpath, f'{feed}.{utc_ts()}.json.gz')
                store_atomic(body, final_path)
                record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                       'stored', status, sha, len(body), os.path.getsize(final_path), final_path, 1, None)
        elif status in (403, 404):
            record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                   'absent', status, None, None, None, None, 1, err)
        else:
            record(manifest_lock, manifest_state, run_id, url, feed, sid, year, race_id,
                   'failed', status, None, None, None, None, 1, err)


# --------------------------------------------------------------------------
# Legacy-cache import (spec section 2.6, one-time in B2)
# --------------------------------------------------------------------------

def import_legacy_cache(manifest_lock, manifest_state, run_id):
    sources = sorted(glob.glob(LEGACY_RACES_GLOB)) + [p for p in LEGACY_EXTRA_FILES if os.path.exists(p)]
    if not sources:
        print('[bronze_fetch] legacy import: no source files found under src/data/')
        return
    imported = 0
    for src in sources:
        name = os.path.basename(src)
        dest = os.path.join(LEGACY_IMPORT_DIR, f'{name}.gz')
        if os.path.exists(dest):
            continue
        with open(src, 'rb') as f:
            raw = f.read()
        try:
            json.loads(raw)
        except Exception as e:
            print(f'[bronze_fetch] legacy import: skipping unparseable {name}: {e!r}')
            continue
        sha = hashlib.sha256(raw).hexdigest()
        store_atomic(raw, dest)
        record(manifest_lock, manifest_state, run_id, None, 'legacy_import', None, None, None,
               'imported', None, sha, len(raw), os.path.getsize(dest), dest, 1, None)
        imported += 1
    print(f'[bronze_fetch] legacy import: {imported} file(s) imported from src/data/ '
          f'({len(sources)} source file(s) found on this machine). Spec section 2.6 assumes '
          f'163 race files (lap-times + weekend-feed) plus race_list_2026.json; the per-race '
          f'cache is absent from this checkout (gitignored, never persisted outside the session '
          f'that originally built races_parsed.pkl) -- flagged for C1: section 4.3\'s mismatch '
          f'attribution will have no legacy-import sha baseline for those races and must fall '
          f'back to owner escalation instead of the mechanical shas-differ check.')


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def print_run_summary(manifest_state):
    c = Counter(manifest_state.values())
    print(f'[bronze_fetch] manifest state snapshot: {dict(c)}')


def cmd_full(workers):
    run_id = utc_ts()
    print(f'[bronze_fetch] run_id={run_id} mode=full workers={workers}')
    manifest_state = load_manifest_state()
    manifest_lock = threading.Lock()

    import_legacy_cache(manifest_lock, manifest_state, run_id)

    current_year = datetime.now(timezone.utc).year
    years = [MIN_INDEX_YEAR - 1] + list(range(MIN_INDEX_YEAR, current_year + 1))

    throttle = Throttle(workers)
    index_json = {}
    for year in years:
        body = fetch_index(year, throttle, manifest_lock, manifest_state, run_id)
        if body is not None:
            index_json[year] = body
        print(f'[bronze_fetch] index {year}: {"ok" if body is not None else "unavailable this run"}')

    tasks = []
    # 2026-07-19 amendment: newest-first task order. Recent years are far more likely to have
    # real detailed-feed data (the circuit breaker trips fast on structurally-absent historical
    # years); processing them first banks the likely-good data at full concurrency before any
    # trip, instead of the reverse (oldest-first hits the absence-heavy stretch immediately and
    # then stays throttled for the healthy years too, per the pre-amendment permanent-trip design).
    for year in sorted(index_json.keys(), reverse=True):
        idx = index_json[year]
        for sid in (1, 2, 3):
            for r in (idx.get(f'series_{sid}') or []):
                if not race_has_run(r):
                    continue
                race_id = r['race_id']
                for feed in ALL_FEEDS:
                    tasks.append((feed, sid, year, race_id, False))

    print(f'[bronze_fetch] {len(tasks)} feed tasks queued across {len(index_json)} year indices')
    tentative_absents = []
    run_tasks(tasks, throttle, manifest_lock, manifest_state, tentative_absents, run_id, workers)

    print(f'[bronze_fetch] sweeping {len(tentative_absents)} tentative-absent URLs')
    sweep_tentative(tentative_absents, manifest_lock, manifest_state, run_id)
    print_run_summary(manifest_state)
    print('[bronze_fetch] full pull complete')


def cmd_update(workers):
    run_id = utc_ts()
    print(f'[bronze_fetch] run_id={run_id} mode=update workers={workers}')
    manifest_state = load_manifest_state()
    manifest_lock = threading.Lock()
    throttle = Throttle(workers)

    current_year = datetime.now(timezone.utc).year
    fresh_years = [current_year, current_year + 1]
    index_json = {}
    for year in fresh_years:
        body = fetch_index(year, throttle, manifest_lock, manifest_state, run_id)
        if body is not None:
            index_json[year] = body

    all_years = [MIN_INDEX_YEAR - 1] + list(range(MIN_INDEX_YEAR, current_year + 2))
    for year in all_years:
        if year in index_json:
            continue
        dirpath = os.path.join(BRONZE_DIR, 'race_list', str(year))
        path = latest_stored_path(dirpath, 'race_list')
        if path:
            with gzip.open(path, 'rb') as f:
                parsed = json.loads(f.read())
            if index_year_matches(parsed, year):
                index_json[year] = parsed

    cutoff = datetime.now(timezone.utc) - timedelta(days=REVISION_WINDOW_DAYS)
    tasks = {}
    for year in sorted(index_json.keys(), reverse=True):
        idx = index_json[year]
        for sid in (1, 2, 3):
            for r in (idx.get(f'series_{sid}') or []):
                if not race_has_run(r):
                    continue
                race_id = r['race_id']
                race_date = parse_race_date(r.get('race_date'))
                has_wf = latest_stored_path(race_dir(sid, year, race_id), 'weekend-feed') is not None
                recent = race_date is not None and race_date >= cutoff
                if not (has_wf or recent):
                    continue
                for feed in ALL_FEEDS:
                    key = (feed, sid, year, race_id)
                    if recent:
                        # 2026-07-19 fix: within the revision window, keep re-checking every
                        # feed regardless of prior state -- a feed marked absent for a
                        # just-finished race may simply not be published yet and could
                        # legitimately appear within the 21-day window.
                        tasks[key] = True
                        continue
                    # backfill trigger ("no stored weekend-feed", historical catch-up):
                    # ordinary section 2.4 resumability -- fetch only if this SPECIFIC
                    # feed is neither already stored nor terminal-absent. Checking only
                    # `!= 'absent'` (without also checking `stored`) was a bug: it kept
                    # re-including every already-successful feed too, since `race_has_run`
                    # gating happens once at race level (via weekend-feed) but each of the
                    # other 5 feeds needs its own stored/absent check.
                    already_stored = latest_stored_path(race_dir(sid, year, race_id), feed) is not None
                    if not already_stored and manifest_state.get(key) != 'absent':
                        tasks[key] = True

    for key, state in manifest_state.items():
        feed = key[0]
        if state == 'failed' and feed not in ('race_list', 'legacy_import'):
            tasks[key] = True

    task_list = [(feed, sid, year, race_id, True) for (feed, sid, year, race_id) in tasks]
    print(f'[bronze_fetch] {len(task_list)} feed tasks queued (revision-window + failed-retry)')
    tentative_absents = []
    run_tasks(task_list, throttle, manifest_lock, manifest_state, tentative_absents, run_id, workers)
    print(f'[bronze_fetch] sweeping {len(tentative_absents)} tentative-absent URLs')
    sweep_tentative(tentative_absents, manifest_lock, manifest_state, run_id)
    print_run_summary(manifest_state)
    print('[bronze_fetch] update complete')


def cmd_verify(sample):
    latest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get('outcome') in ('stored', 'imported') and e.get('path') and e.get('sha256'):
                    latest[e['path']] = e
    records = list(latest.values())
    if sample and sample < len(records):
        records = random.sample(records, sample)
    print(f'[bronze_fetch] verify: checking {len(records)} file(s)')
    ok = missing = mismatch = 0
    for e in records:
        full_path = os.path.join(REPO_ROOT, e['path'])
        if not os.path.exists(full_path):
            missing += 1
            print(f'  MISSING on disk: {e["path"]}')
            continue
        actual = sha256_of_gz(full_path)
        if actual != e['sha256']:
            mismatch += 1
            print(f'  SHA MISMATCH: {e["path"]} manifest={e["sha256"][:12]} actual={actual[:12]}')
        else:
            ok += 1
    print(f'[bronze_fetch] verify complete: {ok} ok, {missing} missing, {mismatch} mismatched')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--full', action='store_true')
    mode.add_argument('--update', action='store_true')
    mode.add_argument('--verify', action='store_true')
    ap.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    ap.add_argument('--sample', type=int, default=None, help='--verify: limit to N random files')
    args = ap.parse_args()

    ensure_dirs()
    clean_tmp()
    workers = min(max(1, args.workers), MAX_WORKERS)

    if args.full:
        cmd_full(workers)
    elif args.update:
        cmd_update(workers)
    else:
        cmd_verify(args.sample)


if __name__ == '__main__':
    main()

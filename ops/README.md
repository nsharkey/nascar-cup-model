# ops/ — local host-level automation recipes (not auto-installed)

Nothing in this directory is wired into the live machine by any script in this
repo. Everything here is a documented recipe the owner runs by hand, because
it touches system-level state (a launchd background job, a `pmset` wake
schedule) that a session should not silently activate. Building the tool is
in-repo, git-tracked, reversible; *installing* it on the laptop is a separate,
explicit step.

## live_feed_poller.py (plan session L4)

`src/live_feed_poller.py` records the in-progress `live-feed.json` stream for
one Cup race. NASCAR's cacher only ever serves the *current* snapshot — once
a race ends, every earlier lap's live state is gone for good (confirmed:
`silver.live_final` is built from "the latest stored snapshot", i.e. the
post-race final frame only). Capturing the intra-race time series is only
possible while the race is actually green.

This is opportunistic and best-effort by design (matches the plan's own L4
note): the log will have gaps whenever the machine sleeps or is off, and
nothing in the pipeline consumes this data yet — it's a retention hedge
against an otherwise-permanent loss, nothing more. Don't over-invest in
making it bulletproof.

### Option A — just run it manually (recommended to start)

No system changes, no risk, works today. Shortly before green flag:

```bash
cd ~/Downloads/nascar-cup-model/src
caffeinate -i python3 live_feed_poller.py --race-id 5619   # or omit --race-id to auto-detect today's race
```

`caffeinate -i` keeps the Mac from sleeping while the poller runs (it does
**not** power the display on or prevent a manual sleep/lid-close). Ctrl-C to
stop early; the poller also stops on its own once the feed reports the
checkered flag for a few consecutive polls. Output:
`data/live_capture/{race_id}/live-feed.jsonl.gz` (gitignored, matches every
other `data/` path in this repo).

### Option B — hands-off via launchd + pmset (optional, requires sudo)

Only worth doing if Option A proves the poller is useful and you want it to
survive you forgetting to start it. This wakes the Mac from sleep for one
race and runs the poller unattended.

1. Find the race's actual green-flag time (local time you want the Mac
   awake for — `race_date` in the bronze index is not confirmed to be in a
   single consistent timezone across all rows; cross-check against the
   public NASCAR schedule for the specific race before scheduling a wake).
2. Schedule a one-off wake ~15 minutes before green flag (requires sudo):
   ```bash
   sudo pmset schedule wake "07/26/26 13:45:00"
   ```
   Verify: `pmset -g sched`. Cancel if needed:
   `sudo pmset schedule cancel wake "07/26/26 13:45:00"`.
3. Copy the template and fill in the race_id + calendar fields:
   ```bash
   cp ops/live_feed_poller.plist.template ~/Library/LaunchAgents/com.nascarcupmodel.livefeedpoller.plist
   # edit the copy: set --race-id and the StartCalendarInterval Hour/Minute/etc.
   ```
4. Load it:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.nascarcupmodel.livefeedpoller.plist
   ```
5. Afterward, unload it so it doesn't fire again next week with a stale
   race_id (this is a one-race job, not a recurring schedule):
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.nascarcupmodel.livefeedpoller.plist
   rm ~/Library/LaunchAgents/com.nascarcupmodel.livefeedpoller.plist
   ```

### Verifying it worked

```bash
ls -la data/live_capture/<race_id>/
python3 -c "import gzip,json; print(sum(1 for _ in gzip.open('data/live_capture/<race_id>/live-feed.jsonl.gz','rt')))"
```

### Offline tests

`python src/test_live_feed_poller.py` — no network, no launchd/pmset touched;
exercises `is_finished`, `poll()`, and `autodetect_race_id` against mocked
data.

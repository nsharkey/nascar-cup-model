---
title: "NASCAR Cup Series Track & Configuration Audit"
research_cutoff: "2026-07-19"
core_scope: "Points-paying NASCAR Cup Series races, 2015 through full 2026 scheduled slate"
configurations: 43
completed_races_2015_2025: 396
scheduled_races_2026: 36
completed_2026_through_cutoff: 20
primary_use: "DFS, betting, race prediction, driver evaluation, strategy and knowledge-base ingestion"
evidence_policy: "Zero-trust: stable source IDs, evidence labels, confidence, sample/era caveats"
version: "1.0"
---

# NASCAR Cup Series Track & Configuration Audit (2015-2026)

## Reader contract

This file is designed for a separate zero-trust NASCAR project. It distinguishes sourced facts from calculations and analyst judgment. Every track/configuration has a stable `track_id`; every source has a stable `source_id`. The companion CSV and JSON files preserve the same identifiers.

**Evidence labels**

- **Verified Fact (VF):** directly supported by a cited primary or high-quality secondary source.
- **Calculated Result (CR):** derived from listed schedules/data with the method stated.
- **Strong Inference (SI):** a reasoned interpretation supported by track geometry, observed racing mechanisms or established analytics practice.
- **Working Hypothesis (WH):** useful idea that requires empirical testing.

**Confidence labels:** High, Medium-High, Medium, Low. Confidence applies to the stated proposition, not to the reputation of a driver or track.

> **Scope boundary:** Only points-paying Cup races are counted and analyzed as the primary event sample. The Clash, All-Star Race/Open, Daytona qualifying races and other exhibitions were deliberately deferred—not accidentally omitted—because their fields, formats, incentives and lengths can distort ordinary points-race tendencies. North Wilkesboro non-points races are mentioned only as weak context before its 2026 points return. Dover’s 2026 All-Star event is likewise excluded from points counts.

## Executive findings

- **[Calculated Result | High]** The audit contains 43 materially distinct Cup track configurations across the 2015-2026 schedule universe. This is larger than a facility count because reconfigurations and alternate layouts are split.
- **[Calculated Result | High]** The schedule audit covers 432 points-race slots: 396 completed races from 2015-2025 plus all 36 scheduled 2026 points races. Through July 12, 2026, 20 of the 36 scheduled 2026 races had been completed; North Wilkesboro was next on July 19.
- **[Strong Inference | High]** For predictive work, physical configuration and rules package must be separate keys. A facility-name-only model will create severe leakage/misclassification at Atlanta, Bristol, Charlotte, COTA, Indianapolis, Phoenix, Sonoma, Texas and Kentucky.
- **[Strong Inference | High]** The best track buckets are hierarchical rather than mutually exclusive: geometry/surface family first, then tire-wear and track-position regime, then rules/tire/event-format overlays.
- **[Strong Inference | High]** DFS scoring increases the value of lap count and dominator concentration; betting increases the value of calibrated uncertainty, correlation and market-specific settlement. A single universal “track rating” is therefore inferior to task-specific features.
- **[Working Hypothesis | Medium]** Surface aging at post-2022 Atlanta may gradually move the venue from pure condensed drafting toward a unique hybrid with more lift, tire falloff and handling separation. This should be tested race by race rather than assumed linear.
- **[Working Hypothesis | Medium]** The 2026 750-hp package at road courses and ovals under 1.5 miles is a broad regime break. Models should partially reset coefficients for throttle control, tire degradation and passing rather than applying a simple recency weight.

## Methodology and limitations

### Universe construction

1. Annual points schedules/results were audited for 2015-2025 using Jayski archives (S012-S022), then the complete 2026 scheduled slate was added from NASCAR (S001-S002).
2. A new configuration key was created when layout, surface, banking, racing width or start/finish/restart geometry materially changed. Rules-package changes remain separate era overlays rather than creating dozens of physical track IDs.
3. Basic specifications were cross-checked against NASCAR’s track directory and RotoWire (S003-S004), with official change reports used for major splits.
4. Event counts are calculated from the schedule mapping embedded in the companion JSON.

### What is and is not empirical in Version 1.0

Physical specifications and schedule counts are sourced/calculated. The 1-10 track scores are **structural priors**, explicitly labeled Working Hypotheses; they are not presented as measured passing, tire or crash rates. This choice avoids manufacturing false precision where a full licensed loop-data extract was not directly available in the research environment. The report includes an exact empirical-calibration plan using NASCAR loop data, FASTLAP/Lap Raptor concepts and the documented `nascaR.data` fields (S005-S008).

### Important limitations

- Race results are not independent observations: driver, team, package, tire, weather, stage rules and playoff incentives co-move.
- Raw pass counts can be misleading at drafting tracks because lane oscillations are not equivalent to independent overtakes.
- Small-sample configurations—especially one-off or new circuits—must borrow strength from hierarchical families.
- Same facility does not imply same track; same family does not imply interchangeable coefficients.
- The 2026 schedule is complete in scope, but races after July 12 were future at the cutoff. Future-event behavior is therefore prior-based, not result-based.

## Schedule audit

| Year | Points events | Distinct configuration keys | Evidence |
| --- | --- | --- | --- |
| 2015 | 36 | 23 | S012 |
| 2016 | 36 | 23 | S013 |
| 2017 | 36 | 23 | S014 |
| 2018 | 36 | 25 | S015 |
| 2019 | 36 | 24 | S016 |
| 2020 | 36 | 22 | S017 |
| 2021 | 36 | 26 | S018 |
| 2022 | 36 | 27 | S019 |
| 2023 | 36 | 27 | S020 |
| 2024 | 36 | 26 | S021 |
| 2025 | 36 | 27 | S022 |
| 2026 | 36 | 27 | S001/S002 |

**[CR | High]** Total scheduled slots in scope: **432**. Completed 2015-2025: **396**. 2026 scheduled: **36**. Completed through July 12, 2026: **20** (S041); 16 remained scheduled as of the July 19 cutoff.

## Track-family taxonomy

The taxonomy is deliberately hierarchical. `primary_family` captures geometry/racing mechanism; `secondary_family` captures the more actionable subtype. Tire and track-position priors then permit similarity across family boundaries without pretending that all 1.5-mile tracks or all road courses are identical.

| Primary family | Configuration count |
| --- | --- |
| Condensed drafting speedway | 1 |
| Dirt oval | 1 |
| Drafting superspeedway | 2 |
| Flat short oval | 4 |
| High-banked compact oval | 3 |
| High-speed intermediate | 2 |
| Hybrid road course | 4 |
| Intermediate oval | 11 |
| Large flat oval | 2 |
| Permanent road course | 7 |
| Short oval | 4 |
| Street course | 2 |

### Recommended modeling buckets

- **Drafting superspeedways:** Daytona and Talladega. Historical plate era and modern tapered-spacer package must be flagged.
- **Condensed drafting hybrid:** post-2022 Atlanta. It borrows pack-racing logic but should retain a unique-track random effect.
- **Worn/multi-groove intermediates:** Darlington, Homestead, Chicagoland, old Atlanta and Auto Club. Emphasize tire falloff and lane adaptability.
- **Conventional/high-speed intermediates:** Kansas, Las Vegas, Charlotte, Michigan and era-specific Texas/Kentucky. Split by surface age and passing regime.
- **Large flat/unique ovals:** Indianapolis and Pocono, with Michigan as a partial high-speed donor. Emphasize strategy, exit speed and clean air.
- **High-banked compact concrete:** Bristol, Dover and Nashville. Similar load/rhythm concepts, but materially different lengths and traffic.
- **Flat/asymmetric short ovals:** Martinsville, Richmond, Phoenix, New Hampshire, Gateway, Iowa and North Wilkesboro. Use subfeatures for tire wear, corner symmetry and progressive banking.
- **Permanent road courses:** split high-speed flowing (Watkins Glen/Road America) from technical/tire-wear (Sonoma/COTA/Mexico).
- **Hybrid/street courses:** Charlotte Roval, Indianapolis road, Daytona road, Chicago and San Diego. Incident and restart models need more weight than at permanent courses.
- **Dirt:** Bristol dirt is a retired one-off micro-regime and should not donate directly to concrete Bristol.

## Rules and chronology overlays

### Recommended era keys

| Era | Suggested key | Modeling implication |
| --- | --- | --- |
| 2015 | gen6_2015_725hp | Horsepower reduction versus prior Gen-6 baseline; keep separate when older data are added. |
| 2016-2018 | gen6_low_downforce | Lower-downforce development; Phoenix start/finish splits in fall 2018. |
| 2019-2021 | gen6_2019_package | 550-hp/high-downforce package at many larger ovals; superspeedways transitioned from plates to tapered spacers. |
| 2022 | nextgen_launch | Next Gen baseline; Atlanta physical reconfiguration begins. |
| 2023-2025 | nextgen_low_downforce_short_road | Short-track/road-course aero revisions plus evolving tire strategies. |
| 2026 | nextgen_750hp_sub15_road | 750 hp at road courses and ovals under 1.5 miles; broad coefficient-reset candidate. |

**[VF | High]** NASCAR retired traditional restrictor plates after the 2019 Daytona 500 and used tapered spacers for subsequent Daytona/Talladega superspeedway packages (S036-S037). Therefore, “plate track” is acceptable historical shorthand but is technically wrong for current races.

**[VF | High]** In 2026, NASCAR increased target horsepower to 750 at all road courses and ovals shorter than 1.5 miles, including Phoenix, Darlington, Martinsville, Bristol, Nashville, North Wilkesboro, Iowa, Richmond, New Hampshire and Gateway (S039). This is not a cosmetic change: it should be an explicit model era.

## Master configuration table

| track_id | Facility | Configuration | Miles | Shape | Surface | Road? | Primary family | 2015-25 completed | 2026 completed | 2026 future | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daytona_oval | Daytona International Speedway | 2.5-mile oval | 2.5 | high-banked tri-oval | asphalt | False | Drafting superspeedway | 22 | 1 | 1 | High |
| talladega_oval | Talladega Superspeedway | 2.66-mile oval | 2.66 | high-banked tri-oval | asphalt | False | Drafting superspeedway | 22 | 1 | 1 | High |
| atlanta_pre_2022 | Atlanta Motor Speedway | pre-2022 1.54-mile oval | 1.54 | quad-oval | aged asphalt | False | Intermediate oval | 8 | 0 | 0 | High |
| atlanta_post_2022 | EchoPark Speedway (Atlanta) | 2022+ 1.54-mile drafting oval | 1.54 | narrow high-banked quad-oval | asphalt | False | Condensed drafting speedway | 8 | 2 | 0 | High |
| auto_club_2mi | Auto Club Speedway | 2.0-mile D-oval | 2.0 | wide D-oval | aged asphalt | False | High-speed intermediate | 8 | 0 | 0 | High |
| charlotte_oval | Charlotte Motor Speedway | 1.5-mile oval | 1.5 | quad-oval | asphalt | False | Intermediate oval | 15 | 1 | 0 | High |
| chicagoland_oval | Chicagoland Speedway | 1.5-mile oval | 1.5 | tri-oval | aged asphalt | False | Intermediate oval | 5 | 1 | 0 | Medium-High |
| darlington | Darlington Raceway | 1.366-mile egg-shaped oval | 1.366 | asymmetrical egg-shaped oval | highly abrasive asphalt | False | Intermediate oval | 18 | 1 | 1 | High |
| homestead | Homestead-Miami Speedway | 1.5-mile oval | 1.5 | progressive-banked oval | abrasive asphalt | False | Intermediate oval | 11 | 0 | 1 | High |
| kansas | Kansas Speedway | 1.5-mile oval | 1.5 | tri-oval | asphalt | False | Intermediate oval | 22 | 1 | 1 | High |
| kentucky_pre_2016 | Kentucky Speedway | pre-2016 1.5-mile oval | 1.5 | tri-oval | aged/bumpy asphalt | False | Intermediate oval | 1 | 0 | 0 | High facts / Low predictive |
| kentucky_post_2016 | Kentucky Speedway | 2016-2020 reconfigured oval | 1.5 | asymmetric tri-oval | repaved asphalt | False | Intermediate oval | 5 | 0 | 0 | High |
| las_vegas | Las Vegas Motor Speedway | 1.5-mile oval | 1.5 | tri-oval | asphalt | False | Intermediate oval | 19 | 1 | 1 | High |
| michigan | Michigan International Speedway | 2.0-mile D-oval | 2.0 | wide D-oval | asphalt | False | High-speed intermediate | 17 | 1 | 0 | High |
| texas_pre_2017 | Texas Motor Speedway | pre-2017 1.5-mile oval | 1.5 | quad-oval | aged asphalt | False | Intermediate oval | 4 | 0 | 0 | High |
| texas_post_2017 | Texas Motor Speedway | 2017+ asymmetric 1.5-mile oval | 1.5 | asymmetric quad-oval | repaved asphalt | False | Intermediate oval | 13 | 1 | 0 | High |
| indianapolis_oval | Indianapolis Motor Speedway | 2.5-mile oval | 2.5 | rectangular oval | asphalt | False | Large flat oval | 8 | 0 | 1 | High |
| pocono | Pocono Raceway | 2.5-mile triangular oval | 2.5 | three-turn triangular oval | asphalt | False | Large flat oval | 18 | 1 | 0 | High |
| bristol_concrete | Bristol Motor Speedway | 0.533-mile concrete oval | 0.533 | high-banked oval | concrete | False | High-banked compact oval | 19 | 1 | 1 | High |
| bristol_dirt | Bristol Motor Speedway | temporary dirt oval (2021-2023) | 0.533 | high-banked dirt-covered oval | temporary dirt over concrete | False | Dirt oval | 3 | 0 | 0 | High facts / Low generalization |
| dover | Dover Motor Speedway | 1.0-mile concrete oval | 1.0 | high-banked oval | concrete | False | High-banked compact oval | 17 | 0 | 0 | High |
| iowa | Iowa Speedway | 0.875-mile oval | 0.875 | D-shaped short oval | asphalt | False | Short oval | 2 | 0 | 1 | Medium-High |
| martinsville | Martinsville Speedway | 0.526-mile oval | 0.526 | paperclip oval | asphalt straights / concrete turns | False | Short oval | 22 | 1 | 1 | High |
| nashville | Nashville Superspeedway | 1.333-mile concrete oval | 1.333 | D-shaped oval | concrete | False | High-banked compact oval | 5 | 1 | 0 | High |
| new_hampshire | New Hampshire Motor Speedway | 1.058-mile oval | 1.058 | flat oval | asphalt | False | Flat short oval | 14 | 0 | 1 | High |
| north_wilkesboro | North Wilkesboro Speedway | 0.625-mile oval | 0.625 | asymmetrical short oval | aged asphalt | False | Short oval | 0 | 0 | 1 | High facts / Low points-sample |
| phoenix_pre_2018f | Phoenix Raceway | pre-November-2018 start/finish orientation | 1.0 | asymmetrical dogleg oval | asphalt | False | Flat short oval | 7 | 0 | 0 | High |
| phoenix_post_2018f | Phoenix Raceway | November 2018+ start/finish orientation | 1.0 | asymmetrical dogleg oval | asphalt | False | Flat short oval | 15 | 1 | 1 | High |
| richmond | Richmond Raceway | 0.75-mile oval | 0.75 | D-shaped short oval | asphalt | False | Short oval | 20 | 0 | 1 | High |
| wwt_gateway | World Wide Technology Raceway | 1.25-mile oval | 1.25 | egg-shaped oval | asphalt | False | Flat short oval | 4 | 0 | 1 | High |
| charlotte_roval_v1 | Charlotte Motor Speedway Roval | 2018-2023 road course | 2.32 | oval/road hybrid | asphalt | True | Hybrid road course | 6 | 0 | 0 | High |
| charlotte_roval_v2 | Charlotte Motor Speedway Roval | 2024+ reconfigured road course | 2.28 | oval/road hybrid | asphalt | True | Hybrid road course | 2 | 0 | 1 | High facts / Medium behavior |
| chicago_street | Chicago Street Course | 2.2-mile street course | 2.2 | temporary street circuit | mixed public-road asphalt/concrete | True | Street course | 3 | 0 | 0 | High facts / Medium priors |
| cota_full | Circuit of The Americas | 2021-2024 full course | 3.41 | permanent road course | asphalt | True | Permanent road course | 4 | 0 | 0 | High |
| cota_short | Circuit of The Americas | 2025+ shortened course | 2.4 | shortened permanent road course | asphalt | True | Permanent road course | 1 | 1 | 0 | High |
| daytona_road | Daytona International Speedway | 3.61-mile road course | 3.61 | oval/infield road course | asphalt | True | Hybrid road course | 2 | 0 | 0 | High facts / Low sample |
| indianapolis_road | Indianapolis Motor Speedway | 2.439-mile road course | 2.439 | oval/infield road course | asphalt | True | Hybrid road course | 3 | 0 | 0 | High |
| mexico_city | Autodromo Hermanos Rodriguez | 2.42-mile road course | 2.42 | permanent road course | asphalt | True | Permanent road course | 1 | 0 | 0 | High facts / Low sample |
| road_america | Road America | 4.048-mile road course | 4.048 | long natural-terrain road course | asphalt | True | Permanent road course | 2 | 0 | 0 | High facts / Low sample |
| san_diego_street | Qualcomm Circuit at Naval Base Coronado | 3.4-mile street/runway course | 3.4 | temporary street and runway circuit | mixed worn streets/runways | True | Street course | 0 | 1 | 0 | High facts / Low sample |
| sonoma_short | Sonoma Raceway | 1.99-mile chute layout | 1.99 | natural-terrain road course | asphalt | True | Permanent road course | 8 | 1 | 0 | High |
| sonoma_carousel | Sonoma Raceway | 2.52-mile carousel layout | 2.52 | natural-terrain road course | asphalt | True | Permanent road course | 2 | 0 | 0 | High facts / Low sample |
| watkins_glen | Watkins Glen International | 2.45-mile road course | 2.45 | high-speed natural-terrain road course | asphalt | True | Permanent road course | 10 | 1 | 0 | High |

## Structural prior scorecard

All scores below are **[WH] analyst priors**, 1=low and 10=high. They are deliberately machine-readable starting points, not claims of measured truth. Calibrate against loop/race data before using as production coefficients.

| track_id | Tire deg. | Track-pos. | Pass diff. | Attrition | Restart vol. | Pit importance | Qualifying | Strategy flex. | DFS dominator | Finish var. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| daytona_oval | 2 | 3 | 2 | 10 | 10 | 6 | 2 | 8 | 3 | 10 |
| talladega_oval | 2 | 2 | 1 | 10 | 10 | 6 | 2 | 9 | 2 | 10 |
| atlanta_pre_2022 | 10 | 4 | 4 | 5 | 6 | 7 | 5 | 7 | 8 | 6 |
| atlanta_post_2022 | 4 | 5 | 3 | 9 | 10 | 6 | 3 | 8 | 4 | 9 |
| auto_club_2mi | 8 | 4 | 3 | 6 | 8 | 7 | 5 | 8 | 7 | 7 |
| charlotte_oval | 5 | 7 | 6 | 4 | 7 | 8 | 7 | 6 | 8 | 4 |
| chicagoland_oval | 8 | 5 | 4 | 5 | 7 | 7 | 5 | 8 | 8 | 6 |
| darlington | 10 | 6 | 5 | 7 | 7 | 8 | 6 | 8 | 8 | 7 |
| homestead | 9 | 5 | 4 | 5 | 7 | 7 | 5 | 8 | 8 | 6 |
| kansas | 7 | 6 | 4 | 4 | 8 | 7 | 6 | 7 | 8 | 5 |
| kentucky_pre_2016 | 6 | 7 | 6 | 5 | 6 | 7 | 7 | 6 | 8 | 5 |
| kentucky_post_2016 | 3 | 9 | 8 | 4 | 7 | 8 | 9 | 4 | 8 | 4 |
| las_vegas | 6 | 7 | 5 | 4 | 7 | 7 | 7 | 6 | 8 | 4 |
| michigan | 4 | 7 | 6 | 5 | 8 | 7 | 7 | 7 | 8 | 5 |
| texas_pre_2017 | 7 | 6 | 5 | 5 | 7 | 7 | 6 | 6 | 8 | 5 |
| texas_post_2017 | 4 | 9 | 9 | 6 | 7 | 8 | 9 | 4 | 8 | 5 |
| indianapolis_oval | 3 | 9 | 9 | 6 | 8 | 9 | 9 | 9 | 7 | 7 |
| pocono | 4 | 8 | 7 | 5 | 8 | 9 | 8 | 9 | 7 | 6 |
| bristol_concrete | 8 | 7 | 6 | 8 | 10 | 8 | 7 | 7 | 9 | 7 |
| bristol_dirt | 6 | 5 | 4 | 9 | 10 | 5 | 4 | 7 | 6 | 10 |
| dover | 7 | 8 | 7 | 7 | 8 | 8 | 8 | 6 | 9 | 6 |
| iowa | 8 | 6 | 5 | 6 | 9 | 7 | 6 | 8 | 8 | 7 |
| martinsville | 5 | 8 | 8 | 7 | 10 | 8 | 8 | 8 | 8 | 7 |
| nashville | 6 | 8 | 7 | 6 | 9 | 8 | 8 | 7 | 8 | 7 |
| new_hampshire | 6 | 8 | 8 | 5 | 9 | 8 | 8 | 8 | 8 | 6 |
| north_wilkesboro | 9 | 7 | 7 | 6 | 9 | 7 | 7 | 8 | 8 | 7 |
| phoenix_pre_2018f | 5 | 8 | 8 | 4 | 7 | 8 | 8 | 7 | 8 | 5 |
| phoenix_post_2018f | 5 | 8 | 8 | 4 | 9 | 8 | 8 | 7 | 8 | 5 |
| richmond | 8 | 6 | 6 | 4 | 7 | 8 | 6 | 9 | 8 | 5 |
| wwt_gateway | 5 | 8 | 8 | 6 | 9 | 8 | 8 | 8 | 8 | 6 |
| charlotte_roval_v1 | 4 | 8 | 7 | 9 | 10 | 9 | 8 | 9 | 6 | 9 |
| charlotte_roval_v2 | 4 | 8 | 7 | 9 | 10 | 9 | 8 | 9 | 6 | 9 |
| chicago_street | 3 | 9 | 9 | 9 | 10 | 9 | 9 | 9 | 6 | 10 |
| cota_full | 5 | 6 | 4 | 7 | 10 | 9 | 7 | 9 | 6 | 8 |
| cota_short | 7 | 6 | 4 | 7 | 10 | 8 | 7 | 8 | 6 | 8 |
| daytona_road | 4 | 7 | 6 | 7 | 9 | 9 | 8 | 9 | 6 | 8 |
| indianapolis_road | 4 | 7 | 6 | 8 | 10 | 9 | 8 | 9 | 6 | 9 |
| mexico_city | 6 | 7 | 6 | 7 | 9 | 9 | 8 | 9 | 7 | 8 |
| road_america | 4 | 6 | 5 | 7 | 8 | 9 | 7 | 10 | 6 | 8 |
| san_diego_street | 7 | 7 | 6 | 8 | 9 | 9 | 8 | 9 | 6 | 8 |
| sonoma_short | 8 | 7 | 7 | 6 | 8 | 9 | 8 | 9 | 7 | 7 |
| sonoma_carousel | 7 | 7 | 7 | 6 | 8 | 9 | 8 | 9 | 7 | 7 |
| watkins_glen | 4 | 7 | 5 | 6 | 9 | 8 | 8 | 8 | 7 | 7 |

## Detailed track/configuration profiles

### EchoPark Speedway (Atlanta) — 2022+ 1.54-mile drafting oval (`atlanta_post_2022`)

**[VF | High] Physical profile:** 1.54 miles; narrow high-banked quad-oval; asphalt; oval; turns: 4; banking/context: 28 deg turns. Sources: S001;S002;S003;S023.

**[CR | High] Scope sample:** 8 completed points races in 2015-2025; 2 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Between 2021 and 2022, banking increased 24 to 28 degrees and width narrowed 55 to 40 feet, creating NASCAR’s third drafting-style track. Surface aging may gradually increase lift and tire management.

**[SI | High] Racing mechanism:** This is not simply a small Daytona. The shorter lap, narrow surface and tighter radius compress reaction time, increase blockage and make track position more persistent when the field becomes two-wide. As the surface ages, the track may migrate toward a hybrid state where handling and tire falloff matter earlier.

**[SI | High] DFS/betting application:** DFS: balance place differential with some laps-led exposure because leaders can defend more effectively than at Talladega. Betting: separate early-era 2022-23 data from later surface-aging races and model crash risk plus handling sensitivity jointly.

**Comparable-track prior:** Daytona; Talladega; unique one-of-one. **Calculated structural neighbors:** daytona_oval (37.1); talladega_oval (36.1).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 5/10; passing difficulty 3/10; attrition 9/10; restart volatility 10/10; pit-road importance 6/10; qualifying importance 3/10; strategy flexibility 8/10; DFS dominator concentration 4/10; finish variance 9/10.

### Bristol Motor Speedway — temporary dirt oval (2021-2023) (`bristol_dirt`)

**[VF | High facts / Low generalization] Physical profile:** 0.533 miles; high-banked dirt-covered oval; temporary dirt over concrete; oval; turns: 4; banking/context: variable after dirt installation. Sources: S018;S019;S020.

**[CR | High] Scope sample:** 3 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Three points races, 2021-2023. Surface preparation, weather and format materially changed the race environment.

**[SI | High facts / Low generalization] Racing mechanism:** This was a surface-state event more than a stable track archetype. Visibility, moisture, groove migration and dirt-specific car control mattered, but Cup dirt experience and non-Cup dirt credentials did not transfer one-for-one.

**[SI | High facts / Low generalization] DFS/betting application:** DFS/betting: treat as a retired micro-regime with tiny sample and extreme uncertainty. Historical results should not influence concrete Bristol projections.

**Comparable-track prior:** No strong Cup comparable; dirt experience only partial. **Calculated structural neighbors:** None within same structural supergroup.

**[WH] Prior vector:** tire degradation 6/10; track-position premium 5/10; passing difficulty 4/10; attrition 9/10; restart volatility 10/10; pit-road importance 5/10; qualifying importance 4/10; strategy flexibility 7/10; DFS dominator concentration 6/10; finish variance 10/10.

### Daytona International Speedway — 2.5-mile oval (`daytona_oval`)

**[VF | High] Physical profile:** 2.5 miles; high-banked tri-oval; asphalt; oval; turns: 4; banking/context: 31 deg turns; 18 deg tri-oval. Sources: S003;S004;S036;S037.

**[CR | High] Scope sample:** 22 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Traditional restrictor-plate venue through the 2019 Daytona 500; tapered-spacer superspeedway packages thereafter. Treat each major package revision as an era break.

**[SI | High] Racing mechanism:** Pack position is a transient state rather than a stable speed ranking. Lane energy, manufacturer cooperation, pit-cycle drafting partners and avoidance probability often matter more than five-lap isolated speed. Daytona is more handling-sensitive than Talladega because its corners are tighter and the surface/bumps can separate cars late in runs.

**[SI | High] DFS/betting application:** DFS: place differential and survival generally dominate conventional dominator logic, but front-row cars can still score early laps led. Betting: demand a large uncertainty premium; matchup and finishing-position markets should incorporate correlated wreck exposure rather than independent driver risk.

**Comparable-track prior:** Talladega; Atlanta post-2022. **Calculated structural neighbors:** talladega_oval (92.9); atlanta_post_2022 (37.1).

**[WH] Prior vector:** tire degradation 2/10; track-position premium 3/10; passing difficulty 2/10; attrition 10/10; restart volatility 10/10; pit-road importance 6/10; qualifying importance 2/10; strategy flexibility 8/10; DFS dominator concentration 3/10; finish variance 10/10.

### Talladega Superspeedway — 2.66-mile oval (`talladega_oval`)

**[VF | High] Physical profile:** 2.66 miles; high-banked tri-oval; asphalt; oval; turns: 4; banking/context: 33 deg turns; 16.5 deg tri-oval. Sources: S003;S004;S036;S037.

**[CR | High] Scope sample:** 22 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Traditional restrictor-plate venue through 2018; first tapered-spacer superspeedway package in spring 2019.

**[SI | High] Racing mechanism:** The width and long lap sustain multi-lane packs and make raw passing counts deceptively high: many passes are low-value oscillations inside a connected draft. The actionable unit is often lane/pack position entering late restarts, not cumulative green-flag passes.

**[SI | High] DFS/betting application:** DFS: maximize correlated upside carefully and avoid projecting multiple high-priced dominators. Betting: outright prices should be flatter than at any non-drafting oval; top-10 parlays are especially exposed to common-cause crash risk.

**Comparable-track prior:** Daytona; Atlanta post-2022. **Calculated structural neighbors:** daytona_oval (92.9); atlanta_post_2022 (36.1).

**[WH] Prior vector:** tire degradation 2/10; track-position premium 2/10; passing difficulty 1/10; attrition 10/10; restart volatility 10/10; pit-road importance 6/10; qualifying importance 2/10; strategy flexibility 9/10; DFS dominator concentration 2/10; finish variance 10/10.

### New Hampshire Motor Speedway — 1.058-mile oval (`new_hampshire`)

**[VF | High] Physical profile:** 1.058 miles; flat oval; asphalt; oval; turns: 4; banking/context: 2-7 deg variable. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 14 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** One annual points race since 2018. Wet-weather tire capability and 2026 horsepower can alter race evolution.

**[SI | High] Racing mechanism:** Low banking makes corner entry, center rotation and rear drive decisive. Passing comparable cars is difficult, so restart lane, pit sequence and short-run launch are strongly monetizable.

**[SI | High] DFS/betting application:** DFS: prioritize likely leaders and drivers with flat-track technique; place differential is capped when pace gaps are small. Betting: use a flat-track composite, but retain meaningful same-track weight because Loudon’s long corners are distinctive.

**Comparable-track prior:** Phoenix; Richmond; Gateway; Martinsville. **Calculated structural neighbors:** phoenix_post_2018f (94.7); wwt_gateway (94.3); phoenix_pre_2018f (92.7); iowa (38.9); north_wilkesboro (38.7).

**[WH] Prior vector:** tire degradation 6/10; track-position premium 8/10; passing difficulty 8/10; attrition 5/10; restart volatility 9/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 6/10.

### Phoenix Raceway — November 2018+ start/finish orientation (`phoenix_post_2018f`)

**[VF | High] Physical profile:** 1.0 miles; asymmetrical dogleg oval; asphalt; oval; turns: 4; banking/context: 9-11 deg turns. Sources: S003;S004;S015;S016;S017;S018;S019;S020;S021;S022;S026;S039;S001.

**[CR | High] Scope sample:** 15 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Start/finish moved to the former Turn 2 for the November 2018 race; championship finale since 2020. 2026 uses 750 hp.

**[SI | High] Racing mechanism:** The relocated line makes the dogleg a first-lap/restart decision point, amplifying lane choice and launch. Long-run passing remains difficult, so clean air and pit execution can outweigh small speed differences.

**[SI | High] DFS/betting application:** DFS: leader exposure is important; championship races may change strategy/incentives but not the underlying geometry. Betting: use post-2018 data preferentially and treat 2026 horsepower/tire changes as a new sub-era.

**Comparable-track prior:** New Hampshire; Richmond; Gateway. **Calculated structural neighbors:** phoenix_pre_2018f (97.8); new_hampshire (94.7); wwt_gateway (91.4); richmond (38.5); iowa (38.4).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 8/10; passing difficulty 8/10; attrition 4/10; restart volatility 9/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 5/10.

### Phoenix Raceway — pre-November-2018 start/finish orientation (`phoenix_pre_2018f`)

**[VF | High] Physical profile:** 1.0 miles; asymmetrical dogleg oval; asphalt; oval; turns: 4; banking/context: 9-11 deg turns. Sources: S004;S012;S013;S014;S015;S026.

**[CR | High] Scope sample:** 7 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Start/finish line remained on the former frontstretch through spring 2018. Physical corners were similar, but restart geometry and lap segmentation changed in fall 2018.

**[SI | High] Racing mechanism:** The dogleg allowed line-cutting and shortcut geometry, but the old restart location changed when the most chaotic section appeared within a lap. Use as a related but distinct era rather than discarding it.

**[SI | High] DFS/betting application:** DFS/betting: apply decay to 2015-spring 2018 data and avoid combining raw restart/lead-change statistics with the post-relocation era.

**Comparable-track prior:** New Hampshire; Richmond. **Calculated structural neighbors:** phoenix_post_2018f (97.8); new_hampshire (92.7); wwt_gateway (89.6); richmond (38.9); iowa (38.1).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 8/10; passing difficulty 8/10; attrition 4/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 5/10.

### World Wide Technology Raceway — 1.25-mile oval (`wwt_gateway`)

**[VF | High] Physical profile:** 1.25 miles; egg-shaped oval; asphalt; oval; turns: 4; banking/context: 11 deg turns 1-2; 9 deg turns 3-4. Sources: S003;S004;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 4 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points debut in 2022; 2026 uses 750 hp because the oval is under 1.5 miles.

**[SI | High] Racing mechanism:** Different corner radii force compromise and reward braking stability plus drive off. Passing is difficult in steady state, so pit sequencing, restarts and mechanical reliability can dominate finishing order.

**[SI | High] DFS/betting application:** DFS: likely leaders and track-position plays are favored; deep place differential needs a meaningful speed mismatch. Betting: 2026 power is a regime break and may increase wheelspin/tire management, reducing direct portability of 2022-25 averages.

**Comparable-track prior:** New Hampshire; Phoenix; Pocono. **Calculated structural neighbors:** new_hampshire (94.3); phoenix_post_2018f (91.4); phoenix_pre_2018f (89.6); iowa (38.3); north_wilkesboro (38.1).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 8/10; passing difficulty 8/10; attrition 6/10; restart volatility 9/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 6/10.

### Bristol Motor Speedway — 0.533-mile concrete oval (`bristol_concrete`)

**[VF | High] Physical profile:** 0.533 miles; high-banked oval; concrete; oval; turns: 4; banking/context: 24-28 deg variable. Sources: S003;S004;S006;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 19 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** The spring event was dirt-covered in 2021-23; those races are separate. Tire/resin/traction-compound conditions can create event-specific regime shifts.

**[SI | High] Racing mechanism:** Bristol combines traffic density, rhythm, tire behavior and contact. Laps led and fastest laps can concentrate heavily, but a dominant car has unusually high exposure to lapped traffic and restart incidents.

**[SI | High] DFS/betting application:** DFS: dominators are essential because of lap volume; roster construction should usually include multiple plausible leaders. Betting: practice long runs, tire notes and groove-development reports are higher value than season-long averages.

**Comparable-track prior:** Dover; Nashville; North Wilkesboro (partial). **Calculated structural neighbors:** dover (83.8); nashville (79.4); martinsville (39.8); north_wilkesboro (31.2); iowa (30.6).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 7/10; passing difficulty 6/10; attrition 8/10; restart volatility 10/10; pit-road importance 8/10; qualifying importance 7/10; strategy flexibility 7/10; DFS dominator concentration 9/10; finish variance 7/10.

### Dover Motor Speedway — 1.0-mile concrete oval (`dover`)

**[VF | High] Physical profile:** 1.0 miles; high-banked oval; concrete; oval; turns: 4; banking/context: 24 deg turns; 9 deg straights. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 17 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Dover’s 2026 Cup date is the non-points All-Star event and is intentionally excluded from the primary event count.

**[SI | High] Racing mechanism:** Elevation change into and out of the corners creates a sustained-load rhythm problem. Track position and long-run balance matter, while concrete consistency does not eliminate rubber and tire-condition effects.

**[SI | High] DFS/betting application:** DFS: high dominator concentration and meaningful fastest-lap upside; prioritize cars likely to control long green runs. Betting: same-track and Bristol/Nashville concrete skill is useful, but no points race is scheduled in 2026.

**Comparable-track prior:** Bristol concrete; Nashville. **Calculated structural neighbors:** nashville (88.2); bristol_concrete (83.8); martinsville (38.5); new_hampshire (31.2); phoenix_pre_2018f (31.1).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 8/10; passing difficulty 7/10; attrition 7/10; restart volatility 8/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 6/10; DFS dominator concentration 9/10; finish variance 6/10.

### Nashville Superspeedway — 1.333-mile concrete oval (`nashville`)

**[VF | High] Physical profile:** 1.333 miles; D-shaped oval; concrete; oval; turns: 4; banking/context: 14 deg turns. Sources: S003;S004;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 5 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points debut in 2021. At 1.333 miles it falls below the 1.5-mile threshold and receives the 750-hp package in 2026.

**[SI | High] Racing mechanism:** Nashville blends concrete consistency, relatively narrow preferred lanes and intermediate-like speed. Restarts and pit cycles can create more passing than steady-state traffic does.

**[SI | High] DFS/betting application:** DFS: dominator candidates and clean-air speed carry large weight; deep value needs credible long-run pace. Betting: 2026 horsepower is a regime change, so shrink prior results and watch tire falloff/off-throttle time.

**Comparable-track prior:** Dover; Gateway; Darlington (power bracket only). **Calculated structural neighbors:** dover (88.2); bristol_concrete (79.4); martinsville (38.2); wwt_gateway (31.6); new_hampshire (31.3).

**[WH] Prior vector:** tire degradation 6/10; track-position premium 8/10; passing difficulty 7/10; attrition 6/10; restart volatility 9/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 7/10.

### Auto Club Speedway — 2.0-mile D-oval (`auto_club_2mi`)

**[VF | High] Physical profile:** 2.0 miles; wide D-oval; aged asphalt; oval; turns: 4; banking/context: 14 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S019;S020.

**[CR | High] Scope sample:** 8 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points races in scope through 2023. Proposed future short-track redevelopment is not included because it is not on the 2026 points schedule.

**[SI | High] Racing mechanism:** Width, seams and surface age created multiple usable lanes and substantial speed variation across a fuel run. Compared with Michigan, Fontana placed more emphasis on tire life, lane searching and traffic management.

**[SI | High] DFS/betting application:** DFS: place differential and long-run ceiling could coexist; a fast car starting deep was less trapped than at narrow intermediates. Betting: historical Auto Club performance transfers better to worn multi-groove tracks than to current drafting Atlanta.

**Comparable-track prior:** Michigan; Homestead; old Atlanta; Chicagoland. **Calculated structural neighbors:** michigan (84.1); chicagoland_oval (39.0); homestead (38.8); atlanta_pre_2022 (38.6); kansas (38.1).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 4/10; passing difficulty 3/10; attrition 6/10; restart volatility 8/10; pit-road importance 7/10; qualifying importance 5/10; strategy flexibility 8/10; DFS dominator concentration 7/10; finish variance 7/10.

### Michigan International Speedway — 2.0-mile D-oval (`michigan`)

**[VF | High] Physical profile:** 2.0 miles; wide D-oval; asphalt; oval; turns: 4; banking/context: 18 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 17 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Moved from two races to one after 2020; package dependence is high because horsepower/drag strongly affect passing.

**[SI | High] Racing mechanism:** Michigan’s width creates theoretical options, but high speed and aerodynamic wake can still make runs difficult to complete. Fuel mileage and restart lane selection can have outsized impact because long green runs produce limited organic reshuffling.

**[SI | High] DFS/betting application:** DFS: dominators matter, but fuel strategy can redistribute late laps led. Betting: emphasize engine/aero platform, restart execution and fuel-window probability; avoid treating Auto Club as a perfect comparable because tire wear differed.

**Comparable-track prior:** Auto Club; Pocono; Kansas. **Calculated structural neighbors:** auto_club_2mi (84.1); kentucky_pre_2016 (39.1); charlotte_oval (39.0); las_vegas (38.8); kansas (38.6).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 7/10; passing difficulty 6/10; attrition 5/10; restart volatility 8/10; pit-road importance 7/10; qualifying importance 7/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 5/10.

### Charlotte Motor Speedway Roval — 2018-2023 road course (`charlotte_roval_v1`)

**[VF | High] Physical profile:** 2.32 miles; oval/road hybrid; asphalt; road/street/hybrid course; turns: 17; banking/context: oval banking plus flat infield. Sources: S004;S015;S016;S017;S018;S019;S020;S028.

**[CR | High] Scope sample:** 6 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Initial Cup Roval era, 2018-2023. Reconfigured for 2024, so do not pool blindly.

**[SI | High] Racing mechanism:** The Roval combines high-speed oval commitment with low-speed infield braking and narrow chicanes. Stage and late-caution dynamics create incident clusters that are not explained by generic road-course pace.

**[SI | High] DFS/betting application:** DFS: qualifying, place differential and incident-adjusted ceiling all matter; dominator scoring is lower than on ovals but fastest laps can concentrate. Betting: price restart/chicane survival and road-course skill separately.

**Comparable-track prior:** Indianapolis road; Daytona road; Chicago street. **Calculated structural neighbors:** charlotte_roval_v2 (99.2); indianapolis_road (94.6); daytona_road (75.5); mexico_city (39.7); watkins_glen (39.1).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 8/10; passing difficulty 7/10; attrition 9/10; restart volatility 10/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 9/10.

### Charlotte Motor Speedway Roval — 2024+ reconfigured road course (`charlotte_roval_v2`)

**[VF | High facts / Medium behavior] Physical profile:** 2.28 miles; oval/road hybrid; asphalt; road/street/hybrid course; turns: 17; banking/context: oval banking plus flat infield. Sources: S003;S021;S022;S028;S039;S001.

**[CR | High] Scope sample:** 2 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Reconfigured for 2024; official entry length 2.28 miles and 17 turns. 2026 uses 750 hp.

**[SI | High facts / Medium behavior] Racing mechanism:** Small geometry changes alter braking sequences and restart flow enough to merit a separate configuration. Historical Roval skill remains relevant, but corner-specific incident rates and lap-time models need re-estimation.

**[SI | High facts / Medium behavior] DFS/betting application:** DFS/betting: use v1 results as a shrunk driver-skill prior, not as identical-track data. Give practice and qualifying a high information value because the v2 points sample is small.

**Comparable-track prior:** Charlotte Roval v1; Indianapolis road; Chicago street. **Calculated structural neighbors:** charlotte_roval_v1 (99.2); indianapolis_road (93.9); daytona_road (75.0); mexico_city (39.6); watkins_glen (39.0).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 8/10; passing difficulty 7/10; attrition 9/10; restart volatility 10/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 9/10.

### Daytona International Speedway — 3.61-mile road course (`daytona_road`)

**[VF | High facts / Low sample] Physical profile:** 3.61 miles; oval/infield road course; asphalt; road/street/hybrid course; turns: 14; banking/context: high-banked oval sections. Sources: S017;S018.

**[CR | High] Scope sample:** 2 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Two points races in scope: 2020 and 2021. No current points date.

**[SI | High facts / Low sample] Racing mechanism:** High-speed banked sections, bus-stop braking and infield traction created a unique hybrid. Tiny sample and changing car generations make track-specific averages fragile.

**[SI | High facts / Low sample] DFS/betting application:** DFS/betting: use as a weak donor for Roval/Indy road-course skills, not a standalone predictive database.

**Comparable-track prior:** Charlotte Roval; Indianapolis road. **Calculated structural neighbors:** indianapolis_road (78.9); charlotte_roval_v1 (75.5); charlotte_roval_v2 (75.0); cota_full (39.9); road_america (39.3).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 7/10; passing difficulty 6/10; attrition 7/10; restart volatility 9/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 8/10.

### Indianapolis Motor Speedway — 2.439-mile road course (`indianapolis_road`)

**[VF | High] Physical profile:** 2.439 miles; oval/infield road course; asphalt; road/street/hybrid course; turns: 14; banking/context: mostly flat. Sources: S018;S019;S020.

**[CR | High] Scope sample:** 3 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points races 2021-2023; oval returned in 2024.

**[SI | High] Racing mechanism:** Long straights into heavy braking created dive-bomb opportunities and restart pileups. Track limits, curb geometry and incident management were at least as important as clean-lap speed.

**[SI | High] DFS/betting application:** DFS: road-course specialists carried ceiling, but attrition widened viable place-differential plays. Betting: do not carry these results into the Brickyard oval; use only for other braking-heavy road courses.

**Comparable-track prior:** Charlotte Roval; Daytona road; COTA short. **Calculated structural neighbors:** charlotte_roval_v1 (94.6); charlotte_roval_v2 (93.9); daytona_road (78.9); mexico_city (40.5); watkins_glen (40.0).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 7/10; passing difficulty 6/10; attrition 8/10; restart volatility 10/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 9/10.

### Atlanta Motor Speedway — pre-2022 1.54-mile oval (`atlanta_pre_2022`)

**[VF | High] Physical profile:** 1.54 miles; quad-oval; aged asphalt; oval; turns: 4; banking/context: 24 deg turns. Sources: S004;S012;S013;S014;S015;S016;S017;S018;S023.

**[CR | High] Scope sample:** 8 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Configuration used through 2021; not comparable to the 2022+ drafting layout despite the same facility.

**[SI | High] Racing mechanism:** Old Atlanta rewarded throttle control, searching for multiple grooves and managing severe falloff. Long-run speed and driver adaptability carried more signal than short-run qualifying trim.

**[SI | High] DFS/betting application:** DFS: strong dominator potential and meaningful fastest-lap concentration; practice long-run averages and historical high-wear skill deserve heavy weight. Betting: upgrades drivers who preserve rear tire and move lanes; downgrade models that pool post-2022 results.

**Comparable-track prior:** Homestead; Darlington; Chicagoland; Auto Club. **Calculated structural neighbors:** homestead (95.0); chicagoland_oval (94.0); kansas (89.4); texas_pre_2017 (89.4); darlington (87.3).

**[WH] Prior vector:** tire degradation 10/10; track-position premium 4/10; passing difficulty 4/10; attrition 5/10; restart volatility 6/10; pit-road importance 7/10; qualifying importance 5/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 6/10.

### Charlotte Motor Speedway — 1.5-mile oval (`charlotte_oval`)

**[VF | High] Physical profile:** 1.5 miles; quad-oval; asphalt; oval; turns: 4; banking/context: 24 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 15 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Fall oval race replaced by the Roval beginning in 2018; the Coca-Cola 600’s distance is a material event-format modifier.

**[SI | High] Racing mechanism:** Charlotte is a balanced intermediate test: aerodynamic platform, traffic behavior, pit execution and changing day-to-night conditions all matter. The 600 creates more pit cycles and more opportunity for elite teams to recover, but also more mechanical and execution exposure.

**[SI | High] DFS/betting application:** DFS: dominator scoring is central because of lap count, especially in the 600; split exposure among plausible long-run leaders rather than overusing place differential. Betting: team depth, pit crew and adjustment quality deserve more weight than at shorter 400-mile intermediates.

**Comparable-track prior:** Las Vegas; Kansas; Texas; Kentucky post-2016. **Calculated structural neighbors:** las_vegas (96.8); kentucky_pre_2016 (94.7); texas_pre_2017 (91.8); kansas (90.0); kentucky_post_2016 (90.0).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 7/10; passing difficulty 6/10; attrition 4/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 7/10; strategy flexibility 6/10; DFS dominator concentration 8/10; finish variance 4/10.

### Chicagoland Speedway — 1.5-mile oval (`chicagoland_oval`)

**[VF | Medium-High] Physical profile:** 1.5 miles; tri-oval; aged asphalt; oval; turns: 4; banking/context: 18 deg turns. Sources: S004;S012;S013;S014;S015;S016;S035;S001;S002.

**[CR | High] Scope sample:** 5 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Hosted Cup through 2019 and returned to the points schedule in 2026. The long hiatus creates a surface/field-experience discontinuity.

**[SI | Medium-High] Racing mechanism:** Progressive banking and aging asphalt reward lane migration and tire management. The 2026 return should be treated as a new observation on an old geometry: historical driver skill is relevant, but setup priors need shrinkage because the car, tire and surface age changed during the absence.

**[SI | Medium-High] DFS/betting application:** DFS: long-run practice and driver high-line skill should be emphasized, with reduced confidence in pre-Next Gen raw averages. Betting: look for market overreaction either to old-track specialists or to complete dismissal of historical skill; blend both with strong era shrinkage.

**Comparable-track prior:** Homestead; Kansas; old Atlanta; Auto Club. **Calculated structural neighbors:** homestead (98.9); atlanta_pre_2022 (94.0); kansas (92.8); texas_pre_2017 (92.8); darlington (88.7).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 5/10; passing difficulty 4/10; attrition 5/10; restart volatility 7/10; pit-road importance 7/10; qualifying importance 5/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 6/10.

### Darlington Raceway — 1.366-mile egg-shaped oval (`darlington`)

**[VF | High] Physical profile:** 1.366 miles; asymmetrical egg-shaped oval; highly abrasive asphalt; oval; turns: 4; banking/context: 25 deg turns 1-2; 23 deg turns 3-4. Sources: S003;S004;S006;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 18 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Geometry is intentionally asymmetric; same-facility data remains more portable across packages than generic intermediate averages, but tire compounds are critical.

**[SI | High] Racing mechanism:** Darlington separates entry precision, wall proximity, tire conservation and traffic technique. Average running position is more informative than finish because wall contact, late cautions and tire cycles can distort the box score.

**[SI | High] DFS/betting application:** DFS: prioritize sustained speed and fastest-lap potential; dominators often emerge, but tire-cycle timing can split laps led. Betting: driver skill and team adjustment quality deserve a larger coefficient than at smooth, symmetric 1.5-mile tracks.

**Comparable-track prior:** Homestead; old Atlanta; Chicagoland. **Calculated structural neighbors:** homestead (89.6); chicagoland_oval (88.7); texas_pre_2017 (87.9); atlanta_pre_2022 (87.3); kansas (86.2).

**[WH] Prior vector:** tire degradation 10/10; track-position premium 6/10; passing difficulty 5/10; attrition 7/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 6/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 7/10.

### Homestead-Miami Speedway — 1.5-mile oval (`homestead`)

**[VF | High] Physical profile:** 1.5 miles; progressive-banked oval; abrasive asphalt; oval; turns: 4; banking/context: 18-20 deg progressive. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 11 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Calendar placement moved from championship finale to regular/playoff roles and back to the 2026 championship finale; pressure context is not a physical track trait.

**[SI | High] Racing mechanism:** Progressive banking supports several lanes, while the wall-adjacent high line can generate speed at elevated risk. Long-run throttle control and the ability to change lanes as rubber builds are highly portable skills.

**[SI | High] DFS/betting application:** DFS: dominator and fastest-lap upside is high; do not overrate qualifying alone. Betting: reward drivers with proven tire conservation and high-line confidence, while separating championship incentives from ordinary race pace.

**Comparable-track prior:** Darlington; Chicagoland; old Atlanta. **Calculated structural neighbors:** chicagoland_oval (98.9); atlanta_pre_2022 (95.0); kansas (91.8); texas_pre_2017 (91.8); darlington (89.6).

**[WH] Prior vector:** tire degradation 9/10; track-position premium 5/10; passing difficulty 4/10; attrition 5/10; restart volatility 7/10; pit-road importance 7/10; qualifying importance 5/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 6/10.

### Kansas Speedway — 1.5-mile oval (`kansas`)

**[VF | High] Physical profile:** 1.5 miles; tri-oval; asphalt; oval; turns: 4; banking/context: 17-20 deg variable/progressive. Sources: S003;S004;S006;S007;S008;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 22 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** No major configuration split in scope; package and tire eras remain essential.

**[SI | High] Racing mechanism:** Kansas has become one of the most informative Next Gen intermediates because multiple lanes, side draft and tire falloff allow both car quality and driver decision-making to express. Restarts create large but not purely random position swings.

**[SI | High] DFS/betting application:** DFS: one or two dominators are often viable, but deep-starting elite cars retain recovery paths. Betting: Kansas is a strong donor track for other multi-groove intermediates, with recent Next Gen performance weighted heavily.

**Comparable-track prior:** Las Vegas; Homestead; Chicagoland; Charlotte. **Calculated structural neighbors:** texas_pre_2017 (95.7); chicagoland_oval (92.8); las_vegas (92.8); homestead (91.8); kentucky_pre_2016 (90.9).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 6/10; passing difficulty 4/10; attrition 4/10; restart volatility 8/10; pit-road importance 7/10; qualifying importance 6/10; strategy flexibility 7/10; DFS dominator concentration 8/10; finish variance 5/10.

### Kentucky Speedway — 2016-2020 reconfigured oval (`kentucky_post_2016`)

**[VF | High] Physical profile:** 1.5 miles; asymmetric tri-oval; repaved asphalt; oval; turns: 4; banking/context: 17 deg turns 1-2; 14 deg turns 3-4. Sources: S004;S013;S014;S015;S016;S017;S025.

**[CR | High] Scope sample:** 5 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** 2016 full reconfiguration/repave increased Turns 1-2 banking and produced asymmetric ends. Last Cup points race was 2020.

**[SI | High] Racing mechanism:** The fresh surface narrowed the competitive groove and raised the value of clean air and restart execution. Because the active sample ended before Next Gen, transfer to current smooth tracks should be conceptual rather than direct.

**[SI | High] DFS/betting application:** DFS: qualifying and likely leaders carried more value than speculative deep place differential. Betting: historical performance is most useful as evidence of driver strength on narrow, aero-sensitive surfaces, with heavy era discount.

**Comparable-track prior:** Texas post-2017; Indianapolis oval; Charlotte. **Calculated structural neighbors:** texas_post_2017 (94.7); charlotte_oval (90.0); las_vegas (87.4); kentucky_pre_2016 (85.7); texas_pre_2017 (83.3).

**[WH] Prior vector:** tire degradation 3/10; track-position premium 9/10; passing difficulty 8/10; attrition 4/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 9/10; strategy flexibility 4/10; DFS dominator concentration 8/10; finish variance 4/10.

### Kentucky Speedway — pre-2016 1.5-mile oval (`kentucky_pre_2016`)

**[VF | High facts / Low predictive] Physical profile:** 1.5 miles; tri-oval; aged/bumpy asphalt; oval; turns: 4; banking/context: 14 deg turns. Sources: S004;S012;S025.

**[CR | High] Scope sample:** 1 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Only the 2015 Cup race is in the requested core window for this version.

**[SI | High facts / Low predictive] Racing mechanism:** The pre-reconfiguration surface’s bumps and lower grip created a materially different setup problem from 2016 onward. With a one-race core sample, use this profile as historical context, not a standalone predictive cluster.

**[SI | High facts / Low predictive] DFS/betting application:** DFS/betting: do not mix the 2015 result with post-2016 Kentucky without a configuration flag. Any driver-specific conclusion has very low sample support.

**Comparable-track prior:** old Texas; Charlotte; Las Vegas. **Calculated structural neighbors:** las_vegas (95.7); charlotte_oval (94.7); texas_pre_2017 (94.7); kansas (90.9); chicagoland_oval (88.2).

**[WH] Prior vector:** tire degradation 6/10; track-position premium 7/10; passing difficulty 6/10; attrition 5/10; restart volatility 6/10; pit-road importance 7/10; qualifying importance 7/10; strategy flexibility 6/10; DFS dominator concentration 8/10; finish variance 5/10.

### Las Vegas Motor Speedway — 1.5-mile oval (`las_vegas`)

**[VF | High] Physical profile:** 1.5 miles; tri-oval; asphalt; oval; turns: 4; banking/context: 20 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 19 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Two annual points races beginning in 2018; no material physical split in scope.

**[SI | High] Racing mechanism:** Las Vegas is a clean test of intermediate organizational speed, aerodynamic balance and long-run pace. It is less forgiving than Kansas for a car that loses front grip in traffic, making track position and pit execution more persistent.

**[SI | High] DFS/betting application:** DFS: dominator concentration is usually important; long-run practice and recent intermediate form should lead projections. Betting: manufacturer/team platform strength can be more predictive here than isolated driver track history.

**Comparable-track prior:** Kansas; Charlotte; Texas; Michigan. **Calculated structural neighbors:** charlotte_oval (96.8); kentucky_pre_2016 (95.7); texas_pre_2017 (94.7); kansas (92.8); chicagoland_oval (88.2).

**[WH] Prior vector:** tire degradation 6/10; track-position premium 7/10; passing difficulty 5/10; attrition 4/10; restart volatility 7/10; pit-road importance 7/10; qualifying importance 7/10; strategy flexibility 6/10; DFS dominator concentration 8/10; finish variance 4/10.

### Texas Motor Speedway — 2017+ asymmetric 1.5-mile oval (`texas_post_2017`)

**[VF | High] Physical profile:** 1.5 miles; asymmetric quad-oval; repaved asphalt; oval; turns: 4; banking/context: 20 deg turns 1-2; 24 deg turns 3-4. Sources: S003;S004;S014;S015;S016;S017;S018;S019;S020;S021;S022;S024;S001.

**[CR | High] Scope sample:** 13 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** 2017 repave reduced Turns 1-2 banking from 24 to 20 degrees and widened that end from 60 to 80 feet; Turns 3-4 stayed 24 degrees.

**[SI | High] Racing mechanism:** The two ends demand different compromises, while the repaved surface historically concentrated usable grip. Passing difficulty makes restart lane, pit exit and clean air unusually valuable, though tire and resin applications can shift the exact behavior by event.

**[SI | High] DFS/betting application:** DFS: prioritize front-end speed and dominator candidates; deep-starting plays need a clear pace edge. Betting: qualifying and pit crew should be explicitly modeled; use same-track recency over generic intermediate history.

**Comparable-track prior:** Kentucky post-2016; Indianapolis oval; Charlotte. **Calculated structural neighbors:** kentucky_post_2016 (94.7); charlotte_oval (87.4); kentucky_pre_2016 (86.5); las_vegas (84.9); texas_pre_2017 (84.1).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 9/10; passing difficulty 9/10; attrition 6/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 9/10; strategy flexibility 4/10; DFS dominator concentration 8/10; finish variance 5/10.

### Texas Motor Speedway — pre-2017 1.5-mile oval (`texas_pre_2017`)

**[VF | High] Physical profile:** 1.5 miles; quad-oval; aged asphalt; oval; turns: 4; banking/context: 24 deg turns. Sources: S004;S012;S013;S024.

**[CR | High] Scope sample:** 4 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Configuration used through 2016; 2017 repave/reconfiguration is a hard split.

**[SI | High] Racing mechanism:** The older Texas rewarded bump management and had more lane evolution than the later configuration. Pooling it with 2017+ data erases the most important physical change at the facility.

**[SI | High] DFS/betting application:** DFS/betting: pre-2017 track history should receive minimal weight for current Texas projections except as broad evidence of 1.5-mile skill.

**Comparable-track prior:** Charlotte; old Atlanta; Las Vegas. **Calculated structural neighbors:** kansas (95.7); kentucky_pre_2016 (94.7); las_vegas (94.7); chicagoland_oval (92.8); charlotte_oval (91.8).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 6/10; passing difficulty 5/10; attrition 5/10; restart volatility 7/10; pit-road importance 7/10; qualifying importance 6/10; strategy flexibility 6/10; DFS dominator concentration 8/10; finish variance 5/10.

### Indianapolis Motor Speedway — 2.5-mile oval (`indianapolis_oval`)

**[VF | High] Physical profile:** 2.5 miles; rectangular oval; asphalt; oval; turns: 4; banking/context: 9 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S021;S022;S001.

**[CR | High] Scope sample:** 8 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup used the road course 2021-2023 and returned to the oval in 2024. Do not pool layouts.

**[SI | High] Racing mechanism:** Four distinct low-banked corners, long straights and narrow aero windows create a momentum and clean-air problem unlike a conventional oval. Pit timing and caution timing can dominate because passing comparable-speed cars is difficult.

**[SI | High] DFS/betting application:** DFS: front-row and early leader exposure is important, but strategy can create late place-differential swings. Betting: qualifying, pit crew and crew-chief strategy deserve premium weights; model incident risk at restarts separately from baseline green-flag pace.

**Comparable-track prior:** Pocono; Texas post-2017; Michigan. **Calculated structural neighbors:** pocono (92.8).

**[WH] Prior vector:** tire degradation 3/10; track-position premium 9/10; passing difficulty 9/10; attrition 6/10; restart volatility 8/10; pit-road importance 9/10; qualifying importance 9/10; strategy flexibility 9/10; DFS dominator concentration 7/10; finish variance 7/10.

### Pocono Raceway — 2.5-mile triangular oval (`pocono`)

**[VF | High] Physical profile:** 2.5 miles; three-turn triangular oval; asphalt; oval; turns: 3; banking/context: 14 deg T1; 8 deg T2; 6 deg T3. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S001.

**[CR | High] Scope sample:** 18 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Two-race doubleheaders in 2020-21 are event-format anomalies; one annual race from 2022.

**[SI | High] Racing mechanism:** Each corner references a different archetype, forcing setup compromise. Long straights make exit speed decisive, while the race distance and pit windows make fuel and stage-break strategy unusually influential.

**[SI | High] DFS/betting application:** DFS: dominator concentration can be lower than lap count suggests because strategy cycles leaders. Betting: crew-chief quality, fuel mileage and restart strength should supplement raw speed; same-track practice is especially valuable.

**Comparable-track prior:** Indianapolis oval; Michigan; Gateway. **Calculated structural neighbors:** indianapolis_oval (92.8).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 8/10; passing difficulty 7/10; attrition 5/10; restart volatility 8/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 7/10; finish variance 6/10.

### Autodromo Hermanos Rodriguez — 2.42-mile road course (`mexico_city`)

**[VF | High facts / Low sample] Physical profile:** 2.42 miles; permanent road course; asphalt; road/street/hybrid course; turns: 15; banking/context: high altitude; mostly flat circuit. Sources: S022;S001.

**[CR | High] Scope sample:** 1 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** First Cup points race in 2025; absent from 2026 schedule. One-race Cup sample.

**[SI | High facts / Low sample] Racing mechanism:** Altitude changes cooling, power and braking demands, while the stadium section and technical sequence reward precision. The single event should be analyzed as a case study, not a stable track average.

**[SI | High facts / Low sample] DFS/betting application:** DFS/betting: road-course specialist priors dominate track history. Market uncertainty should remain high until multiple tire/weather/rules observations exist.

**Comparable-track prior:** COTA short; Sonoma; Indianapolis road. **Calculated structural neighbors:** sonoma_carousel (93.0); watkins_glen (92.3); cota_short (90.6); sonoma_short (86.8); cota_full (78.4).

**[WH] Prior vector:** tire degradation 6/10; track-position premium 7/10; passing difficulty 6/10; attrition 7/10; restart volatility 9/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 7/10; finish variance 8/10.

### Circuit of The Americas — 2021-2024 full course (`cota_full`)

**[VF | High] Physical profile:** 3.41 miles; permanent road course; asphalt; road/street/hybrid course; turns: 20; banking/context: significant elevation change. Sources: S003;S018;S019;S020;S021;S029.

**[CR | High] Scope sample:** 4 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** First four Cup races used the full roughly 3.4-mile circuit; shortened in 2025.

**[SI | High] Racing mechanism:** The full layout combined long straights, technical esses, heavy braking and weather sensitivity. Long laps increased the cost of an off-course event and created broad pit-window options.

**[SI | High] DFS/betting application:** DFS: road-course skill and fastest-lap potential mattered, but stage/pit timing could invert running order. Betting: full-course results should not be treated as identical to 2025+ short COTA.

**Comparable-track prior:** Road America; Sonoma; Indianapolis road. **Calculated structural neighbors:** road_america (84.5); cota_short (80.2); mexico_city (78.4); watkins_glen (76.7); sonoma_carousel (76.3).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 6/10; passing difficulty 4/10; attrition 7/10; restart volatility 10/10; pit-road importance 9/10; qualifying importance 7/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 8/10.

### Circuit of The Americas — 2025+ shortened course (`cota_short`)

**[VF | High] Physical profile:** 2.4 miles; shortened permanent road course; asphalt; road/street/hybrid course; turns: 17; banking/context: significant elevation change. Sources: S002;S022;S029;S030;S039.

**[CR | High] Scope sample:** 1 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** 2025 revision shortened the course to 2.4 miles and 17 turns, increasing lap count from 68 to 95 in the first event. 2026 uses 750 hp.

**[SI | High] Racing mechanism:** The shorter lap compresses field encounters and adds restart/passing opportunities while preserving COTA’s braking and elevation identity. Softer tires can make degradation a more central variable than on the full course.

**[SI | High] DFS/betting application:** DFS: more laps modestly increase fastest-lap/dominator relevance; practice long runs and tire notes matter. Betting: give 2025-26 short-course data priority and retain full-course data only as driver/organization road-skill evidence.

**Comparable-track prior:** Sonoma short; Watkins Glen; Mexico City. **Calculated structural neighbors:** mexico_city (90.6); watkins_glen (89.2); sonoma_carousel (86.4); sonoma_short (81.5); cota_full (80.2).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 6/10; passing difficulty 4/10; attrition 7/10; restart volatility 10/10; pit-road importance 8/10; qualifying importance 7/10; strategy flexibility 8/10; DFS dominator concentration 6/10; finish variance 8/10.

### Road America — 4.048-mile road course (`road_america`)

**[VF | High facts / Low sample] Physical profile:** 4.048 miles; long natural-terrain road course; asphalt; road/street/hybrid course; turns: 14; banking/context: substantial elevation change. Sources: S018;S019.

**[CR | High] Scope sample:** 2 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points races in 2021 and 2022; no current date.

**[SI | High facts / Low sample] Racing mechanism:** The four-mile lap, elevation and long straights create broad strategy windows and punish mistakes with long recovery time. Caution timing can create enormous field inversions because a pit stop consumes a large fraction of a lap.

**[SI | High facts / Low sample] DFS/betting application:** DFS: fastest laps and place differential are viable, but lap count suppresses conventional dominator volume. Betting: strategy variance and small Cup sample require wide confidence intervals.

**Comparable-track prior:** Watkins Glen; COTA full. **Calculated structural neighbors:** cota_full (84.5); mexico_city (70.7); watkins_glen (70.4); sonoma_carousel (70.0); cota_short (69.9).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 6/10; passing difficulty 5/10; attrition 7/10; restart volatility 8/10; pit-road importance 9/10; qualifying importance 7/10; strategy flexibility 10/10; DFS dominator concentration 6/10; finish variance 8/10.

### Sonoma Raceway — 1.99-mile chute layout (`sonoma_short`)

**[VF | High] Physical profile:** 1.99 miles; natural-terrain road course; asphalt; road/street/hybrid course; turns: 10; banking/context: substantial elevation change. Sources: S003;S004;S012;S013;S014;S015;S019;S020;S021;S022;S027;S039;S001.

**[CR | High] Scope sample:** 8 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Used 2015-2018 and again from 2022; carousel layout used in 2019 and 2021. 2026 uses 750 hp.

**[SI | High] Racing mechanism:** Sonoma’s elevation, low-speed traction and tire falloff make it one of the most complete road-course tests. Passing requires exit setup and braking confidence; pit windows can create undercut/overcut value.

**[SI | High] DFS/betting application:** DFS: road specialists with tire management and clean execution deserve priority; dominator points are secondary but not irrelevant. Betting: same-layout Sonoma data is highly valuable, with 2026 horsepower treated as a new sub-era.

**Comparable-track prior:** COTA short; Mexico City; Watkins Glen. **Calculated structural neighbors:** sonoma_carousel (89.5); mexico_city (86.8); watkins_glen (83.9); cota_short (81.5); cota_full (70.0).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 7/10; passing difficulty 7/10; attrition 6/10; restart volatility 8/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 7/10; finish variance 7/10.

### Sonoma Raceway — 2.52-mile carousel layout (`sonoma_carousel`)

**[VF | High facts / Low sample] Physical profile:** 2.52 miles; natural-terrain road course; asphalt; road/street/hybrid course; turns: 12; banking/context: substantial elevation change. Sources: S016;S018;S027.

**[CR | High] Scope sample:** 2 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Used for Cup points races in 2019 and 2021; 2020 event canceled.

**[SI | High facts / Low sample] Racing mechanism:** The carousel added sustained cornering and changed lap flow, tire energy and passing setup. Driver skill transfers to short Sonoma, but raw lap and strategy statistics do not.

**[SI | High facts / Low sample] DFS/betting application:** DFS/betting: two-race sample is contextual only; map driver performance to road-course skill rather than current Sonoma track average.

**Comparable-track prior:** Sonoma short; COTA full. **Calculated structural neighbors:** mexico_city (93.0); watkins_glen (90.7); sonoma_short (89.5); cota_short (86.4); cota_full (76.3).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 7/10; passing difficulty 7/10; attrition 6/10; restart volatility 8/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 7/10; finish variance 7/10.

### Watkins Glen International — 2.45-mile road course (`watkins_glen`)

**[VF | High] Physical profile:** 2.45 miles; high-speed natural-terrain road course; asphalt; road/street/hybrid course; turns: 7; banking/context: elevation change; fast corners. Sources: S003;S004;S012;S013;S014;S015;S016;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 10 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** No major layout split in core window; chicane/curb and tire rules remain event variables. 2026 uses 750 hp.

**[SI | High] Racing mechanism:** Watkins Glen rewards commitment, braking stability and exit speed more than low-speed rotation. Its speed profile makes it a poor one-for-one comparable for Sonoma despite both being road courses.

**[SI | High] DFS/betting application:** DFS: qualifying and road-course speed are important, with moderate fastest-lap concentration. Betting: weight high-speed road-course evidence and avoid overgeneralizing from street circuits.

**Comparable-track prior:** Road America; COTA short; Sonoma. **Calculated structural neighbors:** mexico_city (92.3); sonoma_carousel (90.7); cota_short (89.2); sonoma_short (83.9); cota_full (76.7).

**[WH] Prior vector:** tire degradation 4/10; track-position premium 7/10; passing difficulty 5/10; attrition 6/10; restart volatility 9/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 8/10; DFS dominator concentration 7/10; finish variance 7/10.

### Iowa Speedway — 0.875-mile oval (`iowa`)

**[VF | Medium-High] Physical profile:** 0.875 miles; D-shaped short oval; asphalt; oval; turns: 4; banking/context: 12-14 deg progressive. Sources: S003;S004;S021;S022;S001;S039.

**[CR | High] Scope sample:** 2 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Cup points debut in 2024; small Cup sample. Surface patches and tire behavior are central event variables.

**[SI | Medium-High] Racing mechanism:** Progressive banking and multiple lanes make Iowa less track-position locked than many flat short tracks. Tire falloff can create comers and goers, but restart aggression still produces sharp short-run variance.

**[SI | Medium-High] DFS/betting application:** DFS: combine long-run speed with moderate place-differential opportunity; dominators remain important due to lap count. Betting: Xfinity/Truck history can inform comfort but must be discounted for car and field differences.

**Comparable-track prior:** Richmond; North Wilkesboro; Phoenix. **Calculated structural neighbors:** north_wilkesboro (90.5); richmond (88.9); martinsville (52.2); new_hampshire (38.9); phoenix_post_2018f (38.4).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 6/10; passing difficulty 5/10; attrition 6/10; restart volatility 9/10; pit-road importance 7/10; qualifying importance 6/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 7/10.

### Martinsville Speedway — 0.526-mile oval (`martinsville`)

**[VF | High] Physical profile:** 0.526 miles; paperclip oval; asphalt straights / concrete turns; oval; turns: 4; banking/context: 12 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 22 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** No major physical split in scope; brake package, shifting rules, tire and horsepower are important era variables.

**[SI | High] Racing mechanism:** Martinsville is a braking, rotation and drive-off contest where traffic and lane control can overwhelm small pace differences. Passing often requires setting up exits or using contact, so average running position and restart retention are valuable diagnostics.

**[SI | High] DFS/betting application:** DFS: laps-led concentration makes dominators essential; starting position matters, but elite cars can move through the field over 500 laps. Betting: model retaliation/contact and late-race restart risk separately from baseline speed.

**Comparable-track prior:** North Wilkesboro; Richmond; New Hampshire. **Calculated structural neighbors:** north_wilkesboro (54.6); iowa (52.2); richmond (51.4); bristol_concrete (39.8); dover (38.5).

**[WH] Prior vector:** tire degradation 5/10; track-position premium 8/10; passing difficulty 8/10; attrition 7/10; restart volatility 10/10; pit-road importance 8/10; qualifying importance 8/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 7/10.

### North Wilkesboro Speedway — 0.625-mile oval (`north_wilkesboro`)

**[VF | High facts / Low points-sample] Physical profile:** 0.625 miles; asymmetrical short oval; aged asphalt; oval; turns: 4; banking/context: 14 deg turns; elevation change. Sources: S003;S004;S001;S002;S040;S039.

**[CR | High] Scope sample:** 0 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** First scheduled points-paying Cup race since 1996 is July 19, 2026; prior 2023-25 Cup events were non-points and are deferred from the primary sample.

**[SI | High facts / Low points-sample] Racing mechanism:** Opposing elevation changes and old pavement create a traction-management problem distinct from a flat paperclip. The scheduled points sample is zero as of the research cutoff, so non-points observations are context only rather than primary evidence.

**[SI | High facts / Low points-sample] DFS/betting application:** DFS/betting: use practice, tire falloff and recent non-points race craft as weak priors, then heavily weight qualifying and live-weekend evidence. Market confidence should be lower than at established short tracks.

**Comparable-track prior:** Martinsville; Iowa; Richmond. **Calculated structural neighbors:** iowa (90.5); richmond (86.3); martinsville (54.6); new_hampshire (38.7); phoenix_post_2018f (38.2).

**[WH] Prior vector:** tire degradation 9/10; track-position premium 7/10; passing difficulty 7/10; attrition 6/10; restart volatility 9/10; pit-road importance 7/10; qualifying importance 7/10; strategy flexibility 8/10; DFS dominator concentration 8/10; finish variance 7/10.

### Richmond Raceway — 0.75-mile oval (`richmond`)

**[VF | High] Physical profile:** 0.75 miles; D-shaped short oval; asphalt; oval; turns: 4; banking/context: 14 deg turns. Sources: S003;S004;S012;S013;S014;S015;S016;S017;S018;S019;S020;S021;S022;S039;S001.

**[CR | High] Scope sample:** 20 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 1 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Schedule reduced to one annual points race beginning in 2025. Option-tire experiments/rules should be treated as event-level flags.

**[SI | High] Racing mechanism:** Richmond’s low banking and worn surface create meaningful falloff and undercut/overcut choices. The track can look processional when tire deltas are small, but becomes strategically rich when compounds or long runs create speed separation.

**[SI | High] DFS/betting application:** DFS: long-run pace and pit-cycle fastest laps matter more than single-lap qualifying. Betting: tire compound and weather should be first-class model inputs; same-track history is portable only across similar tire regimes.

**Comparable-track prior:** Iowa; Phoenix; New Hampshire. **Calculated structural neighbors:** iowa (88.9); north_wilkesboro (86.3); martinsville (51.4); phoenix_pre_2018f (38.9); phoenix_post_2018f (38.5).

**[WH] Prior vector:** tire degradation 8/10; track-position premium 6/10; passing difficulty 6/10; attrition 4/10; restart volatility 7/10; pit-road importance 8/10; qualifying importance 6/10; strategy flexibility 9/10; DFS dominator concentration 8/10; finish variance 5/10.

### Chicago Street Course — 2.2-mile street course (`chicago_street`)

**[VF | High facts / Medium priors] Physical profile:** 2.2 miles; temporary street circuit; mixed public-road asphalt/concrete; road/street/hybrid course; turns: 12; banking/context: flat. Sources: S003;S004;S020;S021;S022;S034.

**[CR | High] Scope sample:** 3 completed points races in 2015-2025; 0 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Points races 2023-2025; paused for 2026 with potential future return. Weather materially affected the inaugural race.

**[SI | High facts / Medium priors] Racing mechanism:** Narrow walls, surface transitions and limited runoff convert small errors into large losses. Passing zones are scarce enough that qualifying and pit timing matter, while cautions and weather can reset the event violently.

**[SI | High facts / Medium priors] DFS/betting application:** DFS: road/street specialists and place differential matter, but crash-adjusted projections need wide distributions. Betting: use conservative staking and avoid treating three races as a stable frequency estimate; live weather is essential.

**Comparable-track prior:** San Diego; Charlotte Roval; Indianapolis road. **Calculated structural neighbors:** san_diego_street (71.7); charlotte_roval_v2 (31.4); charlotte_roval_v1 (31.3); indianapolis_road (30.8); mexico_city (30.2).

**[WH] Prior vector:** tire degradation 3/10; track-position premium 9/10; passing difficulty 9/10; attrition 9/10; restart volatility 10/10; pit-road importance 9/10; qualifying importance 9/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 10/10.

### Qualcomm Circuit at Naval Base Coronado — 3.4-mile street/runway course (`san_diego_street`)

**[VF | High facts / Low sample] Physical profile:** 3.4 miles; temporary street and runway circuit; mixed worn streets/runways; road/street/hybrid course; turns: 16; banking/context: flat with mixed surfaces. Sources: S001;S002;S031;S032;S033;S039.

**[CR | High] Scope sample:** 0 completed points races in 2015-2025; 1 completed in 2026 through the cutoff; 0 additional 2026 points race(s) scheduled.

**Configuration/chronology:** Debuted June 21, 2026; one completed Cup points race as of cutoff. First active U.S. military installation to host a major NASCAR event.

**[SI | High facts / Low sample] Racing mechanism:** Unlike Chicago’s compact canyon, San Diego combines long, fast sections with mixed worn pavement and runway surfaces. The first race provides evidence about braking, tire and passing zones, but one result cannot establish stable rates.

**[SI | High facts / Low sample] DFS/betting application:** DFS/betting: treat track-specific history as near-zero; rely on street/road skill, practice, surface reports and setup adaptability. Apply a large novelty/incident uncertainty term.

**Comparable-track prior:** Chicago street; Road America; COTA full. **Calculated structural neighbors:** chicago_street (71.7); daytona_road (31.4); cota_full (31.3); mexico_city (30.0); road_america (30.0).

**[WH] Prior vector:** tire degradation 7/10; track-position premium 7/10; passing difficulty 6/10; attrition 8/10; restart volatility 9/10; pit-road importance 9/10; qualifying importance 8/10; strategy flexibility 9/10; DFS dominator concentration 6/10; finish variance 8/10.

## Original metric specifications for empirical calibration

The following indices are proposed for the downstream project. They should be calculated by track configuration × rules era, with Bayesian shrinkage toward the relevant family when samples are small. Use race-level bootstrapping so multiple drivers from one race do not masquerade as independent observations.

| Metric | Proposed calculation | Use |
| --- | --- | --- |
| Track Position Premium (TPP) | Weighted z-score of start/qualifying-to-running-position persistence, clean-air lap delta, restart retention and green-flag pass scarcity. Exclude drafting lane oscillations or model them separately. | Raises leader/qualifying weight; lowers optimistic place-differential conversion. |
| Passing Difficulty Index (PDI) | Inverse of quality-adjusted green-flag passes per competitive car-lap, controlling for speed differential, tire age and restart proximity. | Sets ceiling on recovery; informs head-to-head and top-N markets. |
| Attrition Risk Score (ARS) | Hierarchical probability of crash/mechanical DNF plus incident-induced major position loss; separate common-cause wrecks from individual failures. | Widens finish distributions; essential at drafting/street tracks. |
| Restart Volatility Score (RVS) | Expected absolute running-position change within 2-5 green laps after restarts, conditioned on lane and restart row. | Quantifies late-caution upset potential. |
| Tire Degradation Score (TDS) | Median green-run lap-time slope after fuel correction, plus dispersion in driver falloff and crossover frequency between old/new tires. | Elevates long-run practice, tire management and pit timing. |
| Pit-Road Importance Score (PIS) | Share of net position change explained by pit-cycle gain/loss, pit penalties and undercut/overcut effectiveness. | Adds team/crew signal beyond driver speed. |
| Qualifying Importance Score (QIS) | Partial effect of starting position on expected finish/running position after controlling for pre-race speed and driver/team strength. | Avoids confusing fast qualifiers with causal track position. |
| Strategy Flexibility Score (SFS) | Entropy/effectiveness of successful pit sequences and fuel/tire paths; measure how many distinct strategies can reach the front. | Raises crew-chief variance and live-betting opportunity. |
| Driver Skill Transferability (DST) | Cross-validated correlation of driver residual performance between track/era pairs after team, car and season controls. | Empirically replaces subjective similar-track lists. |
| Dominator Concentration Index (DCI) | Herfindahl index of laps led and fastest laps by driver, normalized for total lap count and overtime. | Directly informs DFS roster construction. |
### Minimum empirical data schema

`race_id, date, season, track_id, facility, config_id, rules_era, tire_code, weather, scheduled_laps, actual_laps, driver_id, team_id, manufacturer, start, finish, avg_running_position, driver_rating, laps_led, fastest_laps, green_flag_passes, quality_passes, pit_stop_time, penalties, DNF_type, stage_positions, practice_5/10/15_lap, qualifying_rank, closing_odds, market_type`.

S005 documents an openly available historical results dataset with start, finish, laps led and rating fields. FASTLAP and Lap Raptor document useful advanced-stat concepts (S006-S008). Production use should validate licensing, definitions and update cadence before ingestion.

## DFS-specific framework

1. **Project scoring, not just finishing order.** Lap count, dominator concentration and fastest-lap allocation make Bristol/Martinsville/Darlington structurally different DFS games from Talladega or Road America.
2. **Separate speed ceiling from survival ceiling.** Drafting and street courses can reward place differential but also create correlated lineup failure.
3. **Use practice correctly.** Prefer sustained 10- or 15-lap pace where tire falloff matters; single-lap speed is more useful for qualifying/track-position regimes. FASTLAP’s practice methodology explicitly distinguishes long-run averages (S006).
4. **Ownership is conditional on track archetype.** At high-variance tracks, duplicated chalk combinations can be more damaging; at dominator tracks, fading the likely leader can be mathematically fatal.
5. **Do not use one comparable set for every salary tier.** A driver’s transferability may differ by skill component: braking, tire management, pack craft, high-line commitment or team aero platform.

## Betting-specific framework

1. **Model common-cause risk.** At Daytona/Talladega/Atlanta, drivers’ outcomes are correlated through the same wrecks; parlay math based on independence is invalid.
2. **Separate fair win probability from bet quality.** Novel tracks can create model uncertainty that should reduce stake even when an edge appears large.
3. **Track market closing lines.** Without odds, historical ROI is selection-biased storytelling. Save opener, bet-time and close for outrights, top-N and matchups.
4. **Prefer matchup markets when mechanism is stable.** Tire-management or flat-track driver advantages may express more reliably head-to-head than in 36-car outrights.
5. **Use weather and tire codes as model keys.** Richmond option tires, wet-weather ovals and street-course rain are not minor annotations.

## Novel hypotheses worth testing

- **[WH | Medium] Atlanta aging transition:** Post-2022 Atlanta should be modeled with a latent “pack-to-handling” state driven by surface age, off-throttle percentage and tire falloff, rather than a fixed superspeedway label.
- **[WH | Medium] Restart geometry index:** Tracks where the start/finish line places a fan-out zone immediately after the restart—post-2018 Phoenix, COTA Turn 1, Roval chicanes—may have systematically higher lane-conditional volatility.
- **[WH | High] Pass quality vs pass volume:** Talladega may have high raw pass volume but low independence/information content. A “durable pass” surviving N laps may predict finish better than raw passes.
- **[WH | High] Concrete transfer is nonlinear:** Bristol, Dover and Nashville share concrete but differ enough in length, banking and aero dependence that surface should be an interaction term, not a standalone cluster.
- **[WH | Medium-High] Championship incentive effect:** Phoenix/Homestead championship races should include a four-contender strategy/incentive flag; however, physical pace estimates should use the full field and avoid assuming contenders are representative.
- **[WH | Medium] Street-course novelty decay:** Incident variance may decline across repeated street events as teams improve simulation and drivers learn sight lines, but infrastructure/layout changes can reset the curve.
- **[WH | Medium] Pit-road geometry as hidden track feature:** Pit entry speed loss, pit-box spacing and merge geometry may explain residual strategy/penalty variance after controlling for track family.
- **[WH | High] Driver skill vector instead of label:** Replace “road-course ringer” or “short-track ace” with a vector: braking, tire management, restart launch, traffic navigation, high-line commitment and pack decision-making.

## Data-engineering recommendations

- Use `track_id` from this audit as the physical configuration key and add separate `rules_era_id`, `tire_regime_id` and `event_format_id`.
- Store all raw sources with retrieval date and content hash. Do not overwrite old track specs when a facility changes.
- Keep `facility_id` above `track_id` so the project can aggregate or split intentionally.
- Use time-aware cross-validation. A random train/test split leaks future team/package information.
- Build track similarity from residual performance, not only geometry. Compare the empirical matrix against the structural prior matrix in the companion file.
- Require minimum effective sample sizes and report posterior uncertainty. One race with 36 drivers is still one event-level environmental observation.
- Preserve canceled/postponed/weather-shortened flags and scheduled versus actual distance.
- Track DFS scoring rules and sportsbook settlement rules by date; market products change.

## Suggested next steps, ordered by value

| Priority | Step | Detail |
| --- | --- | --- |
| 1 | Ingest race-level results | Load S005 or an equivalent licensed dataset; map every race to `track_id`; reconcile counts to 396 completed races for 2015-2025 and 20 through July 12, 2026. |
| 2 | Acquire loop data | Add average running position, driver rating, green-flag passes, quality passes, fastest laps and restart positions from licensed/approved sources. |
| 3 | Build era-aware baselines | Estimate driver/team/manufacturer residuals by rules era before calculating track effects. |
| 4 | Calibrate priors | Replace or update the 1-10 structural priors with posterior metric estimates and credible intervals. |
| 5 | Estimate empirical similarity | Use cross-validated residual correlations and hierarchical partial pooling; compare against `nascar_track_similarity_edges.csv`. |
| 6 | Add betting market data | Archive opening/closing odds and limits; calculate CLV before ROI. |
| 7 | Add DFS contest data | Store salary, ownership, scoring and contest payout structure; backtest roster construction by DCI/variance regime. |
| 8 | Automate schedule/config watch | Monitor NASCAR announcements for repaves, layout changes, tire compounds, horsepower/aero and future tracks such as a possible Chicago Street return. |
## Confidence and evidence ledger

- Physical length/shape/surface fields: generally **High**, except where official and secondary pages conflict on rounded length; official event documents control.
- Event counts: **High**, calculated from annual schedule audit; configuration mapping remains inspectable in JSON.
- Racing mechanisms: **Medium-High to High** for established tracks, **Medium or Low** for one-race/new configurations.
- Structural scores: **Working Hypothesis**, intended for calibration.
- Structural nearest neighbors: **Calculated Result from analyst priors**, not empirical similarity.

## Source ledger

| ID | Publisher | Title | Type | Reliability | Coverage | URL |
| --- | --- | --- | --- | --- | --- | --- |
| S001 | NASCAR | NASCAR releases 2026 Cup Series schedule | official schedule announcement | Primary | 2026 points schedule, Chicagoland/North Wilkesboro/San Diego/Homestead changes | https://www.nascar.com/news-media/2025/08/20/nascar-releases-2026-schedule-adding-chicagoland-and-shifting-all-star-to-dover/ |
| S002 | NASCAR | 2026 NASCAR Cup Series schedule | official live schedule/results | Primary | 2026 event order and completion status | https://www.nascar.com/nascar-cup-series/2026/schedule/ |
| S003 | NASCAR | List of NASCAR tracks | official track directory | Primary | current track names, locations and basic classification | https://www.nascar.com/tracks/ |
| S004 | RotoWire | NASCAR Track Stats | track reference | Secondary | track length, shape, banking, road-course turn counts; cross-check source | https://www.rotowire.com/racing/tracks.php |
| S005 | Kyle Grealis / CRAN | nascaR.data package and data documentation | open historical race-results dataset documentation | Secondary-data | race-by-race fields: season, race, track, start, finish, laps, led, rating; sourced with permission from DriverAverages.com | https://www.kylegrealis.com/nascaR.data/ |
| S006 | FASTLAP | FASTLAP glossary | analytics methodology | Secondary-analytics | dominance, practice, running position, luck delta and simulation metric definitions | https://fastlap.io/glossary |
| S007 | Lap Raptor | NASCAR Advanced Stats & Results | advanced statistics platform | Secondary-analytics | loop data and track/driver analytical research from 2017 onward | https://www.lapraptor.com/dashboard/ |
| S008 | Lap Raptor | NASCAR Driver Stats by Track Index | track-index reference | Secondary-analytics | track-indexed advanced driver statistics | https://www.lapraptor.com/indexes/nascar/stats-by-track |
| S009 | Fantasy Racing Cheat Sheet | NASCAR track groupings | comparables framework | Secondary-analytics | data-informed track grouping by shape, length and banking | https://fantasyracingcheatsheet.com/nascar/track-groups |
| S010 | Action Network | NASCAR DFS strategy and track-type guidance | DFS/betting analysis | Secondary-editorial | long-run practice emphasis, track-type context and market strategy | https://www.actionnetwork.com/nascar |
| S011 | iFantasyRace | NASCAR similar-track analysis | DFS comparables | Secondary-editorial | track similarity and historical fantasy application | https://ifantasyrace.com/ |
| S012 | Jayski | 2015 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2015 points-race universe | https://www.jayski.com/nascar-cup-series/2015-nascar-cup-series-race-results/ |
| S013 | Jayski | 2016 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2016 points-race universe | https://www.jayski.com/nascar-cup-series/2016-nascar-cup-series-race-results/ |
| S014 | Jayski | 2017 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2017 points-race universe | https://www.jayski.com/nascar-cup-series/2017-nascar-cup-series-race-results/ |
| S015 | Jayski | 2018 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2018 points-race universe | https://www.jayski.com/nascar-cup-series/2018-nascar-cup-series-race-results/ |
| S016 | Jayski | 2019 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2019 points-race universe | https://www.jayski.com/nascar-cup-series/2019-nascar-cup-series-race-results/ |
| S017 | Jayski | 2020 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2020 pandemic-adjusted points-race universe | https://www.jayski.com/nascar-cup-series/2020-nascar-cup-series-race-results/ |
| S018 | Jayski | 2021 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2021 points-race universe | https://www.jayski.com/nascar-cup-series/2021-nascar-cup-series-race-results/ |
| S019 | Jayski | 2022 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2022 points-race universe | https://www.jayski.com/nascar-cup-series/2022-nascar-cup-series-race-results/ |
| S020 | Jayski | 2023 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2023 points-race universe | https://www.jayski.com/nascar-cup-series/2023-nascar-cup-series-race-results/ |
| S021 | Jayski | 2024 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2024 points-race universe | https://www.jayski.com/nascar-cup-series/2024-nascar-cup-series-race-results/ |
| S022 | Jayski | 2025 NASCAR Cup Series race results | schedule/results archive | High-quality secondary | 2025 points-race universe | https://www.jayski.com/nascar-cup-series/2025-nascar-cup-series-race-results/ |
| S023 | NASCAR | Atlanta 'one-of-one' in uniqueness as surface ages | official configuration analysis | Primary | 2022 reconfiguration: banking 24 to 28 degrees, width 55 to 40 feet, drafting style | https://www.nascar.com/news-media/2024/02/24/atlanta-one-of-one-unique-surface-ages/ |
| S024 | NASCAR | Drivers eager to see newly repaved Texas Motor Speedway | official configuration report | Primary | 2017 Texas repave and asymmetric 20/24-degree banking | https://www.nascar.com/news-media/2017/04/06/drivers-eager-to-see-newly-repaved-texas-motor-speedway/ |
| S025 | NASCAR | Kentucky Speedway to add layer of asphalt | official configuration report | Primary | 2016 reconfiguration, repave, increased Turns 1-2 banking | https://www.nascar.com/news-media/2016/10/10/kentucky-speedway-to-add-layer-of-asphalt/ |
| S026 | NASCAR | Phoenix Raceway through the years | official track history | Primary | 2018 start/finish relocation and championship-era context | https://www.nascar.com/gallery/flashback-phoenix-raceway-changes-through-the-years/ |
| S027 | NASCAR | Sonoma's twists present next road-racing test | official configuration report | Primary | 2.52-mile carousel in 2019/2021; 1.99-mile chute layout from 2022 | https://www.nascar.com/news-media/2022/06/08/cup-series-2022-sonoma-raceway-preview-next-gen/ |
| S028 | NASCAR | Cup Series drivers bracing for reconfigured Roval | official configuration report | Primary | 2024 Roval revision, 2.28 miles, 17 turns | https://www.nascar.com/news-media/2024/10/09/cup-series-2024-playoffs-charlotte-road-course-reconfiguration-reaction/ |
| S029 | NASCAR | What to Watch: 2025 Circuit of The Americas | official configuration report | Primary | full-course first four races and 2025 shortened layout | https://www.nascar.com/news-media/2025/03/01/what-to-watch-2025-circuit-of-the-americas/ |
| S030 | NASCAR | Christopher Bell wins on shortened COTA | official race report | Primary | 2.4-mile, 17-turn short COTA confirmation | https://www.nascar.com/news-media/2025/03/02/2025-nascar-cup-series-circuit-of-the-americas-race-recap/ |
| S031 | NASCAR | NASCAR to race in San Diego in 2026 | official venue announcement | Primary | first Cup race at Naval Base Coronado | https://www.nascar.com/news-media/2025/07/23/nascar-heads-to-san-diego-in-2026-for-street-races-at-naval-base-coronado/ |
| S032 | NASCAR | San Diego race course revealed | official configuration report | Primary | 3.4-mile, 16-turn street circuit | https://www.nascar.com/news-media/2025/10/21/san-diego-race-course-revealed-for-naval-base-coronado/ |
| S033 | NASCAR | San Diego Cup race recap | official race report | Primary | first completed Cup race on 3.4-mile, 16-turn Qualcomm Circuit | https://www.nascar.com/news-media/2026/06/21/nascar-cup-series-naval-base-coronado-results-recap/ |
| S034 | NASCAR | NASCAR pauses Chicago Street Race for 2026 | official schedule status | Primary | Chicago Street Course absent in 2026, future return possible | https://www.nascar.com/news-media/2025/07/18/nascar-puts-pause-on-chicago-street-race-for-2026/ |
| S035 | NASCAR | Chicagoland returns to NASCAR schedule in 2026 | official schedule/configuration report | Primary | 1.5-mile oval returns after 2019 | https://www.nascar.com/news-media/2025/08/20/chicagoland-returns-to-nascar-schedule-in-2026/ |
| S036 | NASCAR | Cup Series to forgo restrictor plates at Daytona and Talladega | official rules report | Primary | plates retired after 2019 Daytona 500; tapered spacer replacement | https://www.nascar.com/news-media/2018/10/02/monster-energy-series-no-restrictor-plates-dayton-talladega/ |
| S037 | NASCAR | Talladega 101: 2019 rules package | official rules report | Primary | first Talladega tapered-spacer superspeedway package | https://www.nascar.com/news-media/2019/04/24/talladega-101-tv-times-tires-rules-package-in-play-this-weekend/ |
| S038 | NASCAR | NASCAR announces 2019 baseline rules packages | official rules report | Primary | 550-hp/high-downforce package on many larger ovals | https://www.nascar.com/news-media/2018/10/02/2019-rules-packages-announced-monster-energy-series/ |
| S039 | NASCAR | NASCAR officials boost horsepower at select tracks for 2026 | official rules report | Primary | 750 hp at road courses and ovals under 1.5 miles in 2026 | https://www.nascar.com/news-media/2025/10/08/nascar-officials-to-boost-cup-series-horsepower-on-select-tracks-in-2026/ |
| S040 | NASCAR | North Wilkesboro points-race return preview | official race preview | Primary | first points-paying Cup race since 1996; 2026 pre-race status | https://www.nascar.com/news-media/2026/07/18/cup-series-2026-what-to-watch-north-wilkesboro-preview/ |
| S041 | NASCAR | 2026 Cup standings after EchoPark | official current standings | Primary | snapshot confirms Race 20 of 36 completed through July 12, 2026 | https://www.nascar.com/standings/nascar-cup-series/ |

## Appendix A — Explicitly deferred non-points events

The Clash (including Los Angeles Memorial Coliseum and Bowman Gray), All-Star Race/Open (including North Wilkesboro and 2026 Dover), Daytona qualifying races and other exhibitions are outside the points-race analytical sample. They may be valuable for practice, tire or configuration context, but must be stored with `event_format_id=non_points` and must not be silently merged with ordinary Cup points races.

## Appendix B — Machine-readable file relationships

- `nascar_cup_track_configurations.csv`: one row per physical configuration with counts, priors, comparables and citations.
- `nascar_cup_track_audit_bundle.json`: metadata, schedule mapping, track records, metric definitions, source ledger and limitations.
- `nascar_track_similarity_edges.csv`: up to five structural neighbors per configuration within the same supergroup.
- `nascar_track_sources.csv`: standalone source ledger.
- `nascar_cup_track_audit_2015_2026.md`: this report.

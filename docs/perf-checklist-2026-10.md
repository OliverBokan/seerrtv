# Performance checklist — October 2026

This is the working list for the findings in
[perf-review-2026-10.md](perf-review-2026-10.md). The review has the full reasoning and the
measurements; this file tracks what's done.

We work through one item at a time. When an item is fixed:
- Tick it.
- Note how it was verified.
- Add an entry under `## 0.34.0` in `CHANGELOG.md` (Symptom / Root cause / Fix / Verified).

Everything stays uncommitted on main and ships with 0.34.0. There is no new version bump.

Paths are relative to `tv/src/main/java/ca/devmesh/seerrtv/`. Line numbers are as of `9aeaa43`
plus the uncommitted 0.34.0 work, so re-check them before editing.

## How to measure (before and after each item)

The scripts and recorded results live in [`tools/perf/`](../tools/perf/README.md).

```bash
tools/perf/build-instrumented.sh
```

```bash
tools/perf/run-scenarios.sh after-N1 3
```

- `build-instrumented.sh` builds main's working tree, including uncommitted changes, plus a
  request logger. It builds in a scratch worktree, so the logger never touches main. It then
  installs the build on `emulator-5554`.
- `run-scenarios.sh` runs the four scenarios three times and writes medians to
  `tools/perf/results/<label>/summary.md`.
- Compare that summary with the baseline below.

### Baseline: `tools/perf/results/baseline-2026-10-22/`

Recorded 2026-10-22. Debug build of 0.34.0 as it stands on main (`9aeaa43` plus the uncommitted
keyword-filter work), on the `Google_TV_1080p` emulator against a test Seerr server on the LAN. Values are
medians of 4 runs, alternated run by run with the after-N1 build so host noise hits both evenly.
Request counts were identical in every run.

Times are seconds from `am start` unless noted. Frame numbers come from a debug build on the
emulator, so use them only for before/after comparisons on the same setup.

| Scenario | Metric | Baseline | Target items |
|---|---|---|---|
| Cold start (empty image cache) | `am start` TotalTime | 990 ms | B1 |
| | API calls | **73** | N1/N2, N6, small items |
| | API payload | **2,074 KB** | N1/N2 |
| | Duplicate API calls | **6** | N2, N6, small items |
| | Per-card `movie/{id}` / `tv/{id}` calls | **35** | N2 |
| | First API call | 2.13 s | — |
| | First home-row request | **8.48 s** | N5 |
| | First poster image | **13.92 s** | N1/N2/N5 |
| | All home rows have data | **14.55 s** | N1/N2/N5 |
| | Image calls / KB | 14 / 1,410 KB | N9 |
| Home row loading (cold), from the first home-row request | Recent Requests row has data | **5.55 s** | N1 |
| | Recently Added row has data | **6.36 s** | N2 |
| | Your Watchlist row has data | 1.88 s | small items |
| | Other discover rows | 0.5–1.1 s | — |
| Warm start (image cache kept) | `am start` TotalTime | 923 ms | B1 |
| | API calls / KB | 73 / 2,074 KB | N2 |
| | First home-row request | 7.44 s | N5 |
| | All home rows have data | 13.07 s | N1/N2/N5 |
| | Recent Requests / Recently Added row has data (from the first home-row request) | 5.04 / 5.67 s | N1 / N2 |
| D-pad scroll (30 RIGHT + 5 DOWN on home) | Image calls / KB | **76 / 7,068 KB** | R2 |
| | `w1280` backdrops | **31** | R2 |
| | Frames / deadline missed | 578 / **30.5** | R1–R7 |
| | p50 / p90 / p99 frame | 21 / 32 / 66.5 ms | R1–R7 |
| | Slow UI thread frames | 20.5 | R1–R7 |
| | PSS after scroll | 145 MB | R2, N8 |
| Open movie details (1st row, 1st card) | API calls / KB | 4 / 85 KB | N4 |
| | Duplicate API calls | 1 (`ratingscombined` ×2) | N4 |
| | Last API response | 0.58 s | N4 |
| | Image calls / KB | 25 / 720 KB | N8 |
| | `original`-size images | **1** | N8 |
| Back to home | API / image calls | 0 / 0 (fine) | — |
| Idle on home for 65 s (measured by hand) | Requests | 0 (fine) | — |

Duplicates seen on every start:
- `/settings/public` ×3
- `/media?filter=allavailable` ×2
- `/request` ×2
- `/discover/watchlist` ×2
- the same `movie/{id}` ×2

### Final result (all fixes): `tools/perf/results/final-2026-10-22`

Single run on a freshly booted emulator, after every item in this checklist. The summary in that
folder lists every metric next to its baseline value.

| | Before | After all fixes |
|---|---|---|
| API calls per launch | 73 | **35 (−52%)** |
| JSON per launch | 2,074 KB | **266 KB (−87%)** |
| Duplicate API calls per launch | 6 | **1** |
| Per-card details calls (from the 2nd launch) | 35 | **1** |
| Cold start: all home rows have data | 14.55 s | **3.67 s (−75%)** |
| Warm start: all home rows have data | 13.07 s | **3.29 s (−75%)** |
| Home opens (splash closes) | ~8.5 s, then ~6 s of placeholders | **~4.9 s, rows already filled** |
| Home D-pad scroll: p90 / p99 frame | 32 / 66.5 ms | **24 / 32 ms** |
| Home D-pad scroll: frames missing their deadline | 30.5 | **9 (−70%)** |
| Home D-pad scroll: slow UI-thread frames | 20.5 | **5 (−76%)** |
| Opening movie details | 4 calls (1 duplicate), 720 KB of images, a 4K `original` backdrop | **3 calls, 505 KB, none** |
| Fast scroll (15 presses): backdrop downloads | 11 (same-session A/B) | **1** |
| Filters drawer, second open | 4 requests | **0** |
| Baseline profile: rules for cards / carousel / details / browse | 0 / 0 / 0 / 0 | **102 / 142 / 224 / 199** |

**Release builds** (`tools/perf/results/release-2026-10-22`, via `tools/perf/release_compare.py`):
`benchmarkRelease` of 0.33.0 against 0.34.0. Both use R8 and are compiled with `speed-profile`
from their own baseline profile, as a Play install would be. Medians of 3 alternating rounds.

| | 0.33.0 | 0.34.0 |
|---|---|---|
| Home shows media cards after launch | 13.1 s | **6.7 s (−49%)** |
| First frame (splash) | 94 ms | 96 ms |
| D-pad scroll: p90 / p99 frame | 21 / 27 ms | **19 / 23 ms** |
| D-pad scroll: frames drawn in the same run | 582 | **635** |

Release builds are already smooth on the emulator (p50 17 ms either way), so most of the gain
users will feel is the time to a usable home screen. The "home shows cards" time is polled through
the accessibility tree, about 2 s per check, so it reads high in both columns. The new profile's own
contribution is not separated out: each build ran with its own profile.

Only `baseline-2026-10-22` and `final-2026-10-22` are kept in `tools/perf/results`, and only their
summaries are tracked (see `.gitignore`). The per-fix numbers below come from runs that were
deleted afterwards.

### Progress

| Item | Metric | Before | After | Results |
|---|---|---|---|---|
| N1 | Recent Requests row has data, cold (from the first home-row request) | 5.55 s | **3.29 s (−41%)** | 2026-10-22 run |
| N1 | Same, warm | 5.04 s | **3.25 s (−36%)** | 2026-10-22 run |
| N1 | All home rows have data, cold | 14.55 s | 13.71 s | Still gated by Recently Added (N2) |
| N2 + card cache | API calls per launch (from the 2nd launch) | 72 | **39** | same-session A/B, 2026-10-22 |
| N2 + card cache | Recently Added + Recent Requests filled, cold (from the first home-row request) | 6.1 s | **1.7 s** | same |
| N4/N8 | Details open: API calls / image KB | 4 / 720 KB | **3 / 486 KB** | 2026-10-22 run |
| N6 slice | API calls per launch / duplicates | 39 / 5 | **37 / 3** | 2026-10-22 run |
| /settings/public | API calls per launch / duplicates | 37 / 3 | **35 / 1** | 2026-10-22 run |
| N5 (splash sleeps) | First API call → first home-row request | 6.35 s | **2.0 s** | 2026-10-22 run |
| All so far | All home rows have data, cold (emulator ~3× slower than at baseline) | 14.55 s | **7.87 s** | 2026-10-22 run |
| N5 (early rows, Sonarr/Radarr together) | First API call → first home-row request | 6.35 s | **0.95 s** | 2026-10-22 run |
| R1–R10 (frames), same-session A/B vs the original build | p50 / p99 frame while scrolling home | 61 / 250 ms | **48 / 200 ms** | same-session A/B, 2026-10-22. Emulator slowed during the run, so compare only the two columns. |
| R1–R10 (frames) | Frames drawn in the same scroll run (more = smoother) | 365 | **448** | Slow-UI-thread frames unchanged (170 → 194): R4/R5 are the remaining main-thread cost |
| R2 | Fast scroll (15 RIGHT back-to-back): `w1280` backdrops / image KB | 10.5 / 2,506 KB | **1 / 721 KB** | 2026-10-22 run |
| Next | Re-record frame baselines once the emulator is back to ~1 s cold starts | | | |

Not covered by the script, so measure by hand when working on these items:
- **N6:** the refresh after a request, because it creates data on the server.
- **N9:** the avatar, which was measured once at 870 KB.
- **N11:** opening the filters drawer.

---

## Tier 1 — small, safe, high impact

- [x] **N1 — Load Recent Requests card details in parallel** — done 2026-10-22, see Progress
  - Where: `viewmodel/SeerrViewModel.kt:2432-2507`
  - Problem: there is one `coroutineScope { async {} }` per item inside `map`, so the 20 detail
    calls run serially.
  - Fix:
    - Put one `coroutineScope` around the whole list.
    - Run an `async` per item, gated by `Semaphore(4)`, then `awaitAll()`.
    - Keep the concurrency at or below 4. OkHttp allows 5 requests per host, so 4 leaves room
      for other rows.
  - Verify: the PerfNet log shows parallel `movie/` and `tv/` calls; row order is unchanged.
  - **Result:**
    - The row has data 3.29 s after home loading starts, down from 5.55 s cold, and 3.25 s
      down from 5.04 s warm.
    - Row order and the request action modal were unchanged.
    - The load-more path was not exercised, because the test server has a single page of
      requests.
    - Concurrency stays at 4 (`CARD_DETAILS_CONCURRENCY`). Seerr fetches TMDB for every
      details call, so with more calls in flight each one got slower (about 0.2 s → 0.45 s).
      Adding more parallelism mostly moves the wait around.

- [x] **N2 — Load Recently Added card details in parallel, and share a details cache** — done 2026-10-22. Parallelism alone didn't shorten the total (the server is the bottleneck), so card metadata is now kept for 24 h in `CardMetadataStore`. From the second launch: 72 → 39 API calls, 2,025 → 326 KB, both rows filled in about 1.7 s instead of 6.1 s. See 2026-10-22 run.
  - Where: `viewmodel/SeerrViewModel.kt:2388-2405`
  - Problem: a plain serial `map` with one details call per item.
  - Fix:
    - Same pattern as N1.
    - Add an in-flight + 5-minute details cache, shared by both rows and by the details screen.
  - Verify:
    - A title that appears in both rows is fetched once.
    - Opening details for a home card doesn't fetch `tv/{id}` again.

- [x] **N3 — Stop wiping the image caches after a request** — done 2026-10-22 (not measured end to end: a test request can start real downloads)
  - Where:
    - `ui/RefreshManager.kt:47-49` (`clearImageCachesAsync`)
    - `ui/MainScreen.kt:1305-1308`
  - Problem: the whole Coil memory **and** disk cache is cleared, so every image is downloaded
    and decoded again.
  - Fix:
    - Remove both calls, or evict a single key if something really must refresh.
    - First check the git log and blame to see why the clear was added.
  - Verify: after a request, home shows 0 image requests for images that were already loaded.

- [x] **N4 — Fetch movie ratings once, after details** — done 2026-10-22: ratings run alongside details, and the first poll cycle reuses the screen's fetch. Details open: 4 → 3 API calls, 0 duplicates.
  - Where: `viewmodel/SeerrViewModel.kt:2079-2081` and `:2023-2025`
  - Problem: details, then ratings via `fetchMovieDetails`, then ratings again via
    `getRatingsCached`, which misses. Polling refetches ratings every cycle too (`:3444-3446`).
  - Fix:
    - Remove ratings from `fetchMovieDetails`.
    - Publish details right away, then merge in ratings from `getRatingsCached`.
  - Verify: opening a movie makes one `ratingscombined` call, and the poll makes none.

- [x] **N7 — Stop building large log strings on Main in release** — done 2026-10-22: 5 whole-object dumps are behind `DEBUG`. Together with the BuildConfig fix, release compiles them out.
  - Where: `viewmodel/SeerrViewModel.kt:2136-2138` (logs the whole TV `MediaDetails`), `:2049`,
    `:304`; `data/SeerrApiService.kt:2020`
  - Fix:
    - Wrap these in `if (BuildConfig.DEBUG)`.
    - Optional: add a `-assumenosideeffects` rule for `Log.d/v/i` to `tv/proguard-rules.pro`.
  - Verify: release logcat no longer shows the dumps.

- [x] **N8 — Use `w1280` instead of `original` backdrops** — done 2026-10-22, plus home cache keys on details. Details open: 720 → 486 KB of images, 0 originals.
  - Where: `ui/MediaDetails.kt:2177`, `ui/PersonScreen.kt:603`, `:634-635`
  - Fix:
    - Change `original` to `w1280`.
    - On PersonScreen, also debounce the backdrop target.
  - Verify: PerfNet shows no `/t/p/original` requests.

- [x] **R1 — Stable home card keys** — done 2026-10-22 (keys deduplicated with a `#n` suffix, plus `contentType`)
  - Where: `ui/components/EnhancedMediaCarousel.kt:1067-1076`
  - Problem: the key contains `isItemSelected`, so each press disposes and recreates two cards,
    and the focus-scale animation never plays.
  - Fix:
    - Key on `"${item.id}_${item.mediaType}"`, deduped across pages, because duplicate keys
      crash a lazy list.
    - Add `contentType`.
  - Verify:
    - Focus zoom animates.
    - Pagination still works.
    - The placeholder still positions correctly.
    - Frame comparison against the baseline.

- [x] **R2 — Debounce the home backdrop and keep a single crossfade** — done 2026-10-22: 250 ms settle, gradient drawn once. Coil's crossfade is kept, since it only animates network loads. With the new `fastscroll` scenario (15 presses back-to-back), backdrops went 10.5 → 1 and image traffic 2.5 → 0.7 MB (2026-10-22 run vs 2026-10-22 run).
  - Where: `ui/MainScreen.kt:1750-1754`, `:1543-1546`, `:2200-2260`
  - Problem: a Compose `Crossfade` around a Coil crossfade, with the gradient drawn in each
    layer, on every press.
  - Fix:
    - Debounce the backdrop target by ~250 ms, separately from the details text.
    - Keep one crossfade.
    - Draw the gradient once, outside the `Crossfade`.
  - Verify: 30 presses produce a handful of `w1280` requests instead of 17.

- [x] **R3 — Make `ApiResult.Loading` a `data object`** — done 2026-10-22
  - Where: `data/SeerrApiService.kt:131`; call sites at `ui/MainScreen.kt:2090`, `:2092`,
    `:2123`, and others (grep for `Loading()`)
  - Problem: a new, never-equal instance each recomposition restarts
    `LaunchedEffect(apiResult)` (`ui/CarouselSection.kt:134`), which triggers `loadMoreForCategory`
    and recomposes every row.
  - Fix: `data object Loading`, and replace `Loading()` with `Loading` everywhere.
  - Verify: it compiles, and the row loading spinners still show.

- [x] **R4a — Wrap `visibleCategories` in `remember`** — done 2026-10-22. `rowList` is already stable: `ifEmpty` returns the same instance.
  - Where: `ui/MainScreen.kt:560-562`, plus `rowList` at `:2073` and `:2159`
  - Fix: `remember(allActiveRows) { … }`. This is the small first slice of R4.
  - Verify: the home rows section can skip recomposition (compiler reports or Layout
    Inspector).

## Tier 2 — next

- [x] **N5 — Splash sleeps and serial Sonarr/Radarr loading** — *done 2026-10-22* (your call: pause only on warnings and errors). First API call → first home-row request: 6.35 → 2.0 s. Sonarr/Radarr concurrency and the early `loadAllCategories()` were also done 2026-10-22 (early start only when no profile picker follows).
  - Where:
    - `MainActivity.kt:350-380`: 300 ms per INFO step, 800 ms per SUCCESS step, and a 100 ms
      trailing delay, about 4.8 s in total
    - `data/SeerrApiService.kt:2458-2469` and `:2510-2521`: one server at a time
    - `MainActivity.kt:403`, `:452`: Sonarr, then Radarr, in sequence
  - Fix:
    - Use one minimum splash duration instead of per-step sleeps.
    - Load Sonarr and Radarr concurrently, with an `async` per server.
    - Start `loadAllCategories()` as soon as auth succeeds.
  - Verify: the gap from the first API call to the first home-row request drops from ~7 s.

- [x] **R7 — Focus scale through `graphicsLayer`** — done 2026-10-22 for MediaCard, CategoryCard and InstalledAppsRow. FiltersDrawer was left alone (0.34.0 keyword work).
  - Where: `ui/components/MediaCard.kt:79-83`, `ui/MainScreen.kt:2534-2541`,
    `ui/InstalledAppsRow.kt:101-113`, `ui/components/FiltersDrawer.kt:2957-2965`
  - Fix: keep the `State` and use
    `Modifier.graphicsLayer { scaleX = s.value; scaleY = s.value }` instead of `Modifier.scale`.

- [ ] **R8 — Only scroll when the target is off-screen** — *on review (2026-10-22): the grids deliberately pin the focused row to the top, so the scroll on each up/down is intended, and it does nothing when the row is already there. Changing it is a UX decision; left as is.*
  - Where:
    - `ui/MediaBrowseScreen.kt:1077` and `ui/MediaDiscoveryScreen.kt:1254` (`ensureRowIsVisible`)
    - `ui/MainScreen.kt:2370-2373` (custom slider)
    - `ui/components/CarouselComponents.kt:158-160` and `:238-240` (cast and similar)
    - `ui/MediaBrowseScreen.kt:796` and `:821`, which read `currentFocus` during composition
  - Fix:
    - Check against `layoutInfo.visibleItemsInfo` before scrolling, as PersonScreen and
      FiltersDrawer already do.
    - Use `derivedStateOf` for the sort/filters-selected flags.

- [ ] ~~**N9 — Stable cache key for the avatar** (870 KB)~~ — *won't do (2026-10-22): the avatar is already served from Coil's disk cache on later launches (warm start: 0 image calls). Only the first launch, or a changed avatar (new `?c=`), downloads it, which is correct behaviour.*
  - Where: `ui/components/ProfileAvatar.kt:51-55`
  - Fix: `memoryCacheKey`/`diskCacheKey` built from the user id plus `c`.

- [x] **N10 — Lighter details polling** — done 2026-10-22: 2 min when nothing is in progress; Similar is keyed on the title id.
  - Where: `viewmodel/SeerrViewModel.kt:3346-3365`; `ui/MediaDetails.kt:432-439`
  - Fix:
    - Stop or back off the poll when nothing is pending.
    - Key the Similar-reload effect on `media.id`, not on the whole details object.

- [x] **N11 — Cache the filters drawer's reference lists** — done 2026-10-22 (session cache in the ViewModel; reopening the drawer makes 0 requests; logos at `w154`) (after the 0.34.0 keyword work is
  final)
  - Where: `viewmodel/MediaDiscoveryViewModel.kt:879-949`, `ui/components/FiltersDrawer.kt:154-167`,
    `:2644-2648`, `:2993`
  - Fix:
    - Cache regions, languages, genres, networks and providers per locale/region.
    - Load them in parallel.
    - Request provider logos at `w92` instead of `w500`.

- [x] **R9 — Add `key` / `contentType` to lazy lists** — done 2026-10-22 with a shared `uniqueLazyKeys` helper (FiltersDrawer lists left alone: 0.34.0 keyword work)
  - Where: `ui/MainScreen.kt:2399`, `:2077` (contentType only);
    `ui/components/CarouselComponents.kt:168`, `:254`; `ui/components/DiscoveryGrid.kt:98`;
    `ui/PersonScreen.kt:826`, `:902`; `ui/components/FiltersDrawer.kt:507`, `:1384`, `:1472`,
    `:1865`, `:2949`

- [x] **R10 — Selection reaches rows and grids in the same frame** — done 2026-10-22
  - Where: `ui/MainScreen.kt:2034-2038`, `ui/components/DiscoveryGrid.kt:48-53`
  - Problem: the selected index is copied into per-row state inside a `LaunchedEffect`, so the
    highlight lands one frame late.
  - Fix: derive the per-row selected index directly during composition.

- [x] **R6 — Rows collect only their own slice of ViewModel state** — done 2026-10-22, using `derivedStateOf` slices inside the carousel (no hoisting needed)
  - Where: `ui/components/EnhancedMediaCarousel.kt:103`, `:107`, `:120`, `:375`; content key at
    `:1008-1015`
  - Fix:
    - Collect the flows once in `ScrollableCategoriesSection` and pass each row its own slice.
    - Compute the content key inside `remember(items)`.

## Tier 3 — refactors (each its own change, with focused D-pad testing)

- [x] **N6 — One refresh path after request / delete / approve** — *done and verified 2026-10-22 (test request for an unreleased title, then Remove from Radarr): return to home refreshes in 0.46 s with the D-pad usable immediately (was ~3.5 s locked); a request causes 2 `/request` calls, a removal 3, and no card-details calls:* forced refreshes are awaited and coalesced, and home's 2 s + 1.5 s key-blocking waits are replaced by waiting for the refresh job. Earlier the same day: resets no longer fetch (`resetApiPagination`, `clearCategoryData`, `loadCategory`). Launch: 39 → 37 calls, Recently Added and Recent Requests ready about 1 s sooner. Still left: collapse the repeated refresh calls and the 500 ms / 2 s timing heuristics.
  - Where:
    - `viewmodel/SeerrViewModel.kt:886-911` (`resetApiPagination` performs real fetches)
    - `:936-940`
    - `:810-880` (`refreshCategoryWithForce`, plus a 500 ms "empty" retry)
    - `ui/RefreshManager.kt:43-45`
    - `ui/MainScreen.kt:1276-1316`
    - `:1911`
    - `viewmodel/SeerrViewModel.kt:2536`, `:2846`
  - Fix:
    - Make the reset a pure state change (`apiService.resetPaginationState(key)`).
    - Keep one refresh call and drop the timing heuristics.
  - Test: request, delete and approve flows. Count `/request` calls; today it's about 7 per
    request.

- [x] **R4 — Stop recomposing the whole MainScreen on every D-pad press** — done 2026-10-22, scoped: the app root and `TopBarController` no longer recompose per press (`derivedStateOf`), and the D-pad configs are stable (`rememberStableDpadConfig`). `MainScreen` itself still recomposes per press because the details header follows the selection; splitting it further would mean moving per-press reads into leaf composables across ~1,800 lines.
  - Where:
    - `ui/MainScreen.kt:438-446` (`setSelection`), which writes
      `ui/focus/AppFocusManager.kt:19`
    - Reads during composition: `ui/MainScreen.kt:168`, `MainActivity.kt:822-843`,
      `ui/components/TopBarController.kt:126`
    - D-pad configs rebuilt every press: `ui/MainScreen.kt:961-1043` and
      `ui/components/TopBarController.kt:363-379`
  - Fix:
    - Handlers read focus when they run, not during composition.
    - Build the D-pad configs once with `remember` + `rememberUpdatedState`.
    - Wrap `TopBarFocusState` in `derivedStateOf`.
  - Test: top bar ⇄ rows ⇄ custom sliders ⇄ apps row.

- [x] **R5 — Cancellable carousel scrolling** — done 2026-10-22: the latest selection's scroll job is kept and the previous one cancelled; `NonCancellable` removed from the selection path; `safeScrollToItem` rethrows cancellation. The pagination placeholder path (which still uses `NonCancellable`) is unchanged.
  - Where: `ui/components/EnhancedMediaCarousel.kt:179-209`, `:378-386`, `:473-588`, `:634-639`
  - Fix:
    - Use one `snapshotFlow { selectedIndex.value }.collectLatest { animateScrollToItem(...) }`.
    - Remove `NonCancellable`, the `delay(50)` re-checks and the "emergency" second scroll.
  - Test:
    - Holding RIGHT.
    - Pagination placeholder positioning (`:634-871`).

## Tier 4 — lock in the gains

- [x] **B2 — Compose compiler reports and stability config** — done 2026-10-22. Reports are opt-in (`-PcomposeReports=true`). They show 189/189 app composables skippable with strong skipping and 157 unstable arguments, compared by cheap identity. A stability config would swap that for `equals()` on model lists, so none was added. `Media` is already inferred stable; `MediaDetails` is unstable only through an unused `var mediaType`.
  - Fix:
    - Add a `composeCompiler { reportsDestination; metricsDestination }` block, gated on a
      Gradle property.
    - Add a `stabilityConfigurationFiles` entry listing `ca.devmesh.seerrtv.model.*` and
      `kotlin.collections.*`.
  - Use the reports to confirm R4, R6 and R9. This could also be done earlier, as a diagnostic.

- [x] **B1 — Regenerate the baseline profile with real journeys** — done 2026-10-22: `startup` + `journeys` tests that wait for real posters; journeys restart the app between segments (killProcess) instead of navigating back. The profile now has 33,472 rules, covering cards, carousels, details, browse and the Discovery grid; the startup profile is separate. Not yet done: a Macrobenchmark to measure it on release builds.
  - Problem: the current profile (generated 2026-09-14) has no entries for MediaCard, the
    carousels, details, browse, discovery, filters, person or search. The only card-related
    entry is `MediaCardPlaceholder`. `startup-prof.txt` is byte-identical to
    `baseline-prof.txt`.
  - Fix (`baselineprofile/.../StartupBaselineProfileGenerator.kt`):
    - Start from a signed-in device.
    - Wait for a real content node (a `testTag` on the first `MediaCard`) instead of
      `waitForIdle`.
    - Split the generators:
      - A startup-only generator with `includeInStartupProfile = true`.
      - Journey generators with `false`, covering home row scroll + pagination,
        details → cast/similar, person, browse + sort/filters, discovery, search and settings.
    - Add a Macrobenchmark with `FrameTimingMetric` for home horizontal scroll and opening
      details.
  - Do this last, after the UI fixes have landed.

## Smaller items (pick up opportunistically)

- [x] `/settings/public` fetched 3× at startup — done 2026-10-22: one shared response, 30 s TTL. 37 → 35 calls.
  - Where: `data/SeerrApiService.kt:2291`, `:2293`; `MainActivity.kt:~501`
  - Fix: fetch once and parse the server type and the hide flags together.
- [x] Custom sliders force-loaded twice — done 2026-10-22 (not verified: the test server has no custom sliders)
  - Where: `ui/MainScreen.kt:2144-2147`
  - Fix: `forceRefresh = false`.
- [ ] Watchlist fetched twice *(low value: on the test server the extra call is 195 bytes; it's the membership check running alongside the row)*
  - Where: membership pages are fetched serially (`data/SeerrApiService.kt:2634-2652`), and the
    row fetches page 1 again (`viewmodel/SeerrViewModel.kt:1661-1691`).
  - Fix: reuse page 1 and bound the enrichment.
- [x] Studio/network logo details are fetched serially, 6 per page — done 2026-10-22 (parallel per page)
  - Where: `data/SeerrApiService.kt:3098-3116`, `:3189-3224`
  - Fix: parallelize or persist them.
- [x] **Bug:** Upcoming rows' pagination reset key mismatch — fixed 2026-10-22 together with the N6 slice below
  - Where: `data/SeerrApiService.kt:1617-1635`
  - Problem: a refresh fetches the next page and resets Popular instead.
- [x] Profiles JSON is decoded on Main for every localized API call — done 2026-10-22 (memoized per stored string)
  - Where: `util/SharedPreferencesUtil.kt:575`, `:605`, `:1314`
  - Fix: memoize, and invalidate on save.
- [x] Main-thread `commit()` on every home load — done 2026-10-22 (skipped when unchanged)
  - Where: `saveCustomSliderMeta` (`util/SharedPreferencesUtil.kt:1397-1402`)
  - Fix: skip when unchanged, and use `apply()`.
- [x] No `Mutex` around re-login when a session expires — done 2026-10-22 (`refreshSessionOnce`)
  - Where: `data/SeerrApiService.kt:1022-1048`, `:1146-1170`
- [x] Details cache stores minutes as milliseconds, so entries are written already expired — fixed with N4 (the bad cache writes were removed)
  - Where: `viewmodel/SeerrViewModel.kt:2089-2108`
- [x] Image auth interceptor recompiles regexes for every image — done 2026-10-22 (origin cached per config)
  - Where: `getSeerrOrigin()` (`data/SeerrApiService.kt:526-546`)
  - Fix: cache the origin on config change.
- [x] 30 s connect timeout per splash step when the server is down — done 2026-10-22 (connect timeout now 10 s; read and request timeouts still 30 s)
  - Where: `data/SeerrApiService.kt:906`, `:936`
  - Fix: use about 10 s.
- [ ] ~~Response bodies are read as a `String` before decoding~~ — *won't do (2026-10-22): the text is kept for debug parse-failure logs, and since the card cache, large bodies are rare (about one 100 KB details call per screen). Streaming would need an experimental API for little gain.*
  - Where: `data/SeerrApiService.kt:1115-1117`, `:1305-1307`
  - Fix: stream-decode.
- [x] **BuildConfig: debug-only logging ran in release** — done 2026-10-22
  - `defaultConfig` declared `buildConfigField("Boolean", "DEBUG", "true")`, so release builds had
    `DEBUG = true`. All 396 `if (BuildConfig.DEBUG)` blocks ran in production: about 47 log calls
    per D-pad press on home, including a stack-trace capture on Back.
  - Separately, `SeerrViewModel.kt` imported the YouTube player library's `BuildConfig` (since
    `3dcfe4d`, 2026-03-17), so that file's debug logs were off even in debug builds.
  - Fix: removed the override, so release gets AGP's constant `false` and the blocks are
    compiled out. Fixed the import. Removed two `updateCategoryState` calls hidden behind the bad
    import, which haven't run in any build since March.
  - Verified: the release dex no longer contains the guarded log strings. See CHANGELOG 0.34.0.
  - This does **not** cover N7: those logs are unguarded and still run in release.
- [x] `AsyncImage` without `imageLoader` (unreachable today, so hygiene only) — done 2026-10-22
  - Where: `ui/MediaDiscoveryScreen.kt:749`, `:912`
- [x] `MediaCard` allocations — done 2026-10-22 (remembered requests, shared brushes, `ModulateAlpha` icon)
  - Where: `ui/components/MediaCard.kt` — the `ImageRequest` isn't remembered (`:408`); a new
    `Brush` per recomposition (`:273`, `:319`, `:401`); `graphicsLayer(alpha = 0.8f)` on the
    status icon (`:487`).
- [x] Clock recomposes every second and reads prefs each tick — done 2026-10-22 (ticks per minute)
  - Where: `ui/components/ClockComponent.kt:24-40`
  - Fix: tick per minute.
- [x] Writes during composition in the carousel — done 2026-10-22 (`SideEffect`; write-only state removed)
  - Where: `ui/components/EnhancedMediaCarousel.kt:1096-1100`; write-only states at `:335-346`,
    `:590`, `:1108`
- [x] Unused `androidx.tv:tv-foundation` dependency — removed 2026-10-22
  - Where: `tv/build.gradle.kts:316`
- [ ] Stale pooled connections: check Settings › Diagnostics for "unexpected end of stream"
  before changing anything
  - Where: `retryOnConnectionFailure(false)` with a 5-minute keep-alive
    (`data/SeerrApiService.kt:910-911`)
- [x] Docs only: Seerr doesn't gzip responses. Add a README/FAQ note recommending compression on — done 2026-10-22 (README FAQ)
  the reverse proxy.

## Wrap-up (before 0.34.0 ships)

- [x] Refresh the headline numbers in `perf-review-2026-10.md` — done 2026-10-22 (Status section at the top)
- [x] Re-record frame timings against the baseline — done 2026-10-22 as a same-session A/B (see Progress). Absolute numbers still depend on emulator health: a long-running emulator slows from ~0.8 s to 3–6 s cold starts.
- [x] Reinstall a normal (non-instrumented) build on `emulator-5554` — done 2026-10-22 (plain debug build of main)
- [ ] Commit the 0.34.0 work: the user commits everything together

## Don't change (already good)

- **Networking:**
  - A single API client with a connection pool.
  - Transparent gzip.
  - JSON is parsed on IO.
  - Cancellation is handled correctly.
- **Home and details loading:**
  - Home rows load in parallel.
  - 5-minute row and slider caches.
  - The ratings in-flight dedupe and 404 cache.
  - Details have a job dedupe, a mutex and a cooldown.
- **Polling and search:**
  - Polling stops on `ON_STOP` and on dispose. Measured: 0 requests while idle.
  - Search is debounced and cancels the previous job.
- **Images (Coil):**
  - One shared `ImageLoader` with bounded dispatchers.
  - Poster, hero and cast image sizes are right.
  - Stable cache keys, and only the visible images load.
- **Rendering:**
  - No blur.
  - The home column has stable row keys.
  - Visibility-guarded scrolling in PersonScreen and FiltersDrawer.
  - Debug logging is compiled out of release builds, since the BuildConfig fix above.
- **Build:**
  - R8 and resource shrinking are on.
  - `profileinstaller` is wired.

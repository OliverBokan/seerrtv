# SeerrTV performance review — October 2026

Scope: the `tv/` module, focused on **network** and **rendering** on low-end Android TV boxes.
Crash and ANR rates are already well under Play thresholds (≤0.09% crash, ≤0.12% ANR), so this
review is about speed and smoothness, not stability.

Paths are relative to `tv/src/main/java/ca/devmesh/seerrtv/` unless stated otherwise. Line
numbers refer to `main` at `9aeaa43`, plus the uncommitted 0.34.0 work.

## Status (end of 2026-10-22)

Most of this review has been implemented for 0.34.0 (uncommitted on main). Each item is tracked in
[perf-checklist-2026-10.md](perf-checklist-2026-10.md), and the CHANGELOG has an entry per fix. The
sections below describe the app **before** the work.

Final result: `tools/perf/results/final-2026-10-22`, compared with
`tools/perf/results/baseline-2026-10-22`. Debug build on a freshly booted Google TV emulator (cold
start ~0.7 s; ~1 s at baseline), same scenarios. Single final run; request counts are exact.

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

Every item in the checklist is done and verified on the emulator, including N6: a real request,
then Remove from Radarr. One caveat: the baseline profile only takes effect in release builds, so
these debug-build numbers do not include it.

## How this was measured

- **Build:** a debug build of `9aeaa43`, with a throwaway OkHttp interceptor that logs every
  API and image request (not committed). It ran on the `Google_TV_1080p` emulator against
  a test Seerr server on the LAN.
- **Cold start, signed in, warm image cache:**
  - `am start -W` TotalTime is about 800 ms.
  - Before the home screen settles, the app makes **73 API requests** totalling about
    **2.1 MB of JSON**, over about 14 s from process start.
  - Breakdown:

    | Phase | Requests | Notes |
    |---|---|---|
    | Splash (auth, settings, Sonarr/Radarr) | 12 | All serial. `/settings/public` is fetched **3×**. |
    | Home row lists | 16 | Fired in parallel. `/media?filter=allavailable` and `/request` are fetched **2×** each, and `/discover/watchlist` **2×**. |
    | Studio/network logos | 12 | Serial. |
    | Per-card `movie/{id}` and `tv/{id}` details | **35** (scripted count; see `tools/perf/results/baseline-2026-10-22`) | Two serial chains, Recently Added and Recent Requests, running side by side. That's about 5 s and about 1.9 MB (each details payload is 10–100 KB). One title appears in both rows and is fetched twice. |
- **Cold start with an empty image cache:** only 14 images load (just the visible ones — good).
  They total 1.4 MB, of which **870 KB is the user avatar** (`/users/{id}/avatar`), shown at
  about 40 dp.
- **Opening a TV details page:** `tv/{id}` is fetched **2×**, after it was already fetched once
  for the home card.
- **Back to home, and 65 s idle on home:** 0 requests. Back navigation and polling behave well.
- **D-pad across two rows (30 presses), then down four rows:** 48 image requests, 4.3 MB. That
  includes **17 `w1280` backdrops**: one per focused card, because the hero backdrop is not
  debounced.
- **Frame timing (`gfxinfo`):** debug build on an emulator, so only useful for before/after
  comparison, not as absolute numbers. Over the same D-pad run: p50 21 ms, p90 31 ms,
  14 of 332 frames missed their deadline.
- **Gzip:** OkHttp already sends `Accept-Encoding: gzip`, but Seerr itself does not compress
  (`/settings/public` returns no `Content-Encoding`). Compression only happens if the user's
  reverse proxy adds it. That's worth a README/FAQ line; there is no app change to make.

## Ranked findings

Impact is High / Med / Low; effort is S (≤½ day), M (1–2 days), L (more). Rank is roughly
impact ÷ effort.

### Network

**N1. Recent Requests loads card details one at a time.** High · S · risk low
- **Where:** `viewmodel/SeerrViewModel.kt:2432-2507`
- **What happens:** each item is wrapped in its own `coroutineScope { async { … } }` inside
  `map`. `coroutineScope` waits for its child before returning, so the 20 `movie|tv/{id}` calls
  run serially. The measured chain took about 5 s.
- **Fix:** put one `coroutineScope` around the list, launch an `async` per item gated by a
  `Semaphore(4)`, then `awaitAll()`.

**N2. Recently Added has the same N+1 pattern, also serial.** High · S · risk low
- **Where:** `viewmodel/SeerrViewModel.kt:2388-2405`
- **What happens:** a plain `map` calls `getMovieDetails`/`getTVDetails` once per item. This is
  the first row on home.
- **Fix:**
  - Same as N1.
  - Add a small in-flight + 5-minute details cache, shared by both rows and the details screen.
    That removes the duplicate fetches measured above: the same title in two rows, and
    `tv/{id}` fetched 3× by home plus details.

**N3. Image caches are wiped after every request.** High · S · risk low
- **Where:**
  - `ui/RefreshManager.kt:47-49` (`clearImageCachesAsync`)
  - `ui/MainScreen.kt:1305-1308` (on return to home)
- **What happens:** the entire Coil memory **and disk** cache is cleared, so every poster and
  backdrop has to be downloaded and decoded again. On a weak box that's the most expensive
  thing the app does. Nothing about the images changes when a request is made.
- **Fix:** remove both calls, or evict by key if a specific image really must refresh. First
  confirm there was no intentional reason behind the clear; neither the code nor its git log
  says what it was for.

**N4. Movie details fetch ratings twice, serially.** High (details time-to-content) · S · risk low
- **Where:** `viewmodel/SeerrViewModel.kt:2079-2081` and `:2023-2025`
- **What happens:**
  - `fetchMovieDetails` calls `apiService.getRatingsData` directly.
  - `fetchMediaDetails` then calls `getRatingsCached`. That misses the cache, because only
    `getRatingsCached` fills it.
  - So the sequence is details → ratings → ratings. Ratings come from Seerr's slow RT/IMDb
    proxy.
  - Polling also refetches ratings on every cycle through the same path (`:3444-3446`).
- **Fix:**
  - Drop ratings from `fetchMovieDetails`.
  - Publish details as soon as they arrive, then fetch ratings through `getRatingsCached` and
    merge them in.

**N5. Splash adds about 4.8 s of fixed sleeps, and home only starts loading after it.** High (perceived cold start) · S–M · product call
- **Where:** `MainActivity.kt:350-380`
- **What happens:**
  - `addLoadingStep` sleeps 300 ms per INFO step and 800 ms per SUCCESS step, plus a 100 ms
    trailing delay.
  - The network chain behind those steps is serial: Sonarr list → each server → Radarr list →
    each server (`data/SeerrApiService.kt:2458-2469`, `:2510-2521`).
  - `loadAllCategories()` only starts once MainScreen composes.
  - Measured: about 7 s between the first API call and the first home row request.
- **Fix:**
  - Replace the per-step sleeps with one minimum splash duration.
  - Load Sonarr and Radarr concurrently, with an `async` per server.
  - Kick off `loadAllCategories()` as soon as auth succeeds.

**N6. Refresh storm after a request, delete or approve.** High · M · risk medium
- **Where:**
  - `resetApiPagination` (`viewmodel/SeerrViewModel.kt:886-911`)
  - `loadCategory(forceRefresh)` (`:936-940`)
- **What happens:**
  - Both "reset" pagination by performing real fetches with `reset=true`. That's one wasted
    list call per row on every load — the duplicate `/media` and `/request` calls measured
    above.
  - After a request, all of these run:
    - `RefreshManager.kt:43-45` (clear, reset, force-refresh)
    - `refreshCategoryWithForce` (`:810-880`), which resets again, then refreshes again after
      500 ms because the slow N+1 has left the list empty
    - `MainScreen.kt:1276-1316`, which repeats the chain after a 2 s delay
  - That's about 7 `/request` calls plus 40–60 serial detail calls. `deleteRequest`
    (`:2536`) and `updateRequestStatus` (`:2846`) reload every row.
- **Fix:**
  - Make reset a pure state operation (`apiService.resetPaginationState(key)`).
  - Keep one refresh path and drop the timing heuristics.
- **Test:** request, delete and approve flows.

**N7. Large `toString()` logs run on Main in release builds.** Med–High · S · risk none
- **Where:** `viewmodel/SeerrViewModel.kt:2136-2138` (the whole TV `MediaDetails`), `:2049`,
  `:304`, and `data/SeerrApiService.kt:2020`
- **What happens:** these run on every details open and every poll. About 190 unguarded
  `Log.d`/`Log.i` calls ship in release.
- **Fix:**
  - Guard the heavy ones with `BuildConfig.DEBUG`.
  - Optionally add a `-assumenosideeffects` rule for `Log.d/v/i` in `tv/proguard-rules.pro`.
    That rule does not skip evaluating the arguments, so the guards are still needed.

**N8. Full-size `original` TMDB backdrops.** High on Details/Person · S · risk none
- **Where:** `ui/MediaDetails.kt:2177`, `ui/PersonScreen.kt:603`, `:634-635`
- **What happens:** originals are often 4K and 1–5 MB each. PersonScreen loads a new one on
  every Known For/Crew focus change, and again every 10 s.
- **Fix:** use `w1280`, as home already does. On PersonScreen, also debounce the backdrop
  target.

**N9. Avatar is an 870 KB download.** Low–Med · S · risk none
- **Where:** `ui/components/ProfileAvatar.kt:51-55`
- **What happens:**
  - The measured avatar (`/users/{id}/avatar?c=…`) was 870 KB, for a roughly 40 dp circle.
  - `AsyncImage` already decodes at layout size, so the cost is the download plus a
    full-file decode pass.
  - Seerr can't serve a smaller avatar.
- **Fix:** give the request a stable `memoryCacheKey`/`diskCacheKey` (user id + `c`) so it's
  downloaded once and not again after every cache wipe (see N3).

**N10. Polling does more than it needs to.** Med · S · risk low
- **Where:**
  - `viewmodel/SeerrViewModel.kt:3346-3365`
  - `ui/MediaDetails.kt:432-439`
- **What happens:**
  - The details poll keeps running every 30 s for available titles with nothing pending, and
    refetches ratings (N4).
  - `LaunchedEffect(mediaDetailsState)` clears and refetches Similar page 1 every time the
    details object changes, including on every poll while a download progresses.
- **Fix:**
  - Key that effect on `media.id`.
  - Stop or back off polling when nothing is pending.

**N11. Filters drawer refetches its reference lists on every open, serially.** Med · S · risk low
- **Where:** `viewmodel/MediaDiscoveryViewModel.kt:879-949`, triggered from
  `ui/components/FiltersDrawer.kt:154-167`
- **What happens:**
  - Regions, languages, genres, networks and watch providers are refetched on every open.
  - Watch providers are fetched again on the providers page (`:2644-2648`).
  - Provider logos are requested at `w500` but drawn at 60 dp (`:2993`).
- **Fix:**
  - Cache these lists per locale/region in the ViewModel and load them in parallel.
  - Use `w92` for logos.
- **Note:** the 0.34.0 keyword work is in this area, so land it first.

**N12. Smaller network items** (all S):
- **`/settings/public` fetched 3× at startup.**
  - Where: `data/SeerrApiService.kt:2291`, `:2293`, `MainActivity.kt:~501`
  - Fix: fetch once and parse the server type and the hide flags together.
- **Custom sliders force-loaded twice.**
  - Where: `viewmodel/SeerrViewModel.kt:616-622` and `ui/MainScreen.kt:2144-2147`
  - Fix: pass `forceRefresh = false` in the `LaunchedEffect`.
- **Watchlist fetched twice.**
  - Where: `data/SeerrApiService.kt:2634-2652` (membership pages one by one) and the row's own
    page 1 (`viewmodel/SeerrViewModel.kt:1661-1691`)
  - Fix: reuse page 1 and bound the enrichment concurrency.
- **Studio/network logo details fetched serially (6 per page).**
  - Where: `data/SeerrApiService.kt:3098-3116`, `:3189-3224`
  - Fix: parallelize them, or persist them, since the IDs are hard-coded.
- **Upcoming rows: pagination reset key mismatch.**
  - Where: `data/SeerrApiService.kt:1617-1635`
  - Impact: reset uses `"discover/movies"` but state is stored under the date-query key, so a
    refresh fetches the *next* page and resets Popular's cursor instead. This is a bug as well
    as wasted calls.
- **Profiles JSON re-decoded on every localized API call, on Main.**
  - Where: `getDiscoveryLanguage` → `getProfiles` (`util/SharedPreferencesUtil.kt:575`, `:605`,
    `:1314`); 40+ decodes per home load
  - Fix: memoize, and invalidate on `saveProfiles`.
- **Main-thread `commit()` on every home load.**
  - Where: `saveCustomSliderMeta` (`util/SharedPreferencesUtil.kt:1397-1402`)
  - Fix: skip the write if nothing changed, and use `apply()`.
- **No `Mutex` around re-login.**
  - Where: `data/SeerrApiService.kt:1022-1048`, `:1146-1170`
  - Impact: when a session expires, each of the 12+ parallel row calls logs in on its own.
- **Details cache unit bug.**
  - Where: `viewmodel/SeerrViewModel.kt:2089-2108`
  - Impact: minutes are stored into `cacheTimeMs` and `toMinutes(10 s)` is 0, so those entries
    are born expired. Minor, because they get overwritten.
- **Image auth interceptor recompiles regexes per image.**
  - Where: `getSeerrOrigin()` (`data/SeerrApiService.kt:526-546`), run for every image,
    including TMDB ones
  - Fix: cache the origin on config change.
- **30 s connect timeout per splash step when the server is down.**
  - Where: `data/SeerrApiService.kt:906`, `:936`
  - Fix: 10 s is plenty for a LAN server.

### Rendering

**R1. Home card key changes on every D-pad press, so both cards are rebuilt.** High · S · risk low–med
- **Where:** `ui/components/EnhancedMediaCarousel.kt:1067-1076`
- **What happens:**
  - The `itemsIndexed` key includes `isItemSelected`
    (`"${category.name}_${item.id}_${index}_$isItemSelected"`).
  - Every left/right press therefore disposes and recreates the card losing focus and the card
    gaining it: a new `MediaCard`, a new image painter and new state.
  - A side effect: the focus-scale animation never plays, because a freshly created
    `animateFloatAsState` starts at its target.
- **Fix:**
  - Key on `"${item.id}_${item.mediaType}"`, deduped across pages; duplicate keys crash a lazy
    list.
  - Add `contentType`, since placeholders and cards share the row.

**R2. Full-screen backdrop crossfades on every press, with no debounce.** High · S · risk low
- **Where:** `ui/MainScreen.kt:1750-1754`, `:1543-1546`, `:2200-2260`
- **What happens:**
  - A Compose `Crossfade` wraps a Coil `.crossfade(true)`, and each layer includes a
    full-screen 4-stop gradient.
  - So during each fade, two full-screen `w1280` bitmaps and two gradients are drawn.
  - Holding RIGHT downloads and decodes a backdrop for every card it passes. Measured: 17
    backdrops in 30 presses.
- **Fix:**
  - Debounce the backdrop target separately from the details text, for example
    `snapshotFlow { selected }.debounce(250)`.
  - Keep a single crossfade.
  - Draw the gradient once, outside the `Crossfade`.

**R3. `ApiResult.Loading()` is allocated during composition.** Med–High during load · S · risk low
- **Where:** `data/SeerrApiService.kt:131`, `ui/MainScreen.kt:2090`, `:2092`, `:2123`
- **What happens:**
  - `Loading` is a plain class, so each recomposition passes a new, unequal instance.
  - That restarts `LaunchedEffect(apiResult)` (`ui/CarouselSection.kt:134`), which calls
    `loadMoreForCategory`, which emits a new `categoryStates` map, which recomposes every row.
- **Fix:** make it `data object Loading`.

**R4. The whole MainScreen recomposes on every D-pad press.** High · M–L · risk medium
- **What triggers it:** `setSelection` (`ui/MainScreen.kt:438-446`) writes
  `AppFocusManager.currentFocus` (`ui/focus/AppFocusManager.kt:19`). That value is read during
  composition by:
  - MainScreen (`:168`)
  - the `setContent` root in `MainActivity.kt:822-843`
  - TopBarController (`ui/components/TopBarController.kt:126`)
- **What re-runs on each press:**
  - The roughly 1,800-line MainScreen body.
  - `visibleCategories` (`:560-562`) is rebuilt without `remember`, so the rows section never
    skips.
  - `createMainScreenDpadConfig` is rebuilt and re-registered through `LaunchedEffect(dpadConfig)`
    (`:961-1043`). It's a data class full of fresh lambdas, so it never compares equal.
- **Fix:**
  - Have handlers read focus when they run, not during composition.
  - Build the D-pad configs once with `remember` plus `rememberUpdatedState`.
  - Wrap `TopBarFocusState` in `derivedStateOf`.
  - Wrap `visibleCategories` in `remember`, which on its own is an S-sized win.
- **Test:** the focus paths top bar ⇄ rows ⇄ custom sliders ⇄ apps row.

**R5. Carousel scroll coroutines can't be cancelled.** High–Med · M · risk medium
- **Where:** `ui/components/EnhancedMediaCarousel.kt:179-209`, `:378-386`, `:473-588`, `:634-639`
- **What happens:**
  - Two `LaunchedEffect`s keyed on the selected index launch `withContext(NonCancellable)`
    scrolls, then a `delay(50)` re-check, then an "emergency" second scroll.
  - A held key queues overlapping scroll and correction passes that fight each other, which
    shows up as rubber-banding.
- **Fix:** use a single
  `snapshotFlow { selectedIndex.value }.collectLatest { animateScrollToItem(target) }`.
- **Test:** the pagination placeholder positioning (`:634-871`) is entangled with this.

**R6. Every carousel collects the global ViewModel flows.** Med · S–M · risk low
- **Where:** `ui/components/EnhancedMediaCarousel.kt:103`, `:107`, `:120`, `:375`
- **What happens:** every row collects `categoryStates`, `showPlaceholders` and the reset/update
  event flows. Any change to any category recomposes every row, and each recomposition rebuilds
  `rowItemsContentKey` by joining every item into a string (`:1008-1015`).
- **Fix:**
  - Collect the flows once in `ScrollableCategoriesSection`.
  - Pass each row only its own slice.
  - Wrap the content key in `remember(items)`.

**R7. Focus scale is read during composition.** Med · S · risk low (do after R1)
- **Where:** `ui/components/MediaCard.kt:79-83`, `ui/MainScreen.kt:2534-2541`,
  `ui/InstalledAppsRow.kt:101-113`, `ui/components/FiltersDrawer.kt:2957-2965`
- **What happens:** `val scale by animateFloatAsState(...)` plus `Modifier.scale(scale)`
  recomposes the whole card on every animation frame.
- **Fix:** use `Modifier.graphicsLayer { scaleX = s.value; scaleY = s.value }`.

**R8. Grids and rows scroll on every press even when the target is already visible.** Med · S · risk low
- **Where:**
  - `ui/MediaBrowseScreen.kt:1077` and `ui/MediaDiscoveryScreen.kt:1254` (`ensureRowIsVisible`
    always animates)
  - `ui/MainScreen.kt:2370-2373` (custom slider)
  - `ui/components/CarouselComponents.kt:158-160` and `:238-240` (cast and similar on details)
- **What happens:**
  - The grid or row moves on every press, even when the target is already on screen.
  - `MediaBrowseScreen.kt:796` and `:821` read `currentFocus` during composition, so the whole
    browse screen recomposes on every grid move.
- **Fix:**
  - Scroll only when the target is outside `layoutInfo.visibleItemsInfo`, as PersonScreen and
    FiltersDrawer already do.
  - Use `derivedStateOf` for the sort/filters-selected flags.

**R9. Lazy lists without `key` or `contentType`.** Med · S each
- **Where:**
  - `ui/MainScreen.kt:2399` (custom slider)
  - `ui/components/CarouselComponents.kt:168` and `:254`
  - `ui/components/DiscoveryGrid.kt:98`: `items(results.size)` with no key, and each cell reads
    `currentSelection`
  - `ui/PersonScreen.kt:826` and `:902`
  - `ui/components/FiltersDrawer.kt:507`, `:1384`, `:1472`, `:1865`, `:2949`
  - The home `LazyColumn` (`ui/MainScreen.kt:2077`) has keys but no `contentType`.

**R10. Selection reaches rows and grids one frame late.** Med (perceived latency) · S
- **Where:** `ui/MainScreen.kt:2034-2038`, `ui/components/DiscoveryGrid.kt:48-53`
- **What happens:** the selected index is copied into per-row state inside a `LaunchedEffect`.
- **Fix:** derive the per-row index directly during composition.

**R11. Smaller rendering items:**
- **Second Coil `ImageLoader`.**
  - Where: `ui/MediaDiscoveryScreen.kt:749`, `:912` (AsyncImage without `imageLoader`)
  - Impact: implicitly creates Coil's default singleton loader. The path is currently
    unreachable, so this is hygiene only.
- **Per-card allocations.**
  - Where: `ui/components/MediaCard.kt` — the `ImageRequest` (`:408`) isn't remembered, a new
    `Brush` is built per recomposition (`:273`, `:319`, `:401`), and `graphicsLayer(alpha = 0.8f)`
    on the status icon (`:487`) forces an offscreen layer.
- **Clock recomposes every second.**
  - Where: `ui/components/ClockComponent.kt:24-40`
  - Impact: it also reads SharedPreferences each tick.
  - Fix: tick per minute.
- **Writes during composition.**
  - Where: `ui/components/EnhancedMediaCarousel.kt:1096-1100` calls `saveUserIndex`, plus the
    write-only states at `:335-346`, `:590` and `:1108`.
- **Unused dependency.** `androidx.tv:tv-foundation` is declared (`tv/build.gradle.kts:316`) but
  never imported.

### Build and baseline profile

**B1. The baseline profile never recorded real content.** High (first-scroll jank, cold paths) · M
- **Where:** `tv/src/main/generated/baselineProfiles/baseline-prof.txt`, generated 2026-09-14
- **What happens:**
  - The profile has 24,200 rules, but none for `EnhancedMediaCarousel`, `MediaCard`,
    `CarouselSection`, `MediaDetails`, `MediaBrowseScreen`, `MediaDiscoveryScreen`,
    `DiscoveryGrid`, `FiltersDrawer`, `PersonScreen`, `RequestModal` or search.
  - The only card-related entry is `MainScreenKt.MediaCardPlaceholder`. So the generator's run
    stopped at the loading placeholders; `waitForIdle` returned before the rows had data. The
    hottest scroll path in the app is therefore interpreted/JIT'd on first use.
  - `startup-prof.txt` is **byte-identical** to `baseline-prof.txt`, because
    `includeInStartupProfile = true` is set on the generator that also does D-pad navigation.
    That defeats the dex-layout benefit the comment in the generator describes.
- **Fix** (`baselineprofile/src/main/java/.../StartupBaselineProfileGenerator.kt`):
  - Start from a signed-in device (the test server).
  - Wait for a real content node, for example a `testTag` on the first `MediaCard`, instead of
    `waitForIdle`.
  - Split the generators:
    - A startup-only generator with `includeInStartupProfile = true`.
    - Journey generators with `false`, covering: home row scroll including pagination, opening
      details then cast/similar, person, the browse grid with sort and filters, discovery,
      search, and settings.
  - Regenerate after the R-fixes land.
  - Add a Macrobenchmark with `FrameTimingMetric` for "home horizontal scroll" and "open
    details", so the rendering fixes can be measured on release builds.

**B2. No Compose compiler reports or stability config.** Med (enabler) · S
- **What happens:**
  - Strong skipping is on (Kotlin 2.4.20).
  - Only three classes are annotated `@Stable`.
  - Models such as `Media` hold `List`s, so they're unstable and compared by identity.
- **Fix:**
  - Add a `composeCompiler { reportsDestination / metricsDestination }` block behind a Gradle
    property.
  - Add a `stabilityConfigurationFiles` entry listing `ca.devmesh.seerrtv.model.*` and
    `kotlin.collections.*`. The models are immutable `val` data classes from deserialization.
  - Use the reports to confirm R4, R6 and R9.

## Already done well

Don't spend time on these:
- **API client:**
  - One API client with a connection pool.
  - Transparent gzip.
  - No body logging in release.
  - JSON is parsed on IO.
  - Cancellation is propagated correctly.
- **Home and details loading:**
  - Home rows are fired in parallel.
  - There are 5-minute row and slider caches, and studio/network caches.
  - Ratings have in-flight dedupe and a 404 negative cache.
  - Details have a job dedupe, a mutex and a cooldown.
- **Polling and search:**
  - Polling stops on `ON_STOP` and on dispose. Measured: 0 requests while idle and on back
    navigation.
  - Search is debounced and cancels the previous job.
- **Images (Coil):**
  - One shared `ImageLoader` with bounded dispatchers (8 total, 4 per host).
  - Poster size `w300_and_h450_face` matches the card, the home hero is `w1280`, cast photos are
    `w185`.
  - Stable cache keys.
  - Only the visible images load.
- **Rendering:**
  - No `Modifier.blur`, and almost no `shadow()`.
  - The home column has stable row keys.
  - `derivedStateOf` and visibility-guarded scrolling are used in PersonScreen and
    FiltersDrawer.
  - `snapshotFlow`-based infinite scroll.
  - Hot-path logs are mostly gated on `BuildConfig.DEBUG`. **Correction (2026-10-22):** that gate did nothing in release, because `defaultConfig` forced `DEBUG = true` for every build type. This is fixed in 0.34.0; see the checklist.
- **Build:** R8, resource shrinking, `profileinstaller` and the baseline profile plugin are all
  wired correctly.

## Suggested order

1. **Safe, small, high impact:** N1 + N2 (parallel details with `Semaphore(4)` and a shared
   details cache), N3 (stop wiping image caches), N4 (single ratings fetch), N8 (`w1280`
   instead of `original`), R1 (stable card keys), R3 (`data object Loading`),
   `remember(visibleCategories)`, R2 (debounce the backdrop), and N7 (guard the big logs).
2. **Next:** N5 (splash sleeps and serial Sonarr/Radarr; needs a product call on how long the
   splash should show), R7, R8, N10, N11 (after the 0.34.0 keyword work lands).
3. **Refactors:** N6 (refresh paths), R4 (focus → recomposition), R5 (carousel scroll), each in
   its own change with focused D-pad testing.
4. **Last:** B1, regenerating the baseline profile with real journeys plus a
   Macrobenchmark, so the gains are locked in and measurable on release builds.

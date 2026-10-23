# Performance measurement

These scripts produce repeatable before/after numbers for the work in
[docs/perf-checklist-2026-10.md](../../docs/perf-checklist-2026-10.md).

## Workflow

1. **Build and install.** Builds main's working tree, including uncommitted changes, with a
   request logger:

   ```bash
   tools/perf/build-instrumented.sh
   ```

   - The build happens in a scratch git worktree (default `$TMPDIR/seerrtv-perfwt`), so the
     logger is never added to main.
   - It installs on `emulator-5554`, or on `$ANDROID_SERIAL` if set.
   - This is a debug build. Before running it, check that the emulator holds a debug build: see
     the project memory on the test server and signature mismatches.
   - The emulator must be signed in to a Seerr server (a local test server keeps timings stable).

2. **Run the scenarios.** One run is the default, about 3 minutes; the label names the results
   folder:

   ```bash
   tools/perf/run-scenarios.sh after-N1
   ```

   - Each start waits until home has settled: at least one row has reported, and nothing new has
     been logged for 4 s, capped at 40 s.
   - Request counts and bytes are exact, so one run is enough for them. Pass a run count, e.g.
     `tools/perf/run-scenarios.sh after-N1 3`, only when a timing difference is small.

3. **Compare.** `results/<label>/summary.md` shows every metric next to
   `results/baseline-2026-10-22`, with the change in percent. Set `PERF_BASELINE` to compare
   against a different recorded run.

### Alternating two builds (only for small timing differences)

Emulator timing drifts with host load. To compare two builds fairly:

1. Build both APKs.
2. Alternate them, using the third argument for the run number:

   ```bash
   adb -s emulator-5554 install -r -t before.apk
   tools/perf/run-scenarios.sh before 1 1
   adb -s emulator-5554 install -r -t after.apk
   tools/perf/run-scenarios.sh after 1 1
   ```

3. Repeat with run number 2, then 3, and so on.

For "before", run `build-instrumented.sh`, then reverse-apply the fix's diff inside the worktree
(`git diff <file> | git -C <worktree> apply -R`) and rebuild there.

## Release builds

`run-scenarios.sh` measures instrumented debug builds. To compare what users actually run, use
`release_compare.py`. It takes two `benchmarkRelease` APKs: R8, the release configuration and the
baseline profile, but signed with the debug key, so they install over the signed-in debug app
without losing the session.

```bash
./gradlew :tv:assemblePlayAppBenchmarkRelease
```

```bash
python3 -I tools/perf/release_compare.py before.apk after.apk 3 tools/perf/results/release-<date>
```

For each round, the script does this for each build:
- install it, launch it once, register its baseline profile, and compile it with
  `speed-profile`, as a Play install would;
- measure the cold-start first frame and the time until the home screen shows media cards. Cards
  are detected through the accessibility tree; each check takes about 2 s, so that time is coarse.
- measure frame stats for the same D-pad scroll as `run-scenarios.sh`.

Build the "before" APK in a separate worktree at the old commit, and set its `appVersionCode` to
the same value as the "after" build. A non-debuggable build with a lower version code is refused as
a downgrade, and the script stops if an install fails.

## Scenarios

| Scenario | What it does |
|---|---|
| cold | Force-stops the app, clears the Coil disk cache, then starts the app and waits 25 s. |
| scroll | On home: 15× RIGHT, DOWN, 15× RIGHT, 4× DOWN, with keys 250 ms apart. Records `gfxinfo` and `meminfo`. |
| fastscroll | DOWN, then 15× RIGHT sent in one `input` command, so the presses arrive back-to-back like a held key. Counts backdrop downloads (R2). |
| warm | Force-stops the app, then starts it with the image cache kept, and waits 25 s. |
| details | Presses CENTER on the first card of the first row (Recently Added) and waits 10 s. |
| back | Presses BACK to home and waits 5 s. |

## Metrics

- **Time:** seconds from `am start`, using the device clock. Each request is timed from its start
  to its completion.
- **Row readiness:** `build-instrumented.sh` also injects a `PerfRow` log where
  `SeerrViewModel.loadCategory` publishes a row's data. The per-row tables are measured from the
  first home-row request, so splash variance doesn't blur row loading. Splash changes show up in
  "first home-row request" instead.
- **Per-card details calls:** requests to `/api/v1/(movie|tv)/<id>`.
- **Duplicates:** identical method + URL pairs within one scenario.
- **Frame stats:** these come from a debug build on the emulator. Compare them only against
  other runs on the same setup.

## Notes

- **What's committed:** only the `baseline-*` and `final-*` summaries (`summary.md`,
  `summary.json`, `version.txt`). The raw per-run logs (`run*/`) and any other result folders are
  ignored in `.gitignore`. The baseline's `summary.json` must stay in the repo: `run-scenarios.sh`
  compares every new run against it.

- **Keep the host quiet while measuring.** A Gradle build running alongside the emulator moved
  "first home-row request" from about 7.5 s to 14 s on 2026-10-22, and the before/after numbers
  from that run were unusable. Build every APK first, then measure.

- **Logger hooks:** `build-instrumented.sh` hooks the logger in with regexes on
  `SeerrApiService.kt` (`.retryOnConnectionFailure(false)`), `MainActivity.kt`
  (`.addInterceptor(SeerrImageAuthInterceptor())`) and `SeerrViewModel.kt` (the
  `put(category, ApiResult.Success(mediaList.toList(), …))` in `loadCategory`). It fails loudly if a fix changes those
  lines, so update the anchors when that happens.
- **Server data:** the results depend on what is on the test server — row contents and
  requests. Re-record the baseline if the library changes a lot.
- **Not scripted:** the request/delete flow (N6) creates data on the server, so measure it by
  hand.

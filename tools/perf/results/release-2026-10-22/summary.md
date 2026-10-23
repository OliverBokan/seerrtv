# Release build comparison (benchmarkRelease, speed-profile)

Medians of 3 alternating rounds on emulator-5554.

| Metric | Before | After | Change |
|---|---|---|---|
| am_total_ms | 94 | 96 | +2% |
| home_content_s | 13.08 | 6.68 | -49% |
| frames | 582 | 635 | +9% |
| deadline_missed | 8 | 9 | +12% |
| p50_ms | 17 | 17 | +0% |
| p90_ms | 21 | 19 | -10% |
| p99_ms | 27 | 23 | -15% |
| slow_ui_thread | 0 | 0 |  |

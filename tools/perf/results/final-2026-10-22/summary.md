# Perf results: final-2026-10-22

Medians of 1 runs. versionName=0.34.0 · 9aeaa43 · uncommitted files: 45

## Cold start (empty image cache)

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| am start TotalTime (ms) | 725 | 725 | 989.5 | -27% |
| API calls | 35 | 35 | 73.0 | -52% |
| API KB | 266 | 266 | 2074.0 | -87% |
| duplicate API calls | 1 | 1 | 6.0 | -83% |
| per-card details calls | 1 | 1 | 35.0 | -97% |
| API errors (4xx/5xx) | 0 | 0 | 0.0 |  |
| first API call (s) | 1.06 | 1.06 | 2.13 | -50% |
| first home-row request (s) | 2.16 | 2.16 | 8.48 | -75% |
| first poster image (s) | 5.04 | 5.04 | 13.92 | -64% |
| last API response (s) | 3.65 | 3.65 | 14.54 | -75% |
| all home rows have data (s) | 3.67 | 3.67 | 14.55 | -75% |
| image calls | 14 | 14 | 14.0 | +0% |
| image KB | 1410 | 1410 | 1410.0 | +0% |

## Warm start (image cache kept)

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| am start TotalTime (ms) | 686 | 686 | 922.5 | -26% |
| API calls | 35 | 35 | 73.0 | -52% |
| API KB | 266 | 266 | 2074.0 | -87% |
| duplicate API calls | 1 | 1 | 6.0 | -83% |
| per-card details calls | 1 | 1 | 35.0 | -97% |
| first home-row request (s) | 2.08 | 2.08 | 7.44 | -72% |
| last API response (s) | 3.27 | 3.27 | 13.05 | -75% |
| all home rows have data (s) | 3.29 | 3.29 | 13.07 | -75% |
| image calls | 0 | 0 | 0.0 |  |

## D-pad scroll (30 RIGHT + 5 DOWN)

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| image calls | 76 | 76 | 76.0 | +0% |
| image KB | 6952 | 6952 | 7067.5 | -2% |
| w1280 backdrops | 31 | 31 | 31.0 | +0% |
| API calls | 0 | 0 | 0.0 |  |
| frames | 642 | 642 | 578.0 | +11% |
| frame deadline missed | 9 | 9 | 30.5 | -70% |
| p50 frame (ms) | 20 | 20 | 21.0 | -5% |
| p90 frame (ms) | 24 | 24 | 32.0 | -25% |
| p99 frame (ms) | 32 | 32 | 66.5 | -52% |
| slow UI thread | 5 | 5 | 20.5 | -76% |
| PSS after scroll (MB) | 141 | 141 | 144.5 | -2% |

## Fast scroll (15 RIGHT back-to-back on the 2nd row)

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| image calls | 16 | 16 |
| image KB | 847 | 847 |
| w1280 backdrops | 1 | 1 |

## Open details (1st row, 1st card)

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| API calls | 3 | 3 | 4.0 | -25% |
| API KB | 85 | 85 | 85.0 | +0% |
| duplicate API calls | 0 | 0 | 1.0 | -100% |
| last API response (s) | 0.87 | 0.87 | 0.58 | +50% |
| image calls | 23 | 23 | 25.0 | -8% |
| image KB | 505 | 505 | 720.0 | -30% |
| original-size images | 0 | 0 | 1.0 | -100% |
| last image response (s) | 0.96 | 0.96 | 0.94 | +2% |

## Back to home

| Metric | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| API calls | 0 | 0 | 0.0 |  |
| image calls | 0 | 0 | 0.0 |  |

## Cold start: seconds from the first home-row request until each row has data

| Row | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| Popular Movies | 0.24 | 0.24 | 0.49 | -51% |
| Trending | 0.49 | 0.49 | 0.53 | -8% |
| Recent Requests | 0.6 | 0.6 | 5.55 | -89% |
| Recently Added | 0.66 | 0.66 | 6.36 | -90% |
| Upcoming Movies | 0.71 | 0.71 | 0.94 | -24% |
| Popular Series | 0.74 | 0.74 | 1.06 | -30% |
| Upcoming Series | 1.38 | 1.38 | 1.01 | +37% |
| Your Watchlist | 1.51 | 1.51 | 1.88 | -20% |

## Warm start: seconds from the first home-row request until each row has data

| Row | Median | Runs | Baseline | Change |
|---|---|---|---|---|
| Trending | 0.3 | 0.3 | 0.23 | +30% |
| Popular Movies | 0.4 | 0.4 | 0.38 | +5% |
| Recently Added | 0.46 | 0.46 | 5.67 | -92% |
| Recent Requests | 0.5 | 0.5 | 5.04 | -90% |
| Upcoming Series | 0.77 | 0.77 | 0.8 | -4% |
| Popular Series | 1.0 | 1.0 | 0.69 | +45% |
| Upcoming Movies | 1.06 | 1.06 | 0.52 | +104% |
| Your Watchlist | 1.21 | 1.21 | 1.33 | -9% |

## Duplicate API calls seen (run 1)

- cold: `GET /api/v1/discover/watchlist?page=1` ×2
- warm: `GET /api/v1/discover/watchlist?page=1` ×2

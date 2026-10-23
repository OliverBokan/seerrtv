# Perf results: baseline-2026-10-22

Medians of 4 runs. versionName=0.34.0 · 9aeaa43 · uncommitted files: 21

## Cold start (empty image cache)

| Metric | Median | Runs |
|---|---|---|
| am start TotalTime (ms) | 989.5 | 963 / 894 / 1016 / 3078 |
| API calls | 73.0 | 73 / 73 / 73 / 73 |
| API KB | 2074.0 | 2074 / 2074 / 2074 / 2074 |
| duplicate API calls | 6.0 | 6 / 6 / 6 / 6 |
| per-card details calls | 35.0 | 35 / 35 / 35 / 35 |
| API errors (4xx/5xx) | 0.0 | 0 / 0 / 0 / 0 |
| first API call (s) | 2.13 | 2.1 / 2.05 / 2.16 / 4.65 |
| first home-row request (s) | 8.48 | 8.44 / 8.53 / 7.42 / 10.93 |
| first poster image (s) | 13.92 | 14.52 / 13.32 / 12.97 / 16.63 |
| last API response (s) | 14.54 | 15.19 / 13.89 / 13.47 / 17.55 |
| all home rows have data (s) | 14.55 | 15.2 / 13.9 / 13.48 / 17.59 |
| image calls | 14.0 | 14 / 14 / 14 / 14 |
| image KB | 1410.0 | 1410 / 1410 / 1410 / 1410 |

## Warm start (image cache kept)

| Metric | Median | Runs |
|---|---|---|
| am start TotalTime (ms) | 922.5 | 930 / 810 / 915 / 2207 |
| API calls | 73.0 | 73 / 73 / 73 / 73 |
| API KB | 2074.0 | 2074 / 2074 / 2074 / 2074 |
| duplicate API calls | 6.0 | 6 / 6 / 6 / 6 |
| per-card details calls | 35.0 | 35 / 35 / 35 / 35 |
| first home-row request (s) | 7.44 | 7.6 / 7.2 / 7.28 / 9.69 |
| last API response (s) | 13.05 | 13.3 / 12.81 / 12.6 / 15.57 |
| all home rows have data (s) | 13.07 | 13.31 / 12.82 / 12.61 / 15.58 |
| image calls | 0.0 | 0 / 0 / 0 / 0 |

## D-pad scroll (30 RIGHT + 5 DOWN)

| Metric | Median | Runs |
|---|---|---|
| image calls | 76.0 | 76 / 75 / 76 / 76 |
| image KB | 7067.5 | 7087 / 6877 / 7048 / 7279 |
| w1280 backdrops | 31.0 | 31 / 30 / 31 / 31 |
| API calls | 0.0 | 0 / 0 / 0 / 0 |
| frames | 578.0 | 588 / 568 / 589 / 431 |
| frame deadline missed | 30.5 | 28 / 33 / 18 / 219 |
| p50 frame (ms) | 21.0 | 21 / 21 / 21 / 48 |
| p90 frame (ms) | 32.0 | 32 / 32 / 30 / 125 |
| p99 frame (ms) | 66.5 | 48 / 85 / 42 / 300 |
| slow UI thread | 20.5 | 18 / 23 / 13 / 171 |
| PSS after scroll (MB) | 144.5 | 149 / 144 / 137 / 145 |

## Open details (1st row, 1st card)

| Metric | Median | Runs |
|---|---|---|
| API calls | 4.0 | 4 / 4 / 4 / 4 |
| API KB | 85.0 | 85 / 85 / 85 / 85 |
| duplicate API calls | 1.0 | 1 / 1 / 1 / 1 |
| last API response (s) | 0.58 | 0.44 / 0.52 / 0.65 / 0.92 |
| image calls | 25.0 | 25 / 25 / 25 / 25 |
| image KB | 720.0 | 908 / 720 / 720 / 720 |
| original-size images | 1.0 | 1 / 1 / 1 / 1 |
| last image response (s) | 0.94 | 0.75 / 0.78 / 1.1 / 1.88 |

## Back to home

| Metric | Median | Runs |
|---|---|---|
| API calls | 0.0 | 0 / 0 / 0 / 0 |
| image calls | 0.0 | 0 / 0 / 0 / 0 |

## Cold start: seconds from the first home-row request until each row has data

| Row | Median | Runs |
|---|---|---|
| Popular Movies | 0.49 | 0.43 / 0.46 / 0.52 / 0.93 |
| Trending | 0.53 | 0.43 / 0.62 / 0.43 / 0.95 |
| Upcoming Movies | 0.94 | 0.94 / 0.5 / 1.4 / 0.94 |
| Upcoming Series | 1.01 | 1.73 / 0.6 / 1.43 / 0.35 |
| Popular Series | 1.06 | 1.77 / 0.58 / 1.55 / 0.53 |
| Your Watchlist | 1.88 | 2.15 / 1.19 / 2.11 / 1.64 |
| Recent Requests | 5.55 | 6.04 / 4.68 / 5.51 / 5.59 |
| Recently Added | 6.36 | 6.76 / 5.37 / 6.06 / 6.66 |

## Warm start: seconds from the first home-row request until each row has data

| Row | Median | Runs |
|---|---|---|
| Trending | 0.23 | 0.21 / 0.26 / 0.3 / 0.17 |
| Popular Movies | 0.38 | 0.29 / 0.24 / 0.51 / 0.47 |
| Upcoming Movies | 0.52 | 0.55 / 0.68 / 0.49 / 0.37 |
| Popular Series | 0.69 | 0.76 / 0.7 / 0.67 / 0.54 |
| Upcoming Series | 0.8 | 0.84 / 0.76 / 0.66 / 0.93 |
| Your Watchlist | 1.33 | 1.37 / 1.24 / 1.3 / 1.37 |
| Recent Requests | 5.04 | 5.05 / 5.02 / 4.7 / 5.07 |
| Recently Added | 5.67 | 5.71 / 5.62 / 5.33 / 5.89 |

## Duplicate API calls seen (run 1)

- cold: `GET /api/v1/settings/public` ×3
- cold: `GET /api/v1/media?filter=allavailable&take=20&skip=0&sort=mediaAdded` ×2
- cold: `GET /api/v1/discover/watchlist?page=1` ×2
- cold: `GET /api/v1/request?filter=all&take=20&sort=modified&skip=0` ×2
- cold: `GET /api/v1/movie/1423191` ×2
- warm: `GET /api/v1/settings/public` ×3
- warm: `GET /api/v1/media?filter=allavailable&take=20&skip=0&sort=mediaAdded` ×2
- warm: `GET /api/v1/request?filter=all&take=20&sort=modified&skip=0` ×2
- warm: `GET /api/v1/discover/watchlist?page=1` ×2
- warm: `GET /api/v1/movie/1423191` ×2
- details: `GET /api/v1/movie/1302904/ratingscombined` ×2

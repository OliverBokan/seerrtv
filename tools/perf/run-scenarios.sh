#!/usr/bin/env bash
# Runs the fixed perf scenarios against the instrumented build (see build-instrumented.sh) and
# writes raw logs plus summary.json/summary.md to tools/perf/results/<label>/.
#
#   tools/perf/run-scenarios.sh <label> [runs=1] [first-run-number=1]
#
# The third argument lets two builds be alternated run by run (install A, run 1; install B,
# run 1; install A, run 2 ...), which spreads host-load noise evenly over both.
# Needs: emulator-5554 running, the instrumented build installed and signed in to the test
# server, the app on the home screen when last used (cold starts land on home).
set -euo pipefail
LABEL="${1:?label, e.g. baseline}"
RUNS="${2:-1}"
FIRST="${3:-1}"
SERIAL="${ANDROID_SERIAL:-emulator-5554}"
PKG=ca.devmesh.seerrtv
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/$LABEL"
mkdir -p "$OUT"
A() { adb -s "$SERIAL" "$@"; }
now() { A shell 'date +%s%3N' | tr -d '\r'; }
key() { A shell input keyevent "$1"; }
dump() { A logcat -d -v epoch -s PerfNet:D PerfRow:D > "$1"; }
# Waits until home has settled: at least one row reported (PerfRow) and no new request or row
# logged for 4 s. Capped at 40 s. Replaces a fixed 25 s wait per start.
settle() {
  local last=-1 quiet=0 i
  for i in $(seq 1 40); do
    sleep 1
    local n rows
    # grep -c exits 1 on zero matches, which pipefail would turn into a script exit.
    n=$(A logcat -d -s PerfNet:D PerfRow:D | grep -c "Perf" || true)
    rows=$(A logcat -d -s PerfRow:D | grep -c "PerfRow" || true)
    if [ "$n" -eq "$last" ] && [ "$rows" -gt 0 ]; then quiet=$((quiet + 1)); else quiet=0; fi
    last=$n
    [ "$quiet" -ge 4 ] && return 0
  done
}

A shell dumpsys package "$PKG" | grep -m1 versionName > "$OUT/version.txt"
git -C "$HERE/../.." rev-parse --short HEAD >> "$OUT/version.txt"
git -C "$HERE/../.." status --short | grep -c . | sed 's/^/uncommitted files: /' >> "$OUT/version.txt"

for r in $(seq "$FIRST" $((FIRST + RUNS - 1))); do
  D="$OUT/run$r"; mkdir -p "$D"
  echo "== run $r"

  # A. Cold start, empty image cache.
  A shell am force-stop "$PKG"
  A shell run-as "$PKG" rm -rf cache/coil3_disk_cache
  A logcat -c
  now > "$D/cold.t0"
  A shell am start -W -n "$PKG/.MainActivity" | tr -d '\r' > "$D/cold.amstart"
  settle
  dump "$D/cold.log"

  # B. D-pad scroll on home: 15x RIGHT, DOWN, 15x RIGHT, 4x DOWN.
  A shell dumpsys gfxinfo "$PKG" reset > /dev/null
  A logcat -c
  now > "$D/scroll.t0"
  for i in $(seq 1 15); do key KEYCODE_DPAD_RIGHT; sleep 0.25; done
  key KEYCODE_DPAD_DOWN; sleep 0.5
  for i in $(seq 1 15); do key KEYCODE_DPAD_RIGHT; sleep 0.25; done
  for i in 1 2 3 4; do key KEYCODE_DPAD_DOWN; sleep 0.5; done
  sleep 3
  dump "$D/scroll.log"
  A shell dumpsys gfxinfo "$PKG" | tr -d '\r' > "$D/scroll.gfxinfo"
  A shell dumpsys meminfo "$PKG" | tr -d '\r' > "$D/scroll.meminfo"

  # B2. Fast scroll: 15x RIGHT sent in one command, so presses arrive back-to-back like a held
  #     key (B's 250 ms + adb spacing is slower than the backdrop debounce).
  A logcat -c
  now > "$D/fastscroll.t0"
  key KEYCODE_DPAD_DOWN; sleep 1
  A shell input keyevent $(printf 'KEYCODE_DPAD_RIGHT %.0s' $(seq 1 15))
  sleep 4
  dump "$D/fastscroll.log"

  # C. Warm start (image cache kept), the common case.
  A shell am force-stop "$PKG"
  A logcat -c
  now > "$D/warm.t0"
  A shell am start -W -n "$PKG/.MainActivity" | tr -d '\r' > "$D/warm.amstart"
  settle
  dump "$D/warm.log"

  # D. Open details for the first card of the first row (Recently Added), then back. The warm
  #    start leaves focus there. (The second row is Recent Requests, which opens the request
  #    action modal instead of details.)
  A logcat -c
  now > "$D/details.t0"
  key KEYCODE_DPAD_CENTER
  sleep 10
  dump "$D/details.log"
  A logcat -c
  key KEYCODE_BACK
  sleep 5
  dump "$D/back.log"
done

python3 -I "$HERE/parse_perfnet.py" "$OUT"

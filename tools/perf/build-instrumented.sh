#!/usr/bin/env bash
# Builds a debug APK of the CURRENT main working tree (committed + uncommitted changes) with
# PerfNetLogger wired into the API and image OkHttp clients, then installs it on the emulator.
# The repo itself is never modified: everything happens in a scratch git worktree.
#
#   tools/perf/build-instrumented.sh [worktree-dir]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WT="${1:-${TMPDIR:-/tmp}/seerrtv-perfwt}"
SERIAL="${ANDROID_SERIAL:-emulator-5554}"

if [ ! -d "$WT/.git" ] && [ ! -f "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" HEAD >/dev/null
fi
# Mirror main's working tree: reset to HEAD, then copy every tracked-modified and untracked file.
git -C "$WT" checkout --detach -q "$(git -C "$REPO" rev-parse HEAD)"
git -C "$WT" reset -q --hard
git -C "$WT" clean -qfd -e local.properties -e tv/signing.properties
(cd "$REPO" && git ls-files -m -o --exclude-standard -z) | (cd "$REPO" && xargs -0 -I{} rsync -R "{}" "$WT/")
cp "$REPO/local.properties" "$WT/" 2>/dev/null || true
cp "$REPO/tv/signing.properties" "$WT/tv/" 2>/dev/null || true

# Wire in the logger.
cp "$REPO/tools/perf/PerfNetLogger.kt" "$WT/tv/src/main/java/ca/devmesh/seerrtv/data/PerfNetLogger.kt"
API="$WT/tv/src/main/java/ca/devmesh/seerrtv/data/SeerrApiService.kt"
MAIN="$WT/tv/src/main/java/ca/devmesh/seerrtv/MainActivity.kt"
perl -0pi -e 's/(\n(\s*)\.retryOnConnectionFailure\(false\)[^\n]*)/$1\n$2.addInterceptor(PerfNetLogger("API"))/' "$API"
perl -0pi -e 's/(\n(\s*)\.addInterceptor\(SeerrImageAuthInterceptor\(\)\))/$1\n$2.addInterceptor(ca.devmesh.seerrtv.data.PerfNetLogger("IMG"))/' "$MAIN"
# Row-ready marker: logged when loadCategory publishes a home row's data.
VM="$WT/tv/src/main/java/ca/devmesh/seerrtv/viewmodel/SeerrViewModel.kt"
perl -0pi -e 's/(\n(\s*)put\(category, ApiResult\.Success\(mediaList\.toList\(\), result\.paginationInfo\)\)\n\s*\}\n)/$1$2android.util.Log.d("PerfRow", "ready \$categoryTitle \${mediaList.size}")\n/' "$VM"
grep -q '"PerfRow"' "$VM" || { echo "PerfRow hook not applied — update build-instrumented.sh" >&2; exit 1; }
grep -q 'PerfNetLogger("API")' "$API" || { echo "API hook not applied — update build-instrumented.sh" >&2; exit 1; }
grep -q 'PerfNetLogger("IMG")' "$MAIN" || { echo "IMG hook not applied — update build-instrumented.sh" >&2; exit 1; }

(cd "$WT" && ./gradlew -q :tv:assemblePlayAppDebug)
APK="$WT/tv/build/outputs/apk/playApp/debug/tv-play-app-debug.apk"
adb -s "$SERIAL" install -r -t "$APK" | tail -1
echo "Installed instrumented build of $(git -C "$REPO" rev-parse --short HEAD) + working tree on $SERIAL"

"""Compare two release-like builds (benchmarkRelease) of SeerrTV on the emulator.

    python3 -I tools/perf/release_compare.py <before.apk> <after.apk> [rounds=3] [out_dir]

Release builds carry no request logger, so this measures what a user sees:
  - cold start: `am start -W` TotalTime, and seconds from launch until the home screen shows
    real media cards (polled from the accessibility tree: >= 6 "Media Poster" nodes);
  - home D-pad scroll: the same key sequence as run-scenarios.sh, with gfxinfo frame stats.

Each APK is installed over the app already on the device (benchmarkRelease is signed with the
debug key, like debug builds, so the signed-in session survives), launched once so
ProfileInstaller registers its baseline profile, and compiled with `speed-profile`, which is
what a Play install gets. The two builds are alternated round by round so host noise hits both.
"""
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

SERIAL = "emulator-5554"
PKG = "ca.devmesh.seerrtv"
POSTERS_FOR_CONTENT = 6
CONTENT_TIMEOUT_S = 40


def adb(*args, check=False):
    return subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, text=True, check=check).stdout


def shell(cmd):
    return adb("shell", cmd)


def poster_count():
    xml = adb("exec-out", "uiautomator", "dump", "/dev/tty")
    return xml.count('content-desc="Media Poster"')


def wait_for_content(t0):
    """Seconds from t0 until the home screen shows real media cards (None on timeout)."""
    while time.time() - t0 < CONTENT_TIMEOUT_S:
        if poster_count() >= POSTERS_FOR_CONTENT:
            return round(time.time() - t0, 2)
        time.sleep(0.2)
    return None


def prepare(apk):
    # Fail loudly: a refused install (e.g. INSTALL_FAILED_VERSION_DOWNGRADE, which a non-debuggable
    # build gets when its versionCode is lower) would otherwise measure the other build twice.
    # Give the "before" build the same versionCode as the "after" one.
    result = subprocess.run(["adb", "-s", SERIAL, "install", "-r", "-t", apk], capture_output=True, text=True)
    if "Success" not in result.stdout:
        sys.exit(f"install failed for {apk}: {(result.stdout + result.stderr).strip()}")
    print("installed", apk, adb("shell", f"dumpsys package {PKG}").split("versionName=")[1].split()[0])
    shell(f"am force-stop {PKG}")
    shell(f"am start -W -n {PKG}/.MainActivity")
    wait_for_content(time.time())
    time.sleep(3)
    shell(f"am broadcast -a androidx.profileinstaller.action.INSTALL_PROFILE "
          f"{PKG}/androidx.profileinstaller.ProfileInstallReceiver")
    shell(f"am force-stop {PKG}")
    out = shell(f"cmd package compile -f -m speed-profile {PKG}").strip()
    print("  compile:", out)


def cold_start():
    shell(f"am force-stop {PKG}")
    time.sleep(1)
    t0 = time.time()
    am = shell(f"am start -W -n {PKG}/.MainActivity")
    m = re.search(r"TotalTime: (\d+)", am)
    content = wait_for_content(t0)
    return {"am_total_ms": int(m.group(1)) if m else None, "home_content_s": content}


def scroll():
    time.sleep(2)
    shell(f"dumpsys gfxinfo {PKG} reset")
    keys = ["KEYCODE_DPAD_RIGHT"] * 15 + ["KEYCODE_DPAD_DOWN"] + ["KEYCODE_DPAD_RIGHT"] * 15 + ["KEYCODE_DPAD_DOWN"] * 4
    for k in keys:
        shell(f"input keyevent {k}")
        time.sleep(0.25 if k.endswith("RIGHT") else 0.5)
    time.sleep(2)
    g = shell(f"dumpsys gfxinfo {PKG}")
    num = lambda pat: (lambda mm: int(mm.group(1)) if mm else None)(re.search(pat, g))
    return {
        "frames": num(r"Total frames rendered: (\d+)"),
        "deadline_missed": num(r"Number Frame deadline missed: (\d+)"),
        "p50_ms": num(r"\n50th percentile: (\d+)ms"),
        "p90_ms": num(r"\n90th percentile: (\d+)ms"),
        "p99_ms": num(r"\n99th percentile: (\d+)ms"),
        "slow_ui_thread": num(r"Number Slow UI thread: (\d+)"),
    }


def main():
    before, after = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).parent / "results" / "release-compare"
    out.mkdir(parents=True, exist_ok=True)
    runs = {"before": [], "after": []}
    for r in range(rounds):
        for label, apk in (("before", before), ("after", after)):
            print(f"== round {r + 1}: {label}")
            prepare(apk)
            result = cold_start()
            result.update(scroll())
            print("  ", result)
            runs[label].append(result)

    keys = ["am_total_ms", "home_content_s", "frames", "deadline_missed", "p50_ms", "p90_ms", "p99_ms", "slow_ui_thread"]
    med = lambda label, k: statistics.median([x[k] for x in runs[label] if x.get(k) is not None] or [float("nan")])
    lines = ["# Release build comparison (benchmarkRelease, speed-profile)", "",
             f"Medians of {rounds} alternating rounds on {SERIAL}.", "",
             "| Metric | Before | After | Change |", "|---|---|---|---|"]
    for k in keys:
        b, a = med("before", k), med("after", k)
        change = f"{(a - b) / b * 100:+.0f}%" if b else ""
        lines.append(f"| {k} | {b} | {a} | {change} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    (out / "runs.json").write_text(json.dumps(runs, indent=2))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

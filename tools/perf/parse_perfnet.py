"""Summarises tools/perf/results/<label>/run*/ into summary.json and summary.md (medians)."""
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

LINE = re.compile(r"PerfNet\s*:\s*(API|IMG) (\S+) (\d+) start=(\d+) end=(\d+) len=(-?\d+) (\S+)")
HOME_ROW = re.compile(r"^/api/v1/(media\?|request\?|discover/|settings/discover)")
CARD_DETAILS = re.compile(r"^/api/v1/(movie|tv)/\d+$")
# Marker injected by build-instrumented.sh where SeerrViewModel.loadCategory publishes a row.
ROW_READY = re.compile(r"^\s*(\d+\.\d+) .*PerfRow\s*: ready (.+) (\d+)$")


def reqs(path):
    out = []
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            m = LINE.search(line)
            if m:
                kind, method, code, s, e, ln, url = m.groups()
                out.append(dict(kind=kind, method=method, code=int(code), start=int(s),
                                end=int(e), len=int(ln), url=url))
    return out


def rows_ready(path, base):
    """Seconds from base until each home row first got data: {row title: seconds}."""
    ready = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            m = ROW_READY.match(line)
            if m and m.group(2) not in ready:
                ready[m.group(2)] = round((float(m.group(1)) * 1000 - base) / 1000, 2)
    return ready


def t0(path):
    return int(path.read_text().strip())


def amstart(path):
    m = re.search(r"TotalTime: (\d+)", path.read_text()) if path.exists() else None
    return int(m.group(1)) if m else None


def net_stats(rs, base):
    api = [r for r in rs if r["kind"] == "API"]
    img = [r for r in rs if r["kind"] == "IMG"]
    keys = Counter(f'{r["method"]} {r["url"]}' for r in api)
    dups = {k: v for k, v in keys.items() if v > 1}
    rel = lambda ms: round((ms - base) / 1000, 2)
    home = [r for r in api if HOME_ROW.match(r["url"])]
    posters = [r for r in img if "/w300_and_h450_face/" in r["url"]]
    return {
        "api_calls": len(api),
        "api_kb": round(sum(max(r["len"], 0) for r in api) / 1024),
        "api_errors": sum(1 for r in api if r["code"] >= 400),
        "duplicate_api_calls": sum(v - 1 for v in dups.values()),
        "card_details_calls": sum(1 for r in api if CARD_DETAILS.match(r["url"])),
        "img_calls": len(img),
        "img_kb": round(sum(max(r["len"], 0) for r in img) / 1024),
        "backdrop_w1280_calls": sum(1 for r in img if "/w1280/" in r["url"]),
        "original_size_calls": sum(1 for r in img if "/original/" in r["url"]),
        "t_first_api_s": rel(min(r["start"] for r in api)) if api else None,
        "t_first_home_row_s": rel(min(r["start"] for r in home)) if home else None,
        "t_first_poster_s": rel(min(r["start"] for r in posters)) if posters else None,
        "t_last_api_s": rel(max(r["end"] for r in api)) if api else None,
        "t_last_img_s": rel(max(r["end"] for r in img)) if img else None,
        "duplicates": dups,
    }


def gfx(path):
    if not path.exists():
        return {}
    t = path.read_text()
    g = lambda pat: (lambda m: int(m.group(1)) if m else None)(re.search(pat, t))
    return {
        "frames": g(r"Total frames rendered: (\d+)"),
        "deadline_missed": g(r"Number Frame deadline missed: (\d+)"),
        "p50_ms": g(r"\n50th percentile: (\d+)ms"),
        "p90_ms": g(r"\n90th percentile: (\d+)ms"),
        "p99_ms": g(r"\n99th percentile: (\d+)ms"),
        "slow_ui_thread": g(r"Number Slow UI thread: (\d+)"),
    }


def pss_mb(path):
    if not path.exists():
        return None
    m = re.search(r"TOTAL PSS:\s+(\d+)", path.read_text()) or re.search(r"\n\s+TOTAL\s+(\d+)", path.read_text())
    return round(int(m.group(1)) / 1024) if m else None


def main(out):
    out = Path(out)
    runs = []
    for d in sorted(out.glob("run*")):
        run = {}
        for sc in ("cold", "warm", "details", "scroll", "fastscroll"):
            base = t0(d / f"{sc}.t0") if (d / f"{sc}.t0").exists() else 0
            run[sc] = net_stats(reqs(d / f"{sc}.log"), base)
        run["back"] = net_stats(reqs(d / "back.log"), 0)
        for sc in ("cold", "warm"):
            ready = rows_ready(d / f"{sc}.log", t0(d / f"{sc}.t0"))
            run[sc]["t_all_rows_ready_s"] = max(ready.values()) if ready else None
            # Per row, measured from the first home-row request so splash-time noise (and splash
            # fixes, which show up in t_first_home_row_s) don't blur the row-loading comparison.
            home = run[sc]["t_first_home_row_s"]
            run[sc]["rows_ready"] = {n: round(v - home, 2) for n, v in ready.items()} if home is not None else {}
        run["cold"]["am_total_ms"] = amstart(d / "cold.amstart")
        run["warm"]["am_total_ms"] = amstart(d / "warm.amstart")
        run["scroll"].update(gfx(d / "scroll.gfxinfo"))
        run["scroll"]["pss_mb"] = pss_mb(d / "scroll.meminfo")
        runs.append(run)

    def med(sc, k):
        vals = [r[sc].get(k) for r in runs if r[sc].get(k) is not None]
        return round(statistics.median(vals), 2) if vals else None

    rows = [
        ("Cold start (empty image cache)", "cold", [
            ("am start TotalTime (ms)", "am_total_ms"), ("API calls", "api_calls"),
            ("API KB", "api_kb"), ("duplicate API calls", "duplicate_api_calls"),
            ("per-card details calls", "card_details_calls"), ("API errors (4xx/5xx)", "api_errors"),
            ("first API call (s)", "t_first_api_s"), ("first home-row request (s)", "t_first_home_row_s"),
            ("first poster image (s)", "t_first_poster_s"), ("last API response (s)", "t_last_api_s"),
            ("all home rows have data (s)", "t_all_rows_ready_s"),
            ("image calls", "img_calls"), ("image KB", "img_kb")]),
        ("Warm start (image cache kept)", "warm", [
            ("am start TotalTime (ms)", "am_total_ms"), ("API calls", "api_calls"), ("API KB", "api_kb"),
            ("duplicate API calls", "duplicate_api_calls"), ("per-card details calls", "card_details_calls"),
            ("first home-row request (s)", "t_first_home_row_s"), ("last API response (s)", "t_last_api_s"),
            ("all home rows have data (s)", "t_all_rows_ready_s"), ("image calls", "img_calls")]),
        ("D-pad scroll (30 RIGHT + 5 DOWN)", "scroll", [
            ("image calls", "img_calls"), ("image KB", "img_kb"), ("w1280 backdrops", "backdrop_w1280_calls"),
            ("API calls", "api_calls"), ("frames", "frames"), ("frame deadline missed", "deadline_missed"),
            ("p50 frame (ms)", "p50_ms"), ("p90 frame (ms)", "p90_ms"), ("p99 frame (ms)", "p99_ms"),
            ("slow UI thread", "slow_ui_thread"), ("PSS after scroll (MB)", "pss_mb")]),
        ("Fast scroll (15 RIGHT back-to-back on the 2nd row)", "fastscroll", [
            ("image calls", "img_calls"), ("image KB", "img_kb"), ("w1280 backdrops", "backdrop_w1280_calls")]),
        ("Open details (1st row, 1st card)", "details", [
            ("API calls", "api_calls"), ("API KB", "api_kb"), ("duplicate API calls", "duplicate_api_calls"),
            ("last API response (s)", "t_last_api_s"), ("image calls", "img_calls"), ("image KB", "img_kb"),
            ("original-size images", "original_size_calls"), ("last image response (s)", "t_last_img_s")]),
        ("Back to home", "back", [("API calls", "api_calls"), ("image calls", "img_calls")]),
    ]
    # Every result is compared against the recorded baseline (override with PERF_BASELINE).
    import os
    base_label = os.environ.get("PERF_BASELINE", "baseline-2026-10-22")
    base_file = out.parent / base_label / "summary.json"
    base = json.loads(base_file.read_text())["median"] if base_file.exists() and out.name != base_label else None

    def cmp(key, value):
        if base is None or value is None or base.get(key) is None:
            return ""
        b = base[key]
        delta = f"{(value - b) / b * 100:+.0f}%" if b else ""
        return f" | {b} | {delta}"

    md = [f"# Perf results: {out.name}", "", f"Medians of {len(runs)} runs. "
          + (out / "version.txt").read_text().replace("\n", " · ").strip(" ·"), ""]
    summary = {"runs": runs, "median": {}}
    for title, sc, metrics in rows:
        head = "| Metric | Median | Runs |" + (" Baseline | Change |" if base else "")
        md += [f"## {title}", "", head, "|---|---|---|" + ("---|---|" if base else "")]
        for label, k in metrics:
            m = med(sc, k)
            summary["median"][f"{sc}.{k}"] = m
            md.append(f"| {label} | {m} | {' / '.join(str(r[sc].get(k)) for r in runs)}{cmp(f'{sc}.{k}', m)} |")
        md.append("")
    for sc, title in (("cold", "Cold start"), ("warm", "Warm start")):
        names = []
        for r in runs:
            names += [n for n in r[sc].get("rows_ready", {}) if n not in names]
        if not names:
            continue
        md += [f"## {title}: seconds from the first home-row request until each row has data", "",
               "| Row | Median | Runs |" + (" Baseline | Change |" if base else ""), "|---|---|---|" + ("---|---|" if base else "")]
        for n in names:
            vals = [r[sc]["rows_ready"].get(n) for r in runs]
            known = [v for v in vals if v is not None]
            m = round(statistics.median(known), 2) if known else None
            summary["median"][f"{sc}.row_ready.{n}"] = m
            md.append(f"| {n} | {m} | {' / '.join(str(v) for v in vals)}{cmp(f'{sc}.row_ready.{n}', m)} |")
        md.append("")
    md += ["## Duplicate API calls seen (run 1)", ""]
    for sc in ("cold", "warm", "details"):
        for k, v in runs[0][sc]["duplicates"].items():
            md.append(f"- {sc}: `{k}` ×{v}")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1])

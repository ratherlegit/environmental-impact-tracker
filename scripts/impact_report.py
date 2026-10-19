#!/usr/bin/env python3
"""Report on the shared environmental impact log.

  impact_report.py report <weekly|monthly|quarterly|annual> [--back N]
  impact_report.py migrate <dir-or-log-file> [...]

--back N reports N periods before the current one (default 0).
Weeks are Mon-Sun; months, quarters and years are calendar-based.
"""
import json, sys, os, argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

LOG = os.path.expanduser("~/.claude/environmental-impact-log.json")


def load():
    if not os.path.exists(LOG):
        return {"entries": []}
    with open(LOG) as f:
        return json.load(f)


def save(data):
    with open(LOG, "w") as f:
        json.dump(data, f, indent=2)


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def bounds(period, back):
    """Return (start, end, label) for the period `back` periods ago, in UTC."""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        start = today - timedelta(days=today.weekday()) - timedelta(weeks=back)
        end = start + timedelta(weeks=1)
        label = f"Week of {start:%b %-d, %Y}"
    elif period == "monthly":
        m = now.year * 12 + now.month - 1 - back
        start = datetime(m // 12, m % 12 + 1, 1, tzinfo=timezone.utc)
        n = m + 1
        end = datetime(n // 12, n % 12 + 1, 1, tzinfo=timezone.utc)
        label = f"{start:%B %Y}"
    elif period == "quarterly":
        q = now.year * 4 + (now.month - 1) // 3 - back
        start = datetime(q // 4, (q % 4) * 3 + 1, 1, tzinfo=timezone.utc)
        n = q + 1
        end = datetime(n // 4, (n % 4) * 3 + 1, 1, tzinfo=timezone.utc)
        label = f"Q{q % 4 + 1} {q // 4}"
    else:
        y = now.year - back
        start = datetime(y, 1, 1, tzinfo=timezone.utc)
        end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        label = str(y)
    return start, end, label


def usable(e):
    return "timestamp" in e and "energy_wh" in e


def totals(entries):
    return (
        sum(e["energy_wh"] for e in entries),
        sum(e.get("water_ml", e["energy_wh"] * 1.7) for e in entries),
        sum(e.get("fresh_tokens", e.get("total_tokens", 0)) for e in entries),
    )


def delta(cur, prev):
    if not prev:
        return "no data last period" if not cur else "new this period"
    pct = (cur - prev) / prev * 100
    return f"{pct:+.0f}% vs last period"


def bar(v, vmax, width=16):
    n = 0 if vmax <= 0 or v <= 0 else max(1, round(v / vmax * width))
    return "🟦" * n + "⬜" * (width - n)


def bucket_key(period, t):
    if period == "weekly":
        return t.strftime("%a %b %-d")
    if period == "monthly":
        monday = t - timedelta(days=t.weekday())
        return "Wk " + monday.strftime("%b %-d")
    return t.strftime("%b %Y") if period == "quarterly" else t.strftime("%b")


def report(period, back):
    entries = [e for e in load()["entries"] if usable(e)]
    start, end, label = bounds(period, back)
    prev_start = bounds(period, back + 1)[0]
    cur = [e for e in entries if start <= parse(e["timestamp"]) < end]
    prev = [e for e in entries if prev_start <= parse(e["timestamp"]) < start]
    if not cur:
        print(f"{label}: no logged entries.")
        return
    wh, ml, tok = totals(cur)
    pwh, pml, _ = totals(prev)
    partial = " (in progress)" if end > datetime.now(timezone.utc) else ""
    print("🌊" * 14)
    print(f"{period.capitalize()} report: {label}{partial}")
    print("🌊" * 14)
    print(f"\n💧 Water   {ml:,.1f} mL   (about {ml / 500:.1f} water bottles, {delta(ml, pml)})")
    print(f"⚡ Energy  {wh:,.1f} Wh   (about {wh / 20:.1f} phone charges, {delta(wh, pwh)})")
    print(f"🔢 Tokens  {tok:,} (cache re-reads excluded) across {len(cur):,} responses")

    top = max(ml, pml)
    print("\nThis vs last period (water)")
    print(f"  This  {bar(ml, top)} {ml:,.0f} mL")
    print(f"  Last  {bar(pml, top)} {pml:,.0f} mL")

    print("\nBy project (share of water)")
    by = defaultdict(list)
    for e in cur:
        by[e.get("project", "unknown")].append(e)
    ranked = sorted(by.items(), key=lambda kv: -totals(kv[1])[0])
    width = max(len(n) for n, _ in ranked[:8])
    for name, es in ranked[:8]:
        pwh_, pml_, _ = totals(es)
        print(f"  {name:<{width}}  {bar(pml_, ranked and totals(ranked[0][1])[1])} {pwh_ / wh * 100:>3.0f}%  {pml_:,.0f} mL")
    if len(ranked) > 8:
        rest = sum(totals(es)[1] for _, es in ranked[8:])
        print(f"  ... and {len(ranked) - 8} smaller projects ({rest:,.0f} mL)")

    buckets = defaultdict(float)
    order = []
    for e in sorted(cur, key=lambda e: e["timestamp"]):
        k = bucket_key(period, parse(e["timestamp"]))
        if k not in buckets:
            order.append(k)
        buckets[k] += e.get("water_ml", e["energy_wh"] * 1.7)
    kind = {"weekly": "day", "monthly": "week", "quarterly": "month", "annual": "month"}[period]
    print(f"\nWater over time (by {kind})")
    peak = max(buckets.values())
    for k in order:
        print(f"  {k:<11} {bar(buckets[k], peak)} {buckets[k]:,.0f} mL")
    busiest = max(buckets, key=buckets.get)
    print(f"\n🌊 Busiest {kind}: {busiest} ({buckets[busiest]:,.0f} mL)")


def migrate(paths):
    data = load()
    seen = {(e.get("project"), e.get("timestamp"), e.get("context")) for e in data["entries"]}
    added = 0
    for p in paths:
        p = os.path.abspath(os.path.expanduser(p))
        f = p if os.path.isfile(p) else os.path.join(p, ".environmental-impact-log.json")
        project = os.path.basename(os.path.dirname(f))
        for e in json.load(open(f))["entries"]:
            e = {**e, "project": e.get("project", project)}
            k = (e["project"], e.get("timestamp"), e.get("context"))
            if k not in seen:
                data["entries"].append(e)
                seen.add(k)
                added += 1
    data["entries"].sort(key=lambda e: e.get("timestamp", ""))
    save(data)
    print(f"Imported {added} entries into {LOG}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("period", choices=["weekly", "monthly", "quarterly", "annual"])
    r.add_argument("--back", type=int, default=0)
    m = sub.add_parser("migrate")
    m.add_argument("paths", nargs="+")
    a = ap.parse_args()
    report(a.period, a.back) if a.cmd == "report" else migrate(a.paths)

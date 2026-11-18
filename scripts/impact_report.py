#!/usr/bin/env python3
"""Report on the shared environmental impact log.

  impact_report.py report <weekly|monthly|quarterly|annual> [--back N]
                          [--format text|html] [--out FILE] [--anonymize]
  impact_report.py migrate <dir-or-log-file> [...]

--back N reports N periods before the current one (default 0).
Weeks are Mon-Sun; months, quarters and years are calendar-based.
--format html writes a self-contained shareable card (default file:
impact-report-<period>.html in the current directory).
--anonymize swaps real project names for made-up ones, so a report can be
shared as an example.
"""
import json, sys, os, argparse, html
from datetime import datetime, timedelta, timezone
from collections import defaultdict

LOG = os.path.expanduser("~/.claude/environmental-impact-log.json")
FAKE_PROJECTS = ["Recipe Box", "garden-planner", "FitTrack", "dev-home",
                 "Budget App", "notes", "Trip Planner", "scratch"]


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


def water_of(e):
    return e.get("water_ml", e["energy_wh"] * 1.7)


def totals(entries):
    return (
        sum(e["energy_wh"] for e in entries),
        sum(water_of(e) for e in entries),
        sum(e.get("fresh_tokens", e.get("total_tokens", 0)) for e in entries),
    )


def delta(cur, prev):
    if not prev:
        return "no data last period" if not cur else "new this period"
    pct = (cur - prev) / prev * 100
    return f"{pct:+.0f}% vs last period"


def bar(v, vmax, width=16, fill="🟦"):
    n = 0 if vmax <= 0 or v <= 0 else max(1, round(v / vmax * width))
    return fill * n + "⬜" * (width - n)


def bucket_key(period, t):
    if period == "weekly":
        return t.strftime("%a %b %-d")
    if period == "monthly":
        monday = t - timedelta(days=t.weekday())
        return "Wk " + monday.strftime("%b %-d")
    return t.strftime("%b %Y") if period == "quarterly" else t.strftime("%b")


def collect(period, back, anonymize=False):
    """Aggregate the log into a plain dict that both renderers consume."""
    entries = [e for e in load()["entries"] if usable(e)]
    start, end, label = bounds(period, back)
    prev_start = bounds(period, back + 1)[0]
    cur = [e for e in entries if start <= parse(e["timestamp"]) < end]
    prev = [e for e in entries if prev_start <= parse(e["timestamp"]) < start]
    if not cur:
        return {"empty": True, "label": label}
    wh, ml, tok = totals(cur)
    pwh, pml, _ = totals(prev)

    by = defaultdict(list)
    for e in cur:
        by[e.get("project", "unknown")].append(e)
    ranked = sorted(by.items(), key=lambda kv: -totals(kv[1])[0])
    projects = []
    for i, (name, es) in enumerate(ranked[:8]):
        pw, pm, _ = totals(es)
        if anonymize:
            name = FAKE_PROJECTS[i]
        projects.append({"name": name, "wh": pw, "ml": pm, "share": pw / wh * 100 if wh else 0})
    rest = ranked[8:]

    water_b, energy_b, order = defaultdict(float), defaultdict(float), []
    for e in sorted(cur, key=lambda e: e["timestamp"]):
        k = bucket_key(period, parse(e["timestamp"]))
        if k not in water_b:
            order.append(k)
        water_b[k] += water_of(e)
        energy_b[k] += e["energy_wh"]
    kind = {"weekly": "day", "monthly": "week", "quarterly": "month", "annual": "month"}[period]
    return {
        "empty": False, "period": period, "label": label, "kind": kind,
        "partial": end > datetime.now(timezone.utc),
        "wh": wh, "ml": ml, "tokens": tok, "responses": len(cur),
        "pwh": pwh, "pml": pml,
        "projects": projects,
        "rest_count": len(rest), "rest_ml": sum(totals(es)[1] for _, es in rest),
        "order": order, "water_b": dict(water_b), "energy_b": dict(energy_b),
    }


def render_text(d):
    if d["empty"]:
        print(f"{d['label']}: no logged entries.")
        return
    wh, ml, pwh, pml = d["wh"], d["ml"], d["pwh"], d["pml"]
    partial = " (in progress)" if d["partial"] else ""
    print("🌊" * 14)
    print(f"{d['period'].capitalize()} report: {d['label']}{partial}")
    print("🌊" * 14)
    print(f"\n💧 Water   {ml:,.1f} mL   (about {ml / 500:.1f} water bottles, {delta(ml, pml)})")
    print(f"⚡ Energy  {wh:,.1f} Wh   (about {wh / 20:.1f} phone charges, {delta(wh, pwh)})")
    print(f"🔢 Tokens  {d['tokens']:,} (cache re-reads excluded) across {d['responses']:,} responses")

    top = max(ml, pml)
    print("\nThis vs last period (water)")
    print(f"  This  {bar(ml, top)} {ml:,.0f} mL")
    print(f"  Last  {bar(pml, top)} {pml:,.0f} mL")

    print("\nBy project (share of water)")
    projects = d["projects"]
    width = max(len(p["name"]) for p in projects)
    for p in projects:
        print(f"  {p['name']:<{width}}  {bar(p['ml'], projects[0]['ml'])} {p['share']:>3.0f}%  {p['ml']:,.0f} mL")
    if d["rest_count"]:
        print(f"  ... and {d['rest_count']} smaller projects ({d['rest_ml']:,.0f} mL)")

    kind, order = d["kind"], d["order"]
    print(f"\nWater over time (by {kind})")
    peak = max(d["water_b"].values())
    for k in order:
        print(f"  {k:<11} {bar(d['water_b'][k], peak)} {d['water_b'][k]:,.0f} mL")
    print(f"\nEnergy over time (by {kind})")
    peak = max(d["energy_b"].values())
    for k in order:
        print(f"  {k:<11} {bar(d['energy_b'][k], peak, fill='🟨')} {d['energy_b'][k]:,.1f} Wh")
    busiest = max(d["water_b"], key=d["water_b"].get)
    print(f"\n🌊 Busiest {kind}: {busiest} ({d['water_b'][busiest]:,.0f} mL)")


CSS = """
:root{--bg:#f4f6fa;--card:#fff;--ink:#14213d;--muted:#5b6678;--line:#e3e8f0;--track:#e9edf4;
--water:#2563eb;--energy:#d97706;--up:#b45309;--down:#15803d;
--w1:#38bdf8;--w2:#2563eb;--e1:#fbbf24;--e2:#ea580c;}
@media (prefers-color-scheme:dark){:root{--bg:#0e1116;--card:#171b22;--ink:#e8ecf3;--muted:#9aa5b8;
--line:#262c37;--track:#242a35;--water:#5b9bff;--energy:#f5a524;--up:#f5a524;--down:#4ade80;
--w1:#7dd3fc;--w2:#3b82f6;--e1:#fde047;--e2:#f97316;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
padding:32px 16px}
.card{max-width:720px;margin:0 auto;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:28px}
h1{font-size:26px;margin:0 0 2px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 24px}
h2{font-size:17px;margin:32px 0 12px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.stat{border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat .v{font-size:26px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.stat .u{font-size:14px;font-weight:500;color:var(--muted);margin-left:3px}
.stat .n{color:var(--muted);font-size:13px;margin-top:2px}
.stat .d{font-size:13px;font-weight:600;margin-top:6px}
.up{color:var(--up)}.down{color:var(--down)}
.water .v{color:var(--water)}.energy .v{color:var(--energy)}
.row{display:grid;grid-template-columns:120px 1fr 112px;gap:12px;align-items:center;margin:8px 0;font-size:14px}
.row .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .num{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.track{height:12px;background:var(--track);border-radius:6px;overflow:hidden}
.fill{height:100%;border-radius:6px}
.w{background:linear-gradient(90deg,var(--w1),var(--w2))}
.e{background:linear-gradient(90deg,var(--e1),var(--e2))}
.col .b.w{background:linear-gradient(180deg,var(--w1),var(--w2))}
.col .b.e{background:linear-gradient(180deg,var(--e1),var(--e2))}
.eq{display:flex;align-items:center;gap:16px;margin:12px 0;padding:14px 16px;border:1px solid var(--line);border-radius:12px}
.icons{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-end;flex:1;min-width:0}
.icons svg{display:block;height:46px;width:auto;overflow:visible}
.eq .cap{flex:0 0 150px;margin:0;font-size:14px;color:var(--muted)}
.eq .cap b{display:block;font-size:22px;color:var(--ink);letter-spacing:-.02em}
.out{stroke:var(--muted);stroke-width:1.5;fill:none}
@media (max-width:520px){.eq{flex-direction:column;align-items:flex-start}.eq .cap{flex:none}}
.note{color:var(--muted);font-size:13px;margin:10px 0 0}
.cols{display:flex;align-items:flex-end;gap:10px;height:150px;padding-top:8px}
.col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;min-width:0}
.col .b{width:100%;max-width:56px;border-radius:6px 6px 0 0;min-height:3px}
.col .val{font-size:12px;color:var(--muted);margin-bottom:4px;font-variant-numeric:tabular-nums}
.axis{display:flex;gap:10px;border-top:1px solid var(--line);padding-top:6px}
.axis span{flex:1;text-align:center;font-size:12px;color:var(--muted);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.foot{margin-top:28px;color:var(--muted);font-size:13px}
@media (max-width:520px){.stats{grid-template-columns:1fr}.row{grid-template-columns:96px 1fr 88px}}
"""


def _pct(cur, prev):
    """Return (css class, text) for a change vs last period."""
    if not prev:
        return "", "no data last period" if not cur else "new this period"
    p = (cur - prev) / prev * 100
    return ("up" if p > 0 else "down"), f"{'▲' if p > 0 else '▼'} {abs(p):.0f}% vs last period"


_uid = [0]


def _icon(kind, f):
    """Inline SVG of a water bottle or phone, filled from the bottom to fraction f."""
    _uid[0] += 1
    cid, f = f"c{_uid[0]}", max(0.0, min(1.0, f))
    if kind == "bottle":
        body = "M8 9H16V13C16 16 20 18 20 23V47A4 4 0 0 1 16 51H8A4 4 0 0 1 4 47V23C4 18 8 16 8 13Z"
        y = 51 - 38 * f
        return (f'<svg viewBox="0 0 24 54" role="img" aria-label="water bottle"><clipPath id="{cid}"><path d="{body}"/></clipPath>'
                f'<rect x="0" y="{y:.1f}" width="24" height="54" fill="url(#wg)" clip-path="url(#{cid})"/>'
                f'<path class="out" d="{body}"/><rect class="out" x="8" y="2" width="8" height="6" rx="2"/></svg>')
    y = 46 - 38 * f
    return (f'<svg viewBox="0 0 30 54" role="img" aria-label="phone"><clipPath id="{cid}"><rect x="6" y="8" width="18" height="38" rx="1.5"/></clipPath>'
            f'<rect x="6" y="{y:.1f}" width="18" height="46" fill="url(#eg)" clip-path="url(#{cid})"/>'
            f'<rect class="out" x="3" y="2" width="24" height="50" rx="5"/>'
            f'<rect x="12" y="4.2" width="6" height="1.6" rx=".8" fill="var(--muted)"/></svg>')


def _equiv(kind, count, noun, each, cap=24):
    """A row of icons for `count` items; scales so at most `cap` icons are drawn."""
    per = max(1, -(-int(count) // cap)) if count > cap else 1
    shown = count / per
    icons = [_icon(kind, 1.0) for _ in range(int(shown))]
    if shown - int(shown) > 0.02:
        icons.append(_icon(kind, shown - int(shown)))
    note = f"{each} each" if per == 1 else f"{each} each, one icon is {per}"
    return (f'<div class="eq"><div class="icons">{"".join(icons)}</div>'
            f'<p class="cap"><b>{count:,.1f}</b>{noun}<br>({note})</p></div>')


def _columns(order, values, cls, fmt, unit=""):
    peak = max(values.values()) or 1
    u = f" {unit}" if unit and len(values) <= 7 else ""
    cols = "".join(
        f'<div class="col"><div class="val">{fmt(values[k])}{u}</div>'
        f'<div class="b {cls}" style="height:{max(values[k] / peak * 100, 2):.1f}%"></div></div>'
        for k in order)
    axis = "".join(f"<span>{html.escape(k)}</span>" for k in order)
    return f'<div class="cols">{cols}</div><div class="axis">{axis}</div>'


def render_html(d):
    if d["empty"]:
        return None
    wh, ml, pwh, pml = d["wh"], d["ml"], d["pwh"], d["pml"]
    partial = " (in progress)" if d["partial"] else ""
    wc, wt = _pct(ml, pml)
    ec, et = _pct(wh, pwh)
    top = max(ml, pml) or 1
    projects = d["projects"]
    prow = "".join(
        f'<div class="row"><div class="name" title="{html.escape(p["name"])}">{html.escape(p["name"])}</div>'
        f'<div class="track"><div class="fill w" style="width:{p["ml"] / projects[0]["ml"] * 100:.1f}%"></div></div>'
        f'<div class="num">{p["share"]:.0f}% · {p["ml"]:,.0f} mL</div></div>'
        for p in projects)
    if d["rest_count"]:
        prow += f'<p class="note">and {d["rest_count"]} smaller projects ({d["rest_ml"]:,.0f} mL)</p>'
    busiest = max(d["water_b"], key=d["water_b"].get)
    kind = d["kind"]
    title = f"{d['period'].capitalize()} impact report"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<linearGradient id="wg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--w1)"/><stop offset="1" style="stop-color:var(--w2)"/></linearGradient>
<linearGradient id="eg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--e1)"/><stop offset="1" style="stop-color:var(--e2)"/></linearGradient>
</defs></svg>
<main class="card">
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(d["label"])}{partial}</p>
<div class="stats">
<div class="stat water"><div class="v">{ml:,.1f}<span class="u">mL</span></div><div class="n">Water used</div><div class="d {wc}">{wt}</div></div>
<div class="stat energy"><div class="v">{wh:,.1f}<span class="u">Wh</span></div><div class="n">Energy used</div><div class="d {ec}">{et}</div></div>
<div class="stat"><div class="v">{d["tokens"] / 1e6:,.2f}<span class="u">M tokens</span></div><div class="n">{d["responses"]:,} responses, cache re-reads excluded</div></div>
</div>
<h2>What that looks like</h2>
{_equiv("bottle", ml / 500, " water bottles", "500 mL")}
{_equiv("phone", wh / 20, " phone charges", "20 Wh")}
<h2>This period vs last (water, mL)</h2>
<div class="row"><div class="name">This</div><div class="track"><div class="fill w" style="width:{ml / top * 100:.1f}%"></div></div><div class="num">{ml:,.0f} mL</div></div>
<div class="row"><div class="name">Last</div><div class="track"><div class="fill w" style="width:{pml / top * 100:.1f}%;opacity:.55"></div></div><div class="num">{pml:,.0f} mL</div></div>
<h2>By project (share of total, water in mL)</h2>
{prow}
<h2>Water over time, by {kind} (mL)</h2>
{_columns(d["order"], d["water_b"], "w", lambda v: f"{v:,.0f}", "mL")}
<h2>Energy over time, by {kind} (Wh)</h2>
{_columns(d["order"], d["energy_b"], "e", lambda v: f"{v:,.1f}", "Wh")}
<p class="foot">Busiest {kind}: {html.escape(busiest)} ({d["water_b"][busiest]:,.0f} mL). Estimates.</p>
</main></body></html>
"""


def report(period, back, fmt="text", out=None, anonymize=False):
    d = collect(period, back, anonymize)
    if fmt == "html":
        page = render_html(d)
        if page is None:
            print(f"{d['label']}: no logged entries.")
            return
        out = os.path.abspath(os.path.expanduser(out or f"impact-report-{period}.html"))
        with open(out, "w") as f:
            f.write(page)
        print(f"Wrote {out}")
    else:
        render_text(d)


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
    r.add_argument("--format", choices=["text", "html"], default="text")
    r.add_argument("--out")
    r.add_argument("--anonymize", action="store_true")
    m = sub.add_parser("migrate")
    m.add_argument("paths", nargs="+")
    a = ap.parse_args()
    if a.cmd == "report":
        report(a.period, a.back, a.format, a.out, a.anonymize)
    else:
        migrate(a.paths)

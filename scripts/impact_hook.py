#!/usr/bin/env python3
"""Stop hook for the environmental-impact-tracker skill.

Reads the session transcript (and its subagent transcripts), converts every
assistant response's token usage to energy and water with the skill's rate
table, and appends new responses to ~/.claude/environmental-impact-log.json.
Tracking always runs unless the mode is `off`.

Modes (single word in ~/.claude/environmental-impact-tracker.state):
  reports       track silently, view reports on request (recommended default)
  per-response  also print a one-line impact after large responses
  both          alias of per-response; reports are always available on request
  off           no tracking, no display
  on            legacy value, treated as per-response

Usage:
  impact_hook.py              run as a Stop hook (JSON on stdin)
  impact_hook.py --backfill   import every transcript under ~/.claude/projects
"""
import json, os, sys, glob, fcntl, functools
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "environmental-impact-log.json")
STATE = os.path.join(HOME, ".claude", "environmental-impact-tracker.state")
PROJECTS = os.path.join(HOME, ".claude", "projects")

# model: (fixed overhead Wh/query, marginal input, marginal output, large-context blended) Wh/MTok
# Typical-tier values are mid-level estimates: 3x the optimized-serving derivation (Joule 2026),
# about the geometric midpoint to measured Claude benchmarks (arXiv 2505.09598). See references/sources.md.
RATES = {
    "fable": (0.531, 270, 1341, 35),
    "opus": (0.264, 135, 669, 18),
    "sonnet": (0.159, 81, 402, 11),
    "haiku": (0.054, 27, 135, 4),
}
LARGE_CONTEXT = 50_000
DISPLAY_THRESHOLD = 5_000
WATER_ML_PER_WH = 1.7


def read_mode():
    try:
        mode = open(STATE).read().strip().lower()
    except OSError:
        return "reports"
    return {"on": "per-response"}.get(mode, mode if mode in ("reports", "per-response", "both", "off") else "reports")


def rates_for(model):
    m = (model or "").lower()
    for key, r in RATES.items():
        if key in m:
            return r
    return RATES["sonnet"]


def energy_wh(model, u):
    overhead, m_in, m_out, large = rates_for(model)
    fresh_in = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
    cached = u.get("cache_read_input_tokens", 0)
    out = u.get("output_tokens", 0)
    total = fresh_in + cached + out
    if total > LARGE_CONTEXT:
        tier = "large-context"
        wh = overhead + (fresh_in + out + 0.1 * cached) * large / 1e6
    else:
        tier = "typical"
        wh = overhead + (fresh_in * m_in + 0.1 * cached * m_in + out * m_out) / 1e6
    return wh, tier, total, fresh_in + out


@functools.lru_cache(maxsize=None)
def project_name(cwd):
    if not cwd:
        return "unknown"
    parts = cwd.split("/")
    # scratchpad dirs: /private/tmp/claude-501/-Users-name/<session>/scratchpad/...
    if cwd.startswith("/private/tmp/claude-") and len(parts) > 4:
        return parts[4].split("-")[-1] or "unknown"
    # a subfolder counts toward the git repo that contains it
    d = cwd
    while d.startswith(HOME + "/") and d != HOME:
        if os.path.exists(os.path.join(d, ".git")):
            return os.path.basename(d)
        d = os.path.dirname(d)
    return os.path.basename(cwd.rstrip("/")) or "unknown"


def first_cwd(path):
    try:
        for line in open(path, errors="ignore"):
            if '"cwd"' in line:
                try:
                    cwd = json.loads(line).get("cwd")
                except ValueError:
                    continue
                if cwd:
                    return cwd
    except OSError:
        pass
    return None


def parse_transcript(path):
    """Return one entry per distinct assistant message id (last usage record wins).

    Each response counts toward the project of its working directory, with
    subfolders rolled up into their git repo.
    """
    best = {}
    try:
        lines = open(path, errors="ignore")
    except OSError:
        return []
    for line in lines:
        if '"usage"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        u = m.get("usage")
        if d.get("type") != "assistant" or not u:
            continue
        if not any(u.get(k) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")):
            continue
        mid = m.get("id") or d.get("uuid")
        if mid:
            best[mid] = (d, m, u)
    out = []
    for mid, (d, m, u) in best.items():
        wh, tier, total, fresh = energy_wh(m.get("model"), u)
        out.append({
            "timestamp": d.get("timestamp", ""),
            "project": project_name(d.get("cwd")),
            "model": m.get("model", "unknown"),
            "tier": tier,
            "energy_wh": round(wh, 4),
            "water_ml": round(wh * WATER_ML_PER_WH, 4),
            "total_tokens": total,
            "fresh_tokens": fresh,
            "id": mid,
            "session": d.get("sessionId"),
            "subagent": bool(d.get("isSidechain")),
        })
    return out


def session_files(transcript_path, session_id):
    files = [transcript_path] if transcript_path else []
    if transcript_path:
        base = os.path.splitext(transcript_path)[0]
        files += glob.glob(os.path.join(base, "subagents", "*.jsonl"))
    return files


def append_new(files):
    """Add unseen responses to the shared log under a lock; return the new entries."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG + ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            data = json.load(open(LOG))
        except (OSError, ValueError):
            data = {"entries": []}
        known = {e["id"] for e in data["entries"] if "id" in e}
        new = []
        for f in files:
            for e in parse_transcript(f):
                if e["id"] not in known:
                    known.add(e["id"])
                    new.append(e)
        if new:
            data["entries"].extend(new)
            data["entries"].sort(key=lambda e: e.get("timestamp", ""))
            tmp = LOG + ".tmp"
            json.dump(data, open(tmp, "w"), indent=1)
            os.replace(tmp, LOG)
        return new


def summary_line(new):
    wh = sum(e["energy_wh"] for e in new)
    ml = sum(e["water_ml"] for e in new)
    fresh = sum(e["fresh_tokens"] for e in new)
    subs = sum(1 for e in new if e["subagent"])
    extra = f" · {subs} subagent responses" if subs else ""
    return f"🌍 Impact this turn: {wh:.2f} Wh · {ml:.1f} mL · {fresh:,} tokens{extra}"


def main():
    if "--backfill" in sys.argv:
        files = glob.glob(os.path.join(PROJECTS, "**", "*.jsonl"), recursive=True)
        new = append_new(files)
        print(f"Backfilled {len(new)} responses from {len(files)} transcripts")
        return
    mode = read_mode()
    if mode == "off":
        return
    try:
        hook = json.load(sys.stdin)
    except ValueError:
        return
    new = append_new(session_files(hook.get("transcript_path"), hook.get("session_id")))
    if mode in ("per-response", "both") and new:
        fresh = sum(e["fresh_tokens"] for e in new)
        if fresh > DISPLAY_THRESHOLD or any(e["subagent"] for e in new):
            print(json.dumps({"systemMessage": summary_line(new)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # a hook must never break the session
        print(f"impact_hook error: {exc}", file=sys.stderr)

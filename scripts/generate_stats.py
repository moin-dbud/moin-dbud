#!/usr/bin/env python3
"""
Generate stats.svg, streak.svg, langs.svg, year.svg from the GitHub GraphQL API.
Stdlib only — no pip installs needed in CI.

Env vars required:
  GITHUB_TOKEN  - provided automatically by Actions (secrets.GITHUB_TOKEN)
  GH_LOGIN      - provided automatically (github.repository_owner)
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
LOGIN = os.environ["GH_LOGIN"]

RAMP = " .`:-=+*cs#%@"  # 13 levels, same ramp as the portrait

# ---------------------------------------------------------------- GraphQL

def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


# Whole-UTC-day window — do NOT let this drift with wall-clock time.
_today = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0)
_from = (_today - timedelta(days=364)).replace(hour=0, minute=0, second=0)
FROM_ISO = _from.isoformat()
TO_ISO = _today.isoformat()

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
    repositories(privacy: PUBLIC, first: 100, ownerAffiliations: OWNER,
                 isFork: false, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        name
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

data = gql(QUERY, {"login": LOGIN, "from": FROM_ISO, "to": TO_ISO})
user = data["user"]
cal = user["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
total = cal["totalContributions"]

# Flatten into a single ordered list of (date, count)
days = []
for w in weeks:
    for d in w["contributionDays"]:
        days.append((d["date"], d["contributionCount"]))

# ---------------------------------------------------------------- streaks

def compute_streaks(days):
    current = longest = 0
    cur_start = cur_end = None
    best_start = best_end = None
    streak_start = None
    for date, count in days:
        if count > 0:
            if streak_start is None:
                streak_start = date
            current += 1
            if current > longest:
                longest = current
                best_start, best_end = streak_start, date
        else:
            current = 0
            streak_start = None
    # trailing current streak (must include most recent day(s))
    trailing = 0
    trail_start = None
    for date, count in reversed(days):
        if count > 0:
            trailing += 1
            trail_start = date
        else:
            break
    return trailing, trail_start, days[-1][0] if trailing else None, longest, best_start, best_end

cur_len, cur_start, cur_end, long_len, long_start, long_end = compute_streaks(days)

# ---------------------------------------------------------------- languages

lang_bytes = {}
for repo in user["repositories"]["nodes"]:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        color = edge["node"]["color"] or "#888"
        lang_bytes.setdefault(name, [0, color])
        lang_bytes[name][0] += edge["size"]

top_langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1][0])[:6]
lang_total = sum(v[0] for _, v in top_langs) or 1

# ---------------------------------------------------------------- svg helpers

SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="monospace">'
STYLE_BG = '<rect width="100%" height="100%" fill="none"/>'

def wrap(w, h, body):
    return f'{SVG_HEAD.format(w=w, h=h)}{STYLE_BG}{body}</svg>'


# ---- stats.svg: hero total + weekly sparkline (columns, not a line)
weekly_totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
max_week = max(weekly_totals) or 1
bar_w, gap, chart_h = 6, 2, 60
bars = []
for i, v in enumerate(weekly_totals):
    h = round((v / max_week) * chart_h)
    x = i * (bar_w + gap)
    y = chart_h - h
    bars.append(f'<rect x="{x}" y="{y+40}" width="{bar_w}" height="{max(h,1)}" fill="currentColor" opacity="0.85"/>')
stats_svg = wrap(
    len(weekly_totals) * (bar_w + gap) + 20, 110,
    f'<text x="0" y="24" font-size="22" fill="currentColor">{total} contributions</text>'
    f'<text x="0" y="40" font-size="11" fill="currentColor" opacity="0.6">past year</text>'
    + "".join(bars)
)

# ---- streak.svg
def fmt(d):
    return d if d else "—"
streak_svg = wrap(
    360, 90,
    f'<text x="0" y="24" font-size="16" fill="currentColor">current streak: {cur_len} days</text>'
    f'<text x="0" y="42" font-size="11" fill="currentColor" opacity="0.6">{fmt(cur_start)} → {fmt(cur_end)}</text>'
    f'<text x="0" y="66" font-size="16" fill="currentColor">longest streak: {long_len} days</text>'
    f'<text x="0" y="84" font-size="11" fill="currentColor" opacity="0.6">{fmt(long_start)} → {fmt(long_end)}</text>'
)

# ---- langs.svg: horizontal bars by byte share
bar_max_w = 260
lang_lines = []
for i, (name, (size, color)) in enumerate(top_langs):
    pct = size / lang_total
    y = i * 26
    w = round(pct * bar_max_w)
    lang_lines.append(
        f'<text x="0" y="{y+14}" font-size="12" fill="currentColor">{name}</text>'
        f'<rect x="90" y="{y+3}" width="{bar_max_w}" height="10" fill="currentColor" opacity="0.15"/>'
        f'<rect x="90" y="{y+3}" width="{w}" height="10" fill="{color}"/>'
        f'<text x="{90+bar_max_w+8}" y="{y+14}" font-size="11" fill="currentColor" opacity="0.6">{pct*100:.1f}%</text>'
    )
langs_svg = wrap(400, len(top_langs) * 26 + 10, "".join(lang_lines))

# ---- year.svg: one character per day, using the portrait's own ramp
counts = [c for _, c in days]
nonzero = [c for c in counts if c > 0]
step = (max(nonzero) / (len(RAMP) - 1)) if nonzero else 1

def char_for(count):
    if count == 0:
        return RAMP[0]
    idx = min(len(RAMP) - 1, 1 + int((count - 1) / step)) if step else 1
    return RAMP[idx]

char_w, char_h = 10, 12
year_rows = []
for wi, w in enumerate(weeks):
    for di, d in enumerate(w["contributionDays"]):
        ch = char_for(d["contributionCount"])
        x = wi * char_w
        y = di * char_h + 10
        year_rows.append(f'<text x="{x}" y="{y}" font-size="12" fill="currentColor">{ch}</text>')
year_svg = wrap(len(weeks) * char_w + 10, 7 * char_h + 10, "".join(year_rows))

# ---------------------------------------------------------------- write

outputs = {
    "stats.svg": stats_svg,
    "streak.svg": streak_svg,
    "langs.svg": langs_svg,
    "year.svg": year_svg,
}
for name, content in outputs.items():
    with open(name, "w") as f:
        f.write(content)

print(f"wrote {', '.join(outputs)} — total={total}, current streak={cur_len}, longest={long_len}")
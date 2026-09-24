"""
Renders the bento-grid stats card as a single self-contained SVG.
Layout mirrors: greeting | photo | social links / graph / website
                total stars | PRs+followers / commits | contributions+streak | current streak
                full-width contribution heatmap
"""
import base64
import datetime
import html
import os

W = 680
MARGIN = 12
GAP = 12
COL_W = (W - 2 * MARGIN - 3 * GAP) // 4


def esc(s):
    return html.escape(str(s))


def rrect(x, y, w, h, fill, rx=16, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {extra}/>'


def text(x, y, s, size=14, weight="400", fill="#fff", anchor="start", family="Segoe UI, Helvetica, Arial, sans-serif"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" font-family="{family}">{esc(s)}</text>'
    )


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def resolve_photo_path(configured_path):
    """Match the configured path exactly if it exists; otherwise fall back
    to any file with the same name but a different extension/case in the
    same folder, so a .jpg-vs-.png mismatch never silently breaks the card."""
    if not configured_path:
        return None
    if os.path.exists(configured_path):
        return configured_path

    directory = os.path.dirname(configured_path) or "."
    stem = os.path.splitext(os.path.basename(configured_path))[0].lower()
    if not os.path.isdir(directory):
        return None
    for fname in sorted(os.listdir(directory)):
        name, ext = os.path.splitext(fname)
        if name.lower() == stem and ext.lower() in IMAGE_EXTS:
            return os.path.join(directory, fname)
    return None


def photo_data_uri(path):
    resolved = resolve_photo_path(path)
    if not resolved:
        return None
    ext = os.path.splitext(resolved)[1].lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(resolved, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{b64}"


def build_heatmap(days, theme, x, y, w, h):
    """days: date-sorted list of {'date','count'}. Renders last ~53 weeks."""
    cell_gap = 3
    cols = 53
    cell = (w - (cols - 1) * cell_gap) / cols
    cell = min(cell, (h - 20 - 6 * cell_gap) / 7)

    by_date = {d["date"]: d["count"] for d in days}
    today = datetime.date.today()
    start = today - datetime.timedelta(weeks=52)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)  # snap to Sunday

    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    def bucket(c):
        if c == 0:
            return 0
        if c <= 2:
            return 1
        if c <= 5:
            return 2
        if c <= 8:
            return 3
        return 4

    svg = [f'<g transform="translate({x},{y})">']
    d = start
    col = 0
    while d <= today:
        row = (d.weekday() + 1) % 7
        cx = col * (cell + cell_gap)
        cy = 20 + row * (cell + cell_gap)
        cnt = by_date.get(d.isoformat(), 0)
        color = colors[bucket(cnt)]
        svg.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
            f'rx="2" fill="{color}"/>'
        )
        if row == 6:
            col += 1
        d += datetime.timedelta(days=1)
    svg.append("</g>")
    return "".join(svg)


def render(stats, config):
    theme = config["theme"]
    login = stats["login"]
    streaks = stats["streaks"]

    parts = []
    parts.append(
        f'<svg width="{W}" height="734" viewBox="0 0 {W} 734" xmlns="http://www.w3.org/2000/svg">'
    )
    parts.append(rrect(0, 0, W, 734, theme["background"], rx=20))

    # column x positions
    x1 = MARGIN
    x2 = x1 + COL_W + GAP
    x3 = x2 + COL_W + GAP
    x4 = x3 + COL_W + GAP

    # ---- Row A/B/C (top section) ----
    yA, hA = 12, 100
    yB, hB = yA + hA + GAP, 96
    yC, hC = yB + hB + GAP, 96

    # Greeting card
    parts.append(f'<defs><linearGradient id="greet" x1="0" y1="0" x2="1" y2="1">'
                  f'<stop offset="0" stop-color="#60a5fa"/><stop offset="1" stop-color="#1d4ed8"/>'
                  f'</linearGradient></defs>')
    parts.append(rrect(x1, yA, COL_W, hA, "url(#greet)"))
    parts.append(text(x1 + 16, yA + 34, config["greeting"], size=15, weight="600", fill="#dbeafe"))
    parts.append(text(x1 + 16, yA + 62, config["display_name"], size=26, weight="700"))

    # blank filler (row B col1)
    parts.append(rrect(x1, yB, COL_W, hB, theme["card_bg"]))

    # username pink card (row C col1)
    parts.append(rrect(x1, yC, COL_W, hC, config["username_card_color"]))
    parts.append(text(x1 + COL_W / 2, yC + hC / 2 + 5, f"@{login}", size=15, weight="700", fill="#fff", anchor="middle"))

    # Photo card spans rowA+rowB in col2
    photo_h = hA + GAP + hB
    photo_uri = photo_data_uri(config.get("photo_path"))
    parts.append(rrect(x2, yA, COL_W * 2 + GAP, photo_h, "#1f2937", rx=16))
    if photo_uri:
        clip_id = "photoClip"
        parts.append(f'<clipPath id="{clip_id}"><rect x="{x2}" y="{yA}" width="{COL_W*2+GAP}" height="{photo_h}" rx="16"/></clipPath>')
        parts.append(
            f'<image href="{photo_uri}" x="{x2}" y="{yA}" width="{COL_W*2+GAP}" height="{photo_h}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})"/>'
        )
    else:
        parts.append(text(x2 + 16, yA + 24, "add a photo at", size=12, fill=theme["text_secondary"]))
        parts.append(text(x2 + 16, yA + 40, config.get("photo_path", "assets/photo.jpg"), size=12, fill=theme["text_secondary"]))

    # Graph placeholder card (row C col2)
    parts.append(rrect(x2, yC, COL_W * 2 + GAP, hC, theme["card_bg"]))
    parts.append(text(x2 + 12, yC + 18, "graph", size=11, fill=theme["text_secondary"]))

    # Social / website cards (col3, all three rows)
    for i, card in enumerate(config["social_cards"]):
        cy = [yA, yB, yC][i]
        ch = [hA, hB, hC][i]
        fill = card["color"]
        parts.append(rrect(x4, cy, COL_W, ch, fill))
        label_fill = "#111" if card.get("text_dark") else "#fff"
        parts.append(text(x4 + 14, cy + ch / 2 + 5, card["label"], size=13, weight="600", fill=label_fill))

    # ---- Bottom stats section ----
    yE, hE = yC + hC + GAP, 250

    # Total Stars (col1, tall)
    parts.append(rrect(x1, yE, COL_W, hE, "#3a2a06"))
    stars_str = "★" * min(5, max(1, stats["total_stars"] // 1 and 5))
    parts.append(text(x1 + 16, yE + 34, "★★★★★", size=18, fill=theme["accent_gold"]))
    parts.append(text(x1 + 16, yE + 70, "Total Stars", size=15, weight="600"))
    parts.append(text(x1 + 16, yE + 118, str(stats["total_stars"]), size=34, weight="800", fill=theme["accent_gold"]))
    parts.append(text(x1 + 16, yE + hE - 40, "Contributed To", size=11, fill=theme["text_secondary"]))
    parts.append(text(x1 + 16, yE + hE - 16, str(stats["contributed_to"]), size=18, weight="700", fill=theme["accent_blue"]))

    # PRs + Followers small cards (col2 top)
    small_w = (COL_W - GAP) / 2
    parts.append(rrect(x2, yE, small_w, 76, "#2a1420"))
    parts.append(text(x2 + 10, yE + 22, "PRs", size=11, fill=theme["text_secondary"]))
    parts.append(text(x2 + 10, yE + 52, str(stats["pull_requests"]), size=22, weight="800", fill="#f472b6"))

    parts.append(rrect(x2 + small_w + GAP, yE, small_w, 76, "#2a1420"))
    parts.append(text(x2 + small_w + GAP + 10, yE + 22, "Followers", size=11, fill=theme["text_secondary"]))
    parts.append(text(x2 + small_w + GAP + 10, yE + 52, str(stats["followers"]), size=22, weight="800", fill="#f472b6"))

    # Commits sparkline card (col2 bottom)
    yCommits = yE + 76 + GAP
    hCommits = hE - 76 - GAP
    parts.append(rrect(x2, yCommits, COL_W, hCommits, "#08120a"))
    parts.append(text(x2 + 14, yCommits + 26, "Commits", size=14, weight="600"))
    # simple decorative sparkline path
    import random
    random.seed(stats["total_commits"])
    pts = []
    n = 24
    for i in range(n):
        px = x2 + 10 + i * (COL_W - 20) / (n - 1)
        py = yCommits + hCommits - 55 + 25 * (0.5 - random.random())
        pts.append(f"{px:.1f},{py:.1f}")
    parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{theme["accent_green"]}" stroke-width="2"/>')
    parts.append(text(x2 + 14, yCommits + hCommits - 14, str(stats["total_commits"]), size=26, weight="800", fill=theme["accent_green"]))

    # Total Contributions card (col3 top)
    parts.append(rrect(x3, yE, COL_W, 76, "#0b1b2b"))
    parts.append(text(x3 + 14, yE + 24, "📅 Total Contributions", size=11, fill=theme["text_secondary"]))
    parts.append(text(x3 + 14, yE + 52, str(stats["total_contributions"]), size=22, weight="800", fill=theme["accent_blue"]))

    # Longest Streak card (col3 bottom)
    yLongest = yE + 76 + GAP
    hLongest = hE - 76 - GAP
    parts.append(rrect(x3, yLongest, COL_W, hLongest, "#2a2306"))
    parts.append(text(x3 + 14, yLongest + 26, "🏆 Longest Streak", size=12, weight="600"))
    parts.append(text(x3 + 14, yLongest + hLongest - 40, str(streaks["longest"]), size=26, weight="800", fill=theme["accent_gold"]))
    date_range = f'{streaks["longest_from"] or "-"} · {streaks["longest_to"] or "-"}'
    parts.append(text(x3 + 14, yLongest + hLongest - 14, date_range, size=10, fill=theme["text_secondary"]))

    # Current Streak (col4, tall)
    parts.append(rrect(x4, yE, COL_W, hE, "#2a0f06"))
    parts.append(text(x4 + COL_W / 2, yE + 60, "🔥", size=30, anchor="middle"))
    parts.append(text(x4 + COL_W / 2, yE + 100, "Current Streak", size=13, weight="600", anchor="middle"))
    parts.append(text(x4 + COL_W / 2, yE + 150, str(streaks["current"]), size=34, weight="800", fill=theme["accent_orange"], anchor="middle"))
    cur_range = f'{streaks["current_from"] or "-"} · Present'
    parts.append(text(x4 + COL_W / 2, yE + hE - 16, cur_range, size=10, fill=theme["text_secondary"], anchor="middle"))

    # ---- Bottom full-width heatmap ----
    yG = yE + hE + GAP
    hG = 734 - 12 - yG
    parts.append(rrect(MARGIN, yG, W - 2 * MARGIN, hG, "#04140a"))
    parts.append(text(MARGIN + 14, yG + 20, f"{login}'s Contribution Graph", size=13, weight="700"))
    parts.append(text(W - MARGIN - 14, yG + 20, "Less ■ ■ ■ ■ More", size=10, fill=theme["text_secondary"], anchor="end"))
    parts.append(build_heatmap(stats["calendar"], theme, MARGIN + 14, yG + 8, W - 2 * MARGIN - 28, hG - 8))

    parts.append("</svg>")
    return "".join(parts)

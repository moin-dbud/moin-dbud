"""
Renders the bento-grid stats card as a single self-contained SVG.
Layout: greeting (with tagline+tags) | photo | X/Twitter + LinkedIn (stacked)
        Recent Activity | Website
        GitHub Username (full width)
        Total Stars | PRs+Followers/Commits | Total Contributions+Longest Streak | Current Streak
        full-width contribution heatmap (with Mon/Wed/Fri labels)
"""
import base64
import datetime
import html
import os

W = 900
MARGIN = 20
GAP = 16
CONTENT_W = W - 2 * MARGIN


def esc(s):
    return html.escape(str(s))


def rrect(x, y, w, h, fill, rx=18, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" {extra}/>'


def text(x, y, s, size=14, weight="400", fill="#fff", anchor="start",
          family="Segoe UI, Helvetica, Arial, sans-serif", opacity=1):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" font-family="{family}" opacity="{opacity}">{esc(s)}</text>')


def icon(name, x, y, size, color="#fff", stroke_w=2):
    """Simple hand-drawn line icons in a 24x24 box, translated+scaled to (x,y,size)."""
    s = size / 24
    body = {
        "wave": None,  # rendered as emoji elsewhere
        "x": '<line x1="4" y1="4" x2="20" y2="20"/><line x1="20" y1="4" x2="4" y2="20"/>',
        "linkedin": '<rect x="2" y="2" width="20" height="20" rx="4" fill="{c}" stroke="none"/>'
                    '<text x="12" y="16.5" font-size="10" font-weight="800" fill="#fff" '
                    'text-anchor="middle" font-family="Segoe UI, Arial, sans-serif">in</text>'.format(c=color),
        "globe": '<circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/>'
                 '<path d="M12 3c3.2 3 3.2 15 0 18M12 3c-3.2 3-3.2 15 0 18" fill="none"/>',
        "code": '<path d="M8 6L2 12l6 6" fill="none"/><path d="M16 6l6 6-6 6" fill="none"/>',
        "copy": '<rect x="9" y="9" width="12" height="12" rx="2" fill="none"/>'
                '<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" fill="none"/>',
        "merge": '<circle cx="6" cy="6" r="2.6" fill="none"/><circle cx="18" cy="18" r="2.6" fill="none"/>'
                 '<path d="M6 8.6V15a3 3 0 003 3h4" fill="none"/><path d="M18 15.4V9" fill="none"/>',
        "commit": '<circle cx="12" cy="12" r="3" fill="none"/><line x1="3" y1="12" x2="9" y2="12"/>'
                  '<line x1="15" y1="12" x2="21" y2="12"/>',
        "people": '<circle cx="9" cy="8" r="3" fill="none"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="none"/>'
                  '<circle cx="17.5" cy="9" r="2.2" fill="none"/><path d="M15.3 20c0-2.3 1.1-4.2 3.2-4.9" fill="none"/>',
        "calendar": '<rect x="3" y="5" width="18" height="16" rx="2" fill="none"/>'
                    '<line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/>'
                    '<line x1="3" y1="10" x2="21" y2="10"/>',
        "trending": '<polyline points="3,17 9,11 13,15 21,7" fill="none"/>'
                    '<polyline points="14,7 21,7 21,14" fill="none"/>',
        "arrow": '<line x1="4" y1="12" x2="19" y2="12"/><polyline points="12,6 19,12 12,18" fill="none"/>',
        "trophy": '<path d="M7 4h10v4a5 5 0 01-10 0V4z" fill="none"/>'
                  '<path d="M7 6H4.5A2.5 2.5 0 007 8.5" fill="none"/>'
                  '<path d="M17 6h2.5A2.5 2.5 0 0117 8.5" fill="none"/>'
                  '<line x1="12" y1="13" x2="12" y2="17.5"/><line x1="8.5" y1="20" x2="15.5" y2="20"/>'
                  '<line x1="9" y1="17.5" x2="15" y2="17.5"/>',
        "star": '<path d="M12 2.7l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.6 6.2 20.6l1.1-6.5-4.7-4.6 6.5-.9z" fill="{c}" stroke="none"/>'.format(c=color),
    }
    path = body.get(name, "")
    stroke_attrs = "" if name in ("linkedin", "star") else f'stroke="{color}" stroke-width="{stroke_w}" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.3f})" {stroke_attrs}>{path}</g>'


def flame(x, y, size, color):
    s = size / 24
    d = "M12 2c1.5 3-2 5-2 8a3 3 0 006 0c0-1.5-.8-2.3-.8-2.3s1.6.6 1.6 3.3a4.8 4.8 0 01-9.6 0C7.2 6.7 11 6 12 2z"
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.3f})"><path d="{d}" fill="{color}" stroke="none"/></g>'


def pill(x, y, s, bg, border, txt_color):
    w = 20 + len(s) * 7.2
    h = 30
    out = rrect(x, y, w, h, bg, rx=15, extra=f'stroke="{border}" stroke-width="1"')
    out += text(x + w / 2, y + h / 2 + 5, s, size=12.5, weight="600", fill=txt_color, anchor="middle")
    return out, w


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def resolve_photo_path(configured_path):
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


def stat_card(x, y, w, h, bg, icon_name, icon_color, label, value, value_color,
              subtitle=None, border=None):
    extra = f'stroke="{border}" stroke-width="1"' if border else ""
    out = rrect(x, y, w, h, bg, rx=16, extra=extra)
    out += icon(icon_name, x + 14, y + 14, 18, icon_color)
    out += text(x + 40, y + 27, label, size=12.5, weight="500", fill="#b6bccb")
    out += text(x + 14, y + h - (26 if subtitle else 14), str(value), size=26, weight="800", fill=value_color)
    if subtitle:
        out += text(x + 14, y + h - 10, subtitle, size=10.5, fill="#8a90a3")
    return out


def build_heatmap(days, x, y, w, h):
    cell_gap = 3
    cols = 53
    cell = (w - (cols - 1) * cell_gap) / cols
    cell = min(cell, (h - (6 * cell_gap)) / 7)

    by_date = {d["date"]: d["count"] for d in days}
    today = datetime.date.today()
    start = today - datetime.timedelta(weeks=52)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)

    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    def bucket(c):
        if c == 0: return 0
        if c <= 2: return 1
        if c <= 5: return 2
        if c <= 8: return 3
        return 4

    svg = [f'<g transform="translate({x:.1f},{y:.1f})">']
    day_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
    for row, label in day_labels.items():
        cy = row * (cell + cell_gap) + cell * 0.8
        svg.append(text(-10, cy, label, size=10.5, fill="#8a90a3", anchor="end"))

    d = start
    col = 0
    while d <= today:
        row = (d.weekday() + 1) % 7
        cx = col * (cell + cell_gap)
        cy = row * (cell + cell_gap)
        cnt = by_date.get(d.isoformat(), 0)
        color = colors[bucket(cnt)]
        svg.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" fill="{color}"/>')
        if row == 6:
            col += 1
        d += datetime.timedelta(days=1)
    svg.append("</g>")
    return "".join(svg)


def sparkline(points, x, y, w, h, color, fill_area=False):
    if len(points) < 2:
        points = [0, 0]
    lo, hi = min(points), max(points)
    rng = (hi - lo) or 1
    step = w / (len(points) - 1)
    pts = []
    for i, v in enumerate(points):
        px = x + i * step
        py = y + h - ((v - lo) / rng) * h
        pts.append((px, py))
    poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    out = f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
    if fill_area:
        area = f"{x:.1f},{y+h:.1f} " + poly + f" {x+w:.1f},{y+h:.1f}"
        out = f'<polygon points="{area}" fill="{color}" opacity="0.12"/>' + out
    return out


def bars(values, x, y, w, h, color):
    if not values:
        values = [1]
    n = len(values)
    gap = 3
    bw = (w - (n - 1) * gap) / n
    hi = max(values) or 1
    out = []
    for i, v in enumerate(values):
        bh = max(3, (v / hi) * h)
        bx = x + i * (bw + gap)
        by = y + h - bh
        out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{bw/2:.1f}" fill="{color}"/>')
    return "".join(out)


def render(stats, config):
    login = stats["login"]
    streaks = stats["streaks"]
    calendar = stats.get("calendar", [])
    links = config.get("links", {})

    # last-year contribution total (matches the "Last year" subtitle, not lifetime)
    last_year_total = sum(d["count"] for d in calendar[-365:]) if calendar else stats["total_contributions"]

    # recent activity bars: last 24 days
    recent_counts = [d["count"] for d in calendar[-24:]] if calendar else [0] * 24

    # commits sparkline: weekly sums over the last ~14 weeks
    weekly = []
    if calendar:
        chunk = 7
        tail = calendar[-(14 * chunk):]
        for i in range(0, len(tail), chunk):
            weekly.append(sum(d["count"] for d in tail[i:i + chunk]))
    if not weekly:
        weekly = [0, 0]

    parts = [f'<svg width="{W}" height="1070" viewBox="0 0 {W} 1070" xmlns="http://www.w3.org/2000/svg">']
    parts.append(rrect(0, 0, W, 1070, "#020409", rx=26))

    # ---------------- Row 1: greeting | photo | (x + linkedin) ----------------
    y1, h1 = MARGIN, 300
    col_greet_w = 300
    col_photo_w = 290
    col_right_x = MARGIN + col_greet_w + GAP + col_photo_w + GAP
    col_right_w = W - MARGIN - col_right_x

    # Greeting card
    parts.append('<defs><linearGradient id="greetGrad" x1="0" y1="0" x2="1" y2="1">'
                  '<stop offset="0" stop-color="#5b3df0"/><stop offset="1" stop-color="#2f6bf0"/>'
                  '</linearGradient></defs>')
    gx, gw = MARGIN, col_greet_w
    parts.append(rrect(gx, y1, gw, h1, "url(#greetGrad)"))
    parts.append(f'<text x="{gx+24}" y="{y1+52}" font-size="26">👋</text>')
    parts.append(text(gx + 24, y1 + 92, "Hey I'm", size=19, weight="400", fill="#dbe3ff"))
    parts.append(text(gx + 24, y1 + 128, config["display_name"], size=30, weight="800"))
    tagline = config.get("tagline", "")
    if tagline:
        words = tagline.split(" ")
        line1, line2 = "", ""
        for w_ in words:
            (line1 if len(line1) < 22 else line2)
        # simple two-line wrap around ~24 chars
        mid = len(tagline) // 2
        split_at = tagline.rfind(" ", 0, 28) if len(tagline) > 28 else -1
        if split_at > 0:
            l1, l2 = tagline[:split_at], tagline[split_at + 1:]
        else:
            l1, l2 = tagline, ""
        parts.append(text(gx + 24, y1 + 160, l1, size=14.5, fill="#c7cfea"))
        if l2:
            parts.append(text(gx + 24, y1 + 182, l2, size=14.5, fill="#c7cfea"))
    tags = config.get("tags", [])
    tag_colors = [("rgba(168,85,247,0.25)", "#a855f7", "#e9d5ff"),
                  ("rgba(45,212,191,0.2)", "#2dd4bf", "#ccfbf1"),
                  ("rgba(52,211,153,0.2)", "#34d399", "#d1fae5")]
    ty = y1 + 210
    tx = gx + 24
    for i, tg in enumerate(tags[:3]):
        bg, border, fg = tag_colors[i % len(tag_colors)]
        pill_svg, pw = pill(tx, ty, tg, bg, border, fg)
        parts.append(pill_svg)
        tx += pw + 10
        if tx > gx + gw - 60 and i < len(tags) - 1:
            tx = gx + 24
            ty += 38

    # Photo card
    px_, pw_ = MARGIN + col_greet_w + GAP, col_photo_w
    parts.append(rrect(px_, y1, pw_, h1, "#1a1a22"))
    photo_uri = photo_data_uri(config.get("photo_path"))
    if photo_uri:
        clip_id = "photoClip"
        parts.append(f'<clipPath id="{clip_id}"><rect x="{px_}" y="{y1}" width="{pw_}" height="{h1}" rx="18"/></clipPath>')
        parts.append(f'<image href="{photo_uri}" x="{px_}" y="{y1}" width="{pw_}" height="{h1}" '
                      f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})"/>')
    else:
        parts.append(text(px_ + 16, y1 + 26, "add a photo at", size=12, fill="#8a90a3"))
        parts.append(text(px_ + 16, y1 + 44, config.get("photo_path", "assets/photo.jpg"), size=12, fill="#8a90a3"))

    # X / Twitter card + LinkedIn card (stacked)
    rx_, rw_ = col_right_x, col_right_w
    rh_each = (h1 - GAP) / 2
    parts.append(rrect(rx_, y1, rw_, rh_each, "#0d1526"))
    x_link = links.get("twitter", {})
    parts.append(icon("x", rx_ + 20, y1 + 22, 22, "#e7ebf5", stroke_w=2.2))
    parts.append(icon("arrow", rx_ + rw_ - 40, y1 + 22, 20, "#8a90a3"))
    parts.append(text(rx_ + 20, y1 + 70, "X (Twitter)", size=16, weight="700"))
    parts.append(text(rx_ + 20, y1 + 92, x_link.get("handle", "@yourhandle"), size=12.5, fill="#8a90a3"))

    y_li = y1 + rh_each + GAP
    parts.append(rrect(rx_, y_li, rw_, rh_each, "#0d1526"))
    li_link = links.get("linkedin", {})
    parts.append(icon("linkedin", rx_ + 18, y_li + 20, 24, "#0a66c2"))
    parts.append(icon("arrow", rx_ + rw_ - 40, y_li + 22, 20, "#8a90a3"))
    parts.append(text(rx_ + 20, y_li + 70, "LinkedIn", size=16, weight="700"))
    parts.append(text(rx_ + 20, y_li + 92, li_link.get("handle", "linkedin.com/in/you"), size=12.5, fill="#8a90a3"))

    # ---------------- Row 2: Recent Activity | Website ----------------
    y2, h2 = y1 + h1 + GAP, 90
    col2_w = (CONTENT_W - GAP) / 2
    parts.append(rrect(MARGIN, y2, col2_w, h2, "#08201a"))
    parts.append(icon("trending", MARGIN + 18, y2 + 18, 18, "#34d399"))
    parts.append(text(MARGIN + 46, y2 + 31, "Recent Activity", size=14, weight="600"))
    parts.append(bars(recent_counts, MARGIN + 18, y2 + 40, col2_w - 36, 36, "#34d399"))

    wx = MARGIN + col2_w + GAP
    parts.append(rrect(wx, y2, col2_w, h2, "#1c0c2b"))
    web = links.get("website", {})
    parts.append(icon("globe", wx + 18, y2 + 18, 18, "#d8b4fe"))
    parts.append(icon("arrow", wx + col2_w - 38, y2 + 22, 20, "#8a90a3"))
    parts.append(text(wx + 46, y2 + 31, "Website", size=14, weight="600"))
    parts.append(text(wx + 18, y2 + 66, web.get("label", "yoursite.dev"), size=18, weight="700", fill="#d8b4fe"))

    # ---------------- Row 3: GitHub Username (full width) ----------------
    y3, h3 = y2 + h2 + GAP, 76
    parts.append(rrect(MARGIN, y3, CONTENT_W, h3, "#180c2b"))
    parts.append(icon("code", MARGIN + 20, y3 + 24, 20, "#c084fc"))
    parts.append(text(MARGIN + 56, y3 + 30, "GitHub Username", size=12.5, fill="#b6bccb"))
    parts.append(text(MARGIN + 56, y3 + 56, login, size=20, weight="800", fill="#e9d5ff"))
    parts.append(icon("copy", MARGIN + CONTENT_W - 40, y3 + 26, 20, "#8a90a3"))

    # ---------------- Row 4: 4 stat columns ----------------
    y4, h4 = y3 + h3 + GAP, 300
    col4_w = (CONTENT_W - 3 * GAP) / 4
    c1x = MARGIN
    c2x = c1x + col4_w + GAP
    c3x = c2x + col4_w + GAP
    c4x = c3x + col4_w + GAP
    half = (col4_w - GAP) / 2
    top_h = 142
    bot_h = h4 - top_h - GAP

    # Total Stars (tall)
    parts.append(rrect(c1x, y4, col4_w, h4, "#0a1626"))
    parts.append(icon("star", c1x + 16, y4 + 16, 16, "#facc15"))
    parts.append(text(c1x + 40, y4 + 29, "Total Stars", size=13, weight="600"))
    star_row = "".join(icon("star", c1x + 16 + i * 24, y4 + 44, 18,
                             "#facc15" if i < min(5, max(1, round(stats["total_stars"] ** 0.5))) else "#2a3550")
                        for i in range(5))
    parts.append(star_row)
    parts.append(text(c1x + 16, y4 + 118, str(stats["total_stars"]), size=32, weight="800", fill="#facc15"))
    parts.append(f'<line x1="{c1x+16}" y1="{y4+150}" x2="{c1x+col4_w-16}" y2="{y4+150}" stroke="#1e2740" stroke-width="1"/>')
    parts.append(icon("people", c1x + 16, y4 + 166, 16, "#7dd3fc"))
    parts.append(text(c1x + 38, y4 + 179, "Contributed To", size=11.5, fill="#b6bccb"))
    parts.append(text(c1x + 16, y4 + 210, str(stats["contributed_to"]), size=22, weight="800", fill="#7dd3fc"))
    parts.append(text(c1x + 16, y4 + 228, "Repositories", size=10.5, fill="#8a90a3"))

    # PRs + Followers (top) / Commits (bottom)
    parts.append(stat_card(c2x, y4, half, top_h, "#0a1626", "merge", "#60a5fa", "PRs",
                            stats["pull_requests"], "#60a5fa", "Merged"))
    parts.append(stat_card(c2x + half + GAP, y4, half, top_h, "#170c2b", "people", "#c084fc", "Followers",
                            stats["followers"], "#c084fc", "People"))
    yc = y4 + top_h + GAP
    parts.append(rrect(c2x, yc, col4_w, bot_h, "#051a10"))
    parts.append(icon("commit", c2x + 16, yc + 16, 16, "#34d399"))
    parts.append(text(c2x + 40, yc + 29, "Commits", size=13, weight="600"))
    parts.append(text(c2x + 16, yc + 62, str(stats["total_commits"]), size=24, weight="800", fill="#34d399"))
    parts.append(text(c2x + 16, yc + 78, "Total commits", size=10.5, fill="#8a90a3"))
    parts.append(sparkline(weekly, c2x + 16, yc + 90, col4_w - 32, bot_h - 100, "#34d399"))

    # Total Contributions (top) / Longest Streak (bottom)
    parts.append(stat_card(c3x, y4, col4_w, top_h, "#231b04", "calendar", "#facc15", "Total Contributions",
                            f'{last_year_total/1000:.1f}k' if last_year_total >= 1000 else last_year_total,
                            "#facc15", "Last year"))
    yls = y4 + top_h + GAP
    parts.append(stat_card(c3x, yls, col4_w, bot_h, "#1c1530", "trophy", "#facc15", "Longest Streak",
                            streaks["longest"], "#facc15", "Days"))

    # Current Streak (tall)
    parts.append(rrect(c4x, y4, col4_w, h4, "#2a0f14"))
    parts.append(flame(c4x + col4_w / 2 - 14, y4 + 18, 28, "#fb7185"))
    parts.append(text(c4x + col4_w / 2, y4 + 74, "Current Streak", size=13.5, weight="600", anchor="middle"))
    parts.append(text(c4x + col4_w / 2, y4 + 122, str(streaks["current"]), size=34, weight="800",
                       fill="#fda4af", anchor="middle"))
    parts.append(text(c4x + col4_w / 2, y4 + 142, "Days", size=11.5, fill="#c9a3a8", anchor="middle"))
    parts.append(f'<line x1="{c4x+24}" y1="{y4+h4-42}" x2="{c4x+col4_w-24}" y2="{y4+h4-42}" stroke="#4a2027" stroke-width="1"/>')
    parts.append(text(c4x + col4_w / 2, y4 + h4 - 18, "Keep going!", size=12, fill="#c9a3a8", anchor="middle"))

    # ---------------- Row 5: Contribution graph ----------------
    y5 = y4 + h4 + GAP
    h5 = 1070 - MARGIN - y5
    parts.append(rrect(MARGIN, y5, CONTENT_W, h5, "#08101e"))
    parts.append(icon("calendar", MARGIN + 20, y5 + 22, 18, "#8fb4ff"))
    parts.append(text(MARGIN + 50, y5 + 34, "Contribution Graph", size=15, weight="700"))
    parts.append(text(MARGIN + 50, y5 + 52, "Last 12 months", size=11.5, fill="#8a90a3"))
    legend_x = MARGIN + CONTENT_W - 190
    parts.append(text(legend_x, y5 + 30, "Less", size=10.5, fill="#8a90a3"))
    for i, c in enumerate(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]):
        parts.append(rrect(legend_x + 34 + i * 16, y5 + 20, 12, 12, c, rx=3))
    parts.append(text(legend_x + 34 + 5 * 16 + 8, y5 + 30, "More", size=10.5, fill="#8a90a3"))
    parts.append(build_heatmap(calendar, MARGIN + 56, y5 + 76, CONTENT_W - 76, h5 - 92))

    parts.append("</svg>")
    return "".join(parts)

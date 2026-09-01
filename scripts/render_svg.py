"""
Renders the bento-grid stats card as a single self-contained, animated SVG.
Every card uses a diagonal brand-color -> near-black gradient with a soft
blurred glow blob (clipped to the card's rounded corners), plus tasteful
SMIL motion: staggered heatmap reveal, a drawing-in sparkline, growing
activity bars, and a gently pulsing streak flame.
"""
import base64
import datetime
import html
import os
import sys

try:
    import requests
except ImportError:
    requests = None

W = 900
MARGIN = 20
GAP = 16
CONTENT_W = W - 2 * MARGIN

_uid = [0]


def uid(prefix):
    _uid[0] += 1
    return f"{prefix}{_uid[0]}"


def esc(s):
    return html.escape(str(s))


def rrect(x, y, w, h, fill, rx=18, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" {extra}/>'


def text(x, y, s, size=14, weight="400", fill="#fff", anchor="start",
          family="Segoe UI, Helvetica, Arial, sans-serif", opacity=1):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" font-family="{family}" opacity="{opacity}">{esc(s)}</text>')


def card_bg(defs, x, y, w, h, start, end, glow=None, rx=16, glow_pos=(0.85, 0.18), glow_r_mult=0.6):
    """Diagonal gradient card background + an optional soft glow blob clipped to its rounded corners."""
    gid = uid("cg")
    defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/></linearGradient>')
    out = rrect(x, y, w, h, f"url(#{gid})", rx=rx)
    if glow:
        cid = uid("clip")
        defs.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"/></clipPath>')
        gx, gy = x + w * glow_pos[0], y + h * glow_pos[1]
        r = min(w, h) * glow_r_mult
        out += (f'<g clip-path="url(#{cid})"><circle cx="{gx:.1f}" cy="{gy:.1f}" r="{r:.1f}" '
                f'fill="{glow}" opacity="0.30" filter="url(#blurSoft)"/></g>')
    return out


def icon(name, x, y, size, color="#fff", stroke_w=2):
    s = size / 24
    body = {
        "x": '<line x1="4" y1="4" x2="20" y2="20"/><line x1="20" y1="4" x2="4" y2="20"/>',
        "linkedin": f'<rect x="2" y="2" width="20" height="20" rx="4" fill="{color}" stroke="none"/>'
                    '<text x="12" y="16.5" font-size="10" font-weight="800" fill="#fff" '
                    'text-anchor="middle" font-family="Segoe UI, Arial, sans-serif">in</text>',
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
        "star": f'<path d="M12 2.7l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.6 6.2 20.6l1.1-6.5-4.7-4.6 6.5-.9z" fill="{color}" stroke="none"/>',
    }
    path = body.get(name, "")
    stroke_attrs = "" if name in ("linkedin", "star") else \
        f'stroke="{color}" stroke-width="{stroke_w}" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.3f})" {stroke_attrs}>{path}</g>'


def flame(x, y, size, color, animate=True):
    """A flame icon that gently 'flickers' via a scale pulse around its own center."""
    s = size / 24
    d = "M12 2c1.5 3-2 5-2 8a3 3 0 006 0c0-1.5-.8-2.3-.8-2.3s1.6.6 1.6 3.3a4.8 4.8 0 01-9.6 0C7.2 6.7 11 6 12 2z"
    cx, cy = x + size / 2, y + size / 2
    inner = f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.3f})"><path d="{d}" fill="{color}" stroke="none"/></g>'
    if not animate:
        return inner
    anim = ('<animateTransform attributeName="transform" type="scale" '
            'values="1;1.12;0.97;1" keyTimes="0;0.4;0.7;1" dur="1.8s" repeatCount="indefinite"/>')
    return (f'<g transform="translate({cx:.1f},{cy:.1f})"><g>{anim}'
            f'<g transform="translate({-cx:.1f},{-cy:.1f})">{inner}</g></g></g>')


def glow_text(x, y, s, size, weight, fill, glow_color, anchor="start"):
    """A big stat number with a soft pulsing glow behind it."""
    t = text(x, y, s, size=size, weight=weight, fill=fill, anchor=anchor)
    halo = (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{glow_color}" '
            f'text-anchor="{anchor}" font-family="Segoe UI, Helvetica, Arial, sans-serif" filter="url(#blurSoft)">'
            f'{esc(s)}<animate attributeName="opacity" values="0.25;0.55;0.25" dur="3s" repeatCount="indefinite"/>'
            f'</text>')
    return halo + t


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


def photo_data_uri(config):
    """Prefers a hosted photo_url (downloaded once per run and embedded as
    base64, so the card never depends on the other host being up at view
    time); falls back to a local file under photo_path / assets/."""
    url = config.get("photo_url")
    if url and requests is not None:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            mime = ctype.split("/")[-1].split(";")[0].lower() if "/" in ctype else ""
            if mime not in ("jpeg", "jpg", "png", "webp", "gif"):
                ext = os.path.splitext(url.split("?")[0])[1].lstrip(".").lower()
                mime = "jpeg" if ext in ("jpg", "jpeg") else (ext or "jpeg")
            b64 = base64.b64encode(resp.content).decode()
            return f"data:image/{mime};base64,{b64}"
        except Exception as e:
            print(f"WARNING: could not fetch photo_url ({e}); falling back to local photo_path", file=sys.stderr)

    resolved = resolve_photo_path(config.get("photo_path"))
    if not resolved:
        return None
    ext = os.path.splitext(resolved)[1].lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(resolved, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{b64}"


def stat_card(defs, x, y, w, h, grad, icon_name, icon_color, label, value, value_color,
              subtitle=None, label_size=12.5, icon_size=18, label_x_offset=40, glow=True):
    start, end, gc = grad
    out = card_bg(defs, x, y, w, h, start, end, glow=gc if glow else None)
    out += icon(icon_name, x + 12, y + 12, icon_size, icon_color)
    out += text(x + label_x_offset, y + 12 + icon_size * 0.72, label, size=label_size, weight="500", fill="#c7cdde")
    out += text(x + 14, y + h - (26 if subtitle else 14), str(value), size=26, weight="800", fill=value_color)
    if subtitle:
        out += text(x + 14, y + h - 10, subtitle, size=10.5, fill="#9aa0b3")
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

    day_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
    svg = [f'<g transform="translate({x:.1f},{y:.1f})">']
    for row, label in day_labels.items():
        cy = row * (cell + cell_gap) + cell * 0.8
        svg.append(text(-10, cy, label, size=10.5, fill="#9aa0b3", anchor="end"))

    # build column-by-column so each week can fade in with a small stagger
    d = start
    col = 0
    col_cells = []
    while d <= today:
        row = (d.weekday() + 1) % 7
        cnt = by_date.get(d.isoformat(), 0)
        color = colors[bucket(cnt)]
        col_cells.append((row, color))
        if row == 6:
            delay = col * 0.012
            cx = col * (cell + cell_gap)
            svg.append(f'<g opacity="0">'
                       f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur="0.5s" fill="freeze"/>')
            for r, c in col_cells:
                cy = r * (cell + cell_gap)
                svg.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" fill="{c}"/>')
            svg.append('</g>')
            col_cells = []
            col += 1
        d += datetime.timedelta(days=1)
    svg.append("</g>")
    return "".join(svg)


def sparkline(points, x, y, w, h, color):
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
    return (f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round" pathLength="100" '
            f'stroke-dasharray="100" stroke-dashoffset="100">'
            f'<animate attributeName="stroke-dashoffset" from="100" to="0" dur="1.4s" fill="freeze"/>'
            f'</polyline>')


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
        delay = i * 0.02
        out.append(
            f'<g transform="translate({bx:.1f},{y+h:.1f})">'
            f'<rect x="0" y="{-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{bw/2:.1f}" fill="{color}" '
            f'transform="scale(1,0)" style="transform-box:fill-box;transform-origin:bottom">'
            f'<animateTransform attributeName="transform" type="scale" from="1 0" to="1 1" '
            f'begin="{delay:.3f}s" dur="0.5s" fill="freeze"/>'
            f'</rect></g>'
        )
    return "".join(out)


def render(stats, config):
    login = stats["login"]
    streaks = stats["streaks"]
    calendar = stats.get("calendar", [])
    links = config.get("links", {})
    defs = []

    last_year_total = sum(d["count"] for d in calendar[-365:]) if calendar else stats["total_contributions"]
    recent_counts = [d["count"] for d in calendar[-24:]] if calendar else [0] * 24

    weekly = []
    if calendar:
        chunk = 7
        tail = calendar[-(14 * chunk):]
        for i in range(0, len(tail), chunk):
            weekly.append(sum(d["count"] for d in tail[i:i + chunk]))
    if not weekly:
        weekly = [0, 0]

    H = 1100
    parts = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    defs.append('<filter id="blurSoft" x="-60%" y="-60%" width="220%" height="220%">'
                 '<feGaussianBlur stdDeviation="22"/></filter>')
    defs.append('<linearGradient id="greetGrad" x1="0" y1="0" x2="1" y2="1">'
                 '<stop offset="0" stop-color="#8b5cf6"/><stop offset="0.45" stop-color="#4338ca"/>'
                 '<stop offset="1" stop-color="#0b1024"/></linearGradient>')

    body = [rrect(0, 0, W, H, "#020409", rx=26)]

    # ---------------- Row 1 ----------------
    y1, h1 = MARGIN, 300
    col_greet_w = 300
    col_photo_w = 290
    col_right_x = MARGIN + col_greet_w + GAP + col_photo_w + GAP
    col_right_w = W - MARGIN - col_right_x

    gx, gw = MARGIN, col_greet_w
    body.append(rrect(gx, y1, gw, h1, "url(#greetGrad)"))
    cid = uid("clip")
    defs.append(f'<clipPath id="{cid}"><rect x="{gx}" y="{y1}" width="{gw}" height="{h1}" rx="16"/></clipPath>')
    body.append(
        f'<g clip-path="url(#{cid})">'
        f'<circle cx="{gx+gw*0.92}" cy="{y1+h1*0.06}" r="130" fill="#c4b5fd" opacity="0.32" filter="url(#blurSoft)"/>'
        f'<circle cx="{gx+gw*0.05}" cy="{y1+h1*0.98}" r="150" fill="#38bdf8" opacity="0.24" filter="url(#blurSoft)"/>'
        f'</g>'
    )
    body.append(f'<text x="{gx+24}" y="{y1+52}" font-size="26">👋</text>')
    body.append(text(gx + 24, y1 + 92, "Hey I'm", size=19, weight="400", fill="#e3e8ff"))
    body.append(text(gx + 24, y1 + 128, config["display_name"], size=30, weight="800"))
    tagline = config.get("tagline", "")
    if tagline:
        split_at = tagline.rfind(" ", 0, 28) if len(tagline) > 28 else -1
        l1, l2 = (tagline[:split_at], tagline[split_at + 1:]) if split_at > 0 else (tagline, "")
        body.append(text(gx + 24, y1 + 160, l1, size=14.5, fill="#d7dcf5"))
        if l2:
            body.append(text(gx + 24, y1 + 182, l2, size=14.5, fill="#d7dcf5"))
    tags = config.get("tags", [])
    tag_colors = [("rgba(168,85,247,0.28)", "#a855f7", "#f1e4ff"),
                  ("rgba(45,212,191,0.22)", "#2dd4bf", "#d7fbf6"),
                  ("rgba(52,211,153,0.22)", "#34d399", "#dbfbea")]
    ty, tx = y1 + 210, gx + 24
    for i, tg in enumerate(tags[:3]):
        bg, border, fg = tag_colors[i % len(tag_colors)]
        pill_svg, pw = pill(tx, ty, tg, bg, border, fg)
        body.append(pill_svg)
        tx += pw + 10
        if tx > gx + gw - 60 and i < len(tags) - 1:
            tx, ty = gx + 24, ty + 38

    # Photo card
    px_, pw_ = MARGIN + col_greet_w + GAP, col_photo_w
    photo_uri = photo_data_uri(config)
    if photo_uri:
        clip_id = uid("clip")
        defs.append(f'<clipPath id="{clip_id}"><rect x="{px_}" y="{y1}" width="{pw_}" height="{h1}" rx="18"/></clipPath>')
        body.append(f'<image href="{photo_uri}" x="{px_}" y="{y1}" width="{pw_}" height="{h1}" '
                     f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})"/>')
    else:
        body.append(card_bg(defs, px_, y1, pw_, h1, "#25263a", "#0a0a12", glow="#5b6bff"))
        body.append(text(px_ + 16, y1 + 26, "add a photo: set photo_url", size=12, fill="#a7acc2"))
        body.append(text(px_ + 16, y1 + 44, "or photo_path in config.json", size=12, fill="#a7acc2"))

    # X + LinkedIn
    rx_, rw_ = col_right_x, col_right_w
    rh_each = (h1 - GAP) / 2
    body.append(card_bg(defs, rx_, y1, rw_, rh_each, "#1b2a4f", "#05070d", glow="#5b8cff"))
    x_link = links.get("twitter", {})
    body.append(icon("x", rx_ + 20, y1 + 22, 22, "#e7ebf5", stroke_w=2.2))
    body.append(icon("arrow", rx_ + rw_ - 40, y1 + 22, 20, "#9aa0b3"))
    body.append(text(rx_ + 20, y1 + 70, "X (Twitter)", size=16, weight="700"))
    body.append(text(rx_ + 20, y1 + 92, x_link.get("handle", "@yourhandle"), size=12.5, fill="#9aa0b3"))

    y_li = y1 + rh_each + GAP
    body.append(card_bg(defs, rx_, y_li, rw_, rh_each, "#123a72", "#05070d", glow="#3b82f6"))
    li_link = links.get("linkedin", {})
    body.append(icon("linkedin", rx_ + 18, y_li + 20, 24, "#0a66c2"))
    body.append(icon("arrow", rx_ + rw_ - 40, y_li + 22, 20, "#9aa0b3"))
    body.append(text(rx_ + 20, y_li + 70, "LinkedIn", size=16, weight="700"))
    body.append(text(rx_ + 20, y_li + 92, li_link.get("handle", "linkedin.com/in/you"), size=12.5, fill="#9aa0b3"))

    # ---------------- Row 2 ----------------
    y2, h2 = y1 + h1 + GAP, 90
    col2_w = (CONTENT_W - GAP) / 2
    body.append(card_bg(defs, MARGIN, y2, col2_w, h2, "#0f3d2e", "#020705", glow="#34d399"))
    body.append(icon("trending", MARGIN + 18, y2 + 18, 18, "#34d399"))
    body.append(text(MARGIN + 46, y2 + 31, "Recent Activity", size=14, weight="600"))
    body.append(bars(recent_counts, MARGIN + 18, y2 + 40, col2_w - 36, 36, "#34d399"))

    wx = MARGIN + col2_w + GAP
    body.append(card_bg(defs, wx, y2, col2_w, h2, "#3a1454", "#08040f", glow="#c084fc"))
    web = links.get("website", {})
    body.append(icon("globe", wx + 18, y2 + 18, 18, "#d8b4fe"))
    body.append(icon("arrow", wx + col2_w - 38, y2 + 22, 20, "#9aa0b3"))
    body.append(text(wx + 46, y2 + 31, "Website", size=14, weight="600"))
    body.append(text(wx + 18, y2 + 66, web.get("label", "yoursite.dev"), size=18, weight="700", fill="#d8b4fe"))

    # ---------------- Row 3 ----------------
    y3, h3 = y2 + h2 + GAP, 76
    body.append(card_bg(defs, MARGIN, y3, CONTENT_W, h3, "#2a1454", "#08040f", glow="#a855f7",
                         glow_pos=(0.92, 0.5), glow_r_mult=0.5))
    body.append(icon("code", MARGIN + 20, y3 + 24, 20, "#c084fc"))
    body.append(text(MARGIN + 56, y3 + 30, "GitHub Username", size=12.5, fill="#c7cdde"))
    body.append(text(MARGIN + 56, y3 + 56, login, size=20, weight="800", fill="#f1e4ff"))
    body.append(icon("copy", MARGIN + CONTENT_W - 40, y3 + 26, 20, "#9aa0b3"))

    # ---------------- Row 4 ----------------
    y4, h4 = y3 + h3 + GAP, 300
    col4_w = (CONTENT_W - 3 * GAP) / 4
    c1x = MARGIN
    c2x = c1x + col4_w + GAP
    c3x = c2x + col4_w + GAP
    c4x = c3x + col4_w + GAP
    small_gap = 10
    half = (col4_w - small_gap) / 2
    top_h = 142
    bot_h = h4 - top_h - GAP

    # Total Stars
    body.append(card_bg(defs, c1x, y4, col4_w, h4, "#3a2a06", "#0a0805", glow="#facc15"))
    body.append(icon("star", c1x + 16, y4 + 16, 16, "#facc15"))
    body.append(text(c1x + 40, y4 + 29, "Total Stars", size=13, weight="600"))
    filled = min(5, max(1, round(stats["total_stars"] ** 0.5)))
    body.append("".join(icon("star", c1x + 16 + i * 24, y4 + 44, 18, "#facc15" if i < filled else "#3a3f57")
                         for i in range(5)))
    body.append(glow_text(c1x + 16, y4 + 118, str(stats["total_stars"]), 32, "800", "#facc15", "#facc15"))
    body.append(f'<line x1="{c1x+16}" y1="{y4+150}" x2="{c1x+col4_w-16}" y2="{y4+150}" stroke="#3a3f57" stroke-width="1"/>')
    body.append(icon("people", c1x + 16, y4 + 166, 16, "#7dd3fc"))
    body.append(text(c1x + 38, y4 + 179, "Contributed To", size=11.5, fill="#c7cdde"))
    body.append(text(c1x + 16, y4 + 210, str(stats["contributed_to"]), size=22, weight="800", fill="#7dd3fc"))
    body.append(text(c1x + 16, y4 + 228, "Repositories", size=10.5, fill="#9aa0b3"))

    # PRs + Followers (top) / Commits (bottom)
    body.append(stat_card(defs, c2x, y4, half, top_h, ("#123055", "#05070d", "#3b82f6"), "merge", "#60a5fa", "PRs",
                           stats["pull_requests"], "#60a5fa", "Merged",
                           label_size=11.5, icon_size=14, label_x_offset=32))
    body.append(stat_card(defs, c2x + half + small_gap, y4, half, top_h, ("#2a1440", "#05070d", "#a855f7"),
                           "people", "#c084fc", "Followers", stats["followers"], "#c084fc", "People",
                           label_size=11.5, icon_size=14, label_x_offset=32))
    yc = y4 + top_h + GAP
    body.append(card_bg(defs, c2x, yc, col4_w, bot_h, "#0d3324", "#020705", glow="#34d399"))
    body.append(icon("commit", c2x + 16, yc + 16, 16, "#34d399"))
    body.append(text(c2x + 40, yc + 29, "Commits", size=13, weight="600"))
    body.append(text(c2x + 16, yc + 62, str(stats["total_commits"]), size=24, weight="800", fill="#34d399"))
    body.append(text(c2x + 16, yc + 78, "Total commits", size=10.5, fill="#9aa0b3"))
    body.append(sparkline(weekly, c2x + 16, yc + 90, col4_w - 32, bot_h - 100, "#34d399"))

    # Total Contributions (top) / Longest Streak (bottom)
    body.append(stat_card(defs, c3x, y4, col4_w, top_h, ("#332705", "#0a0805", "#facc15"), "calendar", "#facc15",
                           "Total Contributions",
                           f'{last_year_total/1000:.1f}k' if last_year_total >= 1000 else last_year_total,
                           "#facc15", "Last year"))
    yls = y4 + top_h + GAP
    body.append(stat_card(defs, c3x, yls, col4_w, bot_h, ("#2a1a4a", "#08040f", "#c084fc"), "trophy", "#facc15",
                           "Longest Streak", streaks["longest"], "#facc15", "Days"))

    # Current Streak
    body.append(card_bg(defs, c4x, y4, col4_w, h4, "#4a1420", "#0a0508", glow="#fb7185"))
    body.append(flame(c4x + col4_w / 2 - 14, y4 + 18, 28, "#fb7185"))
    body.append(text(c4x + col4_w / 2, y4 + 74, "Current Streak", size=13.5, weight="600", anchor="middle"))
    body.append(glow_text(c4x + col4_w / 2, y4 + 122, str(streaks["current"]), 34, "800", "#fda4af", "#fb7185", "middle"))
    body.append(text(c4x + col4_w / 2, y4 + 142, "Days", size=11.5, fill="#d6b0b5", anchor="middle"))
    body.append(f'<line x1="{c4x+24}" y1="{y4+h4-42}" x2="{c4x+col4_w-24}" y2="{y4+h4-42}" stroke="#5a2732" stroke-width="1"/>')
    body.append(text(c4x + col4_w / 2, y4 + h4 - 18, "Keep going!", size=12, fill="#d6b0b5", anchor="middle"))

    # ---------------- Row 5 ----------------
    y5 = y4 + h4 + GAP
    h5 = 200
    body.append(card_bg(defs, MARGIN, y5, CONTENT_W, h5, "#0d1830", "#03060d", glow="#3b82f6",
                         glow_pos=(0.9, 0.1), glow_r_mult=0.45))
    body.append(icon("calendar", MARGIN + 20, y5 + 22, 18, "#8fb4ff"))
    body.append(text(MARGIN + 50, y5 + 34, "Contribution Graph", size=15, weight="700"))
    body.append(text(MARGIN + 50, y5 + 52, "Last 12 months", size=11.5, fill="#9aa0b3"))
    legend_x = MARGIN + CONTENT_W - 190
    body.append(text(legend_x, y5 + 30, "Less", size=10.5, fill="#9aa0b3"))
    for i, c in enumerate(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]):
        body.append(rrect(legend_x + 34 + i * 16, y5 + 20, 12, 12, c, rx=3))
    body.append(text(legend_x + 34 + 5 * 16 + 8, y5 + 30, "More", size=10.5, fill="#9aa0b3"))
    body.append(build_heatmap(calendar, MARGIN + 56, y5 + 76, CONTENT_W - 76, h5 - 92))

    # ---------------- Attribution ----------------
    body.append(text(W / 2, 1076, "✦ GitFrame ✦", size=17, weight="500", fill="#5a627a", anchor="middle",
                     family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace"))

    svg = parts[0] + f"<defs>{''.join(defs)}</defs>" + "".join(body) + "</svg>"
    return svg

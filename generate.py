#!/usr/bin/env python3
"""
Fast26-styled GitHub profile card generator.

Fetches live stats from the GitHub GraphQL API and renders a single light-mode
SVG card in the Fast26 design language: navy on bone-white, dot-grid backdrop,
a fading inset frame, and the Sora / Plus Jakarta Sans type pairing.

Output:
  - dist/profile-card.svg

Run locally with a token in the GH_TOKEN env var:
    GH_TOKEN=ghp_xxx GH_USERNAME=Faldi0126 python generate.py
"""

import os
import sys
import json
import html
import base64
import datetime
import urllib.request
import urllib.error

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _font_b64(filename):
    with open(os.path.join(FONT_DIR, filename), "rb") as f:
        return base64.b64encode(f.read()).decode()


def font_face_block():
    """Return a <style> block embedding the subset fonts as base64 WOFF2 so the
    card renders identically anywhere, including GitHub's sanitized SVG host."""
    sora = _font_b64("sora-500.woff2")
    jk400 = _font_b64("jakarta-400.woff2")
    jk600 = _font_b64("jakarta-600.woff2")
    return f"""
    <style>
      @font-face {{ font-family:'Sora'; font-weight:500;
        src:url('data:font/woff2;base64,{sora}') format('woff2'); }}
      @font-face {{ font-family:'Plus Jakarta Sans'; font-weight:400;
        src:url('data:font/woff2;base64,{jk400}') format('woff2'); }}
      @font-face {{ font-family:'Plus Jakarta Sans'; font-weight:600;
        src:url('data:font/woff2;base64,{jk600}') format('woff2'); }}
      text {{ font-family:'Plus Jakarta Sans', sans-serif; }}
    </style>"""

USERNAME = os.environ.get("GH_USERNAME", "Faldi0126")
TOKEN = os.environ.get("GH_TOKEN", "")

# ---- your identity (edit these any time) ------------------------------------
DISPLAY_NAME = os.environ.get("DISPLAY_NAME", "M Rifaldi")
TAGLINE = os.environ.get("TAGLINE", "I care deeply about design and turn ideas into polished products.")
CAREER_START = datetime.date(2023, 11, 1)
# -----------------------------------------------------------------------------

API_GRAPHQL = "https://api.github.com/graphql"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def _post_graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(API_GRAPHQL, data=body, method="POST")
    req.add_header("Authorization", f"bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def years_of_experience(today=None):
    """Decimal years since CAREER_START, one place, e.g. 2.7."""
    today = today or datetime.date.today()
    return round((today - CAREER_START).days / 365.25, 1)


def _all_time_commits(years):
    """Sum totalCommitContributions across every year the user contributed.

    contributionsCollection is capped at a one-year window, so an all-time
    number means one sub-query per contribution year. Aliases let us do it in
    a single request.
    """
    if not years:
        return 0
    slices = "\n".join(
        f'        y{y}: contributionsCollection('
        f'from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
        f"{{ totalCommitContributions }}"
        for y in years
    )
    query = f"""
    query($login: String!) {{
      user(login: $login) {{
{slices}
      }}
    }}
    """
    data = _post_graphql(query, {"login": USERNAME})
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    user = data["data"]["user"]
    return sum(user[f"y{y}"]["totalCommitContributions"] for y in years)


def fetch_stats():
    """Return a dict of everything the card needs."""
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
        }
        contributionsCollection {
          contributionYears
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    data = _post_graphql(query, {"login": USERNAME})
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    user = data["data"]["user"]

    # Streak: walk the contribution calendar backwards from the most recent day.
    days = []
    for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in week["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort(key=lambda x: x[0])
    current_streak = 0
    for _, count in reversed(days):
        if count > 0:
            current_streak += 1
        else:
            # allow the streak to still be alive if today simply has 0 yet
            if current_streak == 0:
                continue
            break

    contrib_years = user["contributionsCollection"]["contributionYears"]
    return {
        "name": user["name"] or DISPLAY_NAME,
        "login": user["login"],
        "repos": user["repositories"]["totalCount"],
        "commits": _all_time_commits(contrib_years),
        "streak": current_streak,
        "years": years_of_experience(),
    }


def demo_stats():
    """Fallback used when no token is present, so the design can be previewed."""
    return {
        "name": DISPLAY_NAME,
        "login": USERNAME,
        "repos": 34,
        "commits": 3184,
        "streak": 47,
        "years": years_of_experience(),
    }


# ---------------------------------------------------------------------------
# Palette — light only. Navy replaces the old near-black.
# ---------------------------------------------------------------------------
P = {
    "bg": "#F5F5F2",
    "dot": "#DBDBD5",
    "surface": "#FFFFFF",
    "navy": "#16233F",          # primary ink / inverse surface
    "on_variant": "#4A5268",
    "on_muted": "#858B99",
    "on_faint": "#9BA1AD",
    "on_inverse": "#F5F5F2",
    "frame": "#16233F",
    "divider": "#E3E3DD",
}

W, H = 840, 496
PAD = 28


def fmt(n):
    """Human number: 1462 -> 1,462."""
    return f"{n:,}"


def monogram(cx, cy):
    """A bold geometric 'F' sitting directly on the card surface (no plate).
    Three slab strokes: a full-height stem, a top arm sheared at 45 degrees on
    its outer end, and a shorter mid arm. Drawn from the letter's top-left, so
    (cx, cy) is that corner, not the centre."""
    stem, arm_h = 11, 11          # stroke weights
    top_w, mid_w = 36, 27         # arm lengths
    height, mid_y = 46, 18        # letter height, mid-arm offset
    shear = 9                     # 45-degree cut on the top arm's outer end
    return f"""
    <g transform="translate({cx},{cy})" fill="{P['navy']}">
      <path d="M0 0 H{top_w} L{top_w - shear} {arm_h} H0 Z"/>
      <path d="M0 {mid_y} H{mid_w} L{mid_w - shear} {mid_y + arm_h} H0 Z"/>
      <rect x="0" y="0" width="{stem}" height="{height}"/>
    </g>"""


def stat_tile(x, y, w, h, number, label, inverted=False):
    """One stat tile: big Sora number + tiny uppercase label."""
    fill = P["navy"] if inverted else P["surface"]
    num_color = P["on_inverse"] if inverted else P["navy"]
    label_color = P["on_inverse"] if inverted else P["on_faint"]
    stroke = "none" if inverted else P["divider"]
    return f"""
    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}"
            stroke="{stroke}" stroke-width="1"/>
      <text x="{x + 18}" y="{y + 44}" font-family="Sora" font-size="30"
            font-weight="500" fill="{num_color}">{html.escape(number)}</text>
      <text x="{x + 18}" y="{y + 67}" font-family="'Plus Jakarta Sans'"
            font-size="10" font-weight="600" letter-spacing="1.4"
            fill="{label_color}">{html.escape(label)}</text>
    </g>"""


# ---------------------------------------------------------------------------
# Tech icons — hand-drawn monochrome glyphs, 22x22 viewBox, navy stroke/fill.
# Each returns the inner markup for a group already translated to the slot.
# ---------------------------------------------------------------------------
NAVY = P["navy"]


def _ts():
    return (f'<rect x="0" y="0" width="22" height="22" rx="4" fill="{NAVY}"/>'
            f'<text x="11" y="15.5" text-anchor="middle" font-family="Sora"'
            f' font-size="11" font-weight="500" fill="#FFFFFF">TS</text>')


def _vue():
    # outer V, then an inset V knocked back so the two read as distinct planes
    return (f'<path d="M1.5 3.5 L6.4 3.5 L11 11.6 L15.6 3.5 L20.5 3.5 L11 19.8 Z"'
            f' fill="{NAVY}" opacity="0.32"/>'
            f'<path d="M6.4 3.5 L8.9 3.5 L11 7.2 L13.1 3.5 L15.6 3.5 L11 11.6 Z"'
            f' fill="{NAVY}"/>')


def _node():
    # hexagon shell with a clean lowercase-n cut inside
    return (f'<path d="M11 1.4 L19.6 6.4 L19.6 15.6 L11 20.6 L2.4 15.6 L2.4 6.4 Z"'
            f' fill="none" stroke="{NAVY}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="M8.4 14.6 L8.4 8.4 M8.4 10 C9.1 8.7 10.2 8.3 11.4 8.3'
            f' C12.8 8.3 13.6 9.2 13.6 10.7 L13.6 14.6"'
            f' fill="none" stroke="{NAVY}" stroke-width="1.6"'
            f' stroke-linecap="round" stroke-linejoin="round"/>')


def _flutter():
    return (f'<path d="M13.9 1 L21 1 L8.6 13.4 L5 9.8 Z" fill="{NAVY}"/>'
            f'<path d="M13.9 10.4 L21 10.4 L15.5 15.9 L11.9 12.3 Z" fill="{NAVY}"'
            f' opacity="0.45"/>'
            f'<path d="M11.9 12.3 L15.5 15.9 L21 21.4 L13.9 21.4 L8.4 15.9 Z"'
            f' fill="{NAVY}"/>')


def _aws():
    return (f'<text x="11" y="10.5" text-anchor="middle" font-family="Sora"'
            f' font-size="9" font-weight="500" fill="{NAVY}">aws</text>'
            f'<path d="M2 15.5 C6 18.6 16 18.6 20 15.5" fill="none"'
            f' stroke="{NAVY}" stroke-width="1.6" stroke-linecap="round"/>'
            f'<path d="M17.4 14.6 L20.4 15.3 L19.4 18.1" fill="none"'
            f' stroke="{NAVY}" stroke-width="1.6" stroke-linecap="round"'
            f' stroke-linejoin="round"/>')


def _kintone():
    return (f'<rect x="1" y="1" width="20" height="20" rx="5" fill="none"'
            f' stroke="{NAVY}" stroke-width="1.6"/>'
            f'<path d="M7.4 5.8 L7.4 16.2 M7.4 11.4 L13 5.8 M9.6 9.2 L14.4 16.2"'
            f' fill="none" stroke="{NAVY}" stroke-width="1.6"'
            f' stroke-linecap="round" stroke-linejoin="round"/>')


TECH = [
    ("TypeScript", _ts),
    ("Vue", _vue),
    ("Node.js", _node),
    ("Flutter", _flutter),
    ("AWS", _aws),
    ("Kintone", _kintone),
]


CHIP_W, CHIP_H, CHIP_GAP = 74, 74, 14


def tech_row(x, y):
    """Row of framed tech chips: icon plate + label beneath."""
    out = ""
    chip_w, chip_h, gap = CHIP_W, CHIP_H, CHIP_GAP
    for i, (name, draw) in enumerate(TECH):
        cx = x + i * (chip_w + gap)
        out += f"""
    <g>
      <rect x="{cx}" y="{y}" width="{chip_w}" height="{chip_h}" rx="16"
            fill="{P['surface']}" stroke="{P['divider']}" stroke-width="1"/>
      <g transform="translate({cx + chip_w/2 - 11},{y + 18})">{draw()}</g>
      <text x="{cx + chip_w/2}" y="{y + 60}" text-anchor="middle"
            font-family="'Plus Jakarta Sans'" font-size="9" font-weight="600"
            letter-spacing="0.6" fill="{P['on_muted']}">{html.escape(name.upper())}</text>
    </g>"""
    return out


def render(stats):
    defs = f"""
    <pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="{P['dot']}"/>
    </pattern>
    <linearGradient id="frameFade" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{P['frame']}" stop-opacity="0.7"/>
      <stop offset="60%" stop-color="{P['frame']}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="cardClip">
      <rect x="{PAD}" y="{PAD}" width="{W - 2*PAD}" height="{H - 2*PAD}" rx="24"/>
    </clipPath>"""

    card_x, card_y = PAD, PAD
    card_w, card_h = W - 2 * PAD, H - 2 * PAD
    inner = card_x + 32

    mark = monogram(card_x + card_w - 84, card_y + 44)

    header = f"""
    <text x="{inner}" y="{card_y + 46}" font-family="'Plus Jakarta Sans'"
          font-size="11" font-weight="600" letter-spacing="2"
          fill="{P['on_muted']}">SOFTWARE ENGINEER · PRODUCT BUILDER</text>
    <text x="{inner}" y="{card_y + 92}" font-family="Sora" font-size="40"
          font-weight="500" fill="{P['navy']}">{html.escape(stats['name'])}</text>
    <text x="{inner}" y="{card_y + 120}" font-family="'Plus Jakarta Sans'"
          font-size="13" font-weight="400"
          fill="{P['on_variant']}">{html.escape(TAGLINE)}</text>
    <text x="{inner}" y="{card_y + 144}" font-family="'Plus Jakarta Sans'"
          font-size="11" font-weight="600" letter-spacing="1"
          fill="{P['on_faint']}">@{html.escape(stats['login'])}</text>"""

    # --- stat tiles: 4 across ---------------------------------------------
    tiles_y = card_y + 176
    tile_gap = 14
    tile_w = (card_w - 64 - tile_gap * 3) / 4
    tile_h = 84
    tiles = ""
    tile_data = [
        (f"{stats['years']:.1f}", "YEARS EXPERIENCE", True),
        (fmt(stats["streak"]), "DAY STREAK", False),
        (fmt(stats["commits"]), "COMMITS", False),
        (fmt(stats["repos"]), "REPOS", False),
    ]
    for i, (num, lbl, inv) in enumerate(tile_data):
        tx = inner + i * (tile_w + tile_gap)
        tiles += stat_tile(tx, tiles_y, tile_w, tile_h, num, lbl, inverted=inv)

    # --- most used section --------------------------------------------------
    label_y = tiles_y + tile_h + 40
    section_label = f"""
    <text x="{inner}" y="{label_y}" font-family="'Plus Jakarta Sans'"
          font-size="10" font-weight="600" letter-spacing="1.6"
          fill="{P['on_faint']}">MOST USED</text>"""

    chips_y = label_y + 16
    chips = tech_row(inner, chips_y)

    updated = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y")
    footer = f"""
    <text x="{card_x + card_w - 32}" y="{chips_y + CHIP_H + 32}"
          text-anchor="end" font-family="'Plus Jakarta Sans'" font-size="10"
          font-weight="500" letter-spacing="0.5"
          fill="{P['on_faint']}">UPDATED {updated.upper()}</text>"""

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="{html.escape(stats['name'])} GitHub profile stats">
  {font_face_block()}
  <defs>{defs}</defs>
  <rect width="{W}" height="{H}" rx="24" fill="{P['bg']}"/>
  <rect width="{W}" height="{H}" rx="24" fill="url(#dots)"/>
  <g clip-path="url(#cardClip)">
    <rect x="{card_x}" y="{card_y}" width="{card_w}" height="{card_h}" rx="24"
          fill="{P['surface']}"/>
  </g>
  <rect x="{card_x + 8}" y="{card_y + 8}" width="{card_w - 16}" height="{card_h - 16}"
        rx="18" fill="none" stroke="url(#frameFade)" stroke-width="1.5"/>
  {mark}
  {header}
  {tiles}
  {section_label}
  {chips}
  {footer}
</svg>"""


def main():
    try:
        if TOKEN:
            stats = fetch_stats()
            print(f"Fetched live stats for {USERNAME}", file=sys.stderr)
        else:
            stats = demo_stats()
            print("No GH_TOKEN set, using demo stats", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"Fetch failed ({e}); falling back to demo stats", file=sys.stderr)
        stats = demo_stats()

    os.makedirs("dist", exist_ok=True)
    path = "dist/profile-card.svg"
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(f"Wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()

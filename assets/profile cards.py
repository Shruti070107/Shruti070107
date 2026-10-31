#!/usr/bin/env python3
"""Regenerates assets/snake.svg, assets/stats.svg and assets/languages.svg
from live GitHub data. Standard library only. Run by the GitHub Action in
.github/workflows/update-profile-cards.yml, or locally with:

    GITHUB_USER=Shruti070107 python3 scripts/update_profile_cards.py
"""
import collections
import datetime
import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("GITHUB_USER", "Shruti070107")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MERGED_PRS = "150+"  # your own number; edit here when it grows
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

FONT = "'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"
LVL = ["#1E1B2E", "#4C1D95", "#6D28D9", "#A855F7", "#E879F9"]
LANG_COLORS = {
    "JavaScript": "#F0DB4F", "Python": "#60A5FA", "Java": "#F97316",
    "TypeScript": "#38BDF8", "HTML": "#F43F5E", "CSS": "#A78BFA",
    "Dart": "#22D3EE", "Rust": "#FB923C", "C++": "#F472B6", "C": "#94A3B8",
}


# ----------------------------------------------------------------- fetching
def http_get(url, api=False):
    headers = {"User-Agent": "profile-cards-script"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if TOKEN:
            headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_contributions():
    """Returns (total, {(col, row): (date, level)})."""
    html = http_get("https://github.com/users/%s/contributions" % USER)
    total = int(re.search(r"([\d,]+)\s+contributions\s+in the last year", html).group(1).replace(",", ""))
    cells = {}
    for tag in re.findall(r"<td\b[^>]*ContributionCalendar-day[^>]*>", html):
        date = re.search(r'data-date="([^"]+)"', tag)
        ident = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
        level = re.search(r'data-level="(\d)"', tag)
        if date and ident and level:
            cells[(int(ident.group(2)), int(ident.group(1)))] = (date.group(1), int(level.group(1)))
    if not cells:
        raise RuntimeError("could not read the contribution calendar")
    return total, cells


def fetch_repos():
    repos, page = [], 1
    while True:
        url = "https://api.github.com/users/%s/repos?per_page=100&type=owner&page=%d" % (USER, page)
        batch = json.loads(http_get(url, api=True))
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if page > 10:
            break
    return repos


# ---------------------------------------------------------------- rendering
def defs():
    return (
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#C084FC"/>'
        '<stop offset="1" stop-color="#F0ABFC"/></linearGradient>'
        '<linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7C3AED"/>'
        '<stop offset="1" stop-color="#C026D3"/></linearGradient>'
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
    )


def frame(w, h):
    return '<rect x="1" y="1" width="%d" height="%d" rx="18" fill="#0D1117" stroke="url(#b)" stroke-width="2"/>' % (w - 2, h - 2)


def streaks(cells):
    active = sorted(datetime.date.fromisoformat(d) for d, l in cells.values() if l > 0)
    best = run = 0
    prev = None
    for d in active:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    last = max(datetime.date.fromisoformat(d) for d, _ in cells.values())
    days = set(active)
    cur = 0
    d = last if last in days else last - datetime.timedelta(days=1)
    while d in days:
        cur += 1
        d -= datetime.timedelta(days=1)
    return best, cur


def stats_svg(total, best, cur, n_repos, stars):
    tiles = [
        (str(total), "contributions · last year"), (MERGED_PRS, "merged PRs"),
        (str(n_repos), "public repositories"), (str(stars), "stars on my own repos"),
        (str(best), "longest streak · days"), (str(cur), "current streak · days"),
    ]
    w, h = 540, 214
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="GitHub stats">' % (w, h, w, h),
         defs(), frame(w, h),
         '<text x="24" y="38" font-family="%s" font-size="18" font-weight="800" fill="url(#g)">GitHub stats</text>' % FONT,
         '<text x="%d" y="38" text-anchor="end" font-family="%s" font-size="11" fill="#6B7280">updated %s</text>'
         % (w - 24, MONO, datetime.date.today().strftime("%d %b %Y"))]
    for i, (num, lab) in enumerate(tiles):
        cx, cy = 24 + (i % 3) * 170, 62 + (i // 3) * 74
        o.append(
            '<rect x="%d" y="%d" width="158" height="64" rx="12" fill="#1A1030" stroke="#7C3AED" stroke-opacity="0.45">'
            '<animate attributeName="stroke-opacity" values="0.3;0.9;0.3" begin="%.1fs" dur="4s" repeatCount="indefinite"/></rect>'
            '<text x="%d" y="%d" font-family="%s" font-size="26" font-weight="800" fill="#FFFFFF">%s</text>'
            '<text x="%d" y="%d" font-family="%s" font-size="11" fill="#C4B5FD">%s</text>'
            % (cx, cy, 0.5 * i, cx + 14, cy + 34, FONT, num, cx + 14, cy + 52, FONT, lab))
    o.append("</svg>")
    return "\n".join(o)


def languages_svg(langs):
    w, h = 420, 214
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Languages across my own repositories">' % (w, h, w, h),
         defs(), frame(w, h),
         '<text x="24" y="38" font-family="%s" font-size="18" font-weight="800" fill="url(#g)">Languages</text>' % FONT,
         '<text x="%d" y="38" text-anchor="end" font-family="%s" font-size="11" fill="#6B7280">my own repos</text>' % (w - 24, MONO)]
    items = langs.most_common(5)
    total = sum(langs.values()) or 1
    top = items[0][1] if items else 1
    y = 62
    for i, (name, n) in enumerate(items):
        bw = max(6, int(190 * n / top))
        o.append(
            '<text x="24" y="%d" font-family="%s" font-size="13" font-weight="600" fill="#E5E7EB">%s</text>'
            '<rect x="120" y="%d" width="190" height="14" rx="7" fill="#1A1030"/>'
            '<rect x="120" y="%d" width="%d" height="14" rx="7" fill="%s">'
            '<animate attributeName="width" from="0" to="%d" begin="0s" dur="%.1fs"/></rect>'
            '<text x="324" y="%d" font-family="%s" font-size="12" fill="#C4B5FD">%d%%  ·  %d</text>'
            % (y + 14, FONT, name, y + 3, y + 3, bw, LANG_COLORS.get(name, "#A855F7"), bw, 1 + 0.2 * i,
               y + 14, MONO, round(100 * n / total), n))
        y += 28
    o.append("</svg>")
    return "\n".join(o)


def snake_svg(total, cells):
    P, X0, Y0 = 14, 26, 62
    cols = max(c for c, _ in cells) + 1
    sw, sh = X0 * 2 + cols * P - 3, Y0 + 7 * P + 26
    order = []
    for c in range(cols):
        for r in (range(7) if c % 2 == 0 else range(6, -1, -1)):
            order.append((c, r))
    n = len(order)
    dur = 22.0
    path = "M" + " L".join("%.1f %.1f" % (X0 + c * P + 5.5, Y0 + r * P + 5.5) for c, r in order)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Contribution snake">' % (sw, sh, sw, sh),
         defs(), frame(sw, sh),
         '<text x="26" y="36" font-family="%s" font-size="18" font-weight="800" fill="url(#g)">%d contributions in the last year</text>' % (FONT, total),
         '<text x="%d" y="36" text-anchor="end" font-family="%s" font-size="11" fill="#6B7280">updated %s</text>'
         % (sw - 26, MONO, datetime.date.today().strftime("%d %b %Y"))]
    for i, (c, r) in enumerate(order):
        if (c, r) not in cells:
            continue
        lvl = cells[(c, r)][1]
        x, y = X0 + c * P, Y0 + r * P
        if lvl == 0:
            o.append('<rect x="%d" y="%d" width="11" height="11" rx="3" fill="%s"/>' % (x, y, LVL[0]))
        else:
            t = 0.02 + 0.93 * i / (n - 1)
            o.append('<rect x="%d" y="%d" width="11" height="11" rx="3" fill="%s"><animate attributeName="fill" calcMode="discrete" '
                     'values="%s;%s;%s;%s" keyTimes="0;%.4f;0.985;1" dur="%ss" repeatCount="indefinite"/></rect>'
                     % (x, y, LVL[lvl], LVL[lvl], LVL[0], LVL[lvl], LVL[lvl], t, dur))
    body = ["#C084FC", "#A855F7", "#9333EA", "#7C3AED", "#6D28D9", "#5B21B6"]
    for k in range(6, -1, -1):
        delay = k * 0.55
        rad = 5.6 if k == 0 else max(3.2, 5.2 - k * 0.3)
        col = "#F0ABFC" if k == 0 else body[min(k - 1, 5)]
        o.append('<circle r="%s" fill="%s" opacity="%d" filter="url(#glow)">%s<animateMotion dur="%ss" begin="%.2fs" repeatCount="indefinite" path="%s"/></circle>'
                 % (rad, col, 1 if k == 0 else 0,
                    '<set attributeName="opacity" to="1" begin="%.2fs"/>' % delay if k else "", dur, delay, path))
    o.append("</svg>")
    return "\n".join(o)


# --------------------------------------------------------------------- main
def main():
    total, cells = fetch_contributions()
    repos = fetch_repos()
    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    langs = collections.Counter(r["language"] for r in own if r.get("language"))
    best, cur = streaks(cells)

    files = {
        "stats.svg": stats_svg(total, best, cur, len(repos), stars),
        "languages.svg": languages_svg(langs),
        "snake.svg": snake_svg(total, cells),
    }
    os.makedirs(OUT, exist_ok=True)
    for name, svg in files.items():  # only written once every fetch succeeded
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print("ok: %d contributions, %d repos, %d stars, streak %d/%d, languages %s"
          % (total, len(repos), stars, best, cur, dict(langs)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail loudly so the Action shows red
        print("error:", exc, file=sys.stderr)
        sys.exit(1)

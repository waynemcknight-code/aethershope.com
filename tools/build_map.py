"""Regenerate content/position/_index.md - a galactic map placing CMDR Aiether
and the fleet carrier on a rendered Milky Way.

Landmark coordinates verified against EDSM (2026-07-26), not recalled.

Projection: true top-down view of the galactic plane. In Elite Dangerous's
coordinate system X and Z span the plane and Y is height above it, so a
top-down map plots X horizontally and Z vertically - no distortion, one shared
scale. The map is centred on Sagittarius A*, which is the actual galactic
centre, so the disc renders concentric the way a real galaxy map does.

Galaxy geometry: the Milky Way is ~105,700 ly across, so ~52,850 ly radius
about the core. Sol sits ~25,900 ly out from the centre, which is why it
appears well off-centre - that is correct, not a bug.

Run from the repo root:  py tools\\build_map.py
"""

import glob
import json
import math
import os
import datetime

JOURNAL_DIR = os.path.join(os.environ['USERPROFILE'], 'Saved Games',
                           'Frontier Developments', 'Elite Dangerous')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'content', 'position', '_index.md')

LANDMARKS = [
    ('Sol',             0.0,        0.0,        0.0,         '#7fe0ff'),
    ('Colonia',        -9530.5,    -910.28125, 19808.125,    '#ffb000'),
    ('Sagittarius A*',  25.21875,  -20.90625,  25899.96875,  '#ff5555'),
    ('Beagle Point',   -1111.5625, -134.21875, 65269.75,     '#c08bff'),
]

CORE = (25.21875, 25899.96875)      # galactic centre, (x, z)
GALAXY_R = 52850.0                  # ly
ID64_ORIGIN = (-49985.0, -40985.0, -24105.0)

W = H = 1000.0
CX = CY = 500.0
SCALE = 468.0 / GALAXY_R            # px per ly


def decode_id64(id64):
    if not id64:
        return None
    m = id64 & 0x7
    v = id64 >> 3
    z = v & ((1 << (14 - m)) - 1); v >>= (14 - m)
    y = v & ((1 << (13 - m)) - 1); v >>= (13 - m)
    x = v & ((1 << (14 - m)) - 1)
    s = 10.0 * (2 ** m)
    return [ID64_ORIGIN[0] + x * s + s / 2,
            ID64_ORIGIN[1] + y * s + s / 2,
            ID64_ORIGIN[2] + z * s + s / 2]


def proj(x, z):
    """Galactic (x, z) -> SVG (px, py). +Z is drawn upward, toward the rim
    beyond the core, matching the in-game galaxy map's orientation."""
    return (CX + (x - CORE[0]) * SCALE, CY - (z - CORE[1]) * SCALE)


def spiral_arms(n_arms=4, turns=1.85, steps=170):
    """Logarithmic spiral arms, the standard model for a barred spiral."""
    paths = []
    b = 0.235
    theta_max = turns * 2 * math.pi
    r0 = GALAXY_R / math.exp(b * theta_max)
    for arm in range(n_arms):
        phase = arm * (2 * math.pi / n_arms)
        pts = []
        for i in range(steps + 1):
            t = theta_max * i / steps
            r = r0 * math.exp(b * t)
            a = t + phase
            gx = CORE[0] + r * math.cos(a)
            gz = CORE[1] + r * math.sin(a)
            px, py = proj(gx, gz)
            pts.append('%.1f %.1f' % (px, py))
        paths.append('M ' + ' L '.join(pts))
    return paths


def scan():
    ship = carrier = None
    for path in sorted(glob.glob(os.path.join(JOURNAL_DIR, 'Journal.*.log'))):
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                ev = e.get('event')
                if ev in ('FSDJump', 'Location', 'CarrierJump') and e.get('StarPos'):
                    ship = e
                elif ev == 'CarrierLocation':
                    carrier = e
    return ship, carrier


def main():
    ship, carrier = scan()
    if not ship:
        raise SystemExit('No ship position found in the journal.')
    sx, sy, sz = ship['StarPos']
    cpos = decode_id64(carrier.get('SystemAddress')) if carrier else None

    s = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
         'style="width:100%%;height:auto;display:block;background:#02020a;'
         'border:1px solid rgba(255,113,0,.3)" role="img" aria-label="Top-down '
         'map of the Milky Way showing current position relative to Sol, '
         'Colonia, Sagittarius A star and Beagle Point">' % (W, H)]

    s.append(
        '<defs>'
        '<radialGradient id="disc"><stop offset="0%" stop-color="#ffe9b8" stop-opacity=".55"/>'
        '<stop offset="12%" stop-color="#ffb45c" stop-opacity=".30"/>'
        '<stop offset="42%" stop-color="#6a7cc4" stop-opacity=".16"/>'
        '<stop offset="78%" stop-color="#31407a" stop-opacity=".08"/>'
        '<stop offset="100%" stop-color="#0a0e22" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="bulge"><stop offset="0%" stop-color="#fff7dd" stop-opacity=".95"/>'
        '<stop offset="45%" stop-color="#ffd98a" stop-opacity=".55"/>'
        '<stop offset="100%" stop-color="#ffb45c" stop-opacity="0"/></radialGradient>'
        '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%">'
        '<feGaussianBlur stdDeviation="11"/></filter>'
        '<filter id="glow" x="-70%" y="-70%" width="240%" height="240%">'
        '<feGaussianBlur stdDeviation="3" result="b"/><feMerge>'
        '<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '</defs>')

    # disc
    s.append('<circle cx="%.0f" cy="%.0f" r="%.0f" fill="url(#disc)"/>'
             % (CX, CY, GALAXY_R * SCALE))

    # spiral arms, drawn twice: wide soft haze then a brighter core line
    for d in spiral_arms():
        s.append('<path d="%s" fill="none" stroke="#8fa8ff" stroke-opacity=".16" '
                 'stroke-width="34" filter="url(#soft)" stroke-linecap="round"/>' % d)
    for d in spiral_arms():
        s.append('<path d="%s" fill="none" stroke="#cfe0ff" stroke-opacity=".22" '
                 'stroke-width="7" stroke-linecap="round"/>' % d)

    # central bulge / bar
    s.append('<ellipse cx="%.0f" cy="%.0f" rx="%.0f" ry="%.0f" fill="url(#bulge)" '
             'transform="rotate(-28 %.0f %.0f)"/>'
             % (CX, CY, 9000 * SCALE, 4200 * SCALE, CX, CY))

    # distance rings from the galactic centre
    for ly in (10000, 20000, 30000, 40000, 50000):
        s.append('<circle cx="%.0f" cy="%.0f" r="%.1f" fill="none" '
                 'stroke="rgba(255,113,0,.13)" stroke-dasharray="3 7"/>'
                 % (CX, CY, ly * SCALE))
        s.append('<text x="%.0f" y="%.1f" fill="rgba(255,176,0,.35)" font-size="9" '
                 'font-family="JetBrains Mono,monospace">%dk ly</text>'
                 % (CX + 3, CY - ly * SCALE - 3, ly // 1000))

    # route line, ship -> carrier
    if cpos:
        a, b = proj(sx, sz), proj(cpos[0], cpos[2])
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ff7100" '
                 'stroke-width="1.4" stroke-dasharray="5 4" opacity=".8"/>'
                 % (a[0], a[1], b[0], b[1]))

    points = list(LANDMARKS)
    points.append(('Your ship', sx, sy, sz, '#ff7100'))
    if cpos:
        points.append(("Aether's Hope", cpos[0], cpos[1], cpos[2], '#7CFF6B'))

    # At galactic scale the ship and carrier can be a few hundred ly apart,
    # which is single-digit pixels - markers and labels merge into a blob. So
    # nudge their labels apart on the main map and give the pair a zoomed
    # inset below.
    ship_px = proj(sx, sz)
    car_px = proj(cpos[0], cpos[2]) if cpos else None
    crowded = bool(car_px and math.dist(ship_px, car_px) < 26)

    for name, x, y, z, colour in points:
        px, py = proj(x, z)
        live = name in ('Your ship', "Aether's Hope")
        r = 6.0 if live else 4.5
        if name == 'Sagittarius A*':
            r = 5.5
        s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" filter="url(#glow)"/>'
                 % (px, py, r, colour))
        if live:
            s.append('<circle cx="%.1f" cy="%.1f" r="8" fill="none" stroke="%s" '
                     'stroke-width="1.2" opacity=".7">'
                     '<animate attributeName="r" values="7;20;7" dur="3s" '
                     'repeatCount="indefinite"/>'
                     '<animate attributeName="opacity" values=".7;0;.7" dur="3s" '
                     'repeatCount="indefinite"/></circle>' % (px, py, colour))

        ly_off = 0.0
        if crowded and live:
            ly_off = -16.0 if name == 'Your ship' else 18.0
        anchor = 'start' if px < W - 190 else 'end'
        dx = 11 if anchor == 'start' else -11
        if ly_off:
            s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                     'stroke-width=".8" opacity=".55"/>'
                     % (px, py, px + dx * 0.7, py + ly_off + (3 if ly_off > 0 else -3),
                        colour))
        s.append('<text x="%.1f" y="%.1f" fill="%s" font-size="13" '
                 'font-family="Orbitron,sans-serif" text-anchor="%s" '
                 'letter-spacing="1" style="paint-order:stroke;stroke:#02020a;'
                 'stroke-width:3px">%s</text>'
                 % (px + dx, py + 4 + ly_off, colour, anchor,
                    name.replace('&', '&amp;')))

    # ---- local detail inset ----
    if cpos:
        gap = math.sqrt(sum((a - b) ** 2 for a, b in
                            zip((sx, sy, sz), cpos)))
        ix, iy, iw = 706.0, 706.0, 268.0
        s.append('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="#04040c" '
                 'fill-opacity=".92" stroke="rgba(255,113,0,.45)"/>'
                 % (ix, iy, iw, iw))
        s.append('<text x="%.0f" y="%.0f" fill="#ffb000" font-size="10" '
                 'font-family="Orbitron,sans-serif" letter-spacing="2">LOCAL DETAIL</text>'
                 % (ix + 10, iy + 18))
        # zoom so the pair spans ~55% of the inset
        span = max(gap, 1.0)
        zs = (iw * 0.55) / span
        mid = ((sx + cpos[0]) / 2.0, (sz + cpos[2]) / 2.0)
        icx, icy = ix + iw / 2.0, iy + iw / 2.0 + 8

        def iproj(x, z):
            return (icx + (x - mid[0]) * zs, icy - (z - mid[1]) * zs)

        a, b = iproj(sx, sz), iproj(cpos[0], cpos[2])
        s.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ff7100" '
                 'stroke-width="1.2" stroke-dasharray="4 3" opacity=".85"/>'
                 % (a[0], a[1], b[0], b[1]))
        s.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#ff7100" filter="url(#glow)"/>'
                 % a)
        s.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#7CFF6B" filter="url(#glow)"/>'
                 % b)
        s.append('<text x="%.1f" y="%.1f" fill="#ff7100" font-size="11" '
                 'font-family="Orbitron,sans-serif" text-anchor="middle">YOU</text>'
                 % (a[0], a[1] - 11))
        s.append('<text x="%.1f" y="%.1f" fill="#7CFF6B" font-size="11" '
                 'font-family="Orbitron,sans-serif" text-anchor="middle">CARRIER</text>'
                 % (b[0], b[1] + 20))
        s.append('<text x="%.0f" y="%.0f" fill="#e6d5c4" font-size="14" '
                 'font-family="JetBrains Mono,monospace" text-anchor="middle">'
                 '{:,.0f} ly apart</text>'.format(gap) % (ix + iw / 2, iy + iw - 14))

    s.append('<text x="14" y="%.0f" fill="rgba(230,213,196,.4)" font-size="10" '
             'font-family="JetBrains Mono,monospace">top-down galactic plane '
             '(X / Z) &#183; centred on Sgr A* &#183; rings measured from the '
             'core</text>' % (H - 14))
    s.append('</svg>')

    def dist(a, b):
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    rows = []
    for name, x, y, z, _c in LANDMARKS:
        d = dist((sx, sy, sz), (x, y, z))
        rows.append('| **%s** | {:,.0f} ly |'.format(d) % name)

    lines = [
        '---',
        'title: "Position"',
        'description: "Where CMDR Aiether is in the galaxy right now."',
        'date: %s' % datetime.date.today().isoformat(),
        '---',
        '',
        '\n'.join(s),
        '',
        '## Current position',
        '',
        '**%s** &mdash; `[%.1f, %.1f, %.1f]`' % (ship.get('StarSystem', '?'), sx, sy, sz),
        '',
        '## Distance from landmarks',
        '',
        '| Landmark | Distance |',
        '|---|---|',
    ] + rows + ['']

    if cpos and carrier:
        d = dist((sx, sy, sz), cpos)
        lines += [
            '## Fleet carrier',
            '',
            "**Aether's Hope** was last confirmed in **%s**, **{:,.0f} ly** away."
            .format(d) % carrier.get('StarSystem', '?'),
            '',
            'Carrier position only updates when the game reports it &mdash; on '
            'load, when docking there, or when a jump completes while aboard '
            '&mdash; so it can lag reality while flying elsewhere.',
            '',
        ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))
    print('wrote %s' % OUT)
    for name, x, y, z, _c in LANDMARKS:
        print('  %-16s %10.0f ly' % (name, dist((sx, sy, sz), (x, y, z))))


if __name__ == '__main__':
    main()

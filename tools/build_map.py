"""Regenerate content/position/_index.md - a galaxy map placing CMDR Aiether
and the fleet carrier against the four reference landmarks.

Landmark coordinates verified against EDSM (2026-07-26), not recalled.

Projection note: the galaxy is a disc, so the natural view is top-down on the
X/Z plane. But these landmarks span Z 0 -> 65,270 ly while only spanning X
-9,530 -> +1,106 - a ~4:1 tall, thin strip that renders badly. The map is
therefore drawn with Z horizontal and X vertical, which is the same top-down
projection simply rotated 90 degrees. Both axes share one scale, so distances
stay visually honest.

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
    ('Sol',              0.0,        0.0,       0.0,      '#00b3f7'),
    ('Colonia',         -9530.5,    -910.28125, 19808.125, '#ffb000'),
    ('Sagittarius A*',   25.21875,  -20.90625,  25899.96875, '#ff3b3b'),
    ('Beagle Point',    -1111.5625, -134.21875, 65269.75,  '#b06bff'),
]

ID64_ORIGIN = (-49985.0, -40985.0, -24105.0)


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

    points = [(n, x, y, z, c) for n, x, y, z, c in LANDMARKS]
    sx, sy, sz = ship['StarPos']
    points.append(('Your ship', sx, sy, sz, '#ff7100'))

    cpos = decode_id64(carrier.get('SystemAddress')) if carrier else None
    if cpos:
        points.append(("Aether's Hope", cpos[0], cpos[1], cpos[2], '#7CFF6B'))

    # --- projection: horizontal = Z, vertical = X, shared scale ---
    W, H, PAD = 1000.0, 300.0, 46.0
    zs = [p[3] for p in points]
    xs = [p[1] for p in points]
    z0, z1 = min(zs), max(zs)
    x0, x1 = min(xs), max(xs)
    zspan = max(z1 - z0, 1.0)
    xspan = max(x1 - x0, 1.0)
    scale = min((W - 2 * PAD) / zspan, (H - 2 * PAD) / xspan)
    zc, xc = (z0 + z1) / 2.0, (x0 + x1) / 2.0

    def proj(x, z):
        return (W / 2.0 + (z - zc) * scale, H / 2.0 - (x - xc) * scale)

    svg = [
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
        'style="width:100%%;height:auto;background:#050508;border:1px solid '
        'rgba(255,113,0,.3);border-radius:2px" role="img" '
        'aria-label="Galaxy map of current position relative to Sol, Colonia, '
        'Sagittarius A* and Beagle Point">' % (W, H),
        '<defs><filter id="g" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="3.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
        '</feMerge></filter></defs>',
    ]

    # galactic plane guide line through the landmark spine
    y_axis = proj(0, 0)[1]
    svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
               'stroke="rgba(255,113,0,.18)" stroke-dasharray="6 6"/>'
               % (PAD * 0.5, y_axis, W - PAD * 0.5, y_axis))

    # route line ship -> carrier
    if cpos:
        a, b = proj(sx, sz), proj(cpos[0], cpos[2])
        svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                   'stroke="#ff7100" stroke-width="1.2" stroke-dasharray="4 4" '
                   'opacity=".75"/>' % (a[0], a[1], b[0], b[1]))

    for name, x, y, z, colour in points:
        px, py = proj(x, z)
        big = name in ('Your ship', "Aether's Hope")
        r = 6.5 if big else 5.0
        svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" '
                   'filter="url(#g)"/>' % (px, py, r, colour))
        if big:
            svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" '
                       'stroke="%s" stroke-width="1" opacity=".55">'
                       '<animate attributeName="r" values="%.1f;%.1f;%.1f" '
                       'dur="2.6s" repeatCount="indefinite"/>'
                       '<animate attributeName="opacity" values=".55;0;.55" '
                       'dur="2.6s" repeatCount="indefinite"/></circle>'
                       % (px, py, r + 4, colour, r + 2, r + 12, r + 2))
        anchor = 'start' if px < W - 170 else 'end'
        dx = 11 if anchor == 'start' else -11
        svg.append('<text x="%.1f" y="%.1f" fill="%s" font-size="13" '
                   'font-family="Orbitron,sans-serif" text-anchor="%s" '
                   'letter-spacing="1">%s</text>'
                   % (px + dx, py + 4, colour, anchor,
                      name.replace('&', '&amp;')))

    svg.append('<text x="%.1f" y="%.1f" fill="rgba(230,213,196,.5)" '
               'font-size="11" font-family="JetBrains Mono,monospace">'
               'horizontal: galactic Z (ly)   vertical: galactic X (ly)   '
               'shared scale</text>' % (PAD * 0.5, H - 12))
    svg.append('</svg>')

    # --- distance table ---
    def dist(ax, ay, az, bx, by, bz):
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)

    rows = []
    for name, x, y, z, _c in LANDMARKS:
        d = dist(sx, sy, sz, x, y, z)
        rows.append('| **%s** | {:,.0f} ly |'.format(d) % name)

    lines = [
        '---',
        'title: "Position"',
        'description: "Where CMDR Aiether is in the galaxy right now."',
        'date: %s' % datetime.date.today().isoformat(),
        '---',
        '',
        '\n'.join(svg),
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
        d = dist(sx, sy, sz, cpos[0], cpos[1], cpos[2])
        lines += [
            '## Fleet carrier',
            '',
            '**Aether\'s Hope** was last confirmed in **%s** (%s), '
            '**{:,.0f} ly** away.'.format(d)
            % (carrier.get('StarSystem', '?'), carrier.get('timestamp', '?')),
            '',
            'Carrier position only updates when the game reports it - on load, '
            'when docking there, or when a jump completes while aboard - so it '
            'can lag reality while flying elsewhere.',
            '',
        ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))
    print('wrote %s' % OUT)
    for name, x, y, z, _c in LANDMARKS:
        print('  %-16s %10.0f ly' % (name, dist(sx, sy, sz, x, y, z)))


if __name__ == '__main__':
    main()

"""Regenerate content/fleet/_index.md from the Elite Dangerous journal.

Reads the newest StoredShips event (the game's own record of ships in storage)
plus every Loadout event seen, and writes a fleet roster page.

Run from the repo root:  py tools\\build_roster.py

Caveat baked into the output: StoredShips is a point-in-time snapshot taken
when you last opened a shipyard, and it never lists the ship you were flying
at that moment. The generator recovers that ship from Loadout events so the
roster isn't silently short by one.
"""

import glob
import json
import os
import datetime

JOURNAL_DIR = os.path.join(os.environ['USERPROFILE'], 'Saved Games',
                           'Frontier Developments', 'Elite Dangerous')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'content', 'fleet', '_index.md')

# Internal ship ids -> display names. Extend as new ships are bought.
SHIP_NAMES = {
    'federation_corvette': 'Federal Corvette',
    'federation_gunship': 'Federal Gunship',
    'federation_dropship': 'Federal Dropship',
    'federation_dropship_mkii': 'Federal Assault Ship',
    'panthermkii': 'Panther Clipper Mk II',
    'corsair': 'Corsair',
    'mandalay': 'Mandalay',
    'explorer_nx': 'Caspian Explorer',
    'lakonminer': 'Type-11 Prospector',
    'cobramkv': 'Cobra Mk V',
    'cobramkiii': 'Cobra Mk III',
    'cobramkiv': 'Cobra Mk IV',
    'asp': 'Asp Explorer',
    'asp_scout': 'Asp Scout',
    'empire_trader': 'Imperial Clipper',
    'cutter': 'Imperial Cutter',
    'krait_mkii': 'Krait Mk II',
    'krait_light': 'Krait Phantom',
    'python': 'Python',
    'python_nx': 'Python Mk II',
    'type9': 'Type-9 Heavy',
    'type9_military': 'Type-10 Defender',
    'anaconda': 'Anaconda',
    'diamondbackxl': 'Diamondback Explorer',
    'sidewinder': 'Sidewinder',
}


def display(internal, localised=None):
    if localised and not localised.islower():
        return localised
    key = (internal or '').lower()
    return SHIP_NAMES.get(key, (internal or 'Unknown').replace('_', ' ').title())


def scan():
    stored, loadouts, carrier = None, {}, {}
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
                if ev == 'StoredShips':
                    stored = e
                elif ev == 'Loadout':
                    loadouts[e.get('ShipID')] = e
                elif ev == 'CarrierStats':
                    carrier = e
    return stored, loadouts, carrier


def main():
    stored, loadouts, carrier = scan()
    if not stored:
        raise SystemExit('No StoredShips event found - visit a shipyard first.')

    rows = []
    seen = set()
    for s in (stored.get('ShipsHere') or []):
        sid = s.get('ShipID')
        seen.add(sid)
        lo = loadouts.get(sid, {})
        rows.append({
            'type': display(s.get('ShipType'), s.get('ShipType_Localised')),
            'name': s.get('Name') or '',
            'id': sid,
            'value': s.get('Value') or (lo.get('HullValue') or 0),
            'range': lo.get('MaxJumpRange'),
            'where': 'Aboard %s' % (stored.get('StationName') or 'carrier'),
        })
    for s in (stored.get('ShipsRemote') or []):
        sid = s.get('ShipID')
        seen.add(sid)
        lo = loadouts.get(sid, {})
        rows.append({
            'type': display(s.get('ShipType'), s.get('ShipType_Localised')),
            'name': s.get('Name') or '',
            'id': sid,
            'value': s.get('Value') or 0,
            'range': lo.get('MaxJumpRange'),
            'where': s.get('StarSystem') or 'Remote',
        })

    # Ships known only from Loadout - i.e. whatever was being flown when the
    # StoredShips snapshot was taken, which the snapshot itself omits.
    for sid, lo in loadouts.items():
        if sid in seen:
            continue
        rows.append({
            'type': display(lo.get('Ship')),
            'name': lo.get('ShipName') or '',
            'id': sid,
            'value': lo.get('HullValue') or 0,
            'range': lo.get('MaxJumpRange'),
            'where': 'In service',
        })

    rows.sort(key=lambda r: -(r['range'] or 0))

    ts = stored.get('timestamp', '')
    lines = [
        '---',
        'title: "The Fleet"',
        'description: "Ships registered to CMDR Aiether."',
        'date: %s' % datetime.date.today().isoformat(),
        '---',
        '',
        '{{< alert >}}',
        'Generated from the game journal by `tools/build_roster.py`. '
        'Ship storage reflects the last shipyard snapshot (%s).' % ts,
        '{{< /alert >}}',
        '',
        '## Registered hulls',
        '',
        '| Ship | Name | Jump range | Value | Location |',
        '|---|---|---|---|---|',
    ]
    for r in rows:
        rng = '%.2f ly' % r['range'] if r['range'] else '--'
        val = '{:,} CR'.format(r['value']) if r['value'] else '--'
        lines.append('| **%s** | %s | %s | %s | %s |'
                     % (r['type'], r['name'] or '*unnamed*', rng, val, r['where']))

    total = sum(r['value'] or 0 for r in rows)
    lines += [
        '',
        '**%d hulls**, combined recorded value **{:,} CR**.'.format(total) % len(rows),
        '',
    ]
    if carrier:
        lines += [
            '## Fleet Carrier',
            '',
            '**%s** - callsign `%s`' % (carrier.get('Name', ''),
                                       carrier.get('Callsign', '')),
            '',
            '| | |', '|---|---|',
            '| Tritium | %s t |' % carrier.get('FuelLevel', '?'),
            '| Jump range | ~500 ly |',
            '| Balance | {:,} CR |'.format(
                (carrier.get('Finance') or {}).get('CarrierBalance', 0)),
            '',
        ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))
    print('wrote %s (%d hulls)' % (OUT, len(rows)))


if __name__ == '__main__':
    main()

"""Regenerate content/loadouts/_index.md - per-ship module buildouts.

Reads every Loadout event and renders the most recent one per ship, grouped
into hardpoints / core internals / optional internals / utility, with
engineering blueprints and their modifiers.

Only ships actually flown since journaling began emit a Loadout, so hulls that
have sat in storage the whole time legitimately have no buildout to show. The
page says so rather than omitting them silently.

Run from the repo root:  py tools\\build_loadouts.py
"""

import glob
import json
import os
import datetime

JOURNAL_DIR = os.path.join(os.environ['USERPROFILE'], 'Saved Games',
                           'Frontier Developments', 'Elite Dangerous')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'content', 'loadouts', '_index.md')

SHIP_NAMES = {
    'federation_corvette': 'Federal Corvette',
    'panthermkii': 'Panther Clipper Mk II',
    'mandalay': 'Mandalay',
    'explorer_nx': 'Caspian Explorer',
    'lakonminer': 'Type-11 Prospector',
    'corsair': 'Corsair',
    'cobramkv': 'Cobra Mk V',
    'asp': 'Asp Explorer',
}

# Cosmetic-only items - excluded from buildout tables.
COSMETIC = ('paintjob', 'decal', 'bobble', 'shipkit', 'nameplate', 'voicepack',
            'enginecustomisation', 'weaponcustomisation', 'string_lights',
            'shipname', 'vehicle')

RATING = {1: 'E', 2: 'D', 3: 'C', 4: 'B', 5: 'A'}

# Base module tokens -> readable names. Anything unmatched falls back to a
# title-cased version of the raw token, which stays readable rather than wrong.
BASE = {
    'powerplant': 'Power Plant', 'engine': 'Thrusters',
    'hyperdrive': 'Frame Shift Drive', 'lifesupport': 'Life Support',
    'powerdistributor': 'Power Distributor', 'sensors': 'Sensors',
    'fueltank': 'Fuel Tank', 'cargorack': 'Cargo Rack',
    'shieldgenerator': 'Shield Generator', 'shieldcellbank': 'Shield Cell Bank',
    'fuelscoop': 'Fuel Scoop', 'refinery': 'Refinery',
    'dronecontrol_collection': 'Collector Limpet Controller',
    'dronecontrol_prospector': 'Prospector Limpet Controller',
    'dronecontrol_repair': 'Repair Limpet Controller',
    'dronecontrol_fueltransfer': 'Fuel Transfer Limpet Controller',
    'detailedsurfacescanner': 'Detailed Surface Scanner',
    'guardianfsdbooster': 'Guardian FSD Booster',
    'guardianpowerplant': 'Guardian Hybrid Power Plant',
    'guardianpowerdistributor': 'Guardian Hybrid Power Distributor',
    'buggybay': 'Planetary Vehicle Hangar',
    'repairer': 'AFM Unit', 'modulereinforcement': 'Module Reinforcement',
    'hullreinforcement': 'Hull Reinforcement', 'metaalloyhullreinforcement':
    'Meta Alloy Hull Reinforcement', 'shieldbooster': 'Shield Booster',
    'heatsinklauncher': 'Heat Sink Launcher', 'chafflauncher': 'Chaff Launcher',
    'plasmapointdefence': 'Point Defence', 'cloudscanner': 'Frame Shift Wake Scanner',
    'cargoscanner': 'Cargo Scanner', 'crimescanner': 'Kill Warrant Scanner',
    'electroniccountermeasure': 'Electronic Countermeasure',
    'mining_abrblstr': 'Abrasion Blaster', 'mining_seismchrgwarhd': 'Seismic Charge Launcher',
    'mining_subsurfdispmisle': 'Sub-surface Displacement Missile',
    'mininglaser': 'Mining Laser', 'pulselaser': 'Pulse Laser',
    'beamlaser': 'Beam Laser', 'multicannon': 'Multi-cannon',
    'plasmaaccelerator': 'Plasma Accelerator', 'railgun': 'Rail Gun',
    'cannon': 'Cannon', 'slugshot': 'Fragment Cannon',
    'dumbfiremissilerack': 'Missile Rack', 'basicmissilerack': 'Seeker Missile Rack',
    'minelauncher': 'Mine Launcher', 'atdumbfiremissile': 'AX Missile Rack',
    'atmulticannon': 'AX Multi-cannon',
    'xenoscanner': 'Xeno Scanner', 'planetapproachsuite': 'Planetary Approach Suite',
    'dockingcomputer_advanced': 'Advanced Docking Computer',
    'dockingcomputer_standard': 'Standard Docking Computer',
    'supercruiseassist': 'Supercruise Assist',
    'multidronecontrol_universal': 'Universal Limpet Controller',
    'multidronecontrol_mining': 'Mining Multi Limpet Controller',
    'multidronecontrol_operations': 'Operations Multi Limpet Controller',
    'multidronecontrol_rescue': 'Rescue Multi Limpet Controller',
    'corrosionproofcargorack': 'Corrosion Resistant Cargo Rack',
    'fsdinterdictor': 'FSD Interdictor',
}

MOUNT = {'fixed': 'Fixed', 'gimbal': 'Gimballed', 'turret': 'Turret'}
CLASS_SZ = {'tiny': 'Tiny', 'small': 'Small', 'medium': 'Medium',
            'large': 'Large', 'huge': 'Huge'}


def pretty_module(item):
    """Turn an internal module id into something a human can read."""
    s = item.lower().lstrip('$').replace('_name;', '')
    for pre in ('hpt_', 'int_'):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    parts = s.split('_')
    size = rating = mount = clssz = None
    keep = []
    for p in parts:
        if p.startswith('size') and p[4:].isdigit():
            size = int(p[4:])
        elif p.startswith('class') and p[5:].isdigit():
            rating = int(p[5:])
        elif p in MOUNT:
            mount = MOUNT[p]
        elif p in CLASS_SZ:
            clssz = CLASS_SZ[p]
        else:
            keep.append(p)
    base_key = '_'.join(keep)
    name = BASE.get(base_key)
    if not name:
        # try progressively shorter prefixes before giving up
        for n in range(len(keep), 0, -1):
            cand = '_'.join(keep[:n])
            if cand in BASE:
                name = BASE[cand] + ' ' + ' '.join(keep[n:]).title()
                break
    if not name:
        name = base_key.replace('_', ' ').title()

    bits = []
    if size and rating:
        bits.append('%d%s' % (size, RATING.get(rating, rating)))
    elif clssz:
        bits.append(clssz)
    if mount:
        bits.append(mount)
    return ('%s [%s]' % (name.strip(), ', '.join(bits))) if bits else name.strip()


def group_of(slot):
    s = slot.lower()
    if 'hardpoint' in s and not s.startswith('tiny'):
        return 'Hardpoints'
    if s.startswith('tinyhardpoint'):
        return 'Utility mounts'
    if s in ('powerplant', 'mainengines', 'frameshiftdrive', 'lifesupport',
             'powerdistributor', 'radar', 'fueltank', 'armour'):
        return 'Core internals'
    if s.startswith('slot') or 'militarysize' in s:
        return 'Optional internals'
    return None  # cosmetic / structural, skipped


ORDER = ['Core internals', 'Hardpoints', 'Utility mounts', 'Optional internals']


def main():
    loadouts = {}
    for path in sorted(glob.glob(os.path.join(JOURNAL_DIR, 'Journal.*.log'))):
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if '"Loadout"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get('event') == 'Loadout':
                    loadouts[e.get('ShipID')] = e

    lines = [
        '---',
        'title: "Buildouts"',
        'description: "Module loadouts for every ship in the fleet."',
        'date: %s' % datetime.date.today().isoformat(),
        '---',
        '',
        '*A buildout is only recorded once a ship has been flown, so hulls that '
        'have sat in storage appear on [the fleet roster](/fleet/) but not '
        'here.*',
        '',
    ]

    for sid, e in sorted(loadouts.items(),
                         key=lambda kv: -(kv[1].get('MaxJumpRange') or 0)):
        ship = SHIP_NAMES.get((e.get('Ship') or '').lower(),
                              (e.get('Ship') or '?').replace('_', ' ').title())
        name = e.get('ShipName') or ''
        ident = e.get('ShipIdent') or ''
        title = ship + (' &mdash; *%s*' % name if name else '')
        lines += ['## %s' % title, '']
        meta = []
        if ident:
            meta.append('ID `%s`' % ident)
        if e.get('MaxJumpRange'):
            meta.append('max jump **%.2f ly**' % e['MaxJumpRange'])
        if e.get('UnladenMass'):
            meta.append('unladen **%.1f t**' % e['UnladenMass'])
        if e.get('CargoCapacity') is not None:
            meta.append('cargo **%d t**' % e['CargoCapacity'])
        total = (e.get('HullValue') or 0) + (e.get('ModulesValue') or 0)
        if total:
            meta.append('value **{:,} CR**'.format(total))
        if e.get('Rebuy'):
            meta.append('rebuy **{:,} CR**'.format(e['Rebuy']))
        lines += [' &middot; '.join(meta), '']

        buckets = {g: [] for g in ORDER}
        for m in (e.get('Modules') or []):
            item = (m.get('Item') or '').lower()
            if any(c in item for c in COSMETIC):
                continue
            g = group_of(m.get('Slot') or '')
            if not g:
                continue
            eng = m.get('Engineering')
            note = ''
            if eng:
                note = '%s G%s' % (eng.get('BlueprintName', '').replace('_', ' '),
                                   eng.get('Level'))
                if eng.get('ExperimentalEffect_Localised'):
                    note += ' + *%s*' % eng['ExperimentalEffect_Localised']
            buckets[g].append((m.get('Slot'), pretty_module(m.get('Item') or ''),
                               'on' if m.get('On') else 'off',
                               m.get('Priority'), note))

        for g in ORDER:
            rows = buckets[g]
            if not rows:
                continue
            lines += ['### %s' % g, '',
                      '| Slot | Module | Pwr | Engineering |',
                      '|---|---|---|---|']
            for slot, mod, on, pri, note in rows:
                lines.append('| `%s` | %s | %s%s | %s |'
                             % (slot, mod, on,
                                '' if pri is None else '/%s' % pri,
                                note or '&mdash;'))
            lines.append('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))
    print('wrote %s (%d ships)' % (OUT, len(loadouts)))


if __name__ == '__main__':
    main()

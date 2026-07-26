"""Regenerate content/ranks/_index.md from the Elite Dangerous journal.

Reads the most recent Rank, Progress and Reputation events. Rank gives the
tier index, Progress gives percent toward the next tier, Reputation gives
standing with the three superpowers.

Run from the repo root:  py tools\\build_ranks.py
"""

import glob
import json
import os
import datetime

JOURNAL_DIR = os.path.join(os.environ['USERPROFILE'], 'Saved Games',
                           'Frontier Developments', 'Elite Dangerous')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'content', 'ranks', '_index.md')

# Standard ED rank ladders. Index == the integer the journal reports.
# The combat-style ladders continue past Elite (8) into Elite I-V (9-13).
ELITE_TAIL = ['Elite', 'Elite I', 'Elite II', 'Elite III', 'Elite IV', 'Elite V']

LADDERS = {
    'Combat': ['Harmless', 'Mostly Harmless', 'Novice', 'Competent', 'Expert',
               'Master', 'Dangerous', 'Deadly'] + ELITE_TAIL,
    'Trade': ['Penniless', 'Mostly Penniless', 'Peddler', 'Dealer', 'Merchant',
              'Broker', 'Entrepreneur', 'Tycoon'] + ELITE_TAIL,
    'Explore': ['Aimless', 'Mostly Aimless', 'Scout', 'Surveyor', 'Trailblazer',
                'Pathfinder', 'Ranger', 'Pioneer'] + ELITE_TAIL,
    'Exobiologist': ['Directionless', 'Mostly Directionless', 'Compiler',
                     'Collector', 'Cataloguer', 'Taxonomist', 'Ecologist',
                     'Geneticist'] + ELITE_TAIL,
    'Soldier': ['Defenceless', 'Mostly Defenceless', 'Rookie', 'Soldier',
                'Gunslinger', 'Warrior', 'Gladiator', 'Deadeye'] + ELITE_TAIL,
    'CQC': ['Helpless', 'Mostly Helpless', 'Amateur', 'Semi Professional',
            'Professional', 'Champion', 'Hero', 'Legend', 'Elite'],
    'Federation': ['Recruit', 'Cadet', 'Midshipman', 'Petty Officer',
                   'Chief Petty Officer', 'Warrant Officer', 'Ensign',
                   'Lieutenant', 'Lieutenant Commander', 'Post Commander',
                   'Post Captain', 'Rear Admiral', 'Vice Admiral', 'Admiral'],
    'Empire': ['Outsider', 'Serf', 'Master', 'Squire', 'Knight', 'Lord',
               'Baron', 'Viscount', 'Count', 'Earl', 'Marquis', 'Duke',
               'Prince', 'King'],
}

LABEL = {'Soldier': 'Mercenary', 'Explore': 'Exploration',
         'Exobiologist': 'Exobiology'}

PILOT = ['Combat', 'Trade', 'Explore', 'Exobiologist', 'Soldier', 'CQC']
NAVY = ['Federation', 'Empire']


def latest():
    rank = progress = rep = cmdr = None
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
                if ev == 'Rank':
                    rank = e
                elif ev == 'Progress':
                    progress = e
                elif ev == 'Reputation':
                    rep = e
                elif ev in ('Commander', 'LoadGame') and e.get('Name' if ev == 'Commander' else 'Commander'):
                    cmdr = e.get('Name') if ev == 'Commander' else e.get('Commander')
    return rank, progress, rep, cmdr


def bar(pct, width=20):
    filled = int(round((pct or 0) / 100.0 * width))
    return '`[' + '#' * filled + '.' * (width - filled) + ']`'


def rows(keys, rank, progress):
    out = []
    for k in keys:
        idx = (rank or {}).get(k)
        if idx is None:
            continue
        ladder = LADDERS[k]
        name = ladder[idx] if idx < len(ladder) else 'Rank %d' % idx
        pct = (progress or {}).get(k, 0)
        maxed = idx >= len(ladder) - 1
        out.append('| **%s** | %s | %d | %s | %s |'
                   % (LABEL.get(k, k), name, idx,
                      bar(pct), 'MAX' if maxed else '%d%%' % pct))
    return out


def main():
    rank, progress, rep, cmdr = latest()
    if not rank:
        raise SystemExit('No Rank event found in the journal.')

    lines = [
        '---',
        'title: "Ranks & Standing"',
        'description: "Pilots Federation and superpower ranks for CMDR %s."' % (cmdr or 'Aiether'),
        'date: %s' % datetime.date.today().isoformat(),
        '---',
        '',
        '## Pilots Federation',
        '',
        '| Branch | Rank | Tier | Progress | |',
        '|---|---|---|---|---|',
    ] + rows(PILOT, rank, progress) + [
        '',
        '## Naval ranks',
        '',
        '| Superpower | Rank | Tier | Progress | |',
        '|---|---|---|---|---|',
    ] + rows(NAVY, rank, progress)

    if rep:
        lines += ['', '## Reputation', '',
                  '| Superpower | Standing |', '|---|---|']
        for k in ('Federation', 'Empire', 'Alliance', 'Independent'):
            v = rep.get(k)
            if v is None:
                continue
            lines.append('| **%s** | %.1f%% |' % (k, v))
        lines.append('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines))
    print('wrote %s' % OUT)


if __name__ == '__main__':
    main()

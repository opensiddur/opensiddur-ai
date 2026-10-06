"""Check Asher pilot PDF content, bilingual stanza geometry, and broken controls."""
import argparse
import copy
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from lxml import etree
from opensiddur.importer.scan.pdf_direction import base

HEBREW = ['במוצאי', 'אתימין', 'דרוש', 'זוחלים', 'יוצר', 'מרוםאם', 'פנה', 'רצה']
ENGLISH = ['On the outgoing', 'O raise', 'O seek', 'They tremble',
           'Thou, who hast formed', 'If the misdeeds', 'Turn, we beseech', 'Be pleased']
# Measured from this pilot's 12pt font and 14.5pt leading. The first stanza
# begins one line higher in Hebrew after the unequal-length bilingual rubrics.
MAX_BASELINE_DIFFERENCE = 16


def plain(text):
    text = text.replace('\ue049', 'Th').replace('\ue04a', 'Th')
    return unicodedata.normalize('NFKC', text)


def check(tree, expanded):
    english = []
    hebrew = []
    for page_no, page in enumerate(tree.findall('page'), 1):
        gutter = 288 if page_no % 2 else 324
        for line in page.findall('.//line'):
            chars = list(line.findall('.//char'))
            en = [c for c in chars if float(c.get('x')) > gutter]
            he = [c for c in chars if base(c.get('c', ' ')) and float(c.get('x')) < gutter]
            if en:
                english.append((page_no, float(en[0].get('y')), plain(''.join(c.get('c') for c in en)), en))
            if he:
                hebrew.append((page_no, float(he[0].get('y')), ''.join(base(c.get('c')) for c in sorted(he, key=lambda c: float(c.get('x')), reverse=True))))
    rows = []
    for he_anchor, en_anchor in zip(HEBREW, ENGLISH):
        h = next((r for r in hebrew if he_anchor in r[2]), None)
        e = next((r for r in english if en_anchor in r[2]), None)
        if h is None or e is None:
            raise ValueError(f'Missing stanza anchor: {he_anchor} / {en_anchor}')
        latin_x = [float(c.get('x')) for c in e[3] if c.get('c').isascii() and c.get('c').isalpha()]
        if latin_x != sorted(latin_x):
            raise ValueError(f'Latin direction failed: {en_anchor}')
        delta = abs(h[1] - e[1])
        if h[0] != e[0] or delta > MAX_BASELINE_DIFFERENCE:
            raise ValueError(f'Stanza alignment failed: {he_anchor}: {h[:2]} / {e[:2]}')
        rows.append(round(delta, 2))
    text = plain(' '.join(line.get('text', '') for line in tree.findall('.//line')))
    if text.count('Appease thy anger and pardon our sins.') != 1:
        raise ValueError('Footnote must occur exactly once')
    if ('Omnipotent King, who' in text) != expanded:
        raise ValueError('El Melekh expansion boundary failed')
    if ('And the Eternal passed by before him' in text) != expanded:
        raise ValueError('Vayaavor expansion boundary failed')
    if 'The hope of Israel' in text:
        raise ValueError('Adjacent prayer outside reference boundary')
    if ('(Hearken,' in text) == expanded:
        raise ValueError('Wrong abbreviation branch')
    return rows


def controls(tree, expanded):
    broken = copy.deepcopy(tree)
    note = next(l for l in broken.findall('.//line') if 'Appease thy anger' in l.get('text', ''))
    note.getparent().append(copy.deepcopy(note))
    try:
        check(broken, expanded)
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate footnote control escaped detection')
    broken = copy.deepcopy(tree)
    for line in broken.findall('.//line'):
        if 'O seek' in plain(line.get('text', '')):
            for char in line.findall('.//char'):
                if float(char.get('x')) > 288:
                    char.set('y', str(float(char.get('y')) + 50))
    try:
        check(broken, expanded)
    except ValueError:
        pass
    else:
        raise AssertionError('Shifted stanza control escaped detection')
    try:
        check(tree, not expanded)
    except ValueError:
        pass
    else:
        raise AssertionError('Wrong expansion control escaped detection')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf', type=Path)
    p.add_argument('--expanded', action='store_true')
    p.add_argument('--control', action='store_true')
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'text.xml'
        subprocess.run(['mutool', 'draw', '-F', 'stext', '-o', str(path), str(args.pdf)], check=True, capture_output=True)
        tree = etree.parse(str(path)).getroot()
        rows = check(tree, args.expanded)
        if args.control:
            controls(tree, args.expanded)
        print(f'8 stanza pairs aligned (baseline deltas {rows}); footnote once; abbreviation and prayer boundaries correct; controls={args.control}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

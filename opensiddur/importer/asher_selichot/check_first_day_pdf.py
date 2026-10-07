"""Check the partial first-day PDF, including the Latin citation direction."""
import argparse
import copy
import subprocess
import tempfile
from pathlib import Path
from lxml import etree
from .check_pdf import plain
from opensiddur.importer.scan.pdf_direction import base

# Measured from first-day.yaml's SBL Hebrew 12pt bilingual output.
MAX_BASELINE_DIFFERENCE = 16
ANCHORS = [('אשרייושביביתך', 'Happy are they who dwell'),
           ('תהלתיי', 'My mouth shall utter'),
           ('יתגדלויתקדש', 'May his great name be exalted'),
           ('יהאשמהרבא', 'May his great name be blessed')]


def check(tree):
    he_rows, en_rows, citation = [], [], []
    for page_no, page in enumerate(tree.findall('page'), 1):
        gutter = 288 if page_no % 2 else 324
        for line in page.findall('.//line'):
            chars = list(line.findall('.//char'))
            en = [c for c in chars if float(c.get('x')) > gutter]
            he = [c for c in chars if base(c.get('c', ' ')) and float(c.get('x')) < gutter]
            if en:
                en_rows.append((page_no, float(en[0].get('y')), plain(''.join(c.get('c') for c in en))))
            if he:
                he_rows.append((page_no, float(he[0].get('y')), ''.join(base(c.get('c')) for c in sorted(he,key=lambda c:float(c.get('x')),reverse=True))))
            left = [c for c in chars if float(c.get('x')) < gutter]
            if 'Ps. cxlv.' in plain(''.join(c.get('c') for c in left)):
                citation.append(left)
    deltas=[]
    for h_anchor, e_anchor in ANCHORS:
        h=next((r for r in he_rows if h_anchor in r[2]),None)
        e=next((r for r in en_rows if e_anchor in r[2]),None)
        if not h or not e:raise ValueError(f'Missing prayer anchor {h_anchor} / {e_anchor}')
        delta=abs(h[1]-e[1])
        if h[0]!=e[0] or delta>MAX_BASELINE_DIFFERENCE:
            raise ValueError(f'Prayer alignment failed: {h[:2]} / {e[:2]}')
        deltas.append(round(delta,2))
    if len(citation)!=1:raise ValueError('Latin Psalm citation must occur once in the Hebrew column')
    x=[float(c.get('x')) for c in citation[0] if c.get('c').isascii() and c.get('c').isalpha()]
    if x!=sorted(x):raise ValueError('Latin Psalm citation is reversed')
    text=plain(' '.join(line.get('text','') for line in tree.findall('.//line')))
    if text.count('Ph. Dr.')!=1 or 'Budinger' not in text or '1912-5672.' not in text:
        raise ValueError('Missing or duplicated English title credits/imprint')
    if 'SECOND DAY' in text or 'Omnipotent King, who' in text:
        raise ValueError('Partial opening contains material beyond its encoded range')
    return deltas


def controls(tree):
    for kind in ['direction','alignment','boundary']:
        broken=copy.deepcopy(tree)
        if kind=='direction':
            line=next(l for l in broken.findall('.//line') if 'Ps. cxlv.' in l.get('text','') and float(l.find('.//char').get('x'))<288)
            chars=[c for c in line.findall('.//char') if float(c.get('x'))<288 and c.get('c').isascii() and c.get('c').isalpha()]
            xs=[c.get('x') for c in chars]
            for c,x in zip(chars,reversed(xs)):c.set('x',x)
        elif kind=='alignment':
            for line in broken.findall('.//line'):
                if 'May his great name be exalted' in plain(line.get('text','')):
                    for c in line.findall('.//char'):
                        if float(c.get('x'))>288:c.set('y',str(float(c.get('y'))+50))
        else:
            etree.SubElement(broken.find('page'),'line',text='SECOND DAY')
        try:check(broken)
        except ValueError:pass
        else:raise AssertionError(f'{kind} control escaped detection')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf',type=Path);p.add_argument('--control',action='store_true')
    args=p.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        xml=Path(tmp)/'text.xml'
        subprocess.run(['mutool','draw','-q','-F','stext','-o',str(xml),str(args.pdf)],check=True)
        tree=etree.parse(str(xml)).getroot()
    print('Prayer baseline differences:',check(tree))
    if args.control:
        controls(tree);print('Reversed citation, shifted prayer, and wrong boundary controls rejected')
    return 0


if __name__=='__main__':raise SystemExit(main())

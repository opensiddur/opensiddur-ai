"""Measure the bilingual fast services against their independently recorded scan readings."""
import argparse
import copy
import json
import re
import subprocess
import tempfile
from pathlib import Path
from lxml import etree
from .check_pdf import plain, strip_numeric_markers
from .check_first_day_pdf import latin_note_runs
from opensiddur.importer.scan.pdf_direction import base
from opensiddur.common.constants import SOURCETEXTS_ROOT


def glyph_rows(tree):
    he,en,headings=[],[],[]
    for number,page in enumerate(tree.findall('page'),1):
        gutter=288 if number%2 else 324
        hrows,erows={},{}
        for line in page.findall('.//line'):
            chars=line.findall('.//char')
            hebrew=''.join(base(c.get('c',' ')) or '' for c in sorted(chars,key=lambda c:float(c.get('x')),reverse=True))
            if hebrew=='פזמון' and not any(c.get('c','').isdigit() for c in chars):headings.append((number,min(float(c.get('y')) for c in chars)))
            for c in line.findall('.//char'):
                x=float(c.get('x'));y=round(float(c.get('y')),2)
                if x<gutter and base(c.get('c',' ')):hrows.setdefault(y,[]).append(c)
                elif x>gutter:erows.setdefault(y,[]).append(c)
        he.extend((number,y,''.join(base(c.get('c')) for c in sorted(chars,key=lambda c:float(c.get('x')),reverse=True))) for y,chars in hrows.items())
        for y,chars in erows.items():
            words='';right=None
            for c in sorted(chars,key=lambda c:float(c.get('x'))):
                if right is not None and float(c.get('x'))-right>2 and words and not words[-1].isspace():words+=' '
                words+=c.get('c','');quad=list(map(float,c.get('quad').split()));right=max(quad[0::2])
            en.append((number,y,plain(words)))
    return he,en,headings


def check(tree, day, source_root=SOURCETEXTS_ROOT, expanded=False):
    source=Path(source_root)/'asher_selichot/scan_reading'
    manifest=json.loads((source/(day+'.json')).read_text())
    units=[json.loads((source/name).read_text())for name in manifest['readings']]
    poem=next(u for u in units if u['kind']=='pizmon')
    he,en,headings=glyph_rows(tree)
    if not headings:
        raise ValueError('Fast service requires its one printed pizmon heading')
    deltas=[];previous=headings[-1]
    for stanza in poem['stanzas']:
        hwords=stanza['fragments'][0]['he']['text'].split()
        ewords=stanza['fragments'][0]['en']['text'].split()
        ha=''.join(base(c)or''for c in ' '.join(hwords[:2]))
        ea=plain(' '.join(ewords[:4]))
        h=next((r for r in he if ha in r[2]and r[:2]>previous),None)
        e=next((r for r in en if ea in r[2]and r[:2]>previous),None)
        if h is None or e is None:raise ValueError('Missing fast stanza: '+str((ha,ea)))
        if h[0]!=e[0]or abs(h[1]-e[1])>16:raise ValueError('Misaligned fast stanza: '+str((h,e)))
        if not deltas and not any(r[0]==h[0]and r[1]<h[1]for r in headings):raise ValueError('Fast pizmon heading stranded')
        deltas.append(round(abs(h[1]-e[1]),2));previous=max(h[:2],e[:2])
    for chars in latin_note_runs(tree).values():
        xs=[float(c.get('x'))for c in chars]
        if any(b<a-.05 for a,b in zip(xs,xs[1:])):raise ValueError('Reversed fast Latin apparatus')
    normalize=lambda words:strip_numeric_markers(plain(re.sub(r'(?<=\w)-\s+(?=\w)','',' '.join(words.split()))))
    text=plain(re.sub(r'(?<=\w)-\s+(?=\w)','',' '.join(n.get('text','')for n in tree.findall('.//line'))))
    body=normalize(' '.join(r[2]for r in en))
    notes=[(phrase,1) for phrase in ({'thursday-fast':['In rewarding the good','Viz., Ishmael.'],'last-monday-fast':['Ps. cii. 28.'],'tenth-tevet':['viz., The 8th, 9th, and 10th','Ptolomæus Philadelphus','The 9th of Tebeth','Ezekiel.','Ezek. xxiv. 1.','Tebeth is the tenth month','The daughter of Zion','Abi Sonoach','Nebusaradon.','Ezek. xxiv. 3.']}[day])]
    if expanded:notes += [('Lev. xxvi',3),('Deut. xxx.',3),('Deut. iv.',2),('Isaiah xliv. 22.',1),('Isaiah xliii. 25.',1),('Isaiah i. 18.',1),('Isaiah vi. 7.',1),('Ezek. xxxvi. 25.',2)]
    for fingerprint,count in notes:
        if text.count(fingerprint)!=count:raise ValueError('Fast footnote occurrence: '+fingerprint)
    if 'May the prayers and supplications' in body:raise ValueError('Unrequested Full Kaddish supplied')
    following={'thursday-fast':'LAST OF THE THREE FASTS','last-monday-fast':'FAST OF TEBETH','tenth-tevet':'FAST OF ESTHER'}[day]
    if following in body:raise ValueError('Following fast entered current service')
    if body.count('Prayers are said as on other week days')!=1:raise ValueError('Weekday Amidah performance rubric lost')
    if expanded:
        for cue in ['Say ', 'Continue from', 'Wherever the words', '(For thou art great, &c.)','(Israel is saved, &c.)']:
            if cue in body:raise ValueError('Fulfilled fast cue remains: '+cue)
        for phrase in ['The Reader continues the Ameedah','Conclude the service as on other week-days.']:
            if body.count(phrase)!=1:raise ValueError('Unsupplied performance instruction lost: '+phrase)
        if body.count('Omnipotent King, who')!=3 or body.count('take us for thy heritage.')!=(6 if day=='last-monday-fast' else 4):raise ValueError('Fast prayer pair bounds changed')
    if day=='thursday-fast':
        if not expanded and (body.count('(For thou art great, &c.)')!=5 or body.count('(Israel is saved, &c.)')!=1):raise ValueError('Documentary fast cues changed')
        if body.count('Israel is saved by the Lord')!=(2 if expanded else 1):raise ValueError('Fast opening repeat count')
        if body.count('for thou art great in pardoning and full of compassion.')!=(7 if expanded else 2):raise ValueError('Fast full refrain count')
    elif day=='last-monday-fast':
        if body.count('(The Eternal, &c.)')!=(0 if expanded else 1):raise ValueError('Final Monday opening cue changed')
        if body.count('an Omnipotent God, merciful and gracious')!=(2 if expanded else 1):raise ValueError('Final Monday attributes count')
    if day=='tenth-tevet':
        if body.count('(When, &c.)')!=(0 if expanded else 13):raise ValueError('Tevet cue count changed')
        if body.count('When our forefathers trusted')!=(13 if expanded else 1):raise ValueError('Tevet complete refrain count changed')
        if 'advanced towards the holy city' not in body:raise ValueError('Tevet facsimile word join lost')
    print(day+': '+str(len(notes))+' apparatus fingerprints; stanza start deltas '+str(deltas))
    return he,en


def controls(tree,day,source_root,expanded):
    he,en=check(tree,day,source_root,expanded)
    broken=copy.deepcopy(tree)
    fingerprint={'thursday-fast':'In rewarding the good','last-monday-fast':'Ps. cii. 28.','tenth-tevet':'The 9th of Tebeth'}[day]
    note=next(n for n in broken.findall('.//line')if fingerprint in n.get('text',''));note.getparent().remove(note)
    try:check(broken,day,source_root,expanded)
    except ValueError:pass
    else:raise AssertionError('Missing fast footnote escaped detection')
    broken=copy.deepcopy(tree);shifted=0
    manifest=json.loads((Path(source_root)/'asher_selichot/scan_reading'/(day+'.json')).read_text())
    poem=next(u for name in manifest['readings'] if (u:=json.loads((Path(source_root)/'asher_selichot/scan_reading'/name).read_text()))['kind']=='pizmon')
    needle=plain(' '.join(poem['stanzas'][1]['fragments'][0]['en']['text'].split()[:4]))
    _,rows,heads=glyph_rows(tree)
    target=next((page,y)for page,y,words in rows if needle in words and (page,y)>heads[-1])
    for number,page in enumerate(broken.findall('page'),1):
        gutter=288 if number%2 else 324
        for c in page.findall('.//char'):
            if number==target[0] and round(float(c.get('y')),2)==target[1] and float(c.get('x'))>gutter:
                c.set('y',str(float(c.get('y'))+50));shifted+=1
    if not shifted:raise AssertionError('Fast control shifted no glyphs')
    try:check(broken,day,source_root,expanded)
    except ValueError:pass
    else:raise AssertionError('Shifted fast stanza escaped detection')
    print(day+': missing-note and shifted-stanza controls rejected')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf');p.add_argument('--day',required=True,choices=['thursday-fast','last-monday-fast','tenth-tevet']);p.add_argument('--expanded',action='store_true');p.add_argument('--control',action='store_true');p.add_argument('--source-root',type=Path,default=SOURCETEXTS_ROOT);a=p.parse_args(argv)
    with tempfile.TemporaryDirectory()as tmp:
        xml=Path(tmp)/'glyphs.xml';subprocess.run(['mutool','draw','-F','stext','-o',str(xml),a.pdf],check=True,capture_output=True);tree=etree.parse(str(xml));check(tree,a.day,a.source_root,a.expanded)
        if a.control:controls(tree,a.day,a.source_root,a.expanded)
    return 0
if __name__=='__main__':raise SystemExit(main())

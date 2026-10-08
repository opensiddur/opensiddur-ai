"""Verify both encoded days, the contents page and the bookmark hierarchy."""
import argparse
import copy
import subprocess
import tempfile
from pathlib import Path
from lxml import etree
from pypdf import PdfReader
from .check_pdf import check as check_poem, controls as poem_controls, plain
from .check_first_day_pdf import check as check_first, controls as first_controls, latin_note_runs
from opensiddur.importer.scan.pdf_direction import base


def outline_rows(reader):
    rows=[]
    def walk(items, depth):
        for item in items:
            if isinstance(item,list):walk(item,depth+1)
            else:rows.append((depth, str(item.title), reader.get_destination_page_number(item)+1,
                              float(item.top) if item.top is not None else None))
    walk(reader.outline,0)
    return rows


def day_bookmarks(rows):
    days=[]
    for caption in ['FIRST DAY','SECOND DAY']:
        hits=[r for r in rows if caption in r[1] and r[0]==0]
        if len(hits)!=1:raise ValueError('Each day requires one top-level bookmark: '+caption)
        days.append(hits[0])
    for day in days:
        index=rows.index(day)
        descendants=[]
        for row in rows[index+1:]:
            if row[0]<=day[0]:break
            descendants.append(row)
        if not any(row[0]>day[0] and 'פזמון' in row[1] for row in descendants):
            raise ValueError('Day bookmark must be above its pizmon')
    return days


def slice_day(tree, start, end=None, keep_titles=False):
    """Retain original page slots, so parity-dependent column gutters remain valid."""
    result=copy.deepcopy(tree)
    pages=result.findall('page')
    start_page,start_top=start[2],start[3]
    end_page,end_top=(end[2],end[3]) if end else (len(pages)+1,None)
    for number,page in enumerate(pages,1):
        height=float(page.get('height'))
        for line in list(page.findall('.//line')):
            chars=line.findall('.//char')
            y=float(chars[0].get('y')) if chars else float('inf')
            after_start=number>start_page or (number==start_page and y>=height-start_top-2)
            before_end=number<end_page or (number==end_page and y<height-end_top-2)
            title=keep_titles and number<=4
            if not(title or (after_start and before_end)):line.getparent().remove(line)
    return result


def second_day_check(tree, expanded):
    for chars in latin_note_runs(tree).values():
        xs=[float(c.get('x')) for c in chars]
        if any(b<a-0.05 for a,b in zip(xs,xs[1:])):
            raise ValueError('Reversed second-day Latin footnote')
    he,en=[],[]
    for number,page in enumerate(tree.findall('page'),1):
        gutter=288 if number%2 else 324
        for line in page.findall('.//line'):
            chars=line.findall('.//char')
            h=[c for c in chars if float(c.get('x'))<gutter and base(c.get('c',' '))]
            e=[c for c in chars if float(c.get('x'))>gutter]
            if h:he.append((number,float(h[0].get('y')),''.join(base(c.get('c')) for c in sorted(h,key=lambda c:float(c.get('x')),reverse=True))))
            if e:en.append((number,float(e[0].get('y')),plain(''.join(c.get('c') for c in e))))
    anchors=[('ישראלנושע','Israel is saved'),('שעריך','They knock'),('פוחדים','They are intimidated'),
             ('מטובך','Anticipate them'),('יושעו','Let them be saved'),('הקשיבה','Attend, O Lord')]
    deltas=[];previous=(0,0)
    for ha,ea in anchors:
        h=next((r for r in he if ha in r[2] and r[:2]>=previous),None)
        e=next((r for r in en if ea in r[2] and r[:2]>=previous),None)
        if h is None or e is None:raise ValueError('Missing second-day stanza '+ha+' / '+ea)
        if h[0]!=e[0] or abs(h[1]-e[1])>16:raise ValueError('Second-day stanza alignment failed: '+str((h,e)))
        deltas.append(round(abs(h[1]-e[1]),2));previous=max(h[:2],e[:2])
    text=plain(' '.join(l.get('text','') for l in tree.findall('.//line')))
    # The closing transclusion adds its own Deut. iv. 31 note in expanded output.
    # Two separate new notes deliberately have the same patriarchs wording.
    for phrase,count in [('Deut. iv. 31.',2 if expanded else 1),('Jacob.',1),('During the Crusades.',1),
                         ('The three patriarchs.',2),('In allusion to the mixed races',1),('Viz., Ishmael.',1)]:
        if text.count(phrase)!=count:raise ValueError('Second-day footnote occurrence: '+phrase)
    if 'THIRD DAY' in text:raise ValueError('Third-day material is outside the encoded boundary')
    body=' '.join(' '.join(r[2] for r in en).split())
    if expanded:
        for phrase in ['Say ', 'Conclude the Service', 'Wherever the words','(For thou art great,','(Israel is saved,']:
            if phrase in body:raise ValueError('Expanded second day retains a fulfilled cue: '+phrase)
        if body.count('Omnipotent King, who')!=3:raise ValueError('Second day requires three prayer-pair expansions')
        if body.count('May the prayers and supplications')!=1:raise ValueError('Second day requires one closing Full Kaddish')
    else:
        if 'Conclude the Service as on the first day' not in body:raise ValueError('Missing second-day closing rubric')
        if body.count('(For thou art great,')!=5:raise ValueError('Expected four printed refrain cues plus the rubric’s quoted cue')
    return deltas


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf',type=Path);parser.add_argument('--expanded',action='store_true');parser.add_argument('--control',action='store_true')
    args=parser.parse_args(argv)
    reader=PdfReader(args.pdf);rows=outline_rows(reader);days=day_bookmarks(rows)
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'text.xml'
        subprocess.run(['mutool','draw','-F','stext','-o',str(path),str(args.pdf)],check=True,capture_output=True)
        tree=etree.parse(str(path)).getroot()
        text=' '.join(l.get('text','') for l in tree.findall('.//line'))
        if 'Contents' not in text:raise ValueError('Missing generated contents page')
        for page in tree.findall('page'):
            if not any('Contents' in l.get('text','') for l in page.findall('.//line')):continue
            for line in page.findall('.//line'):
                digits=[c for c in line.findall('.//char') if c.get('c','').isdigit()]
                xs=[float(c.get('x')) for c in digits]
                if xs!=sorted(xs):raise ValueError('Reversed TOC page number')
        first=slice_day(tree,days[0],days[1],keep_titles=True);second=slice_day(tree,days[1])
        first_deltas=check_first(first,complete=True,expanded=args.expanded)
        poem_deltas=check_poem(first,args.expanded,complete=True)
        second_deltas=second_day_check(second,args.expanded)
        if args.control:
            first_controls(first,complete=True,expanded=args.expanded);poem_controls(first,args.expanded,complete=True)
            broken=[(1 if 'SECOND DAY' in r[1] else r[0],*r[1:]) for r in rows]
            try:day_bookmarks(broken)
            except ValueError:pass
            else:raise AssertionError('Wrong bookmark depth escaped detection')
            broken=copy.deepcopy(second)
            note=next(l for l in broken.findall('.//line') if 'Viz., Ishmael.' in l.get('text',''))
            note.getparent().append(copy.deepcopy(note))
            try:second_day_check(broken,args.expanded)
            except ValueError:pass
            else:raise AssertionError('Duplicate second-day note escaped detection')
            broken=copy.deepcopy(second)
            for number,page in enumerate(broken.findall('page'),1):
                gutter=288 if number%2 else 324
                for line in page.findall('.//line'):
                    if 'They knock' in plain(line.get('text','')):
                        for char in line.findall('.//char'):
                            if float(char.get('x'))>gutter:char.set('y',str(float(char.get('y'))+50))
            try:second_day_check(broken,args.expanded)
            except ValueError:pass
            else:raise AssertionError('Shifted second-day stanza escaped detection')
        print(f'{len(reader.pages)} pages; contents generated; day bookmarks above pizmons; first-day prayers {first_deltas}; first pizmon {poem_deltas}; second pizmon {second_deltas}; footnotes and expansion boundaries checked; controls={args.control}')
    return 0


if __name__=='__main__':raise SystemExit(main())

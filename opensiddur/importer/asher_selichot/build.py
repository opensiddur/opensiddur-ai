"""Encode the image-adjudicated Asher pilot, retaining printed and expanded forms.

Reads the committed scan reading, not OCR. Dependency ranges are authored from
this edition, never substituted from another project's prayer text.
"""
import argparse
import json
from pathlib import Path
import unicodedata
from lxml import etree
from opensiddur.common.constants import SOURCETEXTS_ROOT, PROJECT_DIRECTORY
from opensiddur.importer.util.validation import validate

TEI='http://www.tei-c.org/ns/1.0'
J='http://jewishliturgy.org/ns/jlptei/2'
XML='{http://www.w3.org/XML/1998/namespace}'
POEM='urn:x-opensiddur:text:poem:bemotzaei_menuhah'
PRAYER='urn:x-opensiddur:text:prayer:'
IA='https://archive.org/details/selichothdavidasher1912'


def element(parent, name, text=None, **attributes):
    tag=f'{{{J if name.startswith("j:") else TEI}}}{name.split(":")[-1]}'
    node=etree.SubElement(parent,tag,attributes)
    node.text=text
    return node


def document(lang, project, title, urn, *, index=False):
    root=etree.Element(f'{{{TEI}}}TEI',nsmap={'tei':TEI,'j':J},attrib={XML+'lang':lang})
    header=element(root,'teiHeader');file=element(header,'fileDesc');titles=element(file,'titleStmt')
    element(titles,'title',title,type='main')
    resp=element(titles,'respStmt');element(resp,'resp','AI-assisted scan reading and encoding by',key='trc')
    element(resp,'name','Codex',ref='urn:x-opensiddur:contributor:opensiddur.org/codex')
    editions=element(file,'editionStmt');element(editions,'edition','Pilot read from the scanned 1912–5672 printing; editorial expansions recorded in the source README.')
    pub=element(file,'publicationStmt');distributor=element(pub,'distributor')
    element(distributor,'ref','Open Siddur Project',target='https://opensiddur.org')
    element(pub,'idno',urn+'@'+project,type='urn')
    availability=element(pub,'availability',status='free')
    element(availability,'licence','Creative Commons Attribution-ShareAlike 4.0 International',target='https://creativecommons.org/licenses/by-sa/4.0/')
    source=element(file,'sourceDesc')
    if index:
        bibl=element(source,'bibl');element(bibl,'title','Selichoth for the Propitiatory and Penitential Days, and for the Minor Fasts')
        element(bibl,'editor','David Asher',role='translator');element(bibl,'publisher','Vallentine & Sons')
        element(bibl,'pubPlace','London');element(bibl,'date','1912–5672',when='1912')
        element(bibl,'idno',IA,type='url');element(bibl,'note','The scan is the source. First publication was 1866; this pilot encodes the 1912 reprint. Asher-specific expansions and reference ranges are documented in sources/asher_selichot/README.md.')
    else:
        p=element(source,'p');element(p,'ref','Asher Selichoth, 1912 source metadata',target='index.xml')
    return root,element(root,'text')


def pb(parent, scan, printed):
    return element(parent,'pb',n=printed,ed='1912',facs=f'https://archive.org/download/selichothdavidasher1912/page/n{int(scan[1:])-1}_medium.jpg')


def marker(parent, urn):
    element(parent,'milestone',unit='stanza',corresp=urn)


def choice(parent, abbr, expan):
    node=element(parent,'choice');element(node,'abbr',abbr);element(node,'expan',expan)
    return node


def expansion_instruction(parent, identity, feature):
    """Keep the printed rubric unless this view supplies the requested text."""
    conditional = element(parent, 'j:conditional')
    conditional.set(XML+'id', identity)
    fs = element(conditional, 'fs', type='asher:expansions')
    value = element(fs, 'f'); value.set('name', feature)
    element(value, 'binary', value='false')
    note = element(parent, 'note', type='instruction')
    element(parent, 'j:endConditional', target='#'+identity)
    return note


def poem(lang,project,data):
    root,text=document(lang,project,'במוצאי מנוחה' if lang=='he' else 'On the outgoing of the Sabbath',POEM)
    div=element(element(text,'body'),'div',corresp=POEM)
    pb(div,'s32' if lang=='he' else 's33','15')
    element(div,'head','פזמון' if lang=='he' else data['heading'])
    marker(div,POEM+'/rubric')
    rubric=expansion_instruction(div, 'refrain_instruction', 'refrains_present')
    rubric.set(XML+'lang','en')
    if lang=='he':
        rubric.text='Wherever the word '
        f=element(rubric,'foreign','לשמוע');f.set(XML+'lang','he');f.tail=' occurs at the end of the verse, repeat from '
        f=element(rubric,'foreign','לִשְׁמֹעַ');f.set(XML+'lang','he');f.tail=' till '
        f=element(rubric,'foreign','וְאֶל־הַתְּפִלָּה');f.set(XML+'lang','he');f.tail='.'
    else:
        rubric.text=data['rubric']
    he_refrain='לִשְׁמֹעַ אֶל־הָרִנָּה וְאֶל־הַתְּפִלָּה׃'
    en_refrain='to hearken unto our hymns of praise, and unto our supplication.'
    for n,stanza in enumerate(data['stanzas'],1):
        marker(div,POEM+f'/{n}')
        if lang=='he':
            lg=element(div,'lg')
            # Raised dots and two-dot stops delimit verse phrases. Physical wrapping
            # runs across these units and is retained separately in image evidence.
            stanza=' '.join(stanza)
            phrases=stanza.split(' · ')
            for i,phrase in enumerate(phrases):
                element(lg,'l',phrase+(' ·' if i<len(phrases)-1 else ''))
            if 2<=n<=7:
                line=element(lg,'l');choice(line,'לשמוע',he_refrain)
            if n==8:
                element(lg,'l',he_refrain)
                line=element(lg,'l');choice(line,data['final_hebrew_rubric'],' '.join(data['stanzas'][0]))
        else:
            p=element(div,'p',stanza)
            if n==2:
                before,after=stanza.split('mighty deed;',1)
                p.text=before+'mighty deed;'
                note=element(p,'note',data['footnote'],type='commentary');note.tail=after
            cue=data['cues'].get(str(n))
            if cue:
                p.text=(p.text or '')+' '
                choice(p,cue,en_refrain)
            if n==8:
                p.text+=' ';choice(p,data['final_cue'],data['stanzas'][0])
    marker(div,POEM+'/conclusion')
    note=expansion_instruction(div, 'prayer_instruction', 'prayers_present');note.set(XML+'lang','en')
    if lang=='he':
        note.text='Say '
        f=element(note,'foreign','אֵל מֶלֶךְ');f.set(XML+'lang','he');f.tail=' and '
        f=element(note,'foreign','וַיַּעֲבֹר');f.set(XML+'lang','he')
    else:
        note.text=data['conclusion']
    return root


def italicize(parent, phrases):
    """Retain this edition's emphasis without changing the documentary words."""
    original = parent.text or ''
    locations = []
    for phrase in phrases:
        position = original.find(phrase)
        if position < 0:
            raise ValueError(f'Missing printed emphasis phrase: {phrase}')
        locations.append((position, phrase))
    locations.sort()
    if not locations:
        return
    parent.text = original[:locations[0][0]]
    for i, (position, phrase) in enumerate(locations):
        hi = element(parent, 'hi', phrase, rend='italic')
        end = locations[i + 1][0] if i + 1 < len(locations) else len(original)
        hi.tail = original[position + len(phrase):end]


def dependency(lang,project,name,pages):
    urn=PRAYER+name
    root,text=document(lang,project,name.replace('_',' '),urn)
    div=element(element(text,'body'),'div',corresp=urn)
    p=None
    for scan,words in pages.items():
        if p is None:
            pb(div,scan,'11');p=element(div,'p',words)
            if lang == 'en' and name == 'el_melekh_yoshev':
                italicize(p, ['by causing', 'charitably', 'of thy mercy', 'we beseech thee', 'attributes,'])
        else:
            brk=pb(p,scan,'12');brk.tail=' '+words
    return root


def service(lang,project,expanded=False):
    urn='urn:x-opensiddur:text:siddur:selichot/first_day/pilot'+('/expanded' if expanded else '')
    root,text=document(lang,project,'Asher Selichoth — '+('expanded' if expanded else 'documentary')+' pilot',urn,index=True)
    front=element(text,'front');pb(front,'s3','[unnumbered]')
    title=element(front,'titlePage');title.set(XML+'lang','en')
    doc=element(title,'docTitle');element(doc,'titlePart','SELICHOTH',type='main')
    element(doc,'titlePart','FOR THE PROPITIATORY AND PENITENTIAL DAYS, AND FOR THE MINOR FASTS.',type='sub')
    element(doc,'titlePart','TO WHICH ARE ADDED THE SELICHOTH FOR THE MINOR DAY OF ATONEMENT',type='desc')
    element(title,'docEdition','With a New English Translation')
    by=element(title,'byline','By ');element(by,'docAuthor','DAVID ASHER, Ph. Dr.')
    imprint=element(title,'docImprint');element(imprint,'pubPlace','LONDON')
    element(imprint,'publisher','VALLENTINE & SONS (Succrs.)');element(imprint,'pubPlace','31, Duke Street, Aldgate, E.C.')
    element(imprint,'docDate','1912–5672.')
    body=element(text,'body');div=element(body,'div')
    element(div,'head','Asher Selichoth: first-day piyyut pilot').set(XML+'lang','en')
    element(div,'j:transclude',target=POEM)
    if expanded:
        for name in ['el_melekh_yoshev','vayaavor']:
            element(div,'j:transclude',target=PRAYER+name)
    return root


def build(source_root,project_directory):
    data=json.loads((Path(source_root)/'asher_selichot/scan_reading/pilot.json').read_text())
    documents=[]
    for lang in ['he','en']:
        project=f'asher_selichot_{lang}_1912';out=Path(project_directory)/project
        docs={'index.xml':service(lang,project),'expanded.xml':service(lang,project,True),
              'bemotzaei_menuhah.xml':poem(lang,project,data[lang]['poem'])}
        for name,pages in data[lang]['prayers'].items():
            docs[name+'.xml']=dependency(lang,project,name,pages)
        for name,root in docs.items():
            xml=unicodedata.normalize('NFKD',etree.tostring(root,encoding='unicode',pretty_print=True))
            valid,errors=validate(xml)
            if not valid:
                raise ValueError(f'{project}/{name}: '+ '\n'.join(errors))
            documents.append((out/name,xml))
    from .first_day import documents as first_day_documents
    for project, name, root in first_day_documents(Path(source_root)/'asher_selichot/scan_reading'):
        xml=unicodedata.normalize('NFKD',etree.tostring(root,encoding='unicode',pretty_print=True))
        valid,errors=validate(xml)
        if not valid:
            raise ValueError(f'{project}/{name}: '+ '\n'.join(errors))
        documents.append((Path(project_directory)/project/name,xml))
    for path,xml in documents:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(xml,encoding='utf-8')
    return [path for path,_ in documents]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=SOURCETEXTS_ROOT)
    parser.add_argument('--project-directory',type=Path,default=PROJECT_DIRECTORY)
    args=parser.parse_args(argv)
    for path in build(args.source_root,args.project_directory):print(path)
    return 0


if __name__=='__main__':raise SystemExit(main())

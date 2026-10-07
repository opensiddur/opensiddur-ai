"""Verify the pilot against independent documentary streams and its expansion policy."""
import argparse
import json
from pathlib import Path
from lxml import etree
from opensiddur.common.constants import SOURCETEXTS_ROOT, PROJECT_DIRECTORY
from opensiddur.importer.scan.reverse import streams, check
from opensiddur.importer.util.validation import validate
from .build import TEI, J, POEM, PRAYER


def verify(source_root, project_directory):
    source=Path(source_root)/'asher_selichot/scan_reading'
    payload=json.loads((source/'documentary-streams.json').read_text())
    expected={(page,lang):text for page,langs in payload.items() for lang,text in langs.items()}
    actual={}
    data=json.loads((source/'pilot.json').read_text())
    files=0
    for lang in ['he','en']:
        project=Path(project_directory)/f'asher_selichot_{lang}_1912'
        for path in sorted(project.glob('*.xml')):
            valid,errors=validate(path)
            if not valid:raise ValueError(f'{path}: {errors}')
            files+=1
        for name in ['bemotzaei_menuhah','el_melekh_yoshev','vayaavor']:
            root=etree.parse(str(project/(name+'.xml'))).getroot()
            for key,text in streams(root,include_notes=True).items():
                actual[key]=(actual.get(key,'')+' '+text).strip()
        root=etree.parse(str(project/'bemotzaei_menuhah.xml'))
        choices=root.findall(f'.//{{{TEI}}}choice')
        if len(choices)!=(7 if lang=='he' else 6):
            raise ValueError(f'{lang}: missing or duplicated refrain choices')
        for node in choices:
            abbr=node.find(f'{{{TEI}}}abbr');expan=node.find(f'{{{TEI}}}expan')
            if abbr is None or expan is None or not ''.join(expan.itertext()).strip():
                raise ValueError('Each refrain needs a printed cue and a nonempty expansion')
        if lang=='he':
            expected_final=' '.join(data['he']['poem']['stanzas'][0])
            refrain=data['he']['poem']['final_refrain']
        else:
            expected_final=data['en']['poem']['stanzas'][0]
            refrain='to hearken unto our hymns of praise, and unto our supplication.'
        if ''.join(choices[-1].find(f'{{{TEI}}}expan').itertext())!=expected_final:
            raise ValueError('Concluding cue must expand to the entire opening stanza')
        if any(''.join(c.find(f'{{{TEI}}}expan').itertext())!=refrain for c in choices[:-1]):
            raise ValueError('Short cue must expand to this edition’s printed refrain')
        for name,targets in [('index.xml',[POEM]),('expanded.xml',[POEM,PRAYER+'el_melekh_yoshev',PRAYER+'vayaavor'])]:
            entry=etree.parse(str(project/name))
            if [n.get('target') for n in entry.findall(f'.//{{{J}}}transclude')]!=targets:
                raise ValueError(f'{name}: unexpected reference expansion boundary')
    verify_opening(source, Path(project_directory))
    differences=check(actual,expected)
    if differences:raise ValueError(differences)
    print(f'{files} schema-valid files; {len(actual)} documentary page/language streams match; expansion targets and forms checked')
    return actual


def verify_opening(source, project_directory):
    """Check page/language streams, partial verse and separate WIP entrypoints."""
    from .first_day import OPENING
    payload=json.loads((source/'opening-documentary-streams.json').read_text())
    expected={(page,lang):words for page,langs in payload.items() for lang,words in langs.items()}
    actual={}
    titles=json.loads((source/'title-pages.json').read_text())
    for lang in ['he','en']:
        project=project_directory/f'asher_selichot_{lang}_1912'
        root=etree.parse(str(project/'first_day_opening.xml')).getroot()
        actual.update(streams(root,include_notes=True))
        urns=[el.get('corresp') for el in root.iter() if el.get('corresp')]
        if len(urns)!=len(set(urns)):
            raise ValueError('Repeated correspondence within the opening module')
        verses=root.findall(f'.//{{{TEI}}}milestone[@corresp="urn:x-opensiddur:text:bible:psalms/145/9"]')
        if len(verses)!=1 or verses[0].getnext().tag!=f'{{{TEI}}}pb':
            raise ValueError('Psalm 145:9 must continue across its printed page break')
        entry=etree.parse(str(project/'first_day.xml')).getroot()
        if [el.get('target') for el in entry.findall(f'.//{{{J}}}transclude')]!=[OPENING]:
            raise ValueError('Partial first-day entry must contain only the contiguous opening')
        front=entry.find(f'.//{{{TEI}}}front')
        title_streams={key:words for key,words in streams(front,include_notes=True).items() if words.strip()}
        wanted={}
        for title_lang in ['he','en']:
            data=titles[title_lang]
            words=data['titles']+[data['edition']]
            if data.get('byline'):words+=[data['byline'],data['credentials']]
            words += [data[key] for key in ['place','publisher','address','date']]
            wanted[(data['scan'],title_lang)]=' '.join(words)
        if check(title_streams,wanted):raise ValueError('Title pages differ from scan readings')
    differences=check(actual,expected)
    if differences:raise ValueError(differences)
    print(f'{len(actual)} opening page/language streams match; both title pages and partial entry boundaries checked')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=SOURCETEXTS_ROOT)
    parser.add_argument('--project-directory',type=Path,default=PROJECT_DIRECTORY)
    args=parser.parse_args(argv)
    verify(args.source_root,args.project_directory)
    return 0


if __name__=='__main__':raise SystemExit(main())

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
    verify_continuation(source, Path(project_directory))
    differences=check(actual,expected)
    if differences:raise ValueError(differences)
    print(f'{files} schema-valid files; {len(actual)} documentary page/language streams match; expansion targets and forms checked')
    return actual


def verify_opening(source, project_directory):
    """Check page/language streams, partial verse and separate WIP entrypoints."""
    from .first_day import ENTRY_TARGETS
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
        if [el.get('target') for el in entry.findall(f'.//{{{J}}}transclude')]!=ENTRY_TARGETS:
            raise ValueError('First-day entry must preserve the complete documentary module order')
        expanded=etree.parse(str(project/'first_day_expanded.xml')).getroot()
        expanded_targets = ENTRY_TARGETS[:]
        poem_position = expanded_targets.index(POEM)+1
        expanded_targets[poem_position:poem_position] = [PRAYER+'el_melekh_yoshev', PRAYER+'vayaavor']
        if [el.get('target') for el in expanded.findall(f'.//{{{J}}}transclude')] != expanded_targets:
            raise ValueError('Expanded first-day entry must supply the piyyut conclusion prayers')
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
    print(f'{len(actual)} opening page/language streams match; both title pages and first-day entry boundaries checked')


def verify_continuation(source, project_directory):
    """Compare authored units to source readings and printed footnote evidence."""
    import re
    import unicodedata
    from .first_day import FIRST_DAY, MODULE_ORDER, EXPANSION_TARGETS
    groups=json.loads((source/'first-day-continuation.json').read_text())['sections']
    count=0
    for lang in ['he','en']:
        for name, readings in groups.items():
            path=project_directory/f'asher_selichot_{lang}_1912'/f'first_day_{name}.xml'
            root=etree.parse(str(path)).getroot()
            div=root.find(f'.//{{{TEI}}}body/{{{TEI}}}div')
            units=div.findall(f'{{{TEI}}}div')
            if list(div)!=units or (div.text or '').strip():
                raise ValueError('Unexpected text outside documentary continuation units')
            if len(units)!=len(readings):raise ValueError('Missing or duplicated first-day unit')
            urns=[n.get('corresp') for n in root.iter() if n.get('corresp')]
            if len(urns)!=len(set(urns)):raise ValueError('Repeated correspondence within a module')
            for unit,reading in zip(units,readings):
                if unit.get('corresp')!=FIRST_DAY+'/'+reading['id']:raise ValueError('Units out of source order')
                targets = EXPANSION_TARGETS.get(reading['id'])
                actual_targets = [n.get('target') for n in unit.findall(f'{{{J}}}transclude')]
                if actual_targets != (targets or []):
                    raise ValueError(f'{reading["id"]}: unexpected editorial expansion targets')
                if targets:
                    # Audit the true branch, then remove it before documentary comparison.
                    scopes = unit.findall(f'{{{J}}}conditional')
                    if len(scopes) != 2:
                        raise ValueError('Expansion requires distinct printed and supplied branches')
                    for scope, value in zip(scopes, ['false', 'true']):
                        binary = scope.find(f'{{{TEI}}}fs/{{{TEI}}}f/{{{TEI}}}binary')
                        if binary is None or binary.get('value') != value:
                            raise ValueError('Expansion branch polarity changed')
                    if reading['id'] == 'reader_kaddish':
                        declaration = scopes[1].getnext()
                        if declaration is None or declaration.tag != f'{{{J}}}declare':
                            raise ValueError('Full Kaddish needs scoped first-day Selichot context')
                        wanted = {'asher:selichot': ('first_day', 'true'),
                                  'opensiddur:holiday-aggregate': ('aseret-ymei-tshuva', 'false')}
                        for fs_type, (feature, value) in wanted.items():
                            binary = declaration.find(f'{{{TEI}}}fs[@type="{fs_type}"]/{{{TEI}}}f[@name="{feature}"]/{{{TEI}}}binary')
                            if binary is None or binary.get('value') != value:
                                raise ValueError('First-day Selichot must exclude Ten Days additions')
                        end_declare = unit.find(f'{{{J}}}endDeclare[@target="#first_day_selichot_kaddish"]')
                        if end_declare is None:raise ValueError('Unclosed first-day Kaddish declaration')
                    start = scopes[1]
                    end = unit.find(f'{{{J}}}endConditional[@target="#{start.get("{http://www.w3.org/XML/1998/namespace}id")}"]')
                    if end is None:raise ValueError('Unclosed expansion branch')
                    children = list(unit)
                    for child in children[children.index(start):children.index(end)+1]:unit.remove(child)
                if reading.get('incipit_he'):
                    invocation = reading['fragments'][0][lang]['text'].split('\n', 1)[0]
                    node = unit.find(f'{{{TEI}}}lg/{{{TEI}}}l' if lang == 'he' else f'{{{TEI}}}p')
                    if unit.findall(f'{{{TEI}}}head') or node is None or not ''.join(node.itertext()).startswith(invocation):
                        raise ValueError(f'{reading["id"]}: piyyut invocation must remain in its opening text')
                expected_notes=[n['text'] for f in reading['fragments'] for n in f['notes'][lang]]
                notes=unit.findall(f'.//{{{TEI}}}note[@type="commentary"]')
                normalize=lambda text:' '.join(unicodedata.normalize('NFKD',text).split())
                if [normalize(' '.join(n.itertext())) for n in notes]!=list(map(normalize,expected_notes)):
                    raise ValueError(f'{reading["id"]}: missing or changed printed footnote')
                # Exclude apparatus after checking it separately, preserving surrounding body text.
                for note in notes:
                    parent=note.getparent();previous=note.getprevious()
                    if previous is None:parent.text=(parent.text or '')+(note.tail or '')
                    else:previous.tail=(previous.tail or '')+(note.tail or '')
                    parent.remove(note)
                expected={}
                for f in reading['fragments']:
                    data=f[lang];page=data['scan'];words=data['text']
                    if reading['kind']=='rubric' and lang=='he':
                        # Independent language separation: Hebrew letters/marks and attached punctuation
                        # belong to cues; English words belong to the instruction.
                        hebrew=' '.join(re.findall(r'[\u0590-\u05ff]+',words))
                        english=re.sub(r'[\u0590-\u05ff]+','',words).replace(' · ',' ')
                        expected[(page,'he')]=normalize(hebrew)
                        expected[(page,'en')]=normalize(english)
                    else:expected[(page,lang)]=normalize(words)
                unit.set('{http://www.w3.org/XML/1998/namespace}lang',lang)
                actual=streams(unit,include_notes=True)
                if reading['kind']=='rubric' and lang=='he':
                    # Preserve printed phrase dots in the Hebrew cue stream.
                    actual={k:v.replace(' · ',' ') for k,v in actual.items()}
                differences=check(actual,expected)
                if differences:raise ValueError(f'{reading["id"]}: {differences}')
                count+=1
        pages=[]
        for name in MODULE_ORDER:
            root=etree.parse(str(project_directory/f'asher_selichot_{lang}_1912'/(name+'.xml')))
            pages.extend(int(re.search(r'/n(\d+)',n.get('facs')).group(1)) for n in root.findall(f'.//{{{TEI}}}pb'))
        required=set(range(5 if lang=='he' else 6, 52 if lang=='he' else 53, 2))
        if pages!=sorted(pages) or set(pages)!=required:
            raise ValueError('First-day facsimiles must follow source order through the final leaf')
        final=groups['closing'][-1]
        if final['id']!='reader_kaddish':raise ValueError('First day must end with Reader’s Kaddish instruction')
    print(f'{count} continuation units match documentary readings; footnotes and final n51/n52 boundary checked')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=SOURCETEXTS_ROOT)
    parser.add_argument('--project-directory',type=Path,default=PROJECT_DIRECTORY)
    args=parser.parse_args(argv)
    verify(args.source_root,args.project_directory)
    return 0


if __name__=='__main__':raise SystemExit(main())

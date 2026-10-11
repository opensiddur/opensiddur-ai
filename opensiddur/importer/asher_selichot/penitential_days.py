"""Manifest-driven authoring and reverse verification of later penitential days."""
import copy
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from lxml import etree
from .build import TEI, XML, PRAYER, document, element, pb, marker, choice
from .first_day import poetic_lines, words_with_notes, mixed_words, expansion_scope, append_words, verify_half_kaddish
from .erev_rosh_hashanah import printed as ordinary_printed, targets
from .penitential_second_day import wrap_hebrew

SERVICE_PREFIX = 'urn:x-opensiddur:text:siddur:selichot/penitential_'
DAYS = ('third', 'fourth', 'fifth')
SERVICES = DAYS + ('erev-yom-kippur',)

def manifest_name(day):
    if day not in SERVICES: raise ValueError('Unsupported selichot service: '+day)
    return 'erev-yom-kippur' if day=='erev-yom-kippur' else 'penitential-'+day+'-day'

def service_filename(day):
    return manifest_name(day).replace('-', '_')+'.xml'

def service_urn(day):
    if day=='erev-yom-kippur': return 'urn:x-opensiddur:text:siddur:selichot/erev_yom_kippur'
    if day not in DAYS: raise ValueError('Unsupported penitential day: '+day)
    return SERVICE_PREFIX+day+'_day'
J = 'http://jewishliturgy.org/ns/jlptei/2'


def readings(source,day):
    manifest=json.loads((source/(manifest_name(day)+'.json')).read_text())
    units=[json.loads((source/name).read_text()) for name in manifest['readings']]
    if not manifest['complete'] or units[0]['id']!='opening_instruction' or units[-1]['id']!='conclusion':
        raise ValueError(day+' penitential day boundaries are incomplete')
    for unit in units:
        if unit['kind']=='poem':
            for lang,prefix in [('he','אלהינו ואלהי אבותינו'),('en','Our God, and the God of our fathers')]:
                if unit['fragments'][0][lang]['text'].count(prefix)>1:
                    raise ValueError('Duplicated invocation in '+unit['id'])
    first,last=manifest['requested_leaves']
    for lang,offset in [('he',1),('en',2)]:
        pages=[int(f[lang]['scan'][1:]) for u in units for f in u['fragments'] if f[lang]['text']]
        if pages!=sorted(pages) or set(pages)!=set(range(first+offset,last+offset,2)):
            raise ValueError(day+' penitential day must cover every source page in order')
    return manifest,units


def pizmon(parent, reading, lang, context):
    """Preserve independent printed cues within shared bilingual semantic units."""
    unit=element(parent,'div',corresp=context)
    first=reading['fragments'][0][lang];pb(unit,first['scan'],first['printed_page'])
    if reading.get('heading',{}).get(lang):element(unit,'head',reading['heading'][lang])
    previous=first['scan']
    cue_pattern=reading['refrain_cues'][lang]
    opening_cue=reading.get('opening_cue',{}).get(lang)
    opening_pattern=re.escape(opening_cue)+r'(?=\s*$)' if opening_cue else None
    opening=' '.join(f[lang]['text'] for f in reading['stanzas'][0]['fragments'])
    for number,stanza in enumerate(reading['stanzas'],1):
        fragments=stanza['fragments'];first=fragments[0][lang]
        if first['scan']!=previous:pb(unit,first['scan'],first['printed_page'])
        marker(unit,context+'/stanza_'+str(number))
        block=element(unit,'lg' if lang=='he' else 'p')
        if lang=='he':
            # One call retains an unfinished verse across the printed page break.
            prepared=copy.deepcopy(fragments);cues=[]
            def cue_token(match):
                cues.append((match.group(0),opening if opening_cue and match.group(0)==opening_cue else reading['refrain'][lang]))
                return '__CUE_'+str(len(cues)-1)+'__|'
            for fragment in prepared:
                fragment['he']['text']=re.sub('(?:'+cue_pattern+')'+('|'+opening_pattern if opening_pattern else ''),cue_token,fragment['he']['text'])
            poetic_lines(block,prepared,{'line_stops':'·׃|'})
            for line in block.findall(f'{{{TEI}}}l'):
                if line.text and re.fullmatch(r'__CUE_\d+__\|',line.text):
                    cue,expansion=cues[int(line.text.split('_')[3])];line.text=None
                    choice(element(line,'seg',type='refrain'),cue,expansion)
        else:
            pattern='(?:'+cue_pattern+')'+('|'+opening_pattern if opening_pattern else '')
            for index,fragment in enumerate(fragments):
                data=fragment[lang]
                if index:pb(block,data['scan'],data['printed_page'])
                for piece in re.split('('+pattern+')',data['text']):
                    if not piece:continue
                    if re.fullmatch(pattern,piece):
                        choice(element(block,'seg',type='refrain'),piece,opening if piece==opening_cue else reading['refrain'][lang])
                    else:
                        full_pattern=reading.get('full_refrain_pattern',{}).get(lang)
                        if full_pattern:
                            for part in re.split('('+full_pattern+')',piece):
                                if re.fullmatch(full_pattern,part):element(block,'seg',part,type='refrain')
                                else:words_with_notes(block,part,[n for n in fragment['notes'][lang] if n['anchor'] in part],lang)
                        else:words_with_notes(block,piece,fragment['notes'][lang],lang)
                    append_words(block,' ')
        previous=fragments[-1][lang]['scan']
        if lang=='he':
            for line in block.findall(f'{{{TEI}}}l'):
                if line.text and (line.text.strip()==reading['refrain'][lang] or re.fullmatch(reading.get('full_refrain_pattern',{}).get(lang,'(?!)'),line.text.strip())):
                    words=line.text;line.text=None;element(line,'seg',words,type='refrain')
        block.tail=' '
    element(unit,'milestone',unit='stanza')
    return unit


def printed(parent,reading,lang,context):
    if reading['kind']=='pizmon':return pizmon(parent,reading,lang,context)
    reading=copy.deepcopy(reading)
    if reading['kind']=='poem':reading['line_stops']='·׃'
    unit=ordinary_printed(parent,reading,lang,context)
    if lang=='en':wrap_hebrew(unit)
    return unit


def full_kaddish(parent,day):
    declaration=element(parent,'j:declare');declaration.set(XML+'id','penitential_'+day+'_day_kaddish')
    for typ,name,value in [('asher:selichot','first_day','false'),('opensiddur:holiday-aggregate','aseret-ymei-tshuva','true')]:
        fs=element(declaration,'fs',type=typ);f=element(fs,'f');f.set('name',name);element(f,'binary',value=value)
    element(parent,'j:transclude',target=PRAYER+'kaddish/shalem')
    element(parent,'j:endDeclare',target='#penitential_'+day+'_day_kaddish')


def expanded_rubric(parent,reading,lang,day):
    context=service_urn(day)
    if reading.get('performance_instruction',{}).get(lang):
        role=element(element(parent,'div'),'note',reading['performance_instruction'][lang],type='instruction');role.set(XML+'lang','en')
    if reading['id'].startswith('verses_after_'):
        # As on Erev, the two language lists belong to one paired prose block.
        div=element(parent,'div');element(div,'milestone',unit='prayer',corresp=context+'/'+reading['id']+'/expanded')
        block=element(div,'p')
        for target in targets(reading,lang):element(block,'j:transclude',target=target,type='inline').tail=' '
        element(div,'milestone',unit='prayer')
    else:
        opening=reading['id']=='opening_instruction'
        if opening:
            declaration=element(parent,'j:declare');declaration.set(XML+'id','penitential_'+day+'_day_opening_ten_days')
            fs=element(declaration,'fs',type='opensiddur:holiday-aggregate')
            feature=element(fs,'f');feature.set('name','aseret-ymei-tshuva');element(feature,'binary',value='true')
        for target in targets(reading,lang):
            if reading.get('supply_kaddish') and target==PRAYER+'kaddish/shalem':full_kaddish(parent,day)
            else:element(parent,'j:transclude',target=target)
        if opening:element(parent,'j:endDeclare',target='#penitential_'+day+'_day_opening_ten_days')
        # Preserve any printed apparatus attached to a fulfilled instruction.
        for note in reading['fragments'][0]['notes'][lang]:
            block=element(element(parent,'div'),'p');node=element(block,'note',type='commentary')
            node.set(XML+'lang',note.get('language',lang));node.text=note['text']


def documents(source,day):
    manifest,units=readings(source,day)
    context_urn=service_urn(day)
    for lang in ['he','en']:
        project=f'asher_selichot_{lang}_1912'
        root,text=document(lang,project,manifest['heading'][lang],context_urn)
        service=element(element(text,'body'),'div',corresp=context_urn)
        first=units[0]['fragments'][0][lang];pb(service,first['scan'],first['printed_page'])
        element(service,'head',manifest['heading'][lang])
        for reading in units:
            context=reading.get('urn',context_urn+'/'+reading['id'])
            if reading.get('filename'):
                module,body=document(lang,project,reading['filename'].replace('_',' '),context)
                printed(element(body,'body'),reading,lang,context)
                yield project,reading['filename']+'.xml',module
                element(service,'j:transclude',target=context)
            elif reading['kind']=='rubric' and (targets(reading,lang) or reading.get('refrain_instruction')):
                unit=element(service,'div',corresp=context)
                if reading.get('heading_before',{}).get(lang):element(unit,'head',reading['heading_before'][lang])
                feature='refrains_present' if reading.get('refrain_instruction') else 'prayers_present'
                stem='penitential_'+day+'_day_'+reading['id']
                expansion_scope(unit,stem+'_printed',False,feature=feature)
                printed(unit,reading,lang,context+'/printed');element(unit,'j:endConditional',target='#'+stem+'_printed')
                if not reading.get('refrain_instruction'):
                    expansion_scope(unit,stem+'_expanded',True,feature=feature)
                    expanded_rubric(unit,reading,lang,day);element(unit,'j:endConditional',target='#'+stem+'_expanded')
            else:printed(service,reading,lang,context)
        yield project,service_filename(day),root


def verify_evidence(source,units,day):
    folder=manifest_name(day)
    records=json.loads((source.parent/(folder+'-proofreading.json')).read_text())['readings']
    if [r['id'] for r in records]!=[u['id'] for u in units]:raise ValueError('Stale penitential day proofreading scope')
    for r in records:
        for key,prefix in [('initial_sha256','initial/'),('assembled_sha256','assembled-preocr/'),('working_sha256','')]:
            path=source/folder/(prefix+r['id']+'.json')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=r[key]:raise ValueError('Stale penitential day evidence: '+r['id'])


def verify_readings(source,project_directory,day):
    context_urn=service_urn(day)
    from opensiddur.importer.scan.reverse import streams,check
    normalize=lambda s:' '.join(unicodedata.normalize('NFKD',s).split())
    manifest,units=readings(source,day);verify_evidence(source,units,day)
    for lang in ['he','en']:
        project=project_directory/f'asher_selichot_{lang}_1912'
        service=etree.parse(str(project/(service_filename(day)))).find(f'.//{{{TEI}}}body/{{{TEI}}}div')
        if normalize(service.find(f'{{{TEI}}}head').text)!=normalize(manifest['heading'][lang]):raise ValueError('penitential day heading changed')
        nodes=[n for n in service if n.tag not in [f'{{{TEI}}}head',f'{{{TEI}}}pb']]
        if len(nodes)!=len(units):raise ValueError('penitential day source order changed')
        for reading,node in zip(units,nodes):
            context=reading.get('urn',context_urn+'/'+reading['id'])
            if reading.get('filename'):
                if node.get('target')!=context:raise ValueError('penitential day module order changed')
                node=etree.parse(str(project/(reading['filename']+'.xml'))).find(f'.//{{{TEI}}}body/{{{TEI}}}div')
            elif node.get('corresp')!=context:raise ValueError('penitential day inline order changed')
            node=copy.deepcopy(node)
            scopes=node.findall(f'{{{J}}}conditional')
            if scopes:
                if [s.find(f'{{{TEI}}}fs/{{{TEI}}}f/{{{TEI}}}binary').get('value') for s in scopes]!=(['false'] if reading.get('refrain_instruction') else ['false','true']):raise ValueError('penitential day expansion polarity changed')
                if len(scopes)==2:
                    if [n.get('target') for n in node.findall(f'.//{{{J}}}transclude')]!=targets(reading,lang):raise ValueError('penitential day expansion range changed')
                    if reading.get('supply_kaddish'):
                        declaration=node.find(f'{{{J}}}declare')
                        if [n.get('value') for n in declaration.findall(f'.//{{{TEI}}}binary')]!=['false','true']:raise ValueError('penitential day Kaddish must use Ten Days context')
                    start=scopes[1];end=node.find(f'{{{J}}}endConditional[@target="#{start.get(XML+"id")}"]');children=list(node)
                    for child in children[children.index(start):children.index(end)+1]:node.remove(child)
            notes=node.findall(f'.//{{{TEI}}}note[@type="commentary"]')
            wanted=[n['text'] for f in reading['fragments'] for n in f['notes'][lang]]
            if list(map(normalize,(''.join(n.itertext()) for n in notes)))!=list(map(normalize,wanted)):raise ValueError('penitential day footnote changed: '+reading['id'])
            for n in notes+node.findall(f'{{{TEI}}}head'):
                parent=n.getparent();prev=n.getprevious()
                if prev is None:parent.text=(parent.text or '')+(n.tail or '')
                else:prev.tail=(prev.tail or '')+(n.tail or '')
                parent.remove(n)
            if reading['kind']=='pizmon':
                choices=node.findall(f'.//{{{TEI}}}choice')
                if len(choices)!=reading['choice_counts'][lang]:raise ValueError(day+' penitential day refrain count changed')
                opening=' '.join(f[lang]['text'] for f in reading['stanzas'][0]['fragments'])
                for c in choices:
                    cue=''.join(c.find(f'{{{TEI}}}abbr').itertext())
                    wanted=opening if cue==reading.get('opening_cue',{}).get(lang) else reading['refrain'][lang]
                    if normalize(''.join(c.find(f'{{{TEI}}}expan').itertext()))!=normalize(wanted):raise ValueError('Refrain expansion changed')
                milestones=node.findall(f'{{{TEI}}}milestone[@corresp]')
                if len(milestones)!=len(reading['stanzas']):raise ValueError('Stanza alignment changed')
            mixed_rubric=lang=='he' and reading['kind']=='rubric' and re.search('[A-Za-z]',reading['fragments'][0]['he']['text'])
            if not mixed_rubric:
                for foreign in node.findall(f'.//{{{TEI}}}foreign'):foreign.attrib.pop(XML+'lang',None)
            node.set(XML+'lang',lang)
            expected=defaultdict(list)
            for f in reading['fragments']:
                data=f[lang];words=data['text']
                if mixed_rubric:
                    expected[data['scan'],'he'].append(' '.join(re.findall(r'[\u0590-\u05ff]+',words)))
                    expected[data['scan'],'en'].append(re.sub(r'[\u0590-\u05ff]+','',words).replace(' · ',' '))
                else:expected[data['scan'],lang].append(words)
            if mixed_rubric:
                node.set(XML+'lang','en')
            actual={k:normalize(v) for k,v in streams(node,include_notes=True).items() if v.strip()}
            expected={k:normalize(' '.join(v)) for k,v in expected.items() if normalize(' '.join(v))}
            differences=check(actual,expected)
            if differences:raise ValueError(f'{reading["id"]}: {differences}')
    print(f'{day} penitential day: {len(units)} bilingual units; documentary branches, refrains, notes, source order and expansion ranges checked')


def verify_compiled(tree,day,expected_petitions):
    """Check each supplied petition pair and both seasonal Kaddishes."""
    context=service_urn(day);ns='http://jewishliturgy.org/ns/processing'
    service=tree.find('.//{'+ns+'}transclude[@target="'+context+'"]')
    # A single-day file can be the compiler root rather than a transclusion.
    if service is None:service=tree.getroot() if hasattr(tree,'getroot') else tree
    verify_half_kaddish(service,ten_days=True)
    kaddishes=service.findall('.//{'+ns+'}transclude[@target="'+PRAYER+'kaddish/shalem"]')
    if len(kaddishes)!=1:raise ValueError('Missing or duplicate '+day+' penitential day Full Kaddish')
    words=''.join(''.join(n.itertext())for n in kaddishes[0].findall('.//{'+ns+'}parallelItem[@role="primary"]'))
    letters=''.join(c for c in unicodedata.normalize('NFD',words)if '\u05d0'<=c<='\u05ea')
    if letters.count('לעלאלעלאמןכלברכתא')!=1:raise ValueError('Full Kaddish lost Ten Days reading')
    seen=[]
    for block in service.findall('.//{'+ns+'}parallel'):
        primary=block.find('{'+ns+'}parallelItem[@role="primary"]')
        if primary is None:continue
        marks=[n.get('corresp')for n in primary.findall('.//{'+TEI+'}milestone')if (n.get('corresp')or'').startswith(context+'/verses_after_')and n.get('corresp').endswith('/expanded')]
        if not marks:continue
        parallel=block.find('{'+ns+'}parallelItem[@role="parallel"]')
        if parallel is None:raise ValueError('Missing bilingual petition expansion')
        if marks!=[n.get('corresp')for n in parallel.findall('.//{'+TEI+'}milestone')if n.get('corresp')in marks]:raise ValueError('Unpaired petition expansion')
        words=' '.join(''.join(parallel.itertext()).split())
        if not all(v in words for v in ['Like a father hath compassion','for thy own sake']):raise ValueError('Wrong English petition range')
        seen.extend(marks)
    if len(seen)!=expected_petitions or len(set(seen))!=expected_petitions:raise ValueError('Missing or duplicate penitential petition expansion')
    print(f'Compiled {day} penitential day: {len(seen)} bilingual petition ranges and seasonal Half/Full Kaddish checked')

"""Encode the complete first day from scan-first documentary readings."""
import json
import re
import unicodedata
from lxml import etree
from pathlib import Path
from .build import TEI, XML, PRAYER, POEM, document, element, pb
from .identities import TEXTS, text_urn

FIRST_DAY = 'urn:x-opensiddur:text:siddur:selichot/first_day'
OBSOLETE_ASSEMBLIES = ('first_day_opening', 'first_day_preface',
                       'first_day_before_piyyut', 'first_day_closing', 'first_day_expanded')


def titles(front, readings):
    for lang in ['he', 'en']:
        data = readings[lang]
        pb(front, data['scan'], '[unnumbered]')
        page = element(front, 'titlePage')
        page.set(XML+'lang', lang)
        title = element(page, 'docTitle')
        for i, words in enumerate(data['titles']):
            element(title, 'titlePart', words, type='main' if i == 0 else 'sub')
        element(page, 'docEdition', data['edition'])
        if data.get('byline'):
            element(page, 'byline', data['byline']+' '+data['credentials'])
        imprint = element(page, 'docImprint')
        for tag, key in [('pubPlace','place'),('publisher','publisher'),('pubPlace','address'),('docDate','date')]:
            element(imprint, tag, data[key])


def rubric(parent, parts):
    note = element(parent, 'note', type='instruction')
    note.set(XML+'lang', 'en')
    last = None
    for part in parts:
        if part['lang'] == 'en':
            if last is None:
                note.text = (note.text or '') + part['text']
            else:
                last.tail = (last.tail or '') + part['text']
        else:
            last = element(note, 'foreign', part['text'])
            last.set(XML+'lang', part['lang'])
    return note


def verse(parent, urn, words):
    node = element(parent, 'milestone', unit='verse', corresp=urn)
    node.tail = words+' '


def opening(lang, project, data):
    root, text = document(lang, project, 'First-day Selichot', FIRST_DAY)
    div = element(element(text, 'body'), 'div', corresp=FIRST_DAY)
    pb(div, data['start_scan'], '[unnumbered]')
    element(div, 'head', data['heading'])
    for parts in data['rubrics']:
        rubric(div, parts)
    ashrei = element(div, 'div', corresp=PRAYER+'ashrei')
    p = element(ashrei, 'p')
    for urn, words in zip(['psalms/84/5','psalms/144/15'], data['prelude']):
        verse(p, 'urn:x-opensiddur:text:bible:'+urn, words)
    p = element(ashrei, 'p', corresp=PRAYER+'ashrei/tehila_ledavid')
    for n, words in enumerate(data['psalm'], 1):
        verse(p, f'urn:x-opensiddur:text:bible:psalms/145/{n}', words)
        if n == 1 and data.get('psalm_label'):
            p[-1].tail = ''
            citation = element(p, 'foreign', data['psalm_label'])
            citation.set(XML+'lang','en')
            citation.tail = ' '+words+' '
        if n == 9:
            brk = pb(p, data['next_scan'], data['next_label'])
            brk.tail = data['verse_9_continuation']+' '
    element(ashrei, 'p', data['postlude'], corresp=PRAYER+'ashrei/quoted_115_18')
    for parts in data['kaddish_rubrics']:
        rubric(div, parts)
    p = element(element(div, 'div'), 'p')
    for urn, words in zip(['numbers/14/17','psalms/25/6'], data['kaddish_preface']):
        verse(p, 'urn:x-opensiddur:text:bible:'+urn, words)
    kad = element(div, 'div', corresp=PRAYER+'kaddish/chatzi')
    element(kad, 'p', data['kaddish'][0], corresp=PRAYER+'kaddish/yitgadal')
    p = element(kad, 'p')
    split = unicodedata.normalize('NFKD', 'יִתְבָּרַךְ') if lang == 'he' else 'and may his hallowed'
    words = unicodedata.normalize('NFKD',data['kaddish'][1])
    before, after = words.split(split, 1)
    verse(p, PRAYER+'kaddish/yehe_shmeh', before.rstrip())
    verse(p, PRAYER+'kaddish/yitbarakh', split+after)
    return root


def entry(lang, project, title_data, expanded=False, *, book=False, include_second_day=False, include_third_day=False, additional_days=(), include_erev=False, include_gedaliah=False, include_penitential_second=False):
    urn = ('urn:x-opensiddur:text:siddur:selichot' + ('/expanded' if expanded else '')) if book else FIRST_DAY
    title = 'Asher Selichoth' if book else 'First-day Selichot'
    if expanded:
        title += ' — expanded edition'
    root, text = document(lang, project, title, urn, index=book)
    edition = root.find(f'.//{{{TEI}}}edition')
    edition.text = 'Complete first-day coverage through Archive leaves n51–52, ending before the second-day heading. Hebrew pointing awaits independent proofreading; remaining book sections await encoding.'
    if book and include_second_day:
        edition.text = 'First and second days through Archive leaves n59–60, ending before the third-day heading. Hebrew pointing awaits independent proofreading; remaining days await encoding.'
    if book and include_third_day:
        edition.text = 'First three days through Archive leaves n67–68, ending before the fourth-day heading. Hebrew pointing awaits independent proofreading; remaining days await encoding.'
    if book and additional_days:
        edition.text = 'Complete services through the '+additional_days[-1]+' day. Hebrew pointing awaits independent proofreading; later services await encoding.'
    if include_erev:
        edition.text = 'First seven services and Erev Rosh Hashanah through Archive n183/n184, ending before the Fast of Gedaliah. Hebrew pointing awaits independent proofreading; later services await encoding.'
    if include_gedaliah:
        edition.text = 'Complete services through Tzom Gedaliah, Archive n207/n208 (printed 103). Hebrew pointing awaits independent proofreading; later services await encoding.'
    if include_penitential_second:
        edition.text = 'Complete services through the second penitential day, Archive n231/n232 (printed 115). Hebrew pointing awaits independent proofreading; later services await encoding.'
    if expanded:
        edition.text += ' Repeated passages are supplied by transclusion; the unprinted Full Kaddish uses the secondary edition selected in export settings.'
    if book:
        titles(element(text, 'front'), title_data)
    div = element(element(text, 'body'), 'div', corresp=urn)
    if book:
        element(div, 'j:transclude', target=FIRST_DAY)
        if include_second_day:
            from .second_day import SECOND_DAY
            element(div, 'j:transclude', target=SECOND_DAY)
        if include_third_day:
            from .third_day import THIRD_DAY
            element(div, 'j:transclude', target=THIRD_DAY)
        for day_name in additional_days:
            element(div, 'j:transclude', target='urn:x-opensiddur:text:siddur:selichot/'+day_name+'_day')
        if include_erev:
            from .erev_rosh_hashanah import EREV
            element(div, 'j:transclude', target=EREV)
        if include_gedaliah:
            from .tzom_gedaliah import GEDALIAH
            from opensiddur.importer.util.occasion import gate, holiday
            opening_markup, closing_markup = gate('tzom_gedaliah_occasion', holiday('tzom-gedalia'))
            for markup in [opening_markup, '<j:transclude target="'+GEDALIAH+'"/>', closing_markup]:
                fragment=etree.fromstring(('<wrapper xmlns:tei="'+TEI+'" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">'+markup+'</wrapper>').encode())
                div.extend(fragment)
        if include_penitential_second:
            from .penitential_second_day import PENITENTIAL_SECOND_DAY
            from opensiddur.importer.util.occasion import gate, aggregate
            opening_markup, closing_markup = gate('penitential_second_occasion', aggregate('aseret-ymei-tshuva'))
            for markup in [opening_markup, '<j:transclude target="'+PENITENTIAL_SECOND_DAY+'"/>', closing_markup]:
                fragment=etree.fromstring(('<wrapper xmlns:tei="'+TEI+'" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">'+markup+'</wrapper>').encode())
                div.extend(fragment)
        return root
    return root


def documents(source):
    include_second_day = (source/'second-day.json').exists()
    include_third_day = (source/'third-day.json').exists()
    additional_days = tuple(day for day in ['fourth','fifth','sixth','seventh'] if (source/(day+'-day.json')).exists())
    structure = source.parent/'poetry-structure.json'
    poetry = json.loads(structure.read_text())['units'] if structure.exists() else {}
    title_data = json.loads((source/'title-pages.json').read_text())
    reading = json.loads((source/'first-day-opening.json').read_text())
    continuation = json.loads((source/'first-day-continuation.json').read_text())['sections']
    for lang in ['he','en']:
        project = f'asher_selichot_{lang}_1912'
        yield project, 'index.xml', entry(lang, project, title_data, book=True, include_second_day=include_second_day, include_third_day=include_third_day, additional_days=additional_days, include_erev=(source/'erev-rosh-hashanah.json').exists(), include_gedaliah=(source/'tzom-gedaliah.json').exists(), include_penitential_second=(source/'penitential-second-day.json').exists())
        yield project, 'expanded.xml', entry(lang, project, title_data, expanded=True, book=True, include_second_day=include_second_day, include_third_day=include_third_day, additional_days=additional_days, include_erev=(source/'erev-rosh-hashanah.json').exists(), include_gedaliah=(source/'tzom-gedaliah.json').exists(), include_penitential_second=(source/'penitential-second-day.json').exists())
        service = entry(lang, project, title_data)
        service_div = service.find(f'.//{{{TEI}}}body/{{{TEI}}}div')
        root = opening(lang, project, reading[lang])
        div = root.find(f'.//{{{TEI}}}body/{{{TEI}}}div')
        units = [div.find(f'{{{TEI}}}div[@corresp="{PRAYER}ashrei"]'),
                 next(n for n in div.findall(f'{{{TEI}}}div') if not n.get('corresp')),
                 div.find(f'{{{TEI}}}div[@corresp="{PRAYER}kaddish/chatzi"]')]
        for unit, filename, urn, scan, label in zip(units,
                ['ashrei', 'kaddish_selichot_preface', 'kaddish_chatzi'],
                [PRAYER+'ashrei', PRAYER+'kaddish/selichot_preface', PRAYER+'kaddish/chatzi'],
                [reading[lang]['start_scan'], reading[lang]['next_scan'], reading[lang]['next_scan']],
                ['[unnumbered]', reading[lang]['next_label'], reading[lang]['next_label']]):
            unit.set('corresp', urn)
            position = div.index(unit)
            div.remove(unit)
            transclusion = element(div, 'j:transclude', target=urn)
            div.remove(transclusion); div.insert(position, transclusion)
            page = pb(unit, scan, label); unit.remove(page); unit.insert(0, page)
            module, module_text = document(lang, project, filename.replace('_', ' '), urn)
            element(module_text, 'body').append(unit)
            yield project, filename+'.xml', module
        service_div.extend(list(div))
        for name, groups in continuation.items():
            if name == 'before_piyyut':
                for prayer in ['el_melekh_yoshev', 'vayaavor']:
                    element(service_div, 'j:transclude', target=PRAYER+prayer)
            elif name == 'closing':
                element(service_div, 'j:transclude', target=POEM)
            root = section(lang, project, name, groups, poetry)
            div = root.find(f'.//{{{TEI}}}body/{{{TEI}}}div')
            for unit, group in zip(list(div), groups):
                if group['kind'] == 'rubric':
                    continue
                filename, _ = TEXTS[group['id']]
                urn = text_urn(group['id'])
                position = div.index(unit)
                div.remove(unit)
                transclusion = element(div, 'j:transclude', target=urn)
                div.remove(transclusion); div.insert(position, transclusion)
                module, module_text = document(lang, project, group.get('incipit_he', filename.replace('_', ' ')), urn)
                if group.get('incipit_he'):
                    module.find(f'.//{{{TEI}}}title').set(XML+'lang', 'he')
                element(module_text, 'body').append(unit)
                yield project, filename+'.xml', module
            service_div.extend(list(div))
        yield project, 'first_day.xml', service


EXPANSION_TARGETS = {
    'after_first_selihah_rubric': [text_urn('morning_scriptural_petitions')+'/repeat', text_urn('daniel_petition')+'/repeat'],
    'after_second_selihah_verses': [text_urn('morning_scriptural_petitions')+'/repeat', text_urn('daniel_petition')+'/repeat'],
    'after_second_selihah_prayers': [PRAYER+'el_melekh_yoshev', PRAYER+'vayaavor'],
    'after_third_selihah_prayers': [PRAYER+'el_melekh_yoshev', PRAYER+'vayaavor'],
    'ashamnu_repeat': [PRAYER+'ashamnu'],
    'ashamnu_repeat_2': [PRAYER+'ashamnu'],
    'reader_kaddish': [PRAYER+'kaddish/shalem'],
}


def expansion_scope(parent, identity, present, *, feature='repetitions_present'):
    conditional = element(parent, 'j:conditional')
    conditional.set(XML+'id', identity)
    fs = element(conditional, 'fs', type='asher:expansions')
    f = element(fs, 'f'); f.set('name', feature)
    element(f, 'binary', value='true' if present else 'false')


def append_words(parent, words):
    if len(parent):
        parent[-1].tail = (parent[-1].tail or '') + words
    else:
        parent.text = (parent.text or '') + words


def mixed_words(parent, words):
    """Keep the edition's English rubrics and Hebrew reference cues explicit."""
    for part in re.split(r'([\u0590-\u05ff][\u0590-\u05ff ·\s]*[\u0590-\u05ff])', words):
        if re.search(r'[\u05d0-\u05ea]', part):
            element(parent, 'foreign', part).set(XML+'lang', 'he')
        else:
            append_words(parent, part)


def words_with_notes(parent, words, notes, lang):
    """Place each printed footnote at its recorded anchor, exactly once."""
    rest = words
    for note in notes:
        anchor = unicodedata.normalize('NFKD', note['anchor'])
        if anchor not in rest:
            raise ValueError(f'Footnote anchor absent: {anchor!r}')
        before, rest = rest.split(anchor, 1)
        append_words(parent, before+anchor)
        node = element(parent, 'note', type='commentary')
        if lang == 'he' and re.search('[A-Za-z]',note['text']):
            first, following = note['text'].split('\n',1)
            p = element(node,'p');p.set(XML+'lang','en');mixed_words(p,first)
            element(node,'p',following)
        elif lang == 'en' and re.search(r'[\u05d0-\u05ea]', note['text']):
            node.set(XML+'lang', 'en')
            mixed_words(node, note['text'])
        else:
            node.text = note['text']
    append_words(parent, rest)


def poetic_lines(node, fragments, rule):
    """Keep semantic verse lines across scan boundaries and mark terminal refrains."""
    stops = rule['line_stops']
    line = None
    for i, fragment in enumerate(fragments):
        data = fragment['he']
        if i:
            pb(line if line is not None else node, data['scan'], data['printed_page'])
        remaining_notes = list(fragment['notes']['he'])
        for words in re.findall(r'[^'+re.escape(stops)+r']+['+re.escape(stops)+r'][\]\)]?|[^'+re.escape(stops)+r']+$', data['text']):
            words = words.strip()
            # A phrase dot is printed apart from the word, but must not wrap alone.
            words = re.sub(r' +(?=·$)', '\u00a0', words)
            if not words:
                continue
            if line is None:
                line = element(node, 'l')
                line.tail = ' '
            notes = [note for note in remaining_notes if note['anchor'] in words]
            for note in notes:
                remaining_notes.remove(note)
            refrain = rule.get('refrain')
            match = re.search(re.escape(refrain)+r'\s*['+re.escape(stops)+r']$', words) if refrain else None
            if match:
                words_with_notes(line, words[:match.start()], notes, 'he')
                element(line, 'seg', words[match.start():], type='refrain')
            else:
                words_with_notes(line, words, notes, 'he')
            if words.rstrip('])')[-1] in stops:
                line = None
            elif not data.get('join_next'):
                append_words(line, ' ')
        if remaining_notes:
            raise ValueError('Poetry footnote anchor crosses a verse boundary')


def section(lang, project, name, groups, poetry=None):
    urn = FIRST_DAY+'/'+name
    root, text = document(lang, project, 'First day: '+name.replace('_',' '), urn)
    div = element(element(text,'body'),'div',corresp=urn)
    for group in groups:
        context = text_urn(group['id']) if group['id'] in TEXTS else FIRST_DAY+'/'+group['id']
        unit = element(div,'div',corresp=context)
        first = group['fragments'][0][lang]
        pb(unit,first['scan'],first['printed_page'])
        kind = group['kind']
        poetic_rule = (poetry or {}).get(group['id']) if lang == 'he' else None
        targets = EXPANSION_TARGETS.get(group['id'])
        if targets:
            expansion_scope(unit, group['id']+'_printed', False)
        if kind == 'rubric':
            node = element(unit,'note',type='instruction');node.set(XML+'lang','en')
        elif poetic_rule or (kind == 'poem' and lang == 'he'):
            node = element(unit,'lg')
        else:
            node = element(unit,'p')
        if poetic_rule:
            poetic_lines(node, group['fragments'], poetic_rule)
        for i, fragment in enumerate([] if poetic_rule else group['fragments']):
            data = fragment[lang]
            if i:
                pb(node,data['scan'],data['printed_page'])
            words = data['text']
            if kind == 'rubric' and lang == 'he':
                mixed_words(node,words)
            elif kind == 'poem' and lang == 'he':
                # The printed invocation is an introductory verse, not a heading.
                if i == 0 and words.startswith('אלהינו ואלהי אבותינו\n'):
                    invocation, words = words.split('\n', 1)
                    element(node, 'l', invocation)
                # Printed verse stops delimit verses; middle dots remain phrase stops.
                for line in re.findall(r'[^׃]+׃|[^׃]+$',words):
                    element(node,'l',line.strip())
            elif kind == 'litany':
                for n,line in enumerate(words.splitlines(),1):
                    if n>1:element(node,'lb')
                    words_with_notes(node,line,fragment['notes'][lang] if n==8 else [],lang)
                    append_words(node,' ')
            else:
                if i == 0 and group.get('repeat_start'):
                    if fragment['notes'][lang]:
                        raise ValueError('Repeat boundary needs explicit footnote placement')
                    before, after = words.split(group['repeat_start'][lang], 1)
                    append_words(node, before)
                    milestone = element(node, 'milestone', unit='repeat-range', corresp=context+'/repeat')
                    milestone.tail = group['repeat_start'][lang]+after
                else:
                    words_with_notes(node,words,fragment['notes'][lang],lang)
            if not data.get('join_next'):
                append_words(node,' ')
        if group.get('repeat_start'):
            element(node, 'milestone', unit='repeat-range')
        if targets:
            element(unit, 'j:endConditional', target='#'+group['id']+'_printed')
            expansion_scope(unit, group['id']+'_expanded', True)
            if group['id'] == 'reader_kaddish':
                declaration = element(unit, 'j:declare')
                declaration.set(XML+'id', 'first_day_selichot_kaddish')
                fs = element(declaration, 'fs', type='asher:selichot')
                f = element(fs, 'f'); f.set('name', 'first_day')
                element(f, 'binary', value='true')
                fs = element(declaration, 'fs', type='opensiddur:holiday-aggregate')
                f = element(fs, 'f'); f.set('name', 'aseret-ymei-tshuva')
                element(f, 'binary', value='false')
            for target in targets:
                element(unit, 'j:transclude', target=target)
            if group['id'] == 'reader_kaddish':
                element(unit, 'j:endDeclare', target='#first_day_selichot_kaddish')
            element(unit, 'j:endConditional', target='#'+group['id']+'_expanded')
    return root

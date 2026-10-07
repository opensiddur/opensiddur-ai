"""Encode the complete first day from scan-first documentary readings."""
import json
import re
import unicodedata
from pathlib import Path
from .build import TEI, XML, PRAYER, POEM, document, element, pb

FIRST_DAY = 'urn:x-opensiddur:text:siddur:selichot/first_day'
OPENING = FIRST_DAY + '/opening'


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
    root, text = document(lang, project, 'First-day opening: Ashrei and Half Kaddish', OPENING)
    div = element(element(text, 'body'), 'div', corresp=OPENING)
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


def entry(lang, project, title_data, expanded=False):
    root, text = document(lang, project, 'Asher Selichoth — first day (work in progress)', FIRST_DAY+('/expanded' if expanded else ''), index=True)
    edition = root.find(f'.//{{{TEI}}}edition')
    edition.text = 'Complete first-day coverage through Archive leaves n51–52, ending before the second-day heading. Hebrew pointing awaits independent proofreading; the remainder of the book is outside this edition.'
    if expanded:
        root.find(f'.//{{{TEI}}}title').text = 'Asher Selichoth — expanded first day (work in progress)'
        edition.text += ' Repeated passages are supplied by transclusion; the unprinted Full Kaddish uses the secondary edition selected in export settings.'
    titles(element(text, 'front'), title_data)
    div = element(element(text, 'body'), 'div')
    for target in ENTRY_TARGETS:
        element(div, 'j:transclude', target=target)
        if expanded and target == POEM:
            for prayer in ('el_melekh_yoshev', 'vayaavor'):
                element(div, 'j:transclude', target=PRAYER+prayer)
    return root


def documents(source):
    title_data = json.loads((source/'title-pages.json').read_text())
    reading = json.loads((source/'first-day-opening.json').read_text())
    continuation = json.loads((source/'first-day-continuation.json').read_text())['sections']
    for lang in ['he','en']:
        project = f'asher_selichot_{lang}_1912'
        yield project, 'first_day.xml', entry(lang, project, title_data)
        yield project, 'first_day_expanded.xml', entry(lang, project, title_data, expanded=True)
        yield project, 'first_day_opening.xml', opening(lang, project, reading[lang])
        for name, groups in continuation.items():
            yield project, f'first_day_{name}.xml', section(lang, project, name, groups)


ENTRY_TARGETS = [OPENING, FIRST_DAY+'/preface', PRAYER+'el_melekh_yoshev',
                 PRAYER+'vayaavor', FIRST_DAY+'/before_piyyut', POEM, FIRST_DAY+'/closing']
MODULE_ORDER = ['first_day_opening', 'first_day_preface', 'el_melekh_yoshev',
                'vayaavor', 'first_day_before_piyyut', 'bemotzaei_menuhah', 'first_day_closing']


EXPANSION_TARGETS = {
    'after_first_selihah_rubric': [FIRST_DAY+'/morning_scriptural_petitions/repeat', FIRST_DAY+'/daniel_petition/repeat'],
    'after_second_selihah_verses': [FIRST_DAY+'/morning_scriptural_petitions/repeat', FIRST_DAY+'/daniel_petition/repeat'],
    'after_second_selihah_prayers': [PRAYER+'el_melekh_yoshev', PRAYER+'vayaavor'],
    'after_third_selihah_prayers': [PRAYER+'el_melekh_yoshev', PRAYER+'vayaavor'],
    'ashamnu_repeat': [FIRST_DAY+'/ashamnu'],
    'ashamnu_repeat_2': [FIRST_DAY+'/ashamnu'],
    'reader_kaddish': [PRAYER+'kaddish/shalem'],
}


def expansion_scope(parent, identity, present):
    conditional = element(parent, 'j:conditional')
    conditional.set(XML+'id', identity)
    fs = element(conditional, 'fs', type='asher:expansions')
    f = element(fs, 'f'); f.set('name', 'repetitions_present')
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
        else:
            node.text = note['text']
    append_words(parent, rest)


def section(lang, project, name, groups):
    urn = FIRST_DAY+'/'+name
    root, text = document(lang, project, 'First day: '+name.replace('_',' '), urn)
    div = element(element(text,'body'),'div',corresp=urn)
    for group in groups:
        context = FIRST_DAY+'/'+group['id']
        unit = element(div,'div',corresp=context)
        first = group['fragments'][0][lang]
        pb(unit,first['scan'],first['printed_page'])
        kind = group['kind']
        targets = EXPANSION_TARGETS.get(group['id'])
        if targets:
            expansion_scope(unit, group['id']+'_printed', False)
        if kind == 'rubric':
            node = element(unit,'note',type='instruction');node.set(XML+'lang','en')
        elif kind == 'poem' and lang == 'he':
            node = element(unit,'lg')
        else:
            node = element(unit,'p')
        for i, fragment in enumerate(group['fragments']):
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
            for target in targets:
                element(unit, 'j:transclude', target=target)
            element(unit, 'j:endConditional', target='#'+group['id']+'_expanded')
    return root

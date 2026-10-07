"""Begin a contiguous first-day edition from committed, scan-first readings.

The entrypoint contains only the opening so far. The final first-day boundary
is recorded separately; isolated pilot passages do not fill the intervening gap.
"""
import json
import unicodedata
from pathlib import Path
from .build import TEI, XML, PRAYER, document, element, pb

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


def entry(lang, project, title_data):
    root, text = document(lang, project, 'Asher Selichoth — first-day opening (work in progress)', FIRST_DAY, index=True)
    edition = root.find(f'.//{{{TEI}}}edition')
    edition.text = 'Work in progress: title pages and opening through Half Kaddish only. The remaining first-day text through Archive leaf n52 is pending.'
    titles(element(text, 'front'), title_data)
    div = element(element(text, 'body'), 'div')
    element(div, 'j:transclude', target=OPENING)
    return root


def documents(source):
    title_data = json.loads((source/'title-pages.json').read_text())
    reading = json.loads((source/'first-day-opening.json').read_text())
    for lang in ['he','en']:
        project = f'asher_selichot_{lang}_1912'
        yield project, 'first_day.xml', entry(lang, project, title_data)
        yield project, 'first_day_opening.xml', opening(lang, project, reading[lang])

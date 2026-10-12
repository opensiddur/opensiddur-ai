"""Exercise authoring algorithms with invented text, never edition readings."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unicodedata
import unittest
from unittest.mock import Mock

from lxml import etree
from opensiddur.importer.scan import authoring as a


class AuthoringTests(unittest.TestCase):
    def parent(self):
        return etree.Element(f'{{{a.TEI}}}div')

    def test_namespaces_choice_milestone_and_boolean_scope(self):
        p = self.parent()
        a.marker(p, 'urn:test:verse')
        self.assertEqual(p[0].get('unit'), 'stanza')
        self.assertEqual(p[0].get('corresp'), 'urn:test:verse')
        choice = a.choice(p, 'short', 'complete phrase')
        self.assertEqual([n.text for n in choice], ['short', 'complete phrase'])
        for present in [False, True]:
            scope = a.conditional_scope(p, 'sample', present, fs_type='test:edition', feature='supplied')
            self.assertEqual(scope.tag, f'{{{a.J}}}conditional')
            self.assertEqual(scope.get(a.XML+'id'), 'sample')
            self.assertEqual(scope[0].get('type'), 'test:edition')
            self.assertEqual(scope[0][0].get('name'), 'supplied')
            self.assertEqual(scope[0][0][0].get('value'), str(present).lower())

    def test_append_preserves_existing_text_children_and_tails(self):
        p = self.parent()
        a.append_words(p, 'before ')
        a.append_words(p, 'again ')
        child = a.element(p, 'hi', 'word')
        a.append_words(p, ' after')
        a.append_words(p, ' end')
        self.assertEqual(p.text, 'before again ')
        self.assertEqual(child.tail, ' after end')
        self.assertEqual(''.join(p.itertext()), 'before again word after end')

    def test_emphasis_keeps_order_and_all_words(self):
        p = self.parent(); p.text = 'One alpha, two beta, three.'
        a.italicize(p, ['beta', 'alpha'])
        self.assertEqual(''.join(p.itertext()), 'One alpha, two beta, three.')
        self.assertEqual([n.text for n in p], ['alpha', 'beta'])
        self.assertTrue(all(n.get('rend') == 'italic' for n in p))
        empty = self.parent(); a.italicize(empty, [])
        self.assertIsNone(empty.text)
        with self.assertRaisesRegex(ValueError, 'Missing printed emphasis'):
            a.italicize(p, ['missing'])

    def test_normalization_retains_binding_spaces_and_sof_pasuq(self):
        p = self.parent(); p.text = 'שָׁם · בָּא\u00a0· סוף׃'
        result = etree.fromstring(a.normalized_xml(p).encode()).text
        self.assertEqual(result, unicodedata.normalize('NFKD', 'שָׁם')+'\u00a0· '+
                         unicodedata.normalize('NFKD', 'בָּא')+'\u00a0· סוף׃')

    def test_mixed_languages_preserve_punctuation_and_words(self):
        p = self.parent(); words = 'Before אֶחָד · שְׁנַיִם, after.'
        a.mixed_words(p, words)
        self.assertEqual(''.join(p.itertext()), words)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].get(a.XML+'lang'), 'he')
        self.assertEqual(p[0].tail, ', after.')
        pure = self.parent(); a.mixed_words(pure, 'English only.')
        self.assertEqual(pure.text, 'English only.')

    def test_notes_follow_sequential_anchors_once(self):
        p = self.parent()
        a.words_with_notes(p, 'echo and echo end', [
            {'anchor':'echo', 'text':'first note'},
            {'anchor':'echo', 'text':'second note'}], 'en')
        self.assertEqual(p.text, 'echo')
        self.assertEqual([n.text for n in p], ['first note', 'second note'])
        self.assertEqual([n.tail for n in p], [' and echo', ' end'])
        with self.assertRaisesRegex(ValueError, 'Footnote anchor absent'):
            a.words_with_notes(self.parent(), 'body', [{'anchor':'absent','text':'note'}], 'en')

    def test_mixed_language_notes_use_correct_scopes(self):
        p = self.parent()
        a.words_with_notes(p, 'אב׃', [{'anchor':'אב','text':'Say גד now\nהו׃'}], 'he')
        note = p[0]
        self.assertEqual(note[0].get(a.XML+'lang'), 'en')
        self.assertEqual(note[0][0].get(a.XML+'lang'), 'he')
        self.assertEqual(note[1].text, 'הו׃')
        self.assertEqual(note.tail, '׃')
        english = self.parent()
        a.words_with_notes(english, 'word.', [{'anchor':'word','text':'See אב.'}], 'en')
        self.assertEqual(english[0].get(a.XML+'lang'), 'en')
        self.assertEqual(english[0][0].get(a.XML+'lang'), 'he')
        plain = self.parent()
        a.words_with_notes(plain, 'אב', [{'anchor':'אב','text':'גד'}], 'he')
        self.assertEqual(plain[0].text, 'גד')

    def test_language_wrapping_preserves_tree_and_is_idempotent(self):
        p = self.parent(); p.text = 'Start אב '
        hi = a.element(p, 'hi', 'inside גד'); hi.tail = ' end הו.'
        hebrew = a.element(p, 'p', 'זח'); hebrew.set(a.XML+'lang', 'he')
        foreign = a.element(p, 'foreign', 'טי'); foreign.set(a.XML+'lang', 'he')
        before = ''.join(p.itertext())
        a.wrap_hebrew(p)
        self.assertEqual(''.join(p.itertext()), before)
        self.assertIs(hi.getparent(), p)
        self.assertEqual(hebrew.text, 'זח')
        self.assertEqual(len(hebrew), 0)
        self.assertEqual(len(foreign), 0)
        frozen = etree.tostring(p)
        a.wrap_hebrew(p)
        self.assertEqual(etree.tostring(p), frozen)

    def fragment(self, text, *, scan='s2', notes=(), join_next=False):
        return {'he':{'text':text,'scan':scan,'printed_page':'x','join_next':join_next},
                'notes':{'he':list(notes)}}

    def test_poetry_keeps_continuing_verse_pagebreak_and_terminal_refrain(self):
        group = self.parent()
        fragments = [self.fragment('אב',join_next=True),
                     self.fragment('גד הו׃ זח ·',scan='s4')]
        def page_break(parent, scan, label):
            return a.element(parent, 'pb', n=label, facs=scan)
        a.poetic_lines(group, fragments, {'line_stops':'׃·','refrain':'הו'}, page_break=page_break)
        self.assertEqual(len(group), 2)
        self.assertEqual(''.join(group[0].itertext()), 'אבגד הו׃')
        self.assertEqual(group[0][0].tag, f'{{{a.TEI}}}pb')
        self.assertEqual(group[0][0].get('facs'), 's4')
        self.assertEqual(group[0][-1].get('type'), 'refrain')
        self.assertEqual(group[1].text, 'זח\u00a0·')
        unit = self.parent(); unit.tag = f'{{{a.TEI}}}div'; group.tag = f'{{{a.TEI}}}lg';unit.append(group)
        a.check_poetry(unit, {'line_count':2,'refrain_count':1,'refrain':'הו'})

    def test_poetry_spaces_closed_lines_and_note_boundaries(self):
        group = self.parent(); callback = Mock()
        a.poetic_lines(group, [self.fragment('אב'),self.fragment(' גד׃)',scan='s4')],
                       {'line_stops':'׃'}, page_break=callback)
        self.assertEqual(''.join(group[0].itertext()), 'אב גד׃)')
        callback.assert_called_once_with(group[0], 's4', 'x')
        closed = self.parent(); callback.reset_mock()
        a.poetic_lines(closed,[self.fragment('אב׃'),self.fragment('גד׃',scan='s4')],
                       {'line_stops':'׃'},page_break=callback)
        callback.assert_called_once_with(closed,'s4','x')
        noted = self.parent()
        a.poetic_lines(noted,[self.fragment('אב׃',notes=[{'anchor':'אב','text':'גד'}])],
                       {'line_stops':'׃'},page_break=callback)
        self.assertEqual(noted[0][0].text, 'גד')
        with self.assertRaisesRegex(ValueError, 'anchor crosses'):
            a.poetic_lines(self.parent(),[self.fragment('אב׃ גד׃',notes=[{'anchor':'אב׃ גד','text':'note'}])],
                           {'line_stops':'׃'},page_break=callback)
        whitespace = self.parent()
        a.poetic_lines(whitespace,[self.fragment('   ')],{'line_stops':'׃'},page_break=callback)
        self.assertEqual(len(whitespace),0)

    def test_structure_audit_rejects_prose_wrong_counts_and_nonterminal_refrains(self):
        unit = self.parent(); lg = a.element(unit,'lg'); line = a.element(lg,'l','אב ')
        refrain = a.element(line,'seg','גד׃',type='refrain')
        rule = {'line_count':1,'refrain_count':1,'refrain':'גד'}
        a.check_poetry(unit,rule)
        for variant in ['prose','line_count','refrain_count','wording','parent','following','tail']:
            with self.subTest(variant=variant):
                broken = copy.deepcopy(unit); r = broken.find(f'.//{{{a.TEI}}}seg'); expected = dict(rule)
                if variant=='prose':a.element(broken,'p','אב גד׃')
                elif variant=='line_count':expected['line_count']=2
                elif variant=='refrain_count':expected['refrain_count']=0
                elif variant=='wording':r.text='הו׃'
                elif variant=='parent':r.getparent().remove(r);broken.append(r)
                elif variant=='following':a.element(r.getparent(),'seg','extra')
                else:r.tail='extra'
                with self.assertRaises(ValueError):a.check_poetry(broken,expected)

    def test_failed_validation_leaves_existing_files_and_obsolete_paths_untouched(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); existing = root/'existing.xml'; existing.write_text('old')
            obsolete = root/'obsolete.xml'; obsolete.write_text('keep')
            validator = Mock(side_effect=[(True,[]),(False,['invalid shape'])])
            with self.assertRaisesRegex(ValueError,'invalid shape'):
                a.write_documents([(existing,self.parent()),(root/'new.xml',self.parent())],
                                  validator=validator,obsolete_paths=[obsolete])
            self.assertEqual(existing.read_text(),'old')
            self.assertFalse((root/'new.xml').exists())
            self.assertTrue(obsolete.exists())

    def test_writes_validated_set_and_removes_only_explicit_obsolete_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp); obsolete = root/'old.xml';obsolete.write_text('old')
            keep = root/'keep.xml';keep.write_text('keep')
            target = root/'nested/new.xml'; validator=Mock(return_value=(True,[]))
            result=a.write_documents([(target,self.parent())],validator=validator,
                                     obsolete_paths=[obsolete,root/'missing.xml'])
            self.assertEqual(result,[target]);validator.assert_called_once()
            self.assertEqual(target.read_text(),validator.call_args.args[0])
            self.assertFalse(obsolete.exists());self.assertTrue(keep.exists())

"""The electronic book's pre-pass: numbering undecided scopes and labelling what they govern."""

import unittest

from lxml import etree

from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE, TEI_NS
from opensiddur.exporter.html.markers import P_CID, P_SCOPES, P_SPAN, prepare

J = JLPTEI_NAMESPACE
P = PROCESSING_NAMESPACE


def _tree(body: str) -> etree.ElementBase:
    return etree.fromstring(
        f'<tei:body xmlns:tei="{TEI_NS}" xmlns:j="{J}" xmlns:p="{P}">{body}</tei:body>')


def _cond(xml_id: str, fs: str = "t:x", name: str | None = None, rubric: str = "",
          pinned: str = "") -> str:
    note = f'<tei:note type="instruction">{rubric}</tei:note>' if rubric else ""
    pin = f"<p:pinned>{pinned}</p:pinned>" if pinned else ""
    return (f'<j:conditional xml:id="{xml_id}">{note}<tei:fs type="{fs}">'
            f'<tei:f name="{name or xml_id}"><tei:binary value="true"/></tei:f></tei:fs>{pin}'
            f'</j:conditional>')


def _end(xml_id: str) -> str:
    return f'<j:endConditional target="#{xml_id}"/>'


def _labels(root) -> list[tuple[str, str]]:
    """(words, scopes) for every labelled element or span, in document order."""
    return [(" ".join("".join(el.itertext()).split()), el.get(P_SCOPES))
            for el in root.iter() if el.get(P_SCOPES) is not None]


class TestNumbering(unittest.TestCase):

    def test_scopes_are_numbered_in_order_on_both_markers(self):
        root = _tree(_cond("a") + "<tei:p>x</tei:p>" + _end("a")
                     + _cond("b") + "<tei:p>y</tei:p>" + _end("b"))
        prepare(root)
        self.assertEqual(
            [(etree.QName(el).localname, el.get(P_CID)) for el in root.iter(
                f"{{{J}}}conditional", f"{{{J}}}endConditional")],
            [("conditional", "0"), ("endConditional", "0"),
             ("conditional", "1"), ("endConditional", "1")])

    def test_identical_conditions_share_an_expression(self):
        root = _tree(_cond("a", name="same") + "<tei:p>x</tei:p>" + _end("a")
                     + _cond("b", name="same") + "<tei:p>y</tei:p>" + _end("b")
                     + _cond("c", name="other") + "<tei:p>z</tei:p>" + _end("c"))
        book = prepare(root)
        self.assertEqual(book.scopes, [0, 0, 1])
        self.assertEqual(len(book.expressions), 2)

    def test_pinned_values_move_into_the_expression(self):
        root = _tree(_cond("a", pinned='{"t:y": {"q": true}}') + "<tei:p>x</tei:p>" + _end("a"))
        book = prepare(root)
        self.assertEqual(book.expressions[0]["pinned"], {"t:y": {"q": True}})
        self.assertIsNone(root.find(f".//{{{P}}}pinned"))

    def test_unpaired_markers_govern_nothing(self):
        root = _tree(_cond("a") + "<tei:p>x</tei:p>")
        with self.assertLogs("opensiddur.exporter.html.markers", level="WARNING"):
            book = prepare(root)
        self.assertEqual(book.scopes, [])
        self.assertIsNone(root.find(f".//{{{J}}}conditional").get(P_CID))
        self.assertEqual(_labels(root), [])


class TestLabels(unittest.TestCase):

    def test_whole_elements_carry_the_label(self):
        root = _tree(_cond("a") + "<tei:p>x</tei:p><tei:p>y</tei:p>" + _end("a")
                     + "<tei:p>z</tei:p>")
        prepare(root)
        self.assertEqual(_labels(root), [("x", "0"), ("y", "0")])

    def test_descendants_do_not_repeat_their_ancestors_label(self):
        root = _tree(_cond("a") + "<tei:div><tei:p>x <tei:hi>y</tei:hi></tei:p></tei:div>"
                     + _end("a"))
        prepare(root)
        self.assertEqual(_labels(root), [("x y", "0")])

    def test_text_within_a_paragraph_is_wrapped(self):
        root = _tree("<tei:p>before " + _cond("a") + "inside" + _end("a") + " after</tei:p>")
        prepare(root)
        self.assertEqual(_labels(root), [("inside", "0")])
        span = root.find(".//" + P_SPAN)
        self.assertEqual(span.getprevious().tag, f"{{{J}}}conditional")

    def test_crossing_scopes(self):
        root = _tree("<tei:p>" + _cond("a") + "one " + _cond("b") + "two " + _end("a")
                     + "three" + _end("b") + "</tei:p>")
        prepare(root)
        self.assertEqual(
            [label for label in _labels(root) if label[0]],
            [("one", "0"), ("two", "0 1"), ("three", "1")])

    def test_a_marker_inside_a_scope_is_governed_by_it(self):
        """A nested scope's rubric goes with the scope around it."""
        root = _tree(_cond("a") + "<tei:p>x</tei:p>" + _cond("b", rubric="Say:")
                     + "<tei:p>y</tei:p>" + _end("b") + _end("a"))
        prepare(root)
        markers = [(etree.QName(el).localname, el.get(P_CID), el.get(P_SCOPES))
                   for el in root.iter(f"{{{J}}}conditional", f"{{{J}}}endConditional")]
        self.assertEqual(markers, [
            ("conditional", "0", None), ("conditional", "1", "0"),
            ("endConditional", "1", "0"), ("endConditional", "0", None)])
        self.assertIn(("y", "0 1"), _labels(root))

    def test_a_scope_closing_inside_an_element(self):
        """The element's leading text is wrapped, and its children still walked."""
        root = _tree(_cond("a") + "<tei:p>x" + _end("a") + "y</tei:p>")
        prepare(root)
        self.assertEqual(_labels(root), [("x", "0")])

    def test_a_paragraph_scope_running_across_rows(self):
        root = _tree(
            '<p:parallel><p:parallelItem role="primary"><tei:p>a ' + _cond("a") + 'b</tei:p>'
            '</p:parallelItem><p:parallelItem role="parallel"><tei:p>e</tei:p></p:parallelItem>'
            '</p:parallel><p:parallel><p:parallelItem role="primary"><tei:p>c' + _end("a")
            + ' d</tei:p></p:parallelItem><p:parallelItem role="parallel"><tei:p>f</tei:p>'
            '</p:parallelItem></p:parallel>')
        prepare(root)
        self.assertEqual([label for label in _labels(root) if label[0]], [("b", "0"), ("c", "0")])

    def test_whitespace_is_not_wrapped(self):
        root = _tree(_cond("a") + "\n   <tei:p>x</tei:p>\n   " + _end("a"))
        prepare(root)
        self.assertIsNone(root.find(".//" + P_SPAN))


class TestColumns(unittest.TestCase):

    @staticmethod
    def _row(primary: str, parallel: str) -> str:
        return (f'<p:parallel><p:parallelItem role="primary">{primary}</p:parallelItem>'
                f'<p:parallelItem role="parallel">{parallel}</p:parallelItem></p:parallel>')

    def test_a_column_scope_runs_down_its_own_column(self):
        root = _tree(
            self._row(_cond("a") + "<tei:p>h1</tei:p>", "<tei:p>e1</tei:p>")
            + self._row("<tei:p>h2</tei:p>", "<tei:p>e2</tei:p>")
            + self._row("<tei:p>h3</tei:p>" + _end("a"), "<tei:p>e3</tei:p>"))
        prepare(root)
        labelled = dict(_labels(root))
        self.assertEqual(labelled.get("h1"), "0")
        self.assertEqual(labelled.get("h2"), "0")
        self.assertEqual(labelled.get("h3"), "0")
        self.assertNotIn("e1", labelled)
        self.assertNotIn("e2", labelled)
        self.assertNotIn("e3", labelled)

    def test_a_scope_outside_the_columns_governs_both(self):
        root = _tree(_cond("a") + self._row("<tei:p>h</tei:p>", "<tei:p>e</tei:p>") + _end("a"))
        prepare(root)
        self.assertEqual(_labels(root), [("he", "0")])


class TestSilence(unittest.TestCase):
    """A scope that governs only where a reading division begins is shown by its label."""

    ALIYAH = '<tei:milestone unit="aliyah.triennial.1" n="first"/>'

    def _silent(self, body: str) -> list[str | None]:
        root = _tree(body)
        prepare(root)
        return [el.get(f"{{{P}}}silent")
                for el in root.iter(f"{{{J}}}conditional", f"{{{J}}}endConditional")]

    def test_a_label_alone_is_silent(self):
        self.assertEqual(self._silent(_cond("a") + self.ALIYAH + _end("a")), ["true", "true"])

    def test_the_label_is_still_governed(self):
        root = _tree(_cond("a") + self.ALIYAH + _end("a"))
        prepare(root)
        self.assertEqual(root.find(f"{{{TEI_NS}}}milestone").get(P_SCOPES), "0")

    def test_text_is_not_silent(self):
        self.assertEqual(self._silent(_cond("a") + self.ALIYAH + "<tei:p>x</tei:p>" + _end("a")),
                         [None, None])

    def test_a_rubric_is_not_silent(self):
        self.assertEqual(self._silent(_cond("a", rubric="Say:") + self.ALIYAH + _end("a")),
                         [None, None])

    def test_other_milestones_are_not_silent(self):
        self.assertEqual(
            self._silent(_cond("a") + '<tei:milestone unit="verse" n="1"/>' + _end("a")),
            [None, None])


class TestFeatures(unittest.TestCase):

    def test_reader_features_with_their_values_and_reach(self):
        root = _tree(
            _cond("a", fs="opensiddur:quorum", name="minyan") + "<tei:p>x</tei:p>" + _end("a")
            + _cond("b", fs="opensiddur:quorum", name="minyan") + "<tei:p>y</tei:p>" + _end("b")
            + '<j:conditional xml:id="c"><tei:fs type="opensiddur:rite"><tei:f name="rite">'
              '<tei:vAlt><tei:symbol value="ashkenaz"/><tei:symbol value="sefard"/></tei:vAlt>'
              '</tei:f></tei:fs></j:conditional><tei:p>z</tei:p>' + _end("c"))
        book = prepare(root)
        self.assertEqual(
            [(f.fs, f.name, f.values, f.scopes) for f in book.features],
            [("opensiddur:quorum", "minyan", [True], 2),
             ("opensiddur:rite", "rite", ["ashkenaz", "sefard"], 1)])

    def test_a_feature_compared_only_with_undefined_is_not_offered(self):
        root = _tree('<j:conditional xml:id="a"><tei:fs type="opensiddur:quorum">'
                     '<tei:f name="minyan"><tei:default/></tei:f></tei:fs></j:conditional>'
                     '<tei:p>x</tei:p>' + _end("a"))
        self.assertEqual(prepare(root).features, [])

    def test_calendar_and_pinned_features_are_not_the_readers(self):
        root = _tree(
            _cond("a", fs="opensiddur:holiday", name="purim") + "<tei:p>x</tei:p>" + _end("a")
            + _cond("b", fs="opensiddur:quorum", name="minyan",
                    pinned='{"opensiddur:quorum": {"minyan": false}}')
            + "<tei:p>y</tei:p>" + _end("b"))
        self.assertEqual(prepare(root).features, [])


if __name__ == "__main__":
    unittest.main()

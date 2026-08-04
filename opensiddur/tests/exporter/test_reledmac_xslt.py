"""Tests for the reledmac/reledpar XSLT (`opensiddur/exporter/tex/reledmac.xslt`).

These tests live one level above the LaTeX engine: they call the XSLT
transformation directly and assert structural properties of the emitted
``.tex`` text. The actual ``lualatex`` invocation is mocked everywhere it
might be triggered, since CI doesn't have a TeXLive install.

Two invariants are critical for reledpar to align verses across page
breaks:

1. Both streams of a ``p:parallel`` block must emit the **same number of**
   ``\\pstart`` (and ``\\pend``) markers, in document order.
2. Each ``tei:milestone[@unit='verse']`` must produce a fresh ``\\pstart``
   so reledpar can pair the Nth verse on each side.

Editorial/instructional notes must come out as well-formed
``\\edtext{...}{...}`` constructs so reledmac places them in the apparatus,
not as floating ``\\footnote``s.
"""

import re
import unittest
from pathlib import Path

from lxml import etree

from opensiddur.common.xslt import xslt_transform_string
from opensiddur.exporter.tex.latex import XSLT_FILE
from opensiddur.exporter.marker_reconstruct import reconstruct_markered_document


def _transform(xml: str, **params) -> str:
    """Transform ``xml`` with the reledmac XSLT, supplying empty defaults
    for the preamble/postamble parameters that the XSLT expects."""
    full_params = {
        "additional-preamble": "",
        "additional-postamble": "",
    }
    full_params.update(params)
    return xslt_transform_string(XSLT_FILE, xml, xslt_params=full_params)


class TestPreamble(unittest.TestCase):
    """The LuaLaTeX preamble must declare the engine, polyglossia, and
    reledmac (plus reledpar when there's any parallel block)."""

    def test_preamble_loads_reledmac_and_polyglossia(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\documentclass", out)
        self.assertIn(r"\usepackage{polyglossia}", out)
        self.assertIn(r"\usepackage{reledmac}", out)
        self.assertIn(r"\Xnonumber[B]", out)
        self.assertIn(r"\newcommand{\OSInterlinearNotemark}", out)
        # No parallel content → no reledpar package.
        self.assertNotIn(r"\usepackage{reledpar}", out)
        self.assertIn(r"\setotherlanguage{hebrew}", out)

    def test_preamble_loads_reledpar_when_parallel(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p>שלום</tei:p></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p>Hello</tei:p></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\usepackage{reledpar}", out)

    def test_preamble_honors_typography_parameters(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(
            xml,
            **{
                "hebrew-font": "Ezra SIL",
                "latin-font": "TeX Gyre Pagella",
                "paper": "letterpaper",
                "fontsize": "12pt",
            },
        )
        self.assertIn(r"\documentclass[12pt,letterpaper]{book}", out)
        self.assertIn("Ezra SIL", out)
        self.assertIn("TeX Gyre Pagella", out)


class TestSingleStreamMapping(unittest.TestCase):
    """Single-language documents (no p:parallel) must still produce a valid
    \\beginnumbering...\\endnumbering block. When there is no parallel alignment
    requirement, verses should flow inline (paragraph-like), not one line per verse."""

    XML = """<?xml version="1.0" encoding="UTF-8"?>
    <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
             xml:lang="en">
      <tei:text><tei:body>
        <tei:p>
          <tei:milestone unit="chapter" n="1"/>
          <tei:milestone unit="verse" n="1"/>In the beginning.
          <tei:milestone unit="verse" n="2"/>And the earth.
          <tei:milestone unit="verse" n="3"/>Let there be light.
        </tei:p>
      </tei:body></tei:text>
    </tei:TEI>"""

    def test_emits_single_numbering_block(self):
        out = _transform(self.XML)
        self.assertEqual(out.count(r"\beginnumbering"), 1)
        self.assertEqual(out.count(r"\endnumbering"), 1)

    def test_verses_flow_inline_in_single_stream(self):
        out = _transform(self.XML)
        # The fixture has one tei:p containing 3 verse milestones, so we expect
        # one verse-paragraph-level \\pstart/\\pend pair (not 1 per verse).
        #
        # The chapter milestone is not in a div[@type='book'], so it emits nothing
        # and does not open a pstart of its own.
        self.assertEqual(out.count(r"\pstart \vno{"), 1)
        self.assertEqual(out.count(r"\pend"), 1)

    def test_chapter_milestone_is_not_a_section(self):
        """Chapter milestones must never become LaTeX sections: the book class would
        auto-number them ("0.1") and the heading is unwanted in liturgical texts."""
        out = _transform(self.XML)
        self.assertNotIn(r"\eledsection", out)
        self.assertNotIn(r"\eledchapter", out)
        self.assertNotIn(r"\eledsubsection", out)

    def test_chapter_milestone_outside_a_book_renders_nothing(self):
        out = _transform(self.XML)
        # \chno is always *defined* in the preamble; assert it is never *used*.
        body = out.split(r"\begin{document}", 1)[1]
        self.assertNotIn(r"\chno", body)

    def test_chapter_milestone_inside_a_book_emits_inline_number(self):
        """In a Bible export the chapter exists only as a milestone, so it must stay
        visible — as an inline marker, not a heading."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:p>
                <tei:milestone unit="chapter" n="1"/>
                <tei:milestone unit="verse" n="1"/>In the beginning.
              </tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # Chapter numbers are forced LTR to avoid digit reversal in RTL contexts.
        self.assertIn(r"\chno{{\textdir TLT\selectlanguage{english}1}}", out)
        self.assertNotIn(r"\eledsection", out)

    def test_chapter_number_forces_ltr_digits_in_hebrew_context(self):
        """Digits inside Hebrew RTL contexts can render reversed unless forced LTR."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:p>
                <tei:milestone unit="chapter" n="12"/>
                <tei:milestone unit="verse" n="1"/>טקסט
              </tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\chno{{\textdir TLT\selectlanguage{english}12}}", out)

    def test_verse_numbers_appear_as_superscripts(self):
        out = _transform(self.XML)
        # The \vno{} command renders as a superscript prefix.
        self.assertIn(r"\vno{1}", out)
        self.assertIn(r"\vno{2}", out)
        self.assertIn(r"\vno{3}", out)


class TestParallelMapping(unittest.TestCase):
    """Parallel blocks must produce two synchronized streams, both wrapped
    in \\beginnumbering...\\endnumbering, surrounded by
    \\begin{pages}/\\end{pages} (or \\begin{pairs}) and ended with the
    matching reledpar typesetter command."""

    XML = """<?xml version="1.0" encoding="UTF-8"?>
    <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
             xmlns:p="http://jewishliturgy.org/ns/processing"
             xml:lang="he">
      <tei:text><tei:body>
        <p:parallel column-order="primary_first">
          <p:parallelItem role="primary" xml:lang="he">
            <tei:p>
              <tei:milestone unit="chapter" n="1"/>
              <tei:milestone unit="verse" n="1"/>בראשית.
              <tei:milestone unit="verse" n="2"/>והארץ.
              <tei:milestone unit="verse" n="3"/>ויאמר.
            </tei:p>
          </p:parallelItem>
          <p:parallelItem role="parallel" xml:lang="en">
            <tei:p>
              <tei:milestone unit="chapter" n="1"/>
              <tei:milestone unit="verse" n="1"/>In the beginning.
              <tei:milestone unit="verse" n="2"/>And the earth.
              <tei:milestone unit="verse" n="3"/>Let there be light.
            </tei:p>
          </p:parallelItem>
        </p:parallel>
      </tei:body></tei:text>
    </tei:TEI>"""

    def test_emits_pages_environment_by_default(self):
        out = _transform(self.XML)
        self.assertIn(r"\begin{pages}", out)
        self.assertIn(r"\end{pages}", out)
        self.assertIn(r"\Pages", out)
        self.assertIn(r"\begin{Leftside}", out)
        self.assertIn(r"\begin{Rightside}", out)

    def test_empty_parallel_block_is_skipped(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p/></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p/></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn(r"\begin{pages}", out)

    def test_parallel_inside_transclude_is_still_grouped(self):
        """The compiled XML can wrap p:parallel blocks in p:transclude; the TeX stage
        must expand the wrapper so parallel blocks still become a reledpar environment."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:transclude target="urn:x-opensiddur:test" type="external">
              <p:parallel column-order="primary_first">
                <p:parallelItem role="primary" xml:lang="he"><tei:p>שלום</tei:p></p:parallelItem>
                <p:parallelItem role="parallel" xml:lang="en"><tei:p>Hello</tei:p></p:parallelItem>
              </p:parallel>
            </p:transclude>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, layout="pairs")
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\begin{Leftside}", out)
        self.assertIn(r"\begin{Rightside}", out)

    def test_nested_transclude_parallels_are_grouped_into_one_pages_run(self):
        """Wrapper expansion must recurse.

        Parallel blocks end at every external transclusion, so a transcluded document that
        itself transcludes nests p:transclude wrappers. A single-level expansion leaves the
        inner wrapper in the flow, where it groups as 'inline' and splits the \\Pages run.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:transclude target="urn:outer" type="external">
              <p:parallel column-order="primary_first">
                <p:parallelItem role="primary" xml:lang="he"><tei:p>אחד</tei:p></p:parallelItem>
                <p:parallelItem role="parallel" xml:lang="en"><tei:p>One</tei:p></p:parallelItem>
              </p:parallel>
              <p:transclude target="urn:inner" type="external">
                <p:parallel column-order="primary_first">
                  <p:parallelItem role="primary" xml:lang="he"><tei:p>שנים</tei:p></p:parallelItem>
                  <p:parallelItem role="parallel" xml:lang="en"><tei:p>Two</tei:p></p:parallelItem>
                </p:parallel>
              </p:transclude>
              <p:parallel column-order="primary_first">
                <p:parallelItem role="primary" xml:lang="he"><tei:p>שלשה</tei:p></p:parallelItem>
                <p:parallelItem role="parallel" xml:lang="en"><tei:p>Three</tei:p></p:parallelItem>
              </p:parallel>
            </p:transclude>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertEqual(out.count(r"\begin{pages}"), 1,
                         "all three blocks belong to a single \\Pages run")
        self.assertIn("Two", out, "the nested transclusion's content must be typeset")

    def test_english_column_not_wrapped_in_hebrew_env(self):
        """The English stream must not inherit the Hebrew stream's RTL environment.

        Regression for the reported symptom: nested parallels were flattened into the Hebrew
        column by the mode="leaves" safety net, so Latin text rendered reversed.
        """
        out = _transform(self.XML, layout="pairs")
        right = re.search(r"\\begin\{Rightside\}(.*?)\\end\{Rightside\}", out, re.DOTALL)
        self.assertIsNotNone(right)
        self.assertIn("In the beginning", right.group(1))
        self.assertNotIn(r"\begin{hebrew}", right.group(1))

    def test_pairs_layout_uses_columns_typesetter(self):
        out = _transform(self.XML, layout="pairs")
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\Columns", out)
        self.assertNotIn(r"\begin{pages}", out)
        self.assertNotIn(r"\Pages", out)

    def test_pairs_layout_line_numbers_on_outer_column_margins(self):
        """Leftside is the physical left column; Rightside is the physical right column.
        Both margins {right} regresses Hebrew numbers into the gutter."""
        out = _transform(self.XML, layout="pairs")
        self.assertIn(r"\linenummarginColumns{left}", out)
        self.assertIn(r"\linenummarginColumnsR{right}", out)

    def test_pairs_layout_forces_ltr_for_columns_assembly(self):
        r"""Avoid RTL \pardir flipping the visual order of the two-column row."""
        out = _transform(self.XML, layout="pairs")
        self.assertIn(r"\let\OSreledparColumnsOrig\Columns", out)
        self.assertIn(r"\pardir TLT\relax\textdir TLT\relax\OSreledparColumnsOrig", out)

    def test_each_side_has_its_own_numbering(self):
        out = _transform(self.XML)
        # One \beginnumbering per side, one \endnumbering per side.
        self.assertEqual(out.count(r"\beginnumbering"), 2)
        self.assertEqual(out.count(r"\endnumbering"), 2)

    def test_pstart_counts_match_across_streams(self):
        """The two streams must emit the SAME number of \\pstart markers,
        else reledpar can't pair them by position."""
        out = _transform(self.XML)
        # Block-level pstart/pend: one per side (one parallel block).
        self.assertEqual(out.count(r"\pstart"), 2)
        self.assertEqual(out.count(r"\pend"), 2)

    def test_pstart_pair_count_matches_verse_count_per_side(self):
        """Within each side's numbering block, we use one block-level \\pstart,
        while verse numbers remain inline via \\vno{n}."""
        out = _transform(self.XML)
        left_match = re.search(
            r"\\begin\{Leftside\}(.*?)\\end\{Leftside\}", out, re.DOTALL
        )
        right_match = re.search(
            r"\\begin\{Rightside\}(.*?)\\end\{Rightside\}", out, re.DOTALL
        )
        self.assertIsNotNone(left_match)
        self.assertIsNotNone(right_match)
        self.assertEqual(left_match.group(1).count(r"\pstart"), 1)
        self.assertEqual(right_match.group(1).count(r"\pstart"), 1)
        for n in ("1", "2", "3"):
            self.assertIn(rf"\vno{{{n}}}", left_match.group(1))
            self.assertIn(rf"\vno{{{n}}}", right_match.group(1))

    def test_column_order_swaps_streams(self):
        """primary_last puts the parallel (English) stream on the left."""
        xml = self.XML.replace('column-order="primary_first"', 'column-order="primary_last"')
        out = _transform(xml)
        left_match = re.search(
            r"\\begin\{Leftside\}(.*?)\\end\{Leftside\}", out, re.DOTALL
        )
        self.assertIsNotNone(left_match)
        # Hebrew text should now be on the right, English on the left.
        self.assertIn("In the beginning", left_match.group(1))
        self.assertNotIn("בראשית", left_match.group(1))

    def test_hebrew_stream_is_wrapped_in_polyglossia_block(self):
        """Hebrew streams need to be inside a hebrew environment so direction
        and font are picked up everywhere inside numbering."""
        out = _transform(self.XML)
        # Look at the Leftside (which is Hebrew when column-order=primary_first
        # and the primary lang=he).
        left_match = re.search(
            r"\\begin\{Leftside\}(.*?)\\end\{Leftside\}", out, re.DOTALL
        )
        self.assertIsNotNone(left_match)
        self.assertIn(r"\begin{hebrew}", left_match.group(1))
        self.assertIn(r"\end{hebrew}", left_match.group(1))

    def test_parallel_row_after_marker_reconstruct(self):
        """After marker reconstruction, the XSLT must still emit a pages-based
        parallel wrapper with two numbering streams (one per side). This test
        belongs with the XSLT structural invariants, not with reconstruction
        mechanics.
        """
        tei_ns = "http://www.tei-c.org/ns/1.0"
        p_ns = "http://jewishliturgy.org/ns/processing"
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="{tei_ns}" xmlns:p="{p_ns}">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p>שלום</tei:p></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p>Hello</tei:p></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        root = etree.fromstring(xml.encode("utf-8"))
        reconstruct_markered_document(root)
        out = xslt_transform_string(
            XSLT_FILE,
            etree.tostring(root, encoding="unicode"),
            xslt_params={"additional-preamble": "", "additional-postamble": ""},
        )

        self.assertIn(r"\begin{pages}", out)
        self.assertIn(r"\Pages", out)
        self.assertEqual(out.count(r"\beginnumbering"), 2)
        self.assertEqual(out.count(r"\endnumbering"), 2)
        self.assertIn("שלום", out)
        self.assertIn("Hello", out)


class TestNotesMapping(unittest.TestCase):
    """Body ``tei:note`` elements (materialized by the compiler) become reledmac
    apparatus footnotes via ``\\edtext{...}{\\Bfootnote{...}}``. ``tei:standOff``
    is not expanded at the TeX stage. Instructional notes use ``\\instructionnote``.
    """

    def test_default_note_is_b_series_apparatus(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body<tei:note>commentary</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # \edtext{\OSInterlinearNotemark}{... \Bfootnote{\OSFootnotemark ...}}: interlinear
        # serial mark + B-series footnote at page bottom (not an endnote after \pend).
        self.assertIn(r"\leavevmode{\OSRTLfalse\edtext{\OSInterlinearNotemark{1}}{\Bfootnote{\OSFootnotemark{1}\notenote{", out)
        self.assertIn("commentary", out)
        self.assertNotIn(r"\footnote{", out)

    def test_instruction_note_is_inline(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body<tei:note type="instruction">stand</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\instructionnote{", out)
        self.assertIn("stand", out)

    def test_body_editorial_note_emits_apparatus(self):
        """Compiler inlines editorial tei:note in the body; XSLT maps it to B-series."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              Hebrew text<tei:note xml:lang="en">English annotation</tei:note> more
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\leavevmode{\OSRTLfalse\edtext{\OSInterlinearNotemark{1}}{\Bfootnote{\OSFootnotemark{1}\notenote{", out)
        self.assertIn("English annotation", out)
        self.assertIn(r"{{\textdir TLT\selectlanguage{english}", out)

    def test_standoff_not_resolved_at_tex_stage(self):
        """tei:standOff is not expanded here; only body notes become apparatus."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              Hebrew text<tei:anchor xml:id="note-ref-1"/> more text
            </tei:p>
          </tei:body></tei:text>
          <tei:standOff type="notes" xml:lang="en">
            <tei:note target="#note-ref-1">StandOff only.</tei:note>
          </tei:standOff>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn("StandOff only.", out)
        self.assertNotIn(r"\leavevmode{\OSRTLfalse\edtext", out)

    def test_inline_note_with_standoff_duplicate_emits_once(self):
        """Body note plus matching tei:standOff (compiler leaves both) must not double TeX."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              Hebrew<tei:note xml:lang="en">Transcription uncertain.</tei:note><tei:anchor xml:id="a1"/>after
            </tei:p>
          </tei:body></tei:text>
          <tei:standOff type="notes" xml:lang="en">
            <tei:note target="#a1">Transcription uncertain.</tei:note>
          </tei:standOff>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertEqual(out.count("Transcription uncertain."), 1)
        self.assertEqual(out.count(r"\leavevmode{\OSRTLfalse\edtext{\OSInterlinearNotemark{1}"), 1)

    def test_two_body_editorial_notes_distinct_serials(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              A<tei:note xml:lang="en">First</tei:note> B<tei:note xml:lang="en">Second</tei:note>
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\OSInterlinearNotemark{1}", out)
        self.assertIn(r"\OSInterlinearNotemark{2}", out)
        self.assertEqual(out.count("First"), 1)
        self.assertEqual(out.count("Second"), 1)

    def test_parallel_body_note_per_column(self):
        """Each parallel stream numbers its own editorial notes from 1."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he"><tei:p>
                <tei:milestone unit="verse" n="1"/>א<tei:note xml:lang="en">Heb note</tei:note>
              </tei:p></p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en"><tei:p>
                <tei:milestone unit="verse" n="1"/>A<tei:note>Eng note</tei:note>
              </tei:p></p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        left = re.search(r"\\begin\{Leftside\}(.*?)\\end\{Leftside\}", out, re.DOTALL)
        right = re.search(r"\\begin\{Rightside\}(.*?)\\end\{Rightside\}", out, re.DOTALL)
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        self.assertIn(r"\OSInterlinearNotemark{1}", left.group(1))
        self.assertIn("Heb note", left.group(1))
        # Editorial serials count preceding notes in document order (Leftside before Rightside).
        self.assertIn(r"\OSInterlinearNotemark{2}", right.group(1))
        self.assertIn("Eng note", right.group(1))

    def test_note_language_forces_direction(self):
        """Notes must force their own direction based on the in-scope xml:lang.

        In practice we do this by wrapping note content with polyglossia
        helpers: \textenglish{...} and \texthebrew{...}.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <tei:text><tei:body>
            <tei:p xml:lang="he">
              עברית<tei:note xml:lang="en">English note</tei:note>
              <tei:note type="instruction" xml:lang="en">Inline English instruction</tei:note>
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"{{\textdir TLT\selectlanguage{english} English note}}", out)
        self.assertIn(r"{{\textdir TLT\selectlanguage{english} Inline English instruction}}", out)


class TestInlineFormatting(unittest.TestCase):
    """Inline formatting elements that survived the compiler should map to
    appropriate LaTeX commands while staying inside the verse's \\pstart."""

    def test_small_caps(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>The <tei:hi rend="small-caps">Lord</tei:hi> said.
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\textsc{Lord}", out)

    def test_kri_ktiv_choice(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>
            <tei:choice>
              <j:read>read</j:read>
              <j:written>written</j:written>
            </tei:choice>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\textit{read}", out)
        self.assertIn("(written)", out)

    def test_special_characters_are_tex_escaped(self):
        """LaTeX-special characters in body text must be escaped to avoid
        compilation failures in lualatex."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>50% of $5 &amp; #1
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"50\% of \$5 \& \#1", out)

    def test_lb_emits_leavevmode_linebreak(self):
        """tei:lb can appear at the start of a paragraph; we must ensure TeX is in
        horizontal mode before emitting \\\\ to avoid 'There's no line here to end.'"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/><tei:lb/>Line 2
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\leavevmode\\{}", out)


class TestConditionalRendering(unittest.TestCase):
    """Only a conditional whose condition could not be decided reaches this stage.

    A decided condition is resolved away by the compiler, so a marker in the input means
    "say this only if ...", and the passage it governs has to be visibly delimited or the
    reader cannot tell how far it runs.
    """

    CONDITION = (
        '<tei:fs type="opensiddur:holiday-aggregate">'
        '<tei:f name="shabbat"><tei:binary value="true"/></tei:f>'
        "</tei:fs>"
    )

    @staticmethod
    def _document_body(tex: str) -> str:
        """Just the typeset material: the preamble always defines every macro."""
        return tex.split(r"\begin{document}", 1)[1]

    def _transform_body(self, body: str) -> str:
        return _transform(
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
              <tei:text><tei:body>{body}</tei:body></tei:text>
            </tei:TEI>"""
        )

    def test_inline_conditional_is_bracketed(self):
        out = self._transform_body(
            f"""<tei:p><tei:milestone unit="verse" n="1"/>before <j:conditional
              xml:id="c">{self.CONDITION}</j:conditional>conditional<j:endConditional
              target="#c"/> after</tei:p>"""
        )
        body = self._document_body(out)
        self.assertIn(r"\OSCondStartInline{}", body)
        self.assertIn(r"\OSCondEndInline{}", body)
        self.assertNotIn(r"\OSCondStartBlock", body)
        for word in ("before", "conditional", "after"):
            with self.subTest(word):
                self.assertIn(word, body)

    def test_block_conditional_gets_rules(self):
        out = self._transform_body(
            f"""<tei:div>
              <j:conditional xml:id="c">{self.CONDITION}</j:conditional>
              <tei:p><tei:milestone unit="verse" n="1"/>conditional paragraph</tei:p>
              <j:endConditional target="#c"/>
            </tei:div>"""
        )
        body = self._document_body(out)
        self.assertIn(r"\OSCondStartBlock{}", body)
        self.assertIn(r"\OSCondEndBlock{}", body)
        self.assertNotIn(r"\OSCondStartInline", body)

    def test_conditional_note_is_emitted(self):
        """The note explains the condition the reader has to judge for themselves."""
        out = self._transform_body(
            f"""<tei:div>
              <j:conditional xml:id="c">
                <tei:note type="instruction">On Shabbat add:</tei:note>{self.CONDITION}
              </j:conditional>
              <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>
              <j:endConditional target="#c"/>
            </tei:div>"""
        )
        self.assertIn("On Shabbat add:", out)

    def test_conditional_macros_are_defined(self):
        out = self._transform_body(
            """<tei:p><tei:milestone unit="verse" n="1"/>x</tei:p>"""
        )
        for macro in (
            r"\newcommand{\OSCondStartInline}",
            r"\newcommand{\OSCondEndInline}",
            r"\newcommand{\OSCondStartBlock}",
            r"\newcommand{\OSCondEndBlock}",
        ):
            with self.subTest(macro):
                self.assertIn(macro, out)


class TestOptionRendering(unittest.TestCase):
    """Alternate wordings: nothing here has chosen between them, so all are shown."""

    def test_all_options_are_rendered(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>
            <tei:choice>
              <j:option xml:lang="he">first</j:option>
              <j:option xml:lang="yi">second</j:option>
            </tei:choice>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn("first", out)
        self.assertIn("(second)", out)


class TestStructuralElements(unittest.TestCase):
    """tei:standOff and tei:pb should be skipped; head should produce a styled
    heading macro instead of inlining the title in the body."""

    def test_standoff_notes_are_skipped(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:p>Body</tei:p>
            <tei:standOff type="notes">
              <tei:note>Should not appear</tei:note>
            </tei:standOff>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn("Body", out)
        self.assertNotIn("Should not appear", out)

    def test_div_head_emits_heading_inside_its_own_pstart(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div>
              <tei:head>Genesis</tei:head>
              <tei:p><tei:milestone unit="verse" n="1"/>In the beginning.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # Top-level head → \OSheadA (LTR wrapper when not Hebrew), and the heading must
        # sit alone in a skipnumbering pstart so it is a real, unnumbered heading.
        self.assertIn(
            "\\pstart \\skipnumbering\n"
            r"\OSheadA{{\textdir TLT\selectlanguage{english}Genesis}}",
            out,
        )
        self.assertNotIn(r"\eledchapter", out)
        self.assertNotIn(r"\eledsubsection", out)

    def test_div_head_emits_pdf_bookmark(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div>
              <tei:head>Genesis</tei:head>
              <tei:p>In the beginning.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            r"\phantomsection\addcontentsline{toc}{section}"
            r"{{\textdir TLT\selectlanguage{english}Genesis}}",
            out,
        )

    def test_heading_level_counts_only_headed_ancestors(self):
        """Transclusion interposes headless container divs, so heading level must follow
        headed ancestors rather than raw nesting depth."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div>
              <tei:div>
                <tei:head>Outer</tei:head>
                <tei:div>
                  <tei:head>Inner</tei:head>
                  <tei:p>Text.</tei:p>
                </tei:div>
              </tei:div>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # Two headless container divs above "Outer" must not push it below level 1.
        self.assertIn(r"\OSheadA{{\textdir TLT\selectlanguage{english}Outer}}", out)
        self.assertIn(r"\OSheadB{{\textdir TLT\selectlanguage{english}Inner}}", out)
        self.assertIn(r"\addcontentsline{toc}{subsection}", out)

    def test_head_markup_is_rendered_not_flattened(self):
        """A mixed-language title (JPS book heads look like this) must keep its Hebrew run
        in a \\texthebrew wrapper — flattened into the surrounding LTR heading the Hebrew
        renders reversed. The line break becomes a horizontal separator, since only the
        first line of a heading carries the centering glue."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head><tei:foreign xml:lang="he">רות</tei:foreign><tei:lb/>RUTH</tei:head>
              <tei:p>And it came to pass.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            r"\OSheadA{{\textdir TLT\selectlanguage{english}"
            r"\texthebrew{רות}\quad RUTH}}",
            out,
        )
        # ...but a line break in body text is still a line break.
        self.assertNotIn(r"\quad", out.split(r"\OSheadA", 1)[0])
        # The bookmark still takes the flattened form: \addcontentsline builds a PDF
        # string and cannot carry markup.
        self.assertIn(
            r"\addcontentsline{toc}{section}{{\textdir TLT\selectlanguage{english}רותRUTH}}",
            out,
        )

    def test_notes_in_a_head_are_dropped(self):
        """A heading sits outside the numbered line stream, so an apparatus entry cannot
        be anchored in it."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body>
            <tei:div>
              <tei:head>Genesis<tei:note>Should not appear</tei:note></tei:head>
              <tei:p>Body</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn("Should not appear", out)
        self.assertIn(r"\OSheadA{{\textdir TLT\selectlanguage{english}Genesis}}", out)

    def test_english_head_in_hebrew_document_uses_ltr_wrapper(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head xml:lang="en">Genesis</tei:head>
              <tei:p><tei:milestone unit="verse" n="1"/>בְּרֵאשִׁית</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            r"\OSheadA{{\textdir TLT\selectlanguage{english}Genesis}}",
            out,
        )

    def test_hebrew_head_in_hebrew_document_has_no_ltr_wrapper(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head>בראשית</tei:head>
              <tei:p><tei:milestone unit="verse" n="1"/>בְּרֵאשִׁית</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\OSheadA{בראשית}", out)
        self.assertNotIn(
            r"\OSheadA{{\textdir TLT\selectlanguage{english}בראשית}}",
            out,
        )


if __name__ == "__main__":
    unittest.main()

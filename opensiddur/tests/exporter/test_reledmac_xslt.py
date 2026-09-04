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

    def test_preamble_declares_running_head_mark_classes(self):
        """Every heading level, plus book and chapter, needs a mark class for the
        running heads to read; the `Alt` family carries the second parallel
        column. Declared unconditionally so the preamble stays deterministic."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        for mark_class in (
            "OSheadA", "OSheadB", "OSheadC", "OSheadD", "OSheadAny",
            "OSbook", "OSchapter",
            "OSheadAAlt", "OSheadBAlt", "OSheadCAlt", "OSheadDAlt",
            "OSheadAnyAlt", "OSbookAlt",
        ):
            with self.subTest(mark_class=mark_class):
                self.assertIn(r"\NewMarkClass{%s}" % mark_class, out)
        self.assertIn(r"\newcommand{\OSHFIfNonEmpty}", out)
        self.assertIn(r"\newcommand{\OSHebrewNumber}", out)

    def test_document_title_comes_from_the_tei_header(self):
        """The header is dropped from the output but is still readable here, and
        it is where {document-title} gets its text."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:teiHeader><tei:fileDesc><tei:titleStmt>
            <tei:title type="main">A Book of Prayer</tei:title>
          </tei:titleStmt></tei:fileDesc></tei:teiHeader>
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            r"\newcommand{\OSDocumentTitle}{{\textdir TLT\selectlanguage{english}"
            r"A Book of Prayer}}",
            out,
        )

    def test_document_title_is_empty_without_one(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        self.assertIn(r"\newcommand{\OSDocumentTitle}{}", _transform(xml))

    def test_page_style_preamble_is_emitted_after_hyperref(self):
        """fancyhdr must load after hyperref, and nothing is emitted when no
        running head is configured."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        self.assertNotIn("fancyhdr", _transform(xml))

        out = _transform(xml, **{"page-style-preamble": r"\usepackage{fancyhdr}"})
        self.assertIn(r"\usepackage{fancyhdr}", out)
        self.assertLess(out.index(r"\usepackage{hyperref}"), out.index("fancyhdr"))
        self.assertLess(out.index("fancyhdr"), out.index(r"\begin{document}"))

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

    def test_documentclass_options_are_passed_through_verbatim(self):
        """The class options are built in Python; the stylesheet only places them."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, **{"documentclass-options": "12pt,a5paper,oneside"})
        self.assertIn(r"\documentclass[12pt,a5paper,oneside]{book}", out)

    def test_typography_preamble_overrides_the_stylesheet_defaults(self):
        """The block has to land after every default it is meant to override,
        and before the bibliography, which is not typography."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(
            xml,
            **{
                "typography-preamble": "\\OSTYPOGRAPHY\n",
                "additional-preamble": "\\OSBIBLIOGRAPHY\n",
            },
        )
        self.assertLess(out.index(r"\newcommand{\OSheadA}"), out.index(r"\OSTYPOGRAPHY"))
        self.assertLess(out.index(r"\setlength{\parskip}"), out.index(r"\OSTYPOGRAPHY"))
        self.assertLess(out.index(r"\OSTYPOGRAPHY"), out.index(r"\OSBIBLIOGRAPHY"))
        self.assertLess(out.index(r"\OSTYPOGRAPHY"), out.index(r"\begin{document}"))

    def test_empty_typography_preamble_leaves_the_defaults_alone(self):
        """A document that configures nothing must be the document this
        exporter has always produced."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        self.assertEqual(_transform(xml), _transform(xml, **{"typography-preamble": ""}))

    def test_preamble_bookmarks_four_levels_deep(self):
        """The deeper heading levels (index > section > haftarah > rite) must reach the PDF
        outline. The book class stops the table of contents at subsection and hyperref
        follows it, which silently drops anything deeper.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\setcounter{tocdepth}{4}", out)
        self.assertIn("bookmarksdepth=4", out)

    def test_a_fourth_level_head_gets_its_own_macro_and_outline_entry(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div><tei:head>Humash</tei:head>
              <tei:div><tei:head>Haftarot</tei:head>
                <tei:div><tei:head>Bereshit</tei:head>
                  <tei:div><tei:head>Ashkenaz</tei:head><tei:p>Hi</tei:p></tei:div>
                </tei:div>
              </tei:div>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\OSheadD{", out)
        self.assertIn(r"\addcontentsline{toc}{paragraph}", out)

    def test_a_fifth_level_head_stays_at_the_fourth(self):
        """Nesting deeper than the macros go must not fall off the end of the sequence."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div><tei:head>One</tei:head>
              <tei:div><tei:head>Two</tei:head>
                <tei:div><tei:head>Three</tei:head>
                  <tei:div><tei:head>Four</tei:head>
                    <tei:div><tei:head>Five</tei:head><tei:p>Hi</tei:p></tei:div>
                  </tei:div>
                </tei:div>
              </tei:div>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn("english}Five}", out)
        self.assertNotIn("OSheadE", out)

    def test_a_third_level_head_is_added_to_the_outline(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div><tei:head>Humash</tei:head>
              <tei:div><tei:head>Genesis</tei:head>
                <tei:div><tei:head>Bereshit</tei:head><tei:p>Hi</tei:p></tei:div>
              </tei:div>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\addcontentsline{toc}{subsubsection}", out)

    def test_a_direction_switch_is_gobbled_whole_in_pdf_strings(self):
        """\textdir takes three letter tokens (TLT). A one-argument gobble leaves "LT" in
        the bookmark, in front of every non-Hebrew title."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>Hi</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\def\textdir#1#2#3{}", out)


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

    def test_chapter_milestone_inside_a_parallel_column_still_emits_its_number(self):
        """The book div now lives *inside* each column, not around the p:parallel.

        Chapter numbers are gated on ancestor::tei:div[@type='book'], so the compiler
        reproducing that div inside each p:parallelItem (stamped p:part when the div is
        split across rows) is what keeps the gate satisfied in parallel mode. If the div
        were hoisted away to flatten the blocks instead, \\chno would silently vanish.
        """
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing" xml:lang="he">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he">
                <tei:div type="book" p:part="first">
                  <tei:p>
                    <tei:milestone unit="chapter" n="3"/>
                    <tei:milestone unit="verse" n="1"/>טקסט
                  </tei:p>
                </tei:div>
              </p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en">
                <tei:div type="book" p:part="first">
                  <tei:p>
                    <tei:milestone unit="chapter" n="3"/>
                    <tei:milestone unit="verse" n="1"/>Text
                  </tei:p>
                </tei:div>
              </p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, layout="pairs")
        self.assertIn(r"\chno{{\textdir TLT\selectlanguage{english}3}}", out)
        # ...and it is genuinely the two-column path, not the linear fallback.
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\Columns", out)

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

    def test_second_column_records_into_the_alt_mark_classes(self):
        """A running head must be able to name either language's heading, so the
        two columns cannot share one set of mark classes."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                 xmlns:p="http://jewishliturgy.org/ns/processing"
                 xml:lang="he">
          <tei:text><tei:body>
            <p:parallel column-order="primary_first">
              <p:parallelItem role="primary" xml:lang="he">
                <tei:div type="book"><tei:head>בראשית</tei:head><tei:p>טקסט</tei:p></tei:div>
              </p:parallelItem>
              <p:parallelItem role="parallel" xml:lang="en">
                <tei:div type="book"><tei:head>GENESIS</tei:head><tei:p>Text</tei:p></tei:div>
              </p:parallelItem>
            </p:parallel>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\InsertMark{OSbook}{\texthebrew{בראשית}}", out)
        self.assertIn(
            r"\InsertMark{OSbookAlt}{{\textdir TLT\selectlanguage{english}GENESIS}}", out
        )
        self.assertIn(r"\InsertMark{OSheadAAlt}{", out)

    def test_chapter_milestone_records_a_mark_without_opening_a_pstart(self):
        """reledpar pairs the two sides by \\pstart count, so a mark must never
        open one of its own."""
        out = _transform(self.XML)
        self.assertIn(
            r"\InsertMark{OSchapter}{{\textdir TLT\selectlanguage{english}1}}", out
        )
        self.assertNotIn(r"}}\pstart", out)

    def test_chapter_number_mark_forces_ltr_digits(self):
        """A slot declaring Hebrew forces RTL, and \\textdir forces a direction
        rather than running the bidi algorithm, so bare digits are laid out
        right to left and chapter 50 reads "05"."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div type="book"><tei:head>בראשית</tei:head>
              <tei:p><tei:milestone unit="chapter" n="50"/>טקסט</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            r"\InsertMark{OSchapter}{{\textdir TLT\selectlanguage{english}50}}", out
        )

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

    def test_notes_can_be_collected_as_endnotes(self):
        """The apparatus series is the same; only where it is printed changes."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body<tei:note>commentary</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, **{"notes-placement": "endnote"})
        self.assertIn(r"\Bendnote{", out)
        self.assertNotIn(r"\Bfootnote{", out)
        # Collected as the document is typeset, so they have to be printed out.
        self.assertIn(r"\doendnotes{B}", out)
        self.assertLess(out.index(r"\doendnotes{B}"), out.index(r"\end{document}"))

    def test_notes_can_be_dropped_entirely(self):
        """Anchor and all: a mark pointing at a note that is not printed would
        be worse than no note."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body<tei:note>commentary</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, **{"notes-placement": "none"})
        self.assertNotIn("commentary", out)
        self.assertNotIn(r"\Bfootnote", out)
        # The macro is still defined in the preamble, which costs nothing; what
        # must be gone is every call to it.
        body = out[out.index(r"\begin{document}"):]
        self.assertNotIn(r"\OSInterlinearNotemark", body)

    def test_note_marks_can_be_drawn_from_another_series(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>A<tei:note>one</tei:note>
            B<tei:note>two</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        alpha = _transform(xml, **{"notes-mark": "alpha"})
        self.assertIn(r"\OSInterlinearNotemark{a}", alpha)
        self.assertIn(r"\OSInterlinearNotemark{b}", alpha)

        roman = _transform(xml, **{"notes-mark": "roman"})
        self.assertIn(r"\OSInterlinearNotemark{i}", roman)
        self.assertIn(r"\OSInterlinearNotemark{ii}", roman)

        symbol = _transform(xml, **{"notes-mark": "symbol"})
        self.assertIn(r"\OSInterlinearNotemark{\textasteriskcentered}", symbol)
        self.assertIn(r"\OSInterlinearNotemark{\textdagger}", symbol)

    def test_the_symbol_series_repeats_once_it_runs_out(self):
        """Six symbols, then the same symbols doubled — how a printed apparatus
        has always done it."""
        notes = "".join(
            f'<tei:note>n{i}</tei:note>' for i in range(1, 9)
        )
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body{notes}
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml, **{"notes-mark": "symbol"})
        self.assertIn(r"\OSInterlinearNotemark{\textparagraph}", out)
        self.assertIn(
            r"\OSInterlinearNotemark{\textasteriskcentered\textasteriskcentered}", out
        )

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

    def test_hebrew_note_wraps_embedded_latin_siglum(self):
        """MAM apparatus notes are Hebrew prose that embeds Latin manuscript
        sigla, e.g. "פטרבורג-EVR-II-B-8". \\textdir TRT forces the whole note
        into strict RTL, which has no per-run bidi detection, so an embedded
        Latin token renders back-to-front unless it gets its own explicit LTR
        override — same as digits already get in \\vno/\\chno."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>טקסט<tei:note xml:lang="he">פטרבורג-EVR-II-B-8 ומ""ג</tei:note>
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"{{\textdir TLT\selectlanguage{english}EVR-II-B-8}}", out)
        # The hyphen joining the Hebrew word to the siglum stays outside the
        # wrap; only the Latin/digit token itself is switched to LTR.
        self.assertIn("פטרבורג-{{\\textdir TLT\\selectlanguage{english}EVR-II-B-8}}", out)

    def test_pure_hebrew_note_has_no_spurious_latin_wrap(self):
        """Hebrew abbreviation punctuation (ASCII gershayim, e.g. מ""ג) must
        not be mistaken for a Latin run: it contains no [A-Za-z0-9], so it
        should pass through unwrapped."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>טקסט<tei:note xml:lang="he">וכך מ""ג ודותן</tei:note>
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn(r"\textdir TLT", out.split(r"\notenote{", 1)[1])

    def test_english_context_latin_text_not_double_wrapped(self):
        """Latin text already in an LTR (English) context must go through
        plain escaping, not the Hebrew-context bidi wrapper — that would be
        redundant with note-content's own English-note wrap."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:lang="en">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>Manuscript EVR-II-B-8 is cited here.
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn(r"\textdir TLT\selectlanguage{english}EVR-II-B-8", out)
        self.assertIn("EVR-II-B-8", out)


class TestSectionSeparator(unittest.TestCase):
    """A milestone[@rend='****'] separates sections that carry no heading."""

    XML = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:p>Before</tei:p>
            <tei:milestone unit="section" rend="****"/>
            <tei:p>After</tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""

    def test_the_separator_goes_through_a_macro(self):
        """Through a macro, so a settings file can change the mark and its
        appearance without the stylesheet knowing what either is."""
        out = _transform(self.XML)
        body = out[out.index(r"\begin{document}"):]
        self.assertIn(r"\OSSectionSeparator", body)

    def test_the_default_macro_prints_what_it_always_printed(self):
        out = _transform(self.XML)
        self.assertIn(
            r"\newcommand{\OSSectionSeparator}{\OSSectionSeparatorStyle{* * * *}}", out
        )
        self.assertIn(
            r"\newcommand{\OSSectionSeparatorStyle}[1]{\begin{center}#1\end{center}}", out
        )


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

    def test_conditional_around_inline_content_outside_a_paragraph_is_bracketed(self):
        """A milestone-structured text has no tei:p, but its runs are still inline.

        The rule is for content set off as a block; used inside a line of text it is a
        full-measure box, which breaks the line.
        """
        out = self._transform_body(
            f"""<tei:div>
              <tei:milestone unit="verse" n="1"/>before <j:conditional
                xml:id="c">{self.CONDITION}</j:conditional>conditional<j:endConditional
                target="#c"/> after
            </tei:div>"""
        )
        body = self._document_body(out)
        self.assertIn(r"\OSCondStartInline{}", body)
        self.assertIn(r"\OSCondEndInline{}", body)
        self.assertNotIn(r"\OSCondStartBlock", body)
        self.assertNotIn(r"\OSCondEndBlock", body)

    def test_conditional_around_aliyah_markers_only_is_silent(self):
        """\\OSaliyah brackets its own label, so a delimiter would double the brackets."""
        out = self._transform_body(
            f"""<tei:div>
              <tei:milestone unit="aliyah.annual" n="first"/>
              <j:conditional xml:id="c">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.1" n="year one first"/>
              <j:endConditional target="#c"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        body = self._document_body(out)
        self.assertNotIn(r"\OSCond", body)
        self.assertIn(r"\OSaliyah{first}", body)
        self.assertIn(r"\OSaliyah{year one first}", body)

    def test_silenced_conditional_keeps_its_labels_on_one_line(self):
        """The point of silencing: no full-measure box between the labels."""
        out = self._transform_body(
            f"""<tei:div>
              <tei:milestone unit="aliyah.annual" n="first"/>
              <j:conditional xml:id="c1">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.1" n="year one"/>
              <j:endConditional target="#c1"/>
              <j:conditional xml:id="c2">{self.CONDITION}</j:conditional>
              <tei:milestone unit="maftir.annual" n="maftir"/>
              <j:endConditional target="#c2"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        body = self._document_body(out)
        labels = re.findall(r"\\OSaliyah\{([^}]*)\}", body)
        self.assertEqual(["first", "year one", "maftir"], labels)
        self.assertEqual(1, body.count(r"\pstart"))

    def test_silencing_a_conditional_leaves_no_blank_line(self):
        """A blank line is \\par, and reledmac does not want one inside a \\pstart.

        Dropping a delimiter puts the whitespace that surrounded it back to back, which
        is exactly how a blank line appears.
        """
        out = self._transform_body(
            f"""<tei:div>
              <j:conditional xml:id="c1">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.1" n="year one"/>
              <j:endConditional target="#c1"/>
              <j:conditional xml:id="c2">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.2" n="year two"/>
              <j:endConditional target="#c2"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        stream = self._document_body(out).split(r"\pstart", 1)[1].split(r"\pend", 1)[0]
        self.assertIsNone(
            re.search(r"\n[ \t]*\n", stream),
            f"blank line inside \\pstart: {stream!r}",
        )

    def test_a_silent_milestone_between_markers_leaves_no_blank_line(self):
        """A qualified parsha unit sets nothing -- the div's heading names the parshah.

        Being invisible, it must not hold apart the whitespace around it: two whitespace
        leaves meeting in the output are a blank line, and a blank line is a \\par.
        """
        out = self._transform_body(
            """<tei:div>
              <tei:head>בְּחֻקֹּתַי</tei:head>
              <tei:milestone unit="aliyah.triennial.2" n="year two fifth"/>
              <tei:milestone unit="parsha.annual" n="בְּחֻקֹּתַי"/>
              <tei:milestone unit="aliyah.annual" n="first"/>
              <tei:milestone unit="verse" n="3"/>verse text
            </tei:div>"""
        )
        body = self._document_body(out)
        # The head occupies a \pstart of its own; the labels are in the one after it.
        stream = body.split(r"\pstart")[-1].split(r"\pend", 1)[0]
        self.assertIsNone(
            re.search(r"\n[ \t]*\n", stream),
            f"blank line inside \\pstart: {stream!r}",
        )
        self.assertEqual(
            ["year two fifth", "first"], re.findall(r"\\OSaliyah\{([^}]*)\}", stream)
        )

    def test_a_silent_milestone_does_not_break_a_run_of_labels(self):
        """It sets nothing, so the labels either side are adjacent and still duplicates."""
        out = self._transform_body(
            """<tei:div>
              <tei:milestone unit="aliyah.triennial.1" n="first"/>
              <tei:milestone unit="edition-verse" n="14"/>
              <tei:milestone unit="aliyah.triennial.2" n="first"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        labels = re.findall(r"\\OSaliyah\{([^}]*)\}", self._document_body(out))
        self.assertEqual(["first"], labels)

    def test_conditional_around_markers_with_a_note_stays_visible(self):
        """The note is what tells the reader; the bracket beside it is redundant."""
        out = self._transform_body(
            f"""<tei:div>
              <j:conditional xml:id="c">
                <tei:note type="instruction">In the triennial cycle:</tei:note>{self.CONDITION}
              </j:conditional>
              <tei:milestone unit="aliyah.triennial.1" n="year one first"/>
              <j:endConditional target="#c"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        body = self._document_body(out)
        self.assertIn("In the triennial cycle:", body)
        # A conditional that announces itself needs no bracket: the instruction says which
        # passage this is and on what it depends, and the bracket reads as stray
        # punctuation beside it.
        self.assertNotIn(r"\OSCondStartInline{}", body)

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


class TestRepeatedAliyahLabels(unittest.TestCase):
    """The combined parshiyot reach the same triennial aliyah under several patterns.

    The conditions differ, so the compiled TEI rightly carries a marker for each; they all
    print the same label, and the reader needs to see it once.
    """

    CONDITION = TestConditionalRendering.CONDITION

    def _labels(self, body: str) -> list[str]:
        out = _transform(
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
              <tei:text><tei:body>{body}</tei:body></tei:text>
            </tei:TEI>"""
        )
        return re.findall(
            r"\\OSaliyah\{([^}]*)\}", out.split(r"\begin{document}", 1)[1]
        )

    def test_repeated_label_at_one_point_is_shown_once(self):
        labels = self._labels(
            f"""<tei:div>
              <j:conditional xml:id="c1">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.a.1" n="year one first"/>
              <j:endConditional target="#c1"/>
              <j:conditional xml:id="c2">{self.CONDITION}</j:conditional>
              <tei:milestone unit="aliyah.triennial.b.1" n="year one first"/>
              <j:endConditional target="#c2"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        self.assertEqual(["year one first"], labels)

    def test_different_labels_at_one_point_are_all_shown(self):
        labels = self._labels(
            """<tei:div>
              <tei:milestone unit="aliyah.annual" n="first"/>
              <tei:milestone unit="aliyah.weekday" n="kohen"/>
              <tei:milestone unit="aliyah.triennial.1" n="year one first"/>
              <tei:milestone unit="verse" n="1"/>verse text
            </tei:div>"""
        )
        self.assertEqual(["first", "kohen", "year one first"], labels)

    def test_the_same_label_at_two_points_is_shown_at_each(self):
        """Two divisions genuinely named alike are not duplicates of one another."""
        labels = self._labels(
            """<tei:div>
              <tei:milestone unit="aliyah.annual" n="first"/>
              <tei:milestone unit="verse" n="1"/>first verse
              <tei:milestone unit="aliyah.triennial.1" n="first"/>
              <tei:milestone unit="verse" n="2"/>second verse
            </tei:div>"""
        )
        self.assertEqual(["first", "first"], labels)


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
        # The running-head marks precede it inside the same pstart.
        self.assertIn(
            "\\pstart \\skipnumbering\n"
            r"\InsertMark{OSheadA}{{\textdir TLT\selectlanguage{english}Genesis}}"
            r"\InsertMark{OSheadAny}{{\textdir TLT\selectlanguage{english}Genesis}}"
            r"\OSheadA{{\textdir TLT\selectlanguage{english}Genesis}}",
            out,
        )
        self.assertNotIn(r"\eledchapter", out)
        self.assertNotIn(r"\eledsubsection", out)

    def test_book_div_head_also_records_the_book_mark(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head>Genesis</tei:head>
              <tei:p>In the beginning.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\InsertMark{OSbook}{{\textdir TLT\selectlanguage{english}Genesis}}", out)

    def test_non_book_div_head_records_no_book_mark(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div type="section">
              <tei:head>A Section</tei:head>
              <tei:p>Text.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\InsertMark{OSheadA}{{\textdir TLT\selectlanguage{english}A Section}}", out)
        self.assertNotIn(r"\InsertMark{OSbook}", out)

    def test_heading_marks_follow_the_heading_level(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body>
            <tei:div><tei:head>Outer</tei:head>
              <tei:div><tei:head>Inner</tei:head><tei:p>Text.</tei:p></tei:div>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\InsertMark{OSheadA}{{\textdir TLT\selectlanguage{english}Outer}}", out)
        self.assertIn(r"\InsertMark{OSheadB}{{\textdir TLT\selectlanguage{english}Inner}}", out)
        # Every heading also records into the any-level class, which backs
        # the {section-title} code.
        self.assertIn(r"\InsertMark{OSheadAny}{{\textdir TLT\selectlanguage{english}Inner}}", out)

    def test_mixed_script_heading_mark_carries_per_run_direction(self):
        """A running head can be placed in a slot of either direction, so the
        mark cannot assume one: Hebrew runs need \\texthebrew (direction *and*
        font) and Latin runs need an explicit LTR wrapper."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head><tei:foreign xml:lang="he">רות</tei:foreign><tei:lb/>RUTH</tei:head>
              <tei:p>Text.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\InsertMark{OSbook}{\texthebrew{רות}", out)
        self.assertIn(r"{\textdir TLT\selectlanguage{english}RUTH}", out)

    def test_a_hyphenated_hebrew_heading_stays_one_run(self):
        """A paired parsha name is written with an en-dash, which is outside the
        Hebrew block. Splitting on it would make the dash its own LTR embedding
        and let a neighbouring chapter number reorder into the middle of the
        name."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div><tei:head>\u05ea\u05b7\u05d6\u05b0\u05e8\u05b4\u05d9\u05e2\u05b7\u2013\u05de\u05b0\u05e6\u05b9\u05e8\u05b8\u05e2</tei:head>
              <tei:p>\u05d8\u05e7\u05e1\u05d8</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(
            "\\InsertMark{OSheadA}{\\texthebrew{"
            "\u05ea\u05b7\u05d6\u05b0\u05e8\u05b4\u05d9\u05e2\u05b7\u2013"
            "\u05de\u05b0\u05e6\u05b9\u05e8\u05b8\u05e2}}",
            out,
        )
        self.assertNotIn("selectlanguage{english}\u2013", out)

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
        # ...but a line break in body text is still a line break. Scoped to the typeset
        # material: the preamble defines macros that legitimately use \quad themselves.
        body = out.split(r"\begin{document}", 1)[1]
        self.assertNotIn(r"\quad", body.split(r"\OSheadA", 1)[0])
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

    def test_digits_embedded_in_a_hebrew_head_are_forced_ltr(self):
        """A Hebrew heading was never expected to carry a number before, so digits in it
        went out unwrapped and would render reversed (e.g. "42:5" as "5:24")."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:div type="book">
              <tei:head>ישעיהו 42:5</tei:head>
              <tei:p><tei:milestone unit="verse" n="1"/>בְּרֵאשִׁית</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # "42" and "5" must wrap as a single LTR run, not two side by side: two separate
        # embeds with only a colon between them can have their *relative* order swapped by
        # the bidi algorithm (this is what previously rendered "42:5" as "43:10-42:5" in a
        # citation — see TestCitationMilestone.test_a_multi_number_range_stays_in_order).
        self.assertIn(
            r"\OSheadA{ישעיהו {{\textdir TLT\selectlanguage{english}42:5}}}",
            out,
        )


class TestFrontMatter(unittest.TestCase):
    """``tei:front`` is set before the body, with title pages on pages of their own
    outside the reledmac line numbering and the rest as ordinary text."""

    TITLE_PAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
      <tei:text>
        <tei:front>
          <tei:pb n="i"/>
          <tei:titlePage>
            <tei:docTitle>
              <tei:titlePart type="main">THE HOLY SCRIPTURES</tei:titlePart>
              <tei:titlePart type="sub">ACCORDING TO THE MASORETIC TEXT</tei:titlePart>
              <tei:titlePart type="alt" xml:lang="he">תורה נביאים וכתובים</tei:titlePart>
            </tei:docTitle>
            <tei:byline><tei:docAuthor>Max L. Margolis</tei:docAuthor></tei:byline>
            <tei:docEdition>Third Impression</tei:docEdition>
            <tei:docImprint>
              <tei:pubPlace>PHILADELPHIA</tei:pubPlace>
              <tei:publisher>THE JEWISH PUBLICATION SOCIETY OF AMERICA</tei:publisher>
              <tei:docDate>5677-1917</tei:docDate>
            </tei:docImprint>
          </tei:titlePage>
          <tei:head>PREFACE</tei:head>
          <tei:p>The sacred task of translating.</tei:p>
        </tei:front>
        <tei:body><tei:p>In the beginning.</tei:p></tei:body>
      </tei:text>
    </tei:TEI>"""

    def test_title_page_carries_no_running_head(self):
        """A title page is not part of the running-head scheme. The titlepage
        environment sets this itself, but `plain` is redefined for running heads,
        so do not leave the guarantee to a class internal."""
        out = _transform(self.TITLE_PAGE_XML)
        self.assertIn("\\begin{titlepage}\n\\thispagestyle{empty}", out)

    def test_front_matter_is_set_before_the_body(self):
        out = _transform(self.TITLE_PAGE_XML)
        self.assertLess(out.index("The sacred task"), out.index("In the beginning."))

    def test_front_matter_switches_page_numbering(self):
        """book-class front matter is numbered in roman and the body restarts at 1."""
        out = _transform(self.TITLE_PAGE_XML)
        self.assertLess(out.index(r"\frontmatter"), out.index(r"\mainmatter"))
        self.assertLess(out.index(r"\mainmatter"), out.index("In the beginning."))

    def test_title_page_is_its_own_page(self):
        out = _transform(self.TITLE_PAGE_XML)
        self.assertIn(r"\begin{titlepage}", out)
        self.assertIn(r"\end{titlepage}", out)

    def test_title_page_carries_no_line_numbering(self):
        """reledmac numbering inside a titlepage would number a transcribed page of
        the source as if it were edited text."""
        out = _transform(self.TITLE_PAGE_XML)
        page = out.split(r"\begin{titlepage}", 1)[1].split(r"\end{titlepage}", 1)[0]
        self.assertNotIn(r"\beginnumbering", page)
        self.assertNotIn(r"\pstart", page)

    def test_title_page_parts_use_their_own_macros(self):
        out = _transform(self.TITLE_PAGE_XML)
        self.assertIn(r"\OSTitleMain{THE HOLY SCRIPTURES}", out)
        self.assertIn(r"\OSTitleSub{ACCORDING TO THE MASORETIC TEXT}", out)
        # A Hebrew line on a Latin title page needs \texthebrew, or it renders reversed.
        self.assertIn(r"\OSTitleAlt{\texthebrew{תורה נביאים וכתובים}}", out)
        self.assertIn(r"\OSByline{Max L. Margolis}", out)
        self.assertIn(r"\OSDocEdition{Third Impression}", out)
        self.assertIn(r"\OSImprintLine{PHILADELPHIA}", out)
        self.assertIn(r"\OSImprintLine{5677-1917}", out)

    def test_prose_front_matter_is_a_numbered_stream(self):
        out = _transform(self.TITLE_PAGE_XML)
        front = out.split(r"\end{titlepage}", 1)[1].split(r"\mainmatter", 1)[0]
        self.assertIn(r"\beginnumbering", front)
        self.assertIn(r"\OSheadA{", front)

    def test_hebrew_title_page_is_wrapped_for_direction(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text>
            <tei:front>
              <tei:titlePage>
                <tei:docTitle>
                  <tei:titlePart type="main">ההגדה לליל שמורים</tei:titlePart>
                </tei:docTitle>
                <tei:docImprint xml:lang="de">
                  <tei:pubPlace>Roedelheim,</tei:pubPlace>
                </tei:docImprint>
              </tei:titlePage>
            </tei:front>
            <tei:body><tei:p>טקסט</tei:p></tei:body>
          </tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        page = out.split(r"\begin{titlepage}", 1)[1].split(r"\end{titlepage}", 1)[0]
        self.assertIn(r"\begin{hebrew}", page)
        # The Hebrew title needs no wrapper; the German imprint on the same page does,
        # or its Latin text would be laid out right to left.
        self.assertIn(r"\OSTitleMain{ההגדה לליל שמורים}", page)
        self.assertIn(
            r"\OSImprintLine{{\textdir TLT\selectlanguage{english}Roedelheim,}}", page
        )

    def test_imprint_parts_stay_inline_in_a_running_imprint(self):
        """A publisher named mid-sentence must not be broken onto a line of its own."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text>
            <tei:front>
              <tei:titlePage type="copyright">
                <tei:docImprint>Copyright, 1917, By <tei:publisher>The Jewish Publication Society of America</tei:publisher></tei:docImprint>
              </tei:titlePage>
            </tei:front>
            <tei:body><tei:p>In the beginning.</tei:p></tei:body>
          </tei:text>
        </tei:TEI>"""
        # \OSImprintLine is always *defined* in the preamble; assert it is never *used*.
        body = _transform(xml).split(r"\begin{document}", 1)[1]
        self.assertIn(
            r"\OSDocImprint{Copyright, 1917, By The Jewish Publication Society of America}",
            body,
        )
        self.assertNotIn(r"\OSImprintLine", body)

    def test_document_without_front_matter_is_unchanged(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body><tei:p>In the beginning.</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn(r"\frontmatter", out)
        self.assertNotIn(r"\mainmatter", out)
        self.assertNotIn(r"\begin{titlepage}", out)

    def test_title_page_in_the_body_is_not_flattened_into_the_text(self):
        """The leaves pass must never pull title page parts into a numbered stream."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body>
            <tei:div>
              <tei:titlePage><tei:docTitle><tei:titlePart>Stray</tei:titlePart></tei:docTitle></tei:titlePage>
              <tei:p>In the beginning.</tei:p>
            </tei:div>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        body = out.split(r"\begin{document}", 1)[1]
        self.assertNotIn("Stray", body)


class TestTableOfContents(unittest.TestCase):
    """``table-of-contents`` optionally prints a TOC page (\\tableofcontents), reusing the
    \\addcontentsline entries the heading template already writes for PDF bookmarks."""

    NESTED_HEADS_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
      <tei:text><tei:body>
        <tei:div><tei:head>Section One</tei:head>
          <tei:div><tei:head>Subsection</tei:head><tei:p>Hi</tei:p></tei:div>
        </tei:div>
      </tei:body></tei:text>
    </tei:TEI>"""

    def test_table_of_contents_omitted_by_default(self):
        out = _transform(self.NESTED_HEADS_XML)
        self.assertNotIn(r"\tableofcontents", out)

    def test_table_of_contents_printed_when_enabled(self):
        out = _transform(self.NESTED_HEADS_XML, **{"table-of-contents": True})
        self.assertIn(r"\tableofcontents", out)

    def test_table_of_contents_comes_after_frontmatter_and_before_mainmatter(self):
        out = _transform(self.NESTED_HEADS_XML, **{"table-of-contents": True})
        self.assertLess(out.index(r"\frontmatter"), out.index(r"\tableofcontents"))
        self.assertLess(out.index(r"\tableofcontents"), out.index(r"\mainmatter"))

    def test_addcontentsline_entries_still_present_when_enabled(self):
        """The TOC page must not replace the existing bookmark plumbing."""
        out = _transform(self.NESTED_HEADS_XML, **{"table-of-contents": True})
        self.assertIn(r"\addcontentsline{toc}{section}", out)
        self.assertIn(r"\addcontentsline{toc}{subsection}", out)

    def test_frontmatter_emitted_even_without_tei_front(self):
        """A document with no tei:front still needs \\frontmatter/\\mainmatter so the TOC
        gets roman-numeral front-matter pagination."""
        out = _transform(self.NESTED_HEADS_XML, **{"table-of-contents": True})
        self.assertIn(r"\frontmatter", out)
        self.assertIn(r"\mainmatter", out)

    def test_document_without_table_of_contents_has_no_frontmatter_switch(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
          <tei:text><tei:body><tei:p>In the beginning.</tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertNotIn(r"\frontmatter", out)
        self.assertNotIn(r"\mainmatter", out)

    def test_table_of_contents_depth_is_scoped_locally(self):
        """A custom depth must not leak into the global tocdepth that drives bookmarks."""
        out = _transform(
            self.NESTED_HEADS_XML,
            **{"table-of-contents": True, "table-of-contents-depth": 2},
        )
        self.assertIn(r"{\setcounter{tocdepth}{2}\tableofcontents}", out)
        # The preamble's global tocdepth (drives bookmarksdepth) is unaffected.
        self.assertIn(r"\setcounter{tocdepth}{4}", out)
        self.assertIn("bookmarksdepth=4", out)

    def test_table_of_contents_depth_defaults_to_four(self):
        out = _transform(self.NESTED_HEADS_XML, **{"table-of-contents": True})
        self.assertIn(r"{\setcounter{tocdepth}{4}\tableofcontents}", out)


class TestParshaMilestones(unittest.TestCase):
    """A parsha is a division containing the chapters and verses that follow it, so its
    milestone legitimately sits between paragraphs rather than inside one. It used to be
    rendered only when a \\pstart happened to be open, which meant every boundary in the
    JPS 1917 Torah — all of them between paragraphs — was silently dropped."""

    def _transform_book(self, body: str) -> str:
        """A div[@type='book'], which is what makes chapter milestones render too."""
        return _transform(
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="en">
              <tei:text><tei:body>
                <tei:div type="book">{body}</tei:div>
              </tei:body></tei:text>
            </tei:TEI>"""
        )

    @staticmethod
    def _document_body(tex: str) -> str:
        """Just the typeset material: the preamble always defines every macro."""
        return tex.split(r"\begin{document}", 1)[1]

    BETWEEN_PARAGRAPHS = """
        <tei:p><tei:milestone unit="verse" n="8"/>But Noah found grace.</tei:p>
        <tei:milestone unit="parsha" n="Noach"/>
        <tei:p><tei:milestone unit="verse" n="9"/>These are the generations.</tei:p>"""

    def test_a_milestone_between_paragraphs_is_rendered(self):
        body = self._document_body(self._transform_book(self.BETWEEN_PARAGRAPHS))
        self.assertIn(r"\OSParsha{Noach}", body)

    def test_a_milestone_inside_a_paragraph_is_still_rendered(self):
        """The shape that happened to work before must keep working."""
        body = self._document_body(self._transform_book(
            """<tei:p><tei:milestone unit="verse" n="8"/>But Noah found grace.</tei:p>
               <tei:p><tei:milestone unit="verse" n="9"/><tei:milestone unit="parsha"
                 n="Noach"/>These are the generations.</tei:p>"""
        ))
        self.assertIn(r"\OSParsha{Noach}", body)

    def test_a_milestone_before_the_first_paragraph_is_rendered(self):
        body = self._document_body(self._transform_book(
            """<tei:head>GENESIS</tei:head>
               <tei:milestone unit="parsha" n="Bereshit"/>
               <tei:p><tei:milestone unit="verse" n="1"/>In the beginning.</tei:p>"""
        ))
        self.assertIn(r"\OSParsha{Bereshit}", body)

    def test_the_name_runs_in_with_the_verse_it_opens(self):
        """The pstart opened for the boundary is the one the following verse uses, so the
        name shares a line with the parsha's first verse instead of standing alone."""
        body = self._document_body(self._transform_book(self.BETWEEN_PARAGRAPHS))
        after = body.split(r"\OSParsha{Noach}", 1)[1]
        block = after.split(r"\pend", 1)[0]
        self.assertIn(r"\vno{9}", block)
        self.assertNotIn(r"\pstart", block)

    def test_a_boundary_is_announced_only_once(self):
        """The B-series footnote this used to emit alongside would repeat the name on the
        same page. The apparatus form is available by \\renewcommand instead."""
        body = self._document_body(self._transform_book(self.BETWEEN_PARAGRAPHS))
        self.assertNotIn(r"\Bfootnote", body)
        self.assertEqual(1, body.count("Noach"))

    def test_the_parsha_macro_is_defined_in_the_preamble(self):
        out = self._transform_book(self.BETWEEN_PARAGRAPHS)
        preamble = out.split(r"\begin{document}", 1)[0]
        self.assertIn(r"\newcommand{\OSParsha}", preamble)

    def test_a_hebrew_name_gets_a_direction_wrapper(self):
        """Parsha names are Hebrew in an otherwise LTR stream and would render reversed."""
        body = self._document_body(self._transform_book(
            """<tei:p><tei:milestone unit="verse" n="8"/>But Noah found grace.</tei:p>
               <tei:milestone unit="parsha" n="נֹח"/>
               <tei:p><tei:milestone unit="verse" n="9"/>These are the generations.</tei:p>"""
        ))
        self.assertIn("\\OSParsha{\\texthebrew{נֹח}}", body)


if __name__ == "__main__":
    unittest.main()


class TestReadingDivisions(unittest.TestCase):
    """Aliyah, maftir and parshah markers, as the humash emits them.

    These divisions overlap on purpose, so their markers are inline rather than breaks: a
    maftir opens inside the seventh aliyah, and a marker that ended a paragraph would assert
    a break that is not there — besides desynchronising a reledpar pairing, which counts
    \\pstart markers on each side.
    """

    @staticmethod
    def _body(tex: str) -> str:
        return tex.split(r"\begin{document}", 1)[1]

    def _transform_body(self, body: str, **params) -> str:
        return _transform(
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
              <tei:text><tei:body>{body}</tei:body></tei:text>
            </tei:TEI>""",
            **params,
        )

    def test_aliyah_marker_is_emitted_inline(self):
        out = self._transform_body(
            """<tei:p><tei:milestone unit="verse" n="1"/>text one
               <tei:milestone unit="aliyah.annual" n="שני"/>text two</tei:p>"""
        )
        body = self._body(out)
        self.assertIn(r"\OSaliyah{", body)
        for word in ("text one", "text two"):
            with self.subTest(word):
                self.assertIn(word, body)

    def test_maftir_and_weekday_and_triennial_all_get_markers(self):
        for unit in ("maftir.annual", "aliyah.weekday", "aliyah.triennial.2"):
            with self.subTest(unit=unit):
                out = self._transform_body(
                    f"""<tei:p><tei:milestone unit="verse" n="1"/>text
                        <tei:milestone unit="{unit}" n="X"/>more</tei:p>"""
                )
                self.assertIn(r"\OSaliyah{X}", self._body(out))

    def test_a_marker_does_not_break_the_paragraph(self):
        """The maftir begins inside the seventh aliyah, so it must not close its pstart."""
        out = self._transform_body(
            """<tei:p><tei:milestone unit="verse" n="1"/>before
               <tei:milestone unit="maftir.annual" n="מפטיר"/>after</tei:p>"""
        )
        body = self._body(out)
        marker = body.index(r"\OSaliyah{")
        # No paragraph is closed and reopened around the marker.
        self.assertNotIn(r"\pend", body[max(0, marker - 120):marker])

    def test_markers_keep_pstart_counts_equal_for_parallel_text(self):
        """reledpar pairs columns by \\pstart count, so a marker on one side only must not
        add or remove one."""
        without = self._transform_body(
            """<tei:p><tei:milestone unit="verse" n="1"/>a</tei:p>"""
        )
        with_marker = self._transform_body(
            """<tei:p><tei:milestone unit="verse" n="1"/><tei:milestone
               unit="aliyah.annual" n="ראשון"/>a</tei:p>"""
        )
        self.assertEqual(
            self._body(without).count(r"\pstart"), self._body(with_marker).count(r"\pstart")
        )
        self.assertEqual(
            self._body(without).count(r"\pend"), self._body(with_marker).count(r"\pend")
        )

    def test_silenced_markers_keep_pstart_counts_equal_for_parallel_text(self):
        """Dropping a marker must not drop the \\pstart it would have opened.

        A conditional and an aliyah marker each open a \\pstart when none is open, so
        silencing the one and deduplicating the other could cost a column a \\pstart that
        the facing column still has, and reledpar pairs the columns by counting them.
        """
        condition = TestConditionalRendering.CONDITION
        without = self._transform_body(
            """<tei:div><tei:milestone unit="verse" n="1"/>a</tei:div>"""
        )
        with_markers = self._transform_body(
            f"""<tei:div>
              <j:conditional xml:id="c1">{condition}</j:conditional>
              <tei:milestone unit="aliyah.triennial.1" n="first"/>
              <j:endConditional target="#c1"/>
              <j:conditional xml:id="c2">{condition}</j:conditional>
              <tei:milestone unit="aliyah.triennial.2" n="first"/>
              <j:endConditional target="#c2"/>
              <tei:milestone unit="verse" n="1"/>a
            </tei:div>"""
        )
        for macro in (r"\pstart", r"\pend"):
            with self.subTest(macro):
                self.assertEqual(
                    self._body(without).count(macro),
                    self._body(with_markers).count(macro),
                )

    def test_a_qualified_parsha_unit_is_left_to_the_heading(self):
        """The humash gives every parshah a tei:head, so printing the milestone too would
        name it twice."""
        out = self._transform_body(
            """<tei:div><tei:head>בראשית</tei:head>
               <tei:p><tei:milestone unit="verse" n="1"/><tei:milestone
                 unit="parsha.annual" n="בראשית"/>text</tei:p></tei:div>"""
        )
        body = self._body(out)
        self.assertNotIn("Parsha:", body)
        self.assertIn("text", body)

    def test_an_unqualified_parsha_unit_still_gets_its_name_rendered(self):
        """wlc and jps1917 mark parshiyot inside a book with no heading of their own."""
        out = self._transform_body(
            """<tei:div type="book"><tei:head>Genesis</tei:head>
               <tei:p><tei:milestone unit="verse" n="1"/>text
               <tei:milestone unit="parsha" n="נח"/>more</tei:p></tei:div>"""
        )
        self.assertIn("\\OSParsha{\\texthebrew{נח}}", self._body(out))

    def test_the_aliyah_macro_is_defined_in_the_preamble(self):
        out = self._transform_body("""<tei:p>text</tei:p>""")
        self.assertIn(r"\newcommand{\OSaliyah}", out.split(r"\begin{document}", 1)[0])


class TestCitationMilestone(unittest.TestCase):
    """A tei:milestone[@unit='citation'] is how the humash states a haftarah/festival
    reading's scriptural source, or where it resumes after a jump (build._citation)."""

    @staticmethod
    def _body(tex: str) -> str:
        return tex.split(r"\begin{document}", 1)[1]

    def _transform_body(self, body: str, **params) -> str:
        return _transform(
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:p="http://jewishliturgy.org/ns/processing">
              <tei:text><tei:body>{body}</tei:body></tei:text>
            </tei:TEI>""",
            **params,
        )

    def test_citation_is_rendered_in_its_own_pstart(self):
        out = self._transform_body(
            """<tei:head>הַפְטָרַת בְּרֵאשִׁית</tei:head>
               <tei:milestone unit="citation" n="ישעיהו מב:ה–מג:י"/>
               <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>"""
        )
        body = self._body(out)
        self.assertIn(r"\OScitation{", body)
        before = body.split(r"\OScitation{", 1)[0]
        self.assertTrue(before.rstrip().endswith(r"\pstart \skipnumbering"))

    def test_the_citation_macro_is_defined_in_the_preamble(self):
        out = self._transform_body("""<tei:p>text</tei:p>""")
        self.assertIn(r"\newcommand{\OScitation}", out.split(r"\begin{document}", 1)[0])

    def test_digits_in_the_citation_are_forced_ltr(self):
        out = self._transform_body(
            """<tei:milestone unit="citation" n="ישעיהו 42:5-43:10"/>
               <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>"""
        )
        body = self._body(out)
        self.assertIn(r"{\textdir TLT\selectlanguage{english}42:5-43:10}", body)

    def test_a_multi_number_range_stays_in_order(self):
        """Two colon/dash-joined number groups sitting side by side in RTL text, with no
        strong character between them to anchor on, do not reliably keep their relative
        order if wrapped as separate LTR embeds: "42:5-43:10" can come out as "43:10-42:5".
        The whole range must go in one embedding instead — see f:emit-bidi-text."""
        out = self._transform_body(
            """<tei:milestone unit="citation" n="ירמיהו 34:8–34:22; 33:25–33:26"/>
               <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>"""
        )
        body = self._body(out)
        self.assertIn(
            r"{\textdir TLT\selectlanguage{english}34:8–34:22; 33:25–33:26}", body,
        )

    def test_a_book_change_still_gets_its_own_wrap(self):
        """A Hebrew book name between two ranges is a strong character, so it is safe to
        end one LTR run and start a fresh one there rather than merging across it."""
        out = self._transform_body(
            """<tei:milestone unit="citation" n="מלכים א 18:46; מלאכי 3:4–3:24"/>
               <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>"""
        )
        body = self._body(out)
        self.assertIn(r"{\textdir TLT\selectlanguage{english}18:46}", body)
        self.assertIn(r"{\textdir TLT\selectlanguage{english}3:4–3:24}", body)

    def test_a_citation_does_not_break_the_reading(self):
        """The reading's own transcluded text still follows in the numbered stream."""
        out = self._transform_body(
            """<tei:milestone unit="citation" n="ישעיהו 42:5-43:10"/>
               <tei:p><tei:milestone unit="verse" n="1"/>text</tei:p>"""
        )
        self.assertIn(r"\vno{1}", self._body(out))

    def test_markers_keep_pstart_counts_equal_for_parallel_text(self):
        """A citation exists only on the Hebrew source's milestones, so it must not add or
        remove a \\pstart on either side, or reledpar's column-pairing desyncs."""
        without = _transform(
            """<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:p="http://jewishliturgy.org/ns/processing" xml:lang="he">
              <tei:text><tei:body>
                <p:parallel column-order="primary_first">
                  <p:parallelItem role="primary" xml:lang="he">
                    <tei:p><tei:milestone unit="verse" n="1"/>שלום</tei:p>
                  </p:parallelItem>
                  <p:parallelItem role="parallel" xml:lang="en">
                    <tei:p><tei:milestone unit="verse" n="1"/>Hello</tei:p>
                  </p:parallelItem>
                </p:parallel>
              </tei:body></tei:text>
            </tei:TEI>"""
        )
        with_citation = _transform(
            """<?xml version="1.0" encoding="UTF-8"?>
            <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0"
                     xmlns:p="http://jewishliturgy.org/ns/processing" xml:lang="he">
              <tei:text><tei:body>
                <p:parallel column-order="primary_first">
                  <p:parallelItem role="primary" xml:lang="he">
                    <tei:p><tei:milestone unit="citation" n="ישעיהו א:א"/>
                      <tei:milestone unit="verse" n="1"/>שלום</tei:p>
                  </p:parallelItem>
                  <p:parallelItem role="parallel" xml:lang="en">
                    <tei:p><tei:milestone unit="verse" n="1"/>Hello</tei:p>
                  </p:parallelItem>
                </p:parallel>
              </tei:body></tei:text>
            </tei:TEI>"""
        )
        self.assertEqual(without.count(r"\pstart"), with_citation.count(r"\pstart"))
        self.assertEqual(without.count(r"\pend"), with_citation.count(r"\pend"))


class TestUnrenderedMilestones(unittest.TestCase):
    """A milestone the stylesheet does not set must not open a paragraph of its own.

    reledmac cannot typeset an empty \pstart: it fails with "You can't use \lastbox in
    vertical mode" and produces no PDF at all. A paragraph holding only such a milestone —
    which is what a range boundary falling inside an edition's own verse produces — used to
    make exactly that.
    """

    XML = """<?xml version="1.0" encoding="UTF-8"?>
    <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
      <tei:text><tei:body>
        <tei:p><tei:milestone unit="verse" n="17"/>text</tei:p>
        <tei:p><tei:milestone unit="edition-verse" n="14"/></tei:p>
      </tei:body></tei:text>
    </tei:TEI>"""

    def test_no_empty_paragraph_is_emitted(self):
        out = _transform(self.XML)
        self.assertNotIn(r"\pstart \pend", out)
        self.assertNotIn("\\pstart\n\\pend", out)

    def test_the_verse_before_it_is_still_set(self):
        out = _transform(self.XML)
        self.assertIn(r"\vno{17}", out)
        self.assertIn("text", out)

    def test_an_edition_verse_prints_nothing(self):
        self.assertNotIn("14", _transform(self.XML).split("begin{document}")[1])


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
        # one paragraph-level \\pstart/\\pend pair (not 1 per verse).
        self.assertEqual(out.count(r"\pstart"), 1)
        self.assertEqual(out.count(r"\pend"), 1)

    def test_chapter_milestone_emits_eledsection(self):
        out = _transform(self.XML)
        # Chapter numbers are forced LTR to avoid digit reversal in RTL contexts.
        self.assertIn(r"\eledsection{\begingroup\textdir TLT\selectlanguage{english}1\endgroup}", out)

    def test_chapter_number_forces_ltr_digits_in_hebrew_context(self):
        """Digits inside Hebrew RTL contexts can render reversed unless forced LTR."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="chapter" n="12"/>
              <tei:milestone unit="verse" n="1"/>טקסט
            </tei:p>
          </tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\eledsection{\begingroup\textdir TLT\selectlanguage{english}12\endgroup}", out)

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

    def test_pairs_layout_uses_columns_typesetter(self):
        out = _transform(self.XML, layout="pairs")
        self.assertIn(r"\begin{pairs}", out)
        self.assertIn(r"\Columns", out)
        self.assertNotIn(r"\begin{pages}", out)
        self.assertNotIn(r"\Pages", out)

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
    """tei:note elements must become reledmac apparatus footnotes anchored
    via \\edtext{...}{\\Bfootnote{...}}. Instructional notes are inline via
    \\instructionnote{...}, not footnotes."""

    def test_default_note_is_b_series_apparatus(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0">
          <tei:text><tei:body><tei:p>
            <tei:milestone unit="verse" n="1"/>Body<tei:note>commentary</tei:note>
          </tei:p></tei:body></tei:text>
        </tei:TEI>"""
        out = _transform(xml)
        # \edtext{}{\Bfootnote{}} is the proper reledmac idiom for apparatus notes:
        # zero-width lemma + B-series footnote at page bottom (not an endnote after \pend).
        self.assertIn(r"\edtext{}{\Bfootnote{\notenote{", out)
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

    def test_standoff_note_appears_at_anchor_position(self):
        """Notes stored in tei:standOff must be emitted as B-series apparatus
        footnotes at the tei:anchor position in the body, not silently dropped."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              Hebrew text<tei:anchor xml:id="note-ref-1"/> more text
            </tei:p>
          </tei:body></tei:text>
          <tei:standOff type="notes" xml:lang="en">
            <tei:note target="#note-ref-1">English annotation</tei:note>
          </tei:standOff>
        </tei:TEI>"""
        out = _transform(xml)
        self.assertIn(r"\edtext{}{\Bfootnote{\notenote{", out)
        self.assertIn("English annotation", out)
        # English note inside Hebrew stream must force LTR direction.
        self.assertIn(r"\begingroup\textdir TLT\selectlanguage{english}", out)

    def test_standoff_note_with_multiple_targets(self):
        """A note targeting multiple anchors must appear at each anchor site."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xml:lang="he">
          <tei:text><tei:body>
            <tei:p>
              <tei:milestone unit="verse" n="1"/>
              Word1<tei:anchor xml:id="a1"/> Word2<tei:anchor xml:id="a2"/>
            </tei:p>
          </tei:body></tei:text>
          <tei:standOff type="notes" xml:lang="en">
            <tei:note target="#a1 #a2">Shared note</tei:note>
          </tei:standOff>
        </tei:TEI>"""
        out = _transform(xml)
        # The same note appears twice — once per anchor.
        self.assertEqual(out.count("Shared note"), 2)

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
        self.assertIn(r"\begingroup\textdir TLT\selectlanguage{english} English note\endgroup", out)
        self.assertIn(r"\begingroup\textdir TLT\selectlanguage{english} Inline English instruction\endgroup", out)


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
        self.assertIn(r"\leavevmode\\", out)


class TestStructuralElements(unittest.TestCase):
    """tei:standOff and tei:pb should be skipped; head should produce a
    sectioning command instead of inlining the title in the body."""

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

    def test_div_head_emits_sectioning(self):
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
        # Top-level body div with head → \eledchapter
        self.assertIn(r"\eledchapter{Genesis}", out)


if __name__ == "__main__":
    unittest.main()

"""Tests for the Miqra intermediate → JLPTEI stylesheet
(``opensiddur/importer/miqra_al_pi_hamasorah/miqra_to_tei.xslt``).

These run the transformation directly over hand-written intermediate XML, so
they exercise the stylesheet without depending on the shape of the real TSV
sources.
"""

import re
import unittest

from lxml import etree

from opensiddur.importer.miqra_al_pi_hamasorah.convert_tsv import intermediate_to_tei

TEI_NS = "http://www.tei-c.org/ns/1.0"
J_NS = "http://jewishliturgy.org/ns/jlptei/2"
NS = {"tei": TEI_NS, "j": J_NS}

TAAM_TACHTON = "urn:x-opensiddur:condition:bible:taam-tachton"
TAAM_ELYON = "urn:x-opensiddur:condition:bible:taam-elyon"


def _book(*rows: str) -> str:
    return (
        '<miqra:book xmlns:miqra="urn:x-opensiddur:miqra:intermediate"'
        ' xmlns:mw="urn:x-opensiddur:mw:intermediate"'
        ' fileName="exodus" bookNameEn="Exodus">'
        + "".join(rows)
        + "</miqra:book>"
    )


def _row(verse: str, text: str, chapter: str = "20") -> str:
    return (
        f'<miqra:row source="s" pageKey="p" rowId="{verse}"'
        f' chapter="{chapter}" verse="{verse}">'
        "<miqra:nav/><miqra:scaffold/>"
        f"<miqra:text>{text}</miqra:text>"
        "</miqra:row>"
    )


def _transform(*rows: str) -> tuple[etree._Element, etree._Element | None]:
    """Return the parsed body and standOff (``None`` when there are no notes)."""
    outputs = intermediate_to_tei(_book(*rows))
    body = etree.fromstring(outputs["body"].encode("utf-8"))
    stand_off = outputs.get("stand_off") or ""
    return body, etree.fromstring(stand_off.encode("utf-8")) if stand_off else None


def _verse_text(body: etree._Element, chapter: str, verse: str) -> str:
    """All text scoped to one verse: from its milestone up to the next verse milestone.

    A verse split by a parashah break repeats its milestone in each paragraph, so the
    text is gathered across paragraphs rather than read out of a single one.
    """
    urn = f"urn:x-opensiddur:text:bible:exodus/{chapter}/{verse}"
    collected: list[str] = []
    collecting = False
    for node in body.iter():
        if node.tag == f"{{{TEI_NS}}}milestone" and node.get("unit") == "verse":
            collecting = node.get("corresp") == urn
        if collecting and node.text and node.tag != f"{{{TEI_NS}}}milestone":
            collected.append(node.text)
        if collecting and node.tail:
            collected.append(node.tail)
    return re.sub(r"\s+", " ", "".join(collected)).strip()


class TestDualAccent(unittest.TestCase):
    """``{{מ:כפול}}`` carries a verse in both cantillations. The two readings are
    alternate wordings — exactly one is read — which is what ``j:option`` expresses."""

    DUAL = (
        "<miqra:dual-accent>"
        "<miqra:merged>גג֑֔ג</miqra:merged>"
        '<miqra:strand role="א">תחתון</miqra:strand>'
        '<miqra:strand role="ב">עליון</miqra:strand>'
        "</miqra:dual-accent>"
    )

    def test_emits_a_choice_of_two_options(self):
        body, _ = _transform(_row("2", self.DUAL))
        options = body.findall(f".//{{{J_NS}}}option")
        self.assertEqual(2, len(options))
        self.assertEqual(
            [TAAM_TACHTON, TAAM_ELYON], [o.get("corresp") for o in options]
        )
        # templates.tsv documents א as ta'am tachton and ב as ta'am elyon.
        self.assertEqual("תחתון", options[0].text)
        self.assertEqual("עליון", options[1].text)

    def test_options_are_not_mixed_with_kri_ktiv(self):
        """Schematron forbids j:option beside j:read/j:written; keep them apart."""
        body, _ = _transform(_row("2", self.DUAL))
        choice = body.find(f".//{{{TEI_NS}}}choice")
        self.assertIsNone(choice.find(f"{{{J_NS}}}read"))
        self.assertIsNone(choice.find(f"{{{J_NS}}}written"))

    def test_merged_text_is_not_rendered_but_its_notes_stay_anchored(self):
        dual = (
            "<miqra:dual-accent>"
            "<miqra:merged>"
            '<miqra:variant noteId="n1"><miqra:display>גג֑֔ג</miqra:display></miqra:variant>'
            '<miqra:note xml:id="n1">הערה</miqra:note>'
            "</miqra:merged>"
            '<miqra:strand role="א">תחתון</miqra:strand>'
            '<miqra:strand role="ב">עליון</miqra:strand>'
            "</miqra:dual-accent>"
        )
        body, stand_off = _transform(_row("2", dual))
        self.assertNotIn("גג֑֔ג", _verse_text(body, "20", "2"))

        note = stand_off.find(f".//{{{TEI_NS}}}note")
        self.assertEqual("#n1-ref", note.get("target"))
        anchors = [
            seg.get(f"{{http://www.w3.org/XML/1998/namespace}}id")
            for seg in body.findall(f".//{{{TEI_NS}}}seg")
        ]
        self.assertIn("n1-ref", anchors)

    def test_parashah_only_strands_become_one_break(self):
        """When both strands hold only a parashah break they agree on where it falls and
        differ only in whether it lands mid-verse. A break is block structure and cannot
        live inside tei:choice, so the ta'am tachton marker is kept and no choice is made."""
        dual = (
            "<miqra:dual-accent>"
            "<miqra:merged/>"
            '<miqra:strand role="א"><miqra:parashah type="close" midVerse="true"/></miqra:strand>'
            '<miqra:strand role="ב"><miqra:parashah type="close"/></miqra:strand>'
            "</miqra:dual-accent>"
        )
        body, _ = _transform(_row("12", f"לפני{dual}אחרי"))
        self.assertEqual([], body.findall(f".//{{{J_NS}}}option"))
        paragraphs = body.findall(f"{{{TEI_NS}}}div/{{{TEI_NS}}}p")
        self.assertEqual(2, len(paragraphs))
        self.assertEqual("closed-1", paragraphs[1].get("type"))
        self.assertEqual("לפני", _verse_text(body, "20", "12")[:4])
        self.assertIn("אחרי", _verse_text(body, "20", "12"))


class TestMidVerseParashah(unittest.TestCase):
    """A parashah break inside a verse splits its paragraph. The verse must keep both
    its text and its milestone on each side of the break."""

    def test_verse_survives_a_mid_text_break(self):
        body, _ = _transform(
            _row("13", 'AAA<miqra:parashah type="close-inline" midVerse="true"/>BBB'),
            _row("14", "CCC"),
        )
        self.assertEqual("AAA BBB", _verse_text(body, "20", "13"))
        milestones = [
            m.get("corresp")
            for m in body.findall(f".//{{{TEI_NS}}}milestone")
            if m.get("unit") == "verse"
        ]
        # The milestone repeats so the verse's corresp scope resumes after the break.
        self.assertEqual(2, milestones.count("urn:x-opensiddur:text:bible:exodus/20/13"))
        self.assertIn("urn:x-opensiddur:text:bible:exodus/20/14", milestones)

    def test_plain_verse_is_unaffected(self):
        body, _ = _transform(_row("14", "CCC"))
        self.assertEqual("CCC", _verse_text(body, "20", "14"))


if __name__ == "__main__":
    unittest.main()

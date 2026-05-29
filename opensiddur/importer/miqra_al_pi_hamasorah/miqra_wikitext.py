"""
Convert Miqra al pi ha-Masorah wikitext (per templates.tsv) to intermediate XML.

All templates documented in sources/miqra_al_pi_hamasorah/sheets/templates.tsv are
handled here, including when nested inside verse text (e.g. {{נוסח|…}}).
"""

from __future__ import annotations

import re
from typing import Callable, Optional
from urllib.parse import quote

import mwparserfromhell

from opensiddur.importer.util.mediawiki_processor import (
    ConversionResult,
    MediaWikiProcessor,
)

MIQRA_NS = "urn:x-opensiddur:miqra:intermediate"
MW_NS = "urn:x-opensiddur:mw:intermediate"

_STRIP_TEMPLATES = frozenset(
    {
        "מ:פסוק",
        "מ:פסוק-שירה",
        "מ:שוליים",
        "מ:שוליים-סוף",
        "מ:טעמי המקרא",
        "מ:טעמי המקרא-סוף",
        "טעמי המקרא באינטרנט",
        "תבנית:טעמי המקרא באינטרנט",
        "מ:ספר חדש",
        "מ:רווח בתרי עשר",
        "רווח בתרי עשר",
        "מ:רווח בתרי עשר בפסוק הראשון",
        "מ:רווח לספר בתהלים",
        "רווח לספר בתהלים",
        "מ:רווח לספר בתהלים בפסוק הראשון",
        "ניווט טעמים",
        "שם הדף המלא",
        "מ:אין פרשה בתחילת פרק",
        'מ:אין פרשה בתחילת פרק בספרי אמ"ת',
        "מ:אין רווח של פרשה בתחילת פרשת השבוע",
        "מ:יישור-בשני-הצדדים",
        "מ:יישור-בשני-הצדדים-סוף",
        "בסיס-משתמש",
        'צורות כתיבה בספרי אמ"ת',
        "documentation",
        "name",
        "template",
        "תבנית",
    }
)

_ANY_HI_RE = re.compile(r"'''''(.*?)'''''|'''(.*?)'''|''(.*?)''")
_TAG_OPEN_RE = re.compile(r"<(miqra|mw):([a-zA-Z0-9-]+)([^>]*?)(/?)>")
_KETEG_START_RE = re.compile(r"<קטע\s+התחלה=([^/>]+)\s*/>", re.IGNORECASE)
_KETEG_END_RE = re.compile(r"<קטע\s+סוף=([^/>]+)\s*/>", re.IGNORECASE)


def normalize_template_name(name: str) -> str:
    n = str(name).strip()
    if n.lower().startswith("תבנית:"):
        n = n.split(":", 1)[1].strip()
    n = n.replace("''", '"').replace("״", '"').replace("׳", "'")
    return n.strip()


def link_target_to_uri(target: str) -> str:
    """Turn a URL or Hebrew Wikisource page title into a valid URI for tei:ref/@target."""
    t = (target or "").strip()
    if not t:
        return ""
    if re.match(r"^https?://", t, re.I):
        return t
    if t.startswith("//"):
        return "https:" + t
    page, sep, frag = t.partition("#")
    page = page.replace(" ", "_").strip()
    if page:
        uri = "https://he.wikisource.org/wiki/" + quote(page, safe="/:%")
    else:
        uri = "https://he.wikisource.org/wiki/"
    if sep:
        uri += "#" + quote(frag, safe=":/%.-_")
    return uri


def _xml_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _wikitext_basic_markup_to_xml(text: str) -> str:
    s = text or ""
    out: list[str] = []
    pos = 0
    for m in _ANY_HI_RE.finditer(s):
        out.append(_xml_escape(s[pos : m.start()]))
        if m.group(1) is not None:
            rend, inner = "bold-italic", m.group(1)
        elif m.group(2) is not None:
            rend, inner = "bold", m.group(2)
        else:
            rend, inner = "italic", m.group(3) or ""
        out.append(f'<mw:hi rend="{rend}">{_xml_escape(inner)}</mw:hi>')
        pos = m.end()
    out.append(_xml_escape(s[pos:]))
    return "".join(out)


def _escape_outside_tags(fragment: str) -> str:
    """Escape text nodes while preserving nested miqra:/mw: XML elements."""

    out: list[str] = []
    pos = 0
    while pos < len(fragment):
        m = _TAG_OPEN_RE.search(fragment, pos)
        if not m:
            out.append(_wikitext_basic_markup_to_xml(fragment[pos:]))
            break
        out.append(_wikitext_basic_markup_to_xml(fragment[pos : m.start()]))
        ns, local, _attrs, self_close = m.group(1), m.group(2), m.group(3), m.group(4)
        if self_close == "/":
            out.append(m.group(0))
            pos = m.end()
            continue
        close = f"</{ns}:{local}>"
        depth = 1
        search = m.end()
        closed_at: Optional[int] = None
        while depth > 0 and search <= len(fragment):
            next_close = fragment.find(close, search)
            if next_close == -1:
                break
            inner_open = _TAG_OPEN_RE.search(fragment, search, next_close)
            if inner_open and inner_open.start() < next_close and inner_open.group(4) != "/":
                inner_local = inner_open.group(2)
                if inner_open.group(1) == ns and inner_local == local:
                    depth += 1
                search = inner_open.end()
            else:
                depth -= 1
                if depth == 0:
                    closed_at = next_close
                else:
                    search = next_close + len(close)
        if closed_at is None:
            out.append(_wikitext_basic_markup_to_xml(fragment[m.start() :]))
            break
        inner = fragment[m.end() : closed_at]
        out.append(m.group(0))
        out.append(_escape_outside_tags(inner))
        out.append(close)
        pos = closed_at + len(close)
    return "".join(out)


def _preprocess_column_c(wikitext: str) -> str:
    """Column C markers from templates.tsv (not templates)."""
    s = wikitext or ""
    s = s.replace("__", " ")
    s = re.sub(r"(?<!https:)(?<!http:)//", "<miqra:lb/>", s)
    return s


def _preprocess_miqra_tags(wikitext: str) -> str:
    s = wikitext or ""
    s = _KETEG_START_RE.sub(
        r'<miqra:segment type="start" name="\1"/>', s
    )
    s = _KETEG_END_RE.sub(r'<miqra:segment type="end" name="\1"/>', s)
    return s


class MiqraWikiTextProcessor(MediaWikiProcessor):
    """MediaWiki processor with handlers for all Miqra templates."""

    def __init__(self) -> None:
        self._note_seq = 0
        super().__init__()

    def _initialize_handlers(self) -> None:
        self.template_handlers = {}
        self.tag_handlers = {}
        self.preprocessors = [_preprocess_miqra_tags]
        self.postprocessors = []
        self._register_template_handlers()
        self._register_tag_handlers()

    def process_wikitext(self, wikitext: str) -> ConversionResult:
        """Miqra uses recursive nested processing, not the JPS top-level loop."""
        warnings: list[str] = []
        errors: list[str] = []
        metadata: dict = {}

        text = wikitext or ""
        for pre in self.preprocessors:
            try:
                text = pre(text)
            except Exception as e:
                errors.append(str(e))

        try:
            xml_content = self._process_nested_content(text)
        except Exception as e:
            xml_content = text
            errors.append(str(e))

        return ConversionResult(
            xml_content=xml_content,
            metadata=metadata,
            warnings=warnings,
            errors=errors,
            wikilinks=self.wikilinks.copy(),
        )

    def _register_tag_handlers(self) -> None:
        self.tag_handlers["noinclude"] = self._handle_strip_tag

    def _handle_strip_tag(self, tag) -> str:
        return ""

    def _register_template_handlers(self) -> None:
        h = self.add_template_handler
        for name in _STRIP_TEMPLATES:
            h(name, self._handle_strip)

        h("נוסח", self._handle_nosach)
        h("ש", self._handle_footnote_mark)
        h("שם", self._handle_strip)

        h("פפ", self._handle_parashah_open)
        h("פפפ", self._handle_parashah_open_line)
        h("רווח בסוף שורה", self._handle_strip)
        h("סס", self._handle_parashah_close)
        h("ססס", self._handle_parashah_close_inline)
        h("סס2", self._handle_parashah_close_narrow)
        h("מ:ששש", self._handle_shirah_break)

        h("ר0", self._handle_poetic_space)
        h("ר1", self._handle_poetic_indent1)
        h("ר2", self._handle_poetic_indent2)
        h("ר3", self._handle_poetic_line)
        h("ר4", self._handle_poetic_verse)
        h("פרשה-מרכז", self._handle_centered_title)

        h("כתיב ולא קרי", self._handle_ketiv_only)
        h("קרי ולא כתיב", self._handle_qeri_only)
        h('מ:קו"כ-אם-2', self._handle_qok_if_matres)
        h('מ:קו"כ קרי שונה מהכתיב בשתי מילים', self._handle_qok_two_qeri_words)

        h("מ:אות-ג", self._handle_large_letter)
        h("מ:אות-ק", self._handle_small_letter)
        h("מ:אות תלויה", self._handle_raised_letter)
        h("מ:אות מנוקדת", self._handle_dotted_letter)
        h('מ:נו"ן הפוכה', self._handle_inverted_nun)
        h("מ:ירושלם", self._handle_yerushalem)
        h("מ:ירושלמה", self._handle_yerushalema)
        h("ירח בן יומו", self._handle_accent_yerah)
        h("ירח בן יומו-2", self._handle_accent_with_word)
        h("גלגל", self._handle_accent_galgal)
        h("גלגל-2", self._handle_accent_with_word)
        h("אתנח הפוך", self._handle_accent_etnah)
        h("מ:קמץ", self._handle_qamats)
        h("מ:טעם ומתג באות אחת", self._handle_taam_meteg)
        h("שני טעמים באות אחת", self._handle_two_taamim)
        h(
            "שני טעמים באות אחת קמץ-תחתון-פתח-עליון",
            self._handle_two_taamim_qupo,
        )
        h("מ:טעם", self._handle_taam_dummy)
        h("תבנית:מ:טעם", self._handle_taam_dummy)
        h("מ:גרש ותלישא גדולה", self._handle_geresh_telisha)
        h("מ:גרשיים ותלישא גדולה", self._handle_gershayim_telisha)
        h("מ:כל קמץ קטן מרכא", self._handle_kol_qamats)
        h("מ:לגרמיה-2", self._handle_legarmeh)
        h("מ:פסק", self._handle_paseq)
        h("מ:מקף אפור", self._handle_grey_maqaf)
        h("מ:דחי", self._handle_dechi)
        h("מ:צינור", self._handle_tzinor)

        h("מ:הערה", self._handle_mam_note)
        h("עוגן בשורה", self._handle_line_anchor)
        h("מ:סיום בטוב", self._handle_good_ending)
        h("קק", self._handle_dual_trope_link)
        h("מ:כפול", self._handle_dual_accent)

        h("מ:קישור בהערה", self._handle_note_link)
        h("מ:קישור פנימי בהערה", self._handle_note_link)
        h("מודגש", self._handle_emphasis)

    def _lookup_handler(self, name: str) -> Optional[Callable]:
        n = normalize_template_name(name)
        if n in self.template_handlers:
            return self.template_handlers[n]
        if n.startswith('מ:כו"ק') or n.startswith('כו"ק') or n.startswith("כו''ק"):
            return self._handle_ketiv_qeri
        if n.startswith('מ:קו"כ') or n.startswith('קו"כ') or n.startswith("קו''כ"):
            return self._handle_qeri_ketiv
        return None

    def _process_nested_content(self, content: str, depth: int = 0) -> str:
        if depth > 12:
            return content

        parsed = mwparserfromhell.parse(content)
        nodes_to_replace = []

        for node in parsed.nodes:
            if hasattr(node, "name"):
                template_name = str(node.name).strip()
                handler = self._lookup_handler(template_name)
                if handler is None:
                    n = normalize_template_name(template_name)
                    if n in _STRIP_TEMPLATES:
                        handler = self._handle_strip
                    else:
                        processed = self._process_nested_content(str(node), depth + 1)
                        nodes_to_replace.append((node, processed))
                        continue
                try:
                    processed_node = self._process_template_with_nesting(node, depth + 1)
                    replacement = handler(processed_node)
                except Exception:
                    replacement = handler(node)
                nodes_to_replace.append((node, replacement))
            elif hasattr(node, "tag"):
                tag_name = str(node.tag).strip().lower()
                if tag_name in self.tag_handlers:
                    try:
                        processed_node = self._process_tag_with_nesting(node, depth + 1)
                        replacement = self.tag_handlers[tag_name](processed_node)
                    except Exception:
                        replacement = self.tag_handlers[tag_name](node)
                    nodes_to_replace.append((node, replacement))
                else:
                    processed = self._process_nested_content(str(node), depth + 1)
                    nodes_to_replace.append((node, processed))
            elif "Wikilink" in str(node.__class__):
                nodes_to_replace.append((node, self._handle_wikilink_miqra(node)))

            elif node.__class__.__name__ == "Heading":
                # Note text uses "=source=reading" notation; mwparser treats it as wikitext headings.
                title = self._process_nested_content(str(node.title), depth + 1)
                nodes_to_replace.append((node, "=" + title + "="))

        for node, replacement in nodes_to_replace:
            parsed.replace(node, replacement)

        return str(parsed)

    def _handle_wikilink_miqra(self, node) -> str:
        raw_title = str(getattr(node, "title", "")).strip()
        target = _xml_escape(link_target_to_uri(raw_title))
        text = str(getattr(node, "text", "")).strip() if getattr(node, "text", None) else ""
        if text:
            return f'<mw:link target="{target}">{_xml_escape(text)}</mw:link>'
        return f'<mw:link target="{target}"/>'

    def _p(self, content: str) -> str:
        return self._process_nested_content(content or "")

    def _param_value(self, template, key: str | int) -> str:
        """Read a template parameter by name or 1-based index.

        mwparserfromhell's ``template.get(1)`` returns ``'1=value'`` when the
        wikitext uses explicit ``1=value`` syntax; iterating ``params`` is reliable.
        """
        key_s = str(key).strip()
        for p in template.params:
            pname = str(p.name).strip()
            if pname == key_s:
                return str(p.value).strip()
            if pname.isdigit() and key_s.isdigit() and int(pname) == int(key_s):
                return str(p.value).strip()
        return ""

    def _param(self, template, index: int) -> str:
        return self._param_value(template, index)

    def _named_param(self, template, name: str) -> str:
        return self._param_value(template, name)

    def _note_params(self, template) -> str:
        parts: list[str] = []
        for p in template.params:
            pname = str(p.name).strip()
            if pname.isdigit() and int(pname) >= 2:
                parts.append(self._p(str(p.value)))
            elif pname in ("2", "הערות", "הערה", "notes"):
                parts.append(self._p(str(p.value)))
        return "".join(parts)

    def _mid_verse_attr(self, template) -> str:
        for p in template.params:
            if "פסקא באמצע פסוק" in str(p.value):
                return ' midVerse="true"'
        return ""

    def _next_note_id(self) -> str:
        self._note_seq += 1
        return f"miqra-note-{self._note_seq}"

    # --- handlers ---

    def _handle_strip(self, template) -> str:
        return ""

    def _handle_nosach(self, template) -> str:
        display = self._p(self._param(template, 1))
        notes = self._note_params(template)
        if not notes:
            return display
        note_id = self._next_note_id()
        return (
            f'<miqra:variant noteId="{note_id}">'
            f"<miqra:display>{display}</miqra:display>"
            f"</miqra:variant>"
            f'<miqra:note xml:id="{note_id}">{notes}</miqra:note>'
        )

    def _handle_footnote_mark(self, template) -> str:
        return "<miqra:fn-mark/>"

    def _handle_ketiv_qeri(self, template) -> str:
        ketiv = self._p(self._param(template, 1))
        qeri = self._p(self._param(template, 2))
        return (
            f'<miqra:kq order="ketiv-first">'
            f"<miqra:ketiv>{ketiv}</miqra:ketiv>"
            f"<miqra:qeri>{qeri}</miqra:qeri>"
            f"</miqra:kq>"
        )

    def _handle_qeri_ketiv(self, template) -> str:
        ketiv = self._p(self._param(template, 1))
        qeri = self._p(self._param(template, 2))
        return (
            f'<miqra:kq order="qeri-first">'
            f"<miqra:ketiv>{ketiv}</miqra:ketiv>"
            f"<miqra:qeri>{qeri}</miqra:qeri>"
            f"</miqra:kq>"
        )

    def _handle_qok_if_matres(self, template) -> str:
        display = self._p(self._param(template, 1))
        ketiv = self._p(self._param(template, 2))
        qeri = self._p(self._param(template, 3))
        return (
            f"{display}"
            f'<miqra:kq-matres>'
            f"<miqra:ketiv>{ketiv}</miqra:ketiv>"
            f"<miqra:qeri>{qeri}</miqra:qeri>"
            f"</miqra:kq-matres>"
        )

    def _handle_qok_two_qeri_words(self, template) -> str:
        ketiv = self._p(self._param(template, 1))
        q1 = self._p(self._param(template, 2))
        q2 = self._p(self._param(template, 3))
        return (
            f'<miqra:kq order="qeri-first" type="split-qeri">'
            f"<miqra:bracketed>{q1}</miqra:bracketed>"
            f"<miqra:qeri>{q2}</miqra:qeri>"
            f"<miqra:ketiv>{ketiv}</miqra:ketiv>"
            f"</miqra:kq>"
        )

    def _handle_ketiv_only(self, template) -> str:
        ketiv = self._p(self._param(template, 1))
        return f'<miqra:ketiv-only>({ketiv})</miqra:ketiv-only>'

    def _handle_qeri_only(self, template) -> str:
        qeri = self._p(self._param(template, 1))
        return f"<miqra:qeri-only>[{qeri}]</miqra:qeri-only>"

    def _handle_parashah_open(self, template) -> str:
        return f'<miqra:parashah type="open"{self._mid_verse_attr(template)}/>'

    def _handle_parashah_open_line(self, template) -> str:
        return f'<miqra:parashah type="open-line"{self._mid_verse_attr(template)}/>'

    def _handle_parashah_close(self, template) -> str:
        return f'<miqra:parashah type="close"{self._mid_verse_attr(template)}/>'

    def _handle_parashah_close_inline(self, template) -> str:
        return f'<miqra:parashah type="close-inline"{self._mid_verse_attr(template)}/>'

    def _handle_parashah_close_narrow(self, template) -> str:
        return f'<miqra:parashah type="close-narrow"{self._mid_verse_attr(template)}/>'

    def _handle_shirah_break(self, template) -> str:
        return '<miqra:parashah type="shirah"/>'

    def _handle_poetic_space(self, template) -> str:
        return '<miqra:poetic level="0"/>'

    def _handle_poetic_indent1(self, template) -> str:
        return '<miqra:poetic level="1"/>'

    def _handle_poetic_indent2(self, template) -> str:
        return '<miqra:poetic level="2"/>'

    def _handle_poetic_line(self, template) -> str:
        return '<miqra:poetic level="3"/>'

    def _handle_poetic_verse(self, template) -> str:
        return '<miqra:poetic level="4"/>'

    def _handle_centered_title(self, template) -> str:
        title = self._p(self._param(template, 1))
        return f"<miqra:centered>{title}</miqra:centered>"

    def _handle_large_letter(self, template) -> str:
        letter = self._p(self._param(template, 1))
        return f'<miqra:hi rend="large">{letter}</miqra:hi>'

    def _handle_small_letter(self, template) -> str:
        letter = self._p(self._param(template, 1))
        return f'<miqra:hi rend="small">{letter}</miqra:hi>'

    def _handle_raised_letter(self, template) -> str:
        letter = self._p(self._param(template, 1))
        return f'<miqra:hi rend="raised">{letter}</miqra:hi>'

    def _handle_dotted_letter(self, template) -> str:
        word = self._p(self._param(template, 1))
        return f"<miqra:dotted>{word}</miqra:dotted>"

    def _handle_inverted_nun(self, template) -> str:
        sym = self._p(self._param(template, 1))
        return f"<miqra:inverted-nun>{sym}</miqra:inverted-nun>"

    def _handle_yerushalem(self, template) -> str:
        p1 = _xml_escape(self._param(template, 1))
        p2 = _xml_escape(self._param(template, 2))
        return f'<miqra:yerushalem vowel="{p1}" accent="{p2}"/>'

    def _handle_yerushalema(self, template) -> str:
        p1 = _xml_escape(self._param(template, 1))
        p2 = _xml_escape(self._param(template, 2))
        return f'<miqra:yerushalema vowel="{p1}" accent="{p2}"/>'

    def _handle_accent_yerah(self, template) -> str:
        return '<miqra:accent type="yerah-ben-yomo"/>'

    def _handle_accent_galgal(self, template) -> str:
        return '<miqra:accent type="galgal"/>'

    def _handle_accent_with_word(self, template) -> str:
        # Word param already includes the accent (galgal / yerah ben yomo).
        return self._p(self._param(template, 1))

    def _handle_accent_etnah(self, template) -> str:
        return '<miqra:accent type="etnah-hafukh"/>'

    def _handle_qamats(self, template) -> str:
        d = self._named_param(template, "ד")
        s = self._named_param(template, "ס")
        text = d or s or self._param(template, 1)
        return self._p(text)

    def _handle_taam_meteg(self, template) -> str:
        return self._p(self._param(template, 1))

    def _handle_two_taamim(self, template) -> str:
        return '<miqra:accent type="geresh-telisha-gedola"/>'

    def _handle_two_taamim_qupo(self, template) -> str:
        above = self._p(self._named_param(template, "עליו") or self._param(template, 1))
        return f'<miqra:qupo-accent above="{_xml_escape(above)}"/>'

    def _handle_taam_dummy(self, template) -> str:
        raw = self._param(template, 1)
        return self._p(raw[1:] if raw else "")

    def _handle_geresh_telisha(self, template) -> str:
        return '<miqra:accent type="geresh-telisha-gedola"/>'

    def _handle_gershayim_telisha(self, template) -> str:
        return '<miqra:accent type="gershayim-telisha-gedola"/>'

    def _handle_kol_qamats(self, template) -> str:
        return self._p(self._param(template, 1)) or "כָּל"

    def _handle_legarmeh(self, template) -> str:
        return '<miqra:punct type="legarmeh">׀</miqra:punct>'

    def _handle_paseq(self, template) -> str:
        return '<miqra:punct type="paseq">׀</miqra:punct>'

    def _handle_grey_maqaf(self, template) -> str:
        return '<miqra:maqaf rend="grey">־</miqra:maqaf>'

    def _handle_dechi(self, template) -> str:
        # Wikisource shows param 1; param 2 marks the dechi (offset accent) form.
        return self._p(self._param(template, 1))

    def _handle_tzinor(self, template) -> str:
        # Wikisource shows param 1; param 2 marks the tzinor accent placement.
        return self._p(self._param(template, 1))

    def _handle_mam_note(self, template) -> str:
        body = self._p(self._param(template, 1))
        note_id = self._next_note_id()
        return (
            f'<miqra:anchor xml:id="{note_id}-ref"/>'
            f'<miqra:note xml:id="{note_id}">{body}</miqra:note>'
        )

    def _handle_line_anchor(self, template) -> str:
        label = _xml_escape(self._param(template, 1))
        return f'<miqra:line-anchor target="{label}"/>'

    def _handle_good_ending(self, template) -> str:
        text = self._p(self._param(template, 1))
        return f"<miqra:good-ending>{text}</miqra:good-ending>"

    def _handle_dual_trope_link(self, template) -> str:
        target = self._p(self._param(template, 1))
        return f"<miqra:dual-trope-link>{target}</miqra:dual-trope-link>"

    def _handle_dual_accent(self, template) -> str:
        dual = self._p(self._named_param(template, "כפול"))
        a = self._p(self._named_param(template, "א"))
        b = self._p(self._named_param(template, "ב"))
        return (
            f'<miqra:dual-accent dual="{_xml_escape(dual)}">'
            f"<miqra:strand role=\"א\">{a}</miqra:strand>"
            f"<miqra:strand role=\"ב\">{b}</miqra:strand>"
            f"</miqra:dual-accent>"
        )

    def _handle_note_link(self, template) -> str:
        raw_target = self._named_param(template, "1") or self._param(template, 1)
        label = self._named_param(template, "2") or self._param(template, 2)
        if not label:
            label = raw_target
        target = _xml_escape(link_target_to_uri(raw_target))
        return f'<mw:link target="{target}">{self._p(label)}</mw:link>'

    def _handle_emphasis(self, template) -> str:
        text = self._p(self._param(template, 1))
        return f'<mw:hi rend="bold">{text}</mw:hi>'


_processor: Optional[MiqraWikiTextProcessor] = None


def _get_processor() -> MiqraWikiTextProcessor:
    global _processor
    if _processor is None:
        _processor = MiqraWikiTextProcessor()
    return _processor


def wikitext_to_intermediate_xml(
    wikitext: str, *, column_c: bool = False
) -> str:
    """Convert wikitext to an escaped intermediate XML fragment."""
    text = wikitext or ""
    if column_c:
        text = _preprocess_column_c(text)
    result = _get_processor().process_wikitext(text)
    return _escape_outside_tags(result.xml_content)


def reset_processor() -> None:
    """Reset the shared processor (for tests)."""
    global _processor
    _processor = None

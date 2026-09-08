"""Envelope for the hand-authored Birnbaum TEI.

The bodies are written by hand, read off the scan, one function per prayer. This module
holds only what every file repeats: the header, the URN, the source pointer and the page
break sigils. Scaffolding — the TEI files it writes are the artifact.
"""
from pathlib import Path

PROJECT_HE = "birnbaum_ashkenaz_he_1949"
PROJECT_EN = "birnbaum_ashkenaz_en_1949"
#: Where the TEI is written. The opensiddur-projects submodule by default, so a fresh
#: checkout writes somewhere that exists; --project-directory overrides it, spelled the way
#: the compiler and pdf exporters already spell that flag.
DEFAULT_PROJECT_DIRECTORY = Path(__file__).resolve().parents[4] / "opensiddur-projects" / "project"
OUT = DEFAULT_PROJECT_DIRECTORY


def set_project_directory(path) -> Path:
    """Point the writers at `path`. Returns it, so a caller can report where it wrote."""
    global OUT
    OUT = Path(path)
    return OUT

IA = "https://archive.org/download/PhilipBirnbaumHaSiddurHaShalemTheDailyPrayerBook1949/page"
# printed page -> IA leaf, from pages.json. Leaf = scan page - 1, scan page = printed + 25.
LEAF = {p: p + 24 for p in range(81, 99)}

#: The second @ed token names which printing a break belongs to, since a shared text is
#: printed at several services. See SIDDUR_URN_SCHEME.md, "One text, printed on several pages".
SIGIL = "1949 chol/shacharit/amidah"

PRAYER = "urn:x-opensiddur:text:prayer:"
SIDDUR = "urn:x-opensiddur:text:siddur:"


def pb(page: int) -> str:
    """A page break, deep-linked to the leaf it falls on."""
    return f'<tei:pb n="{page}" ed="{SIGIL}" facs="{IA}/n{LEAF[page]}_medium.jpg"/>'


def header(*, title_he: str, title_en: str, urn: str, project: str,
           first: int, last: int, lang: str) -> str:
    """The teiHeader every file carries.

    Philip Birnbaum gets no respStmt: a respStmt records who *digitised* a text, and he
    is the author, recorded as a source. The people who read this off the scan are the
    ones who digitised it.
    """
    if title_he:
        titles = f'<tei:title type="main" xml:lang="he">{title_he}</tei:title>'
        if title_en:
            titles += f'\n        <tei:title type="alt" xml:lang="en">{title_en}</tei:title>'
    else:
        titles = f'<tei:title type="main" xml:lang="en">{title_en}</tei:title>'
    scope = (f'<tei:biblScope unit="pages" from="{first}" to="{last}"/>'
             if first else "")
    return f"""  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt>
        {titles}
        <tei:respStmt>
          <tei:resp key="trc">Read from the 1949 scan and encoded by</tei:resp>
          <tei:name ref="urn:x-opensiddur:contributor:opensiddur.org/efraim-feinstein">Efraim Feinstein</tei:name>
        </tei:respStmt>
      </tei:titleStmt>
      <tei:editionStmt>
        <tei:edition>Read directly from the scanned 1949 printing, page by page</tei:edition>
      </tei:editionStmt>
      <tei:publicationStmt>
        <tei:distributor>
          <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
        </tei:distributor>
        <tei:idno type="urn">{urn}@{project}</tei:idno>
        <tei:availability status="free">
          <tei:licence target="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc>
        <tei:bibl>
          <tei:ptr target="/{project}/index#project_source_bibl"/>
          {scope}
        </tei:bibl>
      </tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>"""


def document(*, body: str, lang: str, **kw) -> str:
    return (f'<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" '
            f'xmlns:j="http://jewishliturgy.org/ns/jlptei/2" xml:lang="{lang}">\n'
            f'{header(lang=lang, **kw)}\n'
            f'  <tei:text>\n    <tei:body>\n{body}\n    </tei:body>\n  </tei:text>\n'
            f'</tei:TEI>\n')


def write(project: str, name: str, text: str) -> Path:
    path = OUT / project / f"{name}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def cond(cid: str, *, note: str = "", note_lang: str = "en", fs: str = "", negate: bool = False) -> str:
    """A j:conditional: the rubric the edition prints, and the test it states."""
    parts = [f'        <j:conditional xml:id="{cid}">']
    if note:
        parts.append(f'          <tei:note type="instruction" xml:lang="{note_lang}">{note}</tei:note>')
    if negate:
        parts.append("          <j:none>")
        parts.append(fs)
        parts.append("          </j:none>")
    else:
        parts.append(fs)
    parts.append("        </j:conditional>")
    return "\n".join(parts)


def endcond(cid: str) -> str:
    return f'        <j:endConditional target="#{cid}"/>'


def feature(fs_type: str, name: str, value: str = '<tei:binary value="true"/>') -> str:
    return (f'          <tei:fs type="{fs_type}">\n'
            f'            <tei:f name="{name}">\n'
            f'              {value}\n'
            f'            </tei:f>\n'
            f'          </tei:fs>')


AGG = "opensiddur:holiday-aggregate"
HOL = "opensiddur:holiday"
SERVICE = "opensiddur:service-time"
RECITATION = "opensiddur:recitation"
QUORUM = "opensiddur:quorum"

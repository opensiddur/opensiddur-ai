# -*- coding: utf-8 -*-
"""The project index: the book's running order, and its front matter.

One function for both projects. The English index used to be derived from the Hebrew one
by byte-exact string replacement, which meant reflowing the Hebrew literal silently
changed the English file; the two now differ only in the arguments passed here.
"""
from .common import PROJECT_EN, PROJECT_HE, SIDDUR

S = SIDDUR

#: What each project says it is. The English is Birnbaum's own translation, and that is
#: said here and in a note beside the citation -- not as a respStmt, which records who
#: *digitised* a text rather than who wrote the one being digitised.
EDITION = {
    PROJECT_HE: "Read directly from the scanned 1949 printing, page by page. "
                "Not derived from any transcription of it.",
    PROJECT_EN: "Birnbaum’s own English, read from the facing pages of the scanned "
                "1949 printing",
}
TRANSLATION_NOTE = ("The English of this project is Birnbaum’s own translation, printed "
                    "on the pages facing the Hebrew.")

#: The running order, in the order the book prints it. Shaḥarith li-Yladim is on pages
#: 1-2 and so comes first. It is filed under the occasion `all` rather than `chol`: a
#: child says it every morning, Sabbaths and festivals included, and filing it under
#: weekdays would be a claim the book does not make. See SIDDUR_URN_SCHEME.md.
BODY = f"""      <tei:div corresp="{S}siddur">
        <tei:div corresp="{S}all">
          <tei:div corresp="{S}all/shacharit">
            <j:transclude type="external" target="{S}all/shacharit/yeladim"/>
          </tei:div>
        </tei:div>
        <tei:div corresp="{S}chol">
          <tei:div corresp="{S}chol/shacharit">
            <j:transclude type="external" target="{S}chol/shacharit/amidah"/>
          </tei:div>
        </tei:div>
      </tei:div>"""


def index(*, project: str, lang: str, front: str) -> str:
    """One project's ``index.xml``: its header, its front matter and its running order."""
    notes = ""
    if project == PROJECT_EN:
        notes = f'          <tei:note xml:lang="en">{TRANSLATION_NOTE}</tei:note>\n'
    return f"""<tei:TEI xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2" xml:lang="{lang}">
  <tei:teiHeader>
    <tei:fileDesc>
      <tei:titleStmt>
        <tei:title type="main" xml:lang="he">הַסִּדּוּר הַשָּׁלֵם</tei:title>
        <tei:title type="alt" xml:lang="en">ha-Siddur ha-Shalem (The Daily Prayer Book)</tei:title>
        <tei:respStmt>
          <tei:resp key="trc">Read from the 1949 scan and encoded by</tei:resp>
          <tei:name ref="urn:x-opensiddur:contributor:opensiddur.org/efraim-feinstein">Efraim Feinstein</tei:name>
        </tei:respStmt>
      </tei:titleStmt>
      <tei:editionStmt>
        <tei:edition>{EDITION[project]}</tei:edition>
      </tei:editionStmt>
      <tei:publicationStmt>
        <tei:distributor>
          <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
        </tei:distributor>
        <tei:idno type="urn">{S}siddur@{project}</tei:idno>
        <tei:availability status="free">
          <tei:licence target="https://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International</tei:licence>
        </tei:availability>
      </tei:publicationStmt>
      <tei:sourceDesc>
        <tei:bibl xml:id="project_source_bibl">
          <tei:title>ha-Siddur ha-Shalem: The Daily Prayer Book</tei:title>
          <tei:author>Philip Birnbaum</tei:author>
          <tei:publisher>Hebrew Publishing Company</tei:publisher>
          <tei:pubPlace>New York</tei:pubPlace>
          <tei:date when="1949">1949</tei:date>
          <tei:date type="accessed" when="2026-09-08">2026-09-08</tei:date>
          <tei:idno type="url">https://archive.org/details/PhilipBirnbaumHaSiddurHaShalemTheDailyPrayerBook1949</tei:idno>
          <tei:idno type="archive.org">PhilipBirnbaumHaSiddurHaShalemTheDailyPrayerBook1949</tei:idno>
{notes}          <tei:note xml:lang="en">The scan cited here is the source of the text, not merely a reference for it: every word was read off it, page by page.</tei:note>
          <tei:note type="encoding" xml:lang="en">Every tei:pb/@facs in this project deep-links into the leaf its page break falls on. The scan is 1541x2291 pixels per leaf, which is the scan itself and not a derivative.</tei:note>
          <tei:note type="encoding" xml:lang="en">In the front matter, tei:pb/@n in square brackets is a designation the book implies rather than prints. The printed Roman sequence runs IX to XXIII on scan leaves 11 to 25, which fixes leaf 3 as I; leaves 1 and 2 precede that sequence and are numbered from the scan.</tei:note>
        </tei:bibl>
      </tei:sourceDesc>
    </tei:fileDesc>
  </tei:teiHeader>
  <tei:text>
{front}
    <tei:body>
{BODY}
    </tei:body>
  </tei:text>
</tei:TEI>
"""

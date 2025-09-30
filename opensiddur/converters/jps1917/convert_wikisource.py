# TODO: validate XML

from pathlib import Path
from typing import Any, Optional
import urllib

from pydantic import BaseModel

from opensiddur.converters.agent.tools import get_credits, get_page
from opensiddur.converters.jps1917.mediawiki_processor import create_processor
from opensiddur.converters.util.prettify import prettify_xml
from opensiddur.converters.util.xslt import xslt_transform_string

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent.parent.parent / "project" / "jps1917" 

class Book(BaseModel):
    book_name_he: str
    book_name_en: str
    file_name: str
    start_page: int
    end_page: int
    is_section: Optional[bool] = False

class Index(BaseModel):
    index_title_en: str
    index_title_he: Optional[str] = None
    index_sub_he: Optional[str] = None
    index_sub_en: Optional[str] = None
    file_name: str
    transclusions: list #[Book | Index]
    start_page: Optional[int] = None
    end_page: Optional[int] = None

PAGE_OFFSET = 22

JPS_1917 = [
    Index(
        index_title_en = "The Holy Scriptures",
        index_title_he = "תורה נביאים וכתובים",
        index_sub_he = None,
        index_sub_en = "According to the Masoretic Text: A New Translation With The Aid of Previous Versions And With Constant Consultation of Jewish Authorities",
        file_name = "index",
        # preface = front matter
        start_page = 9,
        end_page = 18,
        transclusions = [
            Index(
                index_title_en = "The Law",
                index_title_he = "תורה",
                file_name = "the_law",
                transclusions = [
                    Book(
                        book_name_en = "Genesis", 
                        book_name_he = "בראשית", 
                        file_name = "genesis", 
                        start_page = 3+PAGE_OFFSET, 
                        end_page = 64+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Exodus", 
                        book_name_he = "שמות", 
                        file_name = "exodus", 
                        start_page = 65+PAGE_OFFSET, 
                        end_page = 117+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Leviticus", 
                        book_name_he = "ויקרא", 
                        file_name = "leviticus", 
                        start_page = 118+PAGE_OFFSET, 
                        end_page = 156+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Numbers", 
                        book_name_he = "במדבר", 
                        file_name = "numbers", 
                        start_page = 157+PAGE_OFFSET, 
                        end_page = 211+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Deuteronomy", 
                        book_name_he = "דברים", 
                        file_name = "deuteronomy", 
                        start_page = 212+PAGE_OFFSET, 
                        end_page = 258+PAGE_OFFSET
                    ),
                ],
            ),
            Index(
                index_title_en = "The Prophets",
                index_title_he = "נביאים",
                file_name = "the_prophets",
                transclusions = [
                    Book(
                        book_name_en = "Joshua",
                        book_name_he = "יהושע",
                        file_name = "joshua",
                        start_page = 261+PAGE_OFFSET,
                        end_page = 292+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Judges",
                        book_name_he = "שפטים",
                        file_name = "judges",
                        start_page = 293+PAGE_OFFSET,
                        end_page = 324+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "I Samuel",
                        book_name_he = "שמואל א",
                        file_name = "samuel_1",
                        start_page = 325+PAGE_OFFSET,
                        end_page = 365+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "II Samuel",
                        book_name_he = "שמואל ב",
                        file_name = "samuel_2",
                        start_page = 366+PAGE_OFFSET,
                        end_page = 400+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "I Kings",
                        book_name_he = "מלכים א",
                        file_name = "kings_1",
                        start_page = 401+PAGE_OFFSET,
                        end_page = 440+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "II Kings",
                        book_name_he = "מלכים ב",
                        file_name = "kings_2",
                        start_page = 441+PAGE_OFFSET,
                        end_page = 478+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Isaiah",
                        book_name_he = "ישעיה",
                        file_name = "isaiah",
                        start_page = 479+PAGE_OFFSET,
                        end_page = 560+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Jeremiah",
                        book_name_he = "ירמיה",
                        file_name = "jeremiah",
                        start_page = 561+PAGE_OFFSET,
                        end_page = 643+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Ezekiel",
                        book_name_he = "יחזקאל",
                        file_name = "ezekiel",
                        start_page = 644+PAGE_OFFSET,
                        end_page = 708+PAGE_OFFSET
                    ),
                    Index(
                        index_title_en = "The Twelve",
                        file_name = "the_twelve",
                        transclusions = [
                            Book(
                                book_name_en = "Hosea",
                                book_name_he = "הושע",
                                file_name = "hosea",
                                start_page = 709+PAGE_OFFSET,
                                end_page = 720+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Joel",
                                book_name_he = "יואל",
                                file_name = "joel",
                                start_page = 720+PAGE_OFFSET,
                                end_page = 725+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Amos",
                                book_name_he = "עמוס",
                                file_name = "amos",
                                start_page = 725+PAGE_OFFSET,
                                end_page = 734+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Obadiah",
                                book_name_he = "עובדיה",
                                file_name = "obadiah",
                                start_page = 734+PAGE_OFFSET,
                                end_page = 736+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Jonah",
                                book_name_he = "יונה",
                                file_name = "jonah",
                                start_page = 736+PAGE_OFFSET,
                                end_page = 739+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Micah", 
                                book_name_he = "מיכה",
                                file_name = "micah",
                                start_page = 739+PAGE_OFFSET,
                                end_page = 746+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Nahum",
                                book_name_he = "נחום",
                                file_name = "nahum",
                                start_page = 746+PAGE_OFFSET,
                                end_page = 749+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Habakkuk",
                                book_name_he = "חבקוק",
                                file_name = "habakkuk",
                                start_page = 749+PAGE_OFFSET,
                                end_page = 753+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Zephaniah",
                                book_name_he = "צפניה",
                                file_name = "zephaniah",
                                start_page = 753+PAGE_OFFSET,
                                end_page = 757+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Haggai",
                                book_name_he = "חגי",
                                file_name = "haggai",
                                start_page = 757+PAGE_OFFSET,
                                end_page = 759+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Zechariah",
                                book_name_he = "זכריה",
                                file_name = "zechariah",
                                start_page = 759+PAGE_OFFSET,
                                end_page = 770+PAGE_OFFSET,
                                is_section = True,
                            ),
                            Book(
                                book_name_en = "Malachi",
                                book_name_he = "מלאכי",
                                file_name = "malachi",
                                start_page = 770+PAGE_OFFSET,
                                end_page = 776+PAGE_OFFSET,
                                is_section = True,
                            ),
                        ],
                    ),
                ],
            ),
            Index(
                index_title_en = "The Writings",
                index_title_he = "כתובים",
                file_name = "the_writings",
                transclusions = [
                    Book(
                        book_name_en = "Psalms",
                        book_name_he = "תהילים",
                        file_name = "psalms",
                        start_page = 777+PAGE_OFFSET,
                        end_page = 882+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Proverbs",
                        book_name_he = "משלי",
                        file_name = "proverbs",
                        start_page = 883+PAGE_OFFSET,
                        end_page = 923+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Job",
                        book_name_he = "איוב",
                        file_name = "job",
                        start_page = 924+PAGE_OFFSET,
                        end_page = 965+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Song of Songs",
                        book_name_he = "שיר השירים",
                        file_name = "song_of_songs",
                        start_page = 966+PAGE_OFFSET,
                        end_page = 972+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Ruth",
                        book_name_he = "רות",
                        file_name = "ruth",
                        start_page = 973+PAGE_OFFSET,
                        end_page = 977+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Lamentations",
                        book_name_he = "איכה",
                        file_name = "lamentations",
                        start_page = 978+PAGE_OFFSET,
                        end_page = 986+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Ecclesiastes",
                        book_name_he = "קהלת",
                        file_name = "ecclesiastes",
                        start_page = 987+PAGE_OFFSET,
                        end_page = 996+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Esther",
                        book_name_he = "אסתר",
                        file_name = "esther",
                        start_page = 997+PAGE_OFFSET,
                        end_page = 1006+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Daniel",
                        book_name_he = "דניאל",
                        file_name = "daniel",
                        start_page = 1007+PAGE_OFFSET,
                        end_page = 1026+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "Ezra",
                        book_name_he = "עזרא",
                        file_name = "ezra",
                        start_page = 1027+PAGE_OFFSET,
                        end_page = 1039+PAGE_OFFSET,
                        is_section = True,
                    ),
                    Book(
                        book_name_en = "Nehemiah",
                        book_name_he = "נחמיה",
                        file_name = "nehemiah",
                        start_page = 1039+PAGE_OFFSET,
                        end_page = 1057+PAGE_OFFSET,
                        is_section = True,
                    ),
                    Book(
                        book_name_en = "I Chronicles",
                        book_name_he = "דברי הימים א",
                        file_name = "chronicles_1",
                        start_page = 1058+PAGE_OFFSET,
                        end_page = 1093+PAGE_OFFSET
                    ),
                    Book(
                        book_name_en = "II Chronicles",
                        book_name_he = "דברי הימים ב",
                        file_name = "chronicles_2",
                        start_page = 1094+PAGE_OFFSET,
                        end_page = 1136+PAGE_OFFSET
                    ),
                ],
            )
        ],
    ),
]

def get_credits_pages(start_page: int, end_page: int) -> list[str]:
    credits = set()
    for page in range(start_page, end_page + 1):
        page_credits = get_credits(page)
        if page_credits is not None:
            credits.update(page_credits)
    return sorted(credits)

def header(
    book_name_he: str,
    book_name_en: str,
    book_sub_he: Optional[str] = None,
    book_sub_en: Optional[str] = None,
    namespace: str = "bible",
    entrypoint: str = "tanakh",
    qualifier: str = "",
    project_id: str = "jps1917",
    license_url: str = "http://www.creativecommons.org/publicdomain/zero/1.0/",
    license_name: str = "Creative Commons Public Domain Dedication 1.0",
    transcription_credits: Optional[list[str]] = None,
):
    transcription_credits = transcription_credits or []
    book_sub_he = (
        f"""<tei:title type="alt-sub" xml:lang="he">{book_sub_he}</tei:title>"""
        if book_sub_he else ""
    )
    book_sub_en = (
        f"""<tei:title type="alt-sub" xml:lang="en">{book_sub_en}</tei:title>"""
        if book_sub_en else ""
    )

    resp_stmt_str = "\n".join([
        f"""<tei:respStmt>
            <tei:resp key="trc">Transcribed by</tei:resp>
            <tei:name ref="urn:x-opensiddur:contributor:en.wikisource.org/{urllib.parse.quote(contributor_name)}">{contributor_name} (English Wikisource contributor)</tei:name>
        </tei:respStmt>"""
        for contributor_name in transcription_credits if contributor_name != "Wikisource-bot"
    ])

    return f"""<tei:teiHeader>
    <tei:fileDesc>
        <tei:titleStmt>
            <tei:title type="main" xml:lang="en">{book_name_en}</tei:title>
            {book_sub_en}
            <tei:title type="alt" xml:lang="he">{book_name_he}</tei:title>
            {book_sub_he}
            {resp_stmt_str}
         </tei:titleStmt>
         <tei:publicationStmt>
            <tei:distributor>
               <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
            </tei:distributor>
            <tei:idno type="urn">urn:x-opensiddur:text:{namespace}:{entrypoint}{qualifier}@{project_id}</tei:idno>
            <tei:availability status="free">
               <tei:licence target="{license_url}">{license_name}</tei:licence>
            </tei:availability>
         </tei:publicationStmt>
         <tei:sourceDesc>
            <tei:bibl>
                <tei:title>Bible (Jewish Publication Society 1917)</tei:title>
                <tei:distributor><tei:ref target="https://en.wikisource.org">Wikisource</tei:ref></tei:distributor>
                <tei:idno type="url">https://en.wikisource.org/wiki/Bible_(Jewish_Publication_Society_1917)</tei:idno>
                <tei:date>2025-07-27</tei:date>
            </tei:bibl>
            <tei:bibl>
               <tei:title type="main">The Holy Scriptures</tei:title>
               <tei:title type="sub">According to the Masoretic Text: A New Translation With The Aid of Previous Versions And With Constant Consultation of Jewish Authorities</tei:title>
               <tei:title xml:lang="he" type="alt">תורה נביאים וכתובים</tei:title>
               <tei:edition>Third Impression, August 1919</tei:edition>
               <tei:publisher>Jewish Publication Society of America</tei:publisher>
               <tei:pubPlace>Philadelphia</tei:pubPlace>
               <tei:date>1917</tei:date>
               <tei:note>Lakeside Press, Chicago</tei:note>
            </tei:bibl>
        </tei:sourceDesc>
    </tei:fileDesc>
</tei:teiHeader>
"""

def tei_file(
    header: str,
    default_lang: str = "en",
    front: Optional[str] = "",
    body: str = "",
    back: Optional[str] = "",
    standOff: Optional[str] = "",
):
    return f"""<tei:TEI xml:lang="{default_lang}" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    {header}
    <tei:text>
    {front}
    {body}
    {back}
    </tei:text>
    {standOff}
    </tei:TEI>
    """

def mediawiki_xml_to_tei(xml_content: str, xslt_params: Optional[dict[str, Any]] = None):
    xslt_file = Path(__file__).parent / "mediawiki_to_tei.xslt"
    outputs = xslt_transform_string(xslt_file, xml_content, multiple_results=True, xslt_params=xslt_params)
    return {
        "front": outputs[""] if "tei:front" in outputs[""] else "",
        "body": outputs[""] if "tei:body" in outputs[""] else "",
        "standOff": outputs["standoff"] if "standoff" in outputs and "tei:note" in outputs["standoff"] else "",
    }

def process_mediawiki(
    start_page: int, 
    end_page: int, 
    wrapper_element: str,
    **kwargs,
) -> str:
    mw_processor = create_processor()
    start_page = start_page
    end_page = end_page

    content = ""
    for page in range(start_page, end_page + 1):
        print(f"Processing page {page}")
        page_content = get_page.invoke({"page_number": page}).content
        content += " " + mw_processor.process_wikitext(page_content).xml_content

    pre_xml = f"""<tei:{wrapper_element} xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <mediawikis>{content}</mediawikis>
    </tei:{wrapper_element}>
    """
    with open("temp.xml", "w") as f:
        f.write(pre_xml)
    return mediawiki_xml_to_tei(pre_xml, xslt_params=kwargs)

def book_file(book: Book) -> str:
    transcription_credits = get_credits_pages(book.start_page, book.end_page)
    header_content = header(
        book_name_he = book.book_name_he,
        book_name_en = book.book_name_en,
        transcription_credits = transcription_credits,
    )
    xml_dict = process_mediawiki(book.start_page, book.end_page, "body", 
        wrapper_div_type="book",
        book_name=book.file_name,
        is_section=book.is_section)
    
    tei_content = tei_file(
        header = header_content,
        **xml_dict,
    )
    with open("temp.tei.xml", "w") as f:
        f.write(tei_content)
    with open(PROJECT_DIRECTORY / f"{book.file_name}.xml", "w") as f:
        print(f"Writing {PROJECT_DIRECTORY / f'{book.file_name}.xml'}")
        f.write(prettify_xml(tei_content))

    return tei_content


def index_file(idx: Index) -> str:
    if idx.start_page is not None and idx.end_page is not None:
        transcription_credits = get_credits_pages(idx.start_page, idx.end_page)
    else:
        transcription_credits = None
    header_content = header(
        book_name_he = idx.index_title_he,
        book_name_en = idx.index_title_en,
        book_sub_he = idx.index_sub_he,
        book_sub_en = idx.index_sub_en,
        transcription_credits = transcription_credits,
    )
    if idx.start_page is not None and idx.end_page is not None:
        xml_dict = process_mediawiki(idx.start_page, idx.end_page, "front",
            wrapper_div_type="",
            book_name="")
    else:
        xml_dict = {}

    transclusion_str = "\n".join([
        f"""<j:transclude target="urn:x-opensiddur:text:bible:{book.file_name}"/>"""
        for book in idx.transclusions
    ])
    index_body = f"""<tei:body>
    <tei:div>
        <tei:head>{idx.index_title_en}</tei:head>
        {transclusion_str}
    </tei:div>
</tei:body>
    """
    xml_dict["body"] = index_body

    tei_content = tei_file(
        header = header_content,
        **xml_dict,
    )
    with open("temp.tei.xml", "w") as f:
        f.write(tei_content)
    with open(PROJECT_DIRECTORY / f"{idx.file_name}.xml", "w") as f:
        print(f"Writing {PROJECT_DIRECTORY / f'{idx.file_name}.xml'}")
        f.write(prettify_xml(tei_content))

    for transclusion in idx.transclusions:
        if isinstance(transclusion, Index):
            index_file(transclusion)
        else:
            book_file(transclusion)
    
    return tei_content

def main():
    PROJECT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for part in JPS_1917:
        index_file(part)

if __name__ == "__main__":
    main()
"""Synthetic opensiddur.org posts for the importer's tests. Nothing here reads sourcetexts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"

CC_BY_SA = "<a href='https://creativecommons.org/licenses/by-sa/4.0/'>Creative Commons Attribution-ShareAlike 4.0 International</a>"

#: Coauthor entries as the export writes them.
TRANSLATOR = {"name": "Rivka Translator (translation)",
              "profile_link": "https://opensiddur.org/profile/rivka-translator-translation"}
TRANSCRIBER = {"name": "Rivka Translator (transcription &amp; naqdanut)",
               "profile_link": "https://opensiddur.org/profile/rivka-translator-transcription"}
POET = {"name": "Yehudah Poet", "profile_link": "https://opensiddur.org/profile/yehudah-poet"}
PRINT_TRANSLATOR = {"name": "Old Print Translator (translation)",
                    "profile_link": "https://opensiddur.org/profile/old-print-translator"}
UNKNOWN_TRANSLATOR = {"name": "Unknown (translation)", "profile_link": "https://opensiddur.org/profile/unknown"}
NEW_PERSON = {"name": "New Person (transcription)",
              "profile_link": "https://opensiddur.org/profile/new-person-transcription"}


def cell(lang: str, css: str, body: str) -> str:
    return f'<td style="vertical-align:top;"><div class="{css}" lang="{lang}">\n{body}\n</div></td>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(f"<tr>{''.join(r)}</tr>" for r in rows)
    return (
        '<table class="draggable toggleable-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


HEBREW_EN_ROWS = [
    [cell("heb-Hebr", "liturgy", "בָּרוּךְ אַתָּה<br />\n<span class=\"divine-referent\">יהוה</span> אֱלֹהֵינוּ"),
     cell("eng-Latn", "english", "Blessed are You,<br />\n<span class=\"divine-referent\">Adonai</span> <span class=\"divine-referent\">our God</span>")],
    [cell("heb-Hebr", "liturgy", "<span class=\"acrostic\">א</span>שִׁירָה<br />\nלְךָ&nbsp;<br />\n&nbsp;<br />\nשִׁיר שֵׁנִי"),
     cell("eng-Latn", "english", "I will <em>sing</em><br />\nto You<br />\n&nbsp;<br />\na second song <span class=\"citation\">(Psalms 1:1)</span>")],
]


def two_column_content(*, intro: str = "<p>An introduction.</p>", notes: str = "") -> str:
    parts = [intro, "<hr />", table(["Source (Hebrew)", "Translation (English)"], HEBREW_EN_ROWS)]
    if notes:
        parts += ["<hr />", notes]
    return "\n".join(parts)


def make_post(
    post_id: int = 101,
    *,
    content: str | None = None,
    title: str = "שִׁירָה | A Song",
    slug: str = "a-song",
    coauthors: list[dict[str, str]] | None = None,
    licence: str = CC_BY_SA,
    last_updated: str = "2026-09-01",
    tags: list[str] | None = None,
    date_src: tuple[str, str] = ("2020-01-01", "2020-01-01"),
) -> dict[str, Any]:
    return {
        "post_id": post_id,
        "title": title,
        "author": "",
        "coauthors": coauthors if coauthors is not None else [TRANSLATOR, POET],
        "date": "2020-01-01",
        "last_updated": last_updated,
        "excerpt": "",
        "content": content if content is not None else two_column_content(),
        "categories": ["Ḥanukkah"],
        "tags": tags or [],
        "custom_fields": {
            "open_content_license": [licence] if licence else [],
            "languages_meta": ['[{"name":"Hebrew","code":"heb"},{"name":"English","code":"eng"}]'],
            "date_src_start": [date_src[0]],
            "date_src_end": [date_src[1]],
        },
        "featured_image": {},
        "source_link": f"https://opensiddur.org/?p={post_id}",
        "permalink": f"https://opensiddur.org/prayers/festivals/{slug}/",
        "slug": slug,
    }


def write_data_dir(root: Path, posts: list[dict[str, Any]], *, commit: str = "c0ffee" * 6 + "abcd") -> Path:
    """A sourcetexts ``opensiddur_org`` directory holding ``posts``, as the download writes it."""
    data_dir = root / "opensiddur_org"
    (data_dir / "posts").mkdir(parents=True, exist_ok=True)
    for name in ("categories.json", "contributors_by_id.json"):
        (data_dir / name).write_text((FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8")
    entries = {}
    for post in posts:
        (data_dir / "posts" / f"{post['post_id']}.json").write_text(json.dumps(post, ensure_ascii=False), encoding="utf-8")
        entries[str(post["post_id"])] = {"path": f"posts/x/{post['slug']}_({post['post_id']}).json",
                                         "last_updated": post["last_updated"], "sha256": "0" * 64}
    manifest = {"upstream_repo": "https://example.org/export.git", "upstream_commit": commit,
                "upstream_commit_date": "2026-10-01", "categories": [1132], "posts": entries}
    (data_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return data_dir

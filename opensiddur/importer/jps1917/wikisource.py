import argparse
import random
import sys
import time
import xml.etree.ElementTree as et
from pathlib import Path

import requests

from opensiddur.importer.util.pages import default_sourcetexts_root, jps1917_data_directory

server = "en.wikisource.org"
wiki_namespace = "Page"
book_name = "JPS-1917-Universal.djvu"
start_page = 443  # 7
pages = range(start_page, 1158 + 1)

# Backward-compatible name for JPS tree under sourcetexts
jps1917_output_directory = jps1917_data_directory

# Default layout (legacy): <repo>/sources/jps1917
output_directory = jps1917_data_directory()


def wiki_url(book_name, page_num, action="raw", namespace=wiki_namespace):
    return f"/w/index.php?title={wiki_namespace}:{book_name}/{page_num}&action={action}"


def get_wiki_page(book_name, page_num, dry_run=True):
    path = "https://" + server + wiki_url(book_name, page_num)
    headers = {
        "User-Agent": "OpenSiddur-AI/1.0 (https://github.com/opensiddur/opensiddur-ai; opensiddur@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    if dry_run:
        print(f"Would retrieve text: {page_num} from {path}")
    else:
        r = requests.get(path, headers=headers, timeout=60)
        if r.status_code >= 400:
            print(f"Error retrieving page {page_num}")
        else:
            return r.text


def get_wiki_contributors(book_name, page_num, dry_run=True):
    path = "https://" + server + wiki_url(book_name, page_num, action="history&feed=atom")
    headers = {
        "User-Agent": "OpenSiddur-AI/1.0 (https://github.com/opensiddur/opensiddur-ai; opensiddur@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }
    if dry_run:
        print(f"Would retrieve history: {page_num} from {path}")
    else:
        r = requests.get(path, headers=headers, timeout=60)
        if r.status_code >= 400:
            print(f"Error retrieving history {page_num}: {r.status_code} {r.text}")
        else:
            feed = et.XML(r.text)
            return list(
                set(
                    [
                        element.find("{http://www.w3.org/2005/Atom}name").text
                        for element in feed.findall(".//{http://www.w3.org/2005/Atom}author")
                    ]
                )
            )


def download_book(dry_run: bool = True, sourcetexts_root: Path | None = None) -> None:
    out = jps1917_output_directory(sourcetexts_root)
    digits = len(str(max(pages)))
    format_string = "%%0%dd" % digits

    out.mkdir(parents=True, exist_ok=True)
    (out / "text").mkdir(parents=True, exist_ok=True)
    (out / "credits").mkdir(parents=True, exist_ok=True)

    for page_num in pages:
        print("Page: %d" % page_num)
        success = False
        retries = 0
        while not success and retries < 3:
            try:
                wp = get_wiki_page(book_name, page_num, dry_run=dry_run)
                wc = get_wiki_contributors(book_name, page_num, dry_run=dry_run)
                success = True
            except Exception as e:
                print(f"Exception: {e} -- waiting 5s to recover...")
                retries += 1
                if retries >= 3:
                    raise
                time.sleep(5.0)
        output_filename = (format_string % page_num) + ".txt"
        text_path = out / "text" / output_filename
        credits_path = out / "credits" / output_filename
        if dry_run:
            print(f"{page_num}: {text_path=}, {credits_path=}")
        else:
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(wp)
            time.sleep(1.3 + random.random())
            with open(credits_path, "w", encoding="utf-8") as f:
                f.write("\n".join(w for w in wc if w != "Wikisource-bot"))
            time.sleep(1.3 + random.random())


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download JPS 1917 Bible pages from English Wikisource into the sourcetexts tree."
    )
    parser.add_argument(
        "--sourcetexts-root",
        type=Path,
        default=default_sourcetexts_root(),
        help=(
            "Root of the opensiddur/sourcetexts repository; page text is written under "
            "<root>/jps1917 (default: <repo>/sources for legacy sources/jps1917)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned fetches and paths without writing files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    download_book(dry_run=args.dry_run, sourcetexts_root=args.sourcetexts_root)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

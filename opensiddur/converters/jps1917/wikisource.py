import random
import requests
import os
import time
import xml.etree.ElementTree as et
from pathlib import Path

# constants
server="en.wikisource.org"
output_directory = Path(__file__).parent.parent.parent.parent / "sources" / "jps1917"
wiki_namespace = "Page"
book_name = "JPS-1917-Universal.djvu"
start_page = 443 #7
pages = range(start_page,1158+1)

def wiki_url(book_name, page_num, action="raw", namespace=wiki_namespace):
    return f"/w/index.php?title={wiki_namespace}:{book_name}/{page_num}&action={action}"

def get_wiki_page(book_name, page_num, dry_run=True):
    path = "https://" + server + wiki_url(book_name, page_num)
    headers = {
        'User-Agent': 'OpenSiddur-AI/1.0 (https://github.com/opensiddur/opensiddur-ai; opensiddur@example.com)',
        'Accept-Encoding': 'gzip, deflate'
    }
    if dry_run:
        print(f"Would retrieve text: {page_num} from {path}")
    else:
        r = requests.get(path, headers=headers)
        if r.status_code >= 400:
            print(f"Error retrieving page {page_num}")
        else:
            return r.text

def get_wiki_contributors(book_name, page_num, dry_run=True):
    path = "https://" + server + wiki_url(book_name, page_num, action="history&feed=atom")
    headers = {
        'User-Agent': 'OpenSiddur-AI/1.0 (https://github.com/opensiddur/opensiddur-ai; opensiddur@example.com)',
        'Accept-Encoding': 'gzip, deflate'
    }
    if dry_run:
        print(f"Would retrieve history: {page_num} from {path}")
    else:
        r = requests.get(path, headers=headers)
        if r.status_code >= 400:
            print(f"Error retrieving history {page_num}: {r.status_code} {r.text}")
        else:
            feed = et.XML(r.text)
            return list(set([element.find("{http://www.w3.org/2005/Atom}name").text for element in feed.findall(".//{http://www.w3.org/2005/Atom}author")]))

def download_book(dry_run=True):
    digits = len(str(max(pages)))
    format_string = "%%0%dd" % digits

    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "text").mkdir(parents=True, exist_ok=True)
    (output_directory / "credits").mkdir(parents=True, exist_ok=True)

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
        text_path = os.path.join(output_directory, "text", output_filename)
        credits_path = os.path.join(output_directory, "credits", output_filename)
        if dry_run:
            print(f"{page_num}: {text_path=}, {credits_path=}")
        else:
            with open(text_path, "w") as f:
                f.write(wp)
            time.sleep(1.3 + random.random())
            with open(credits_path, "w") as f:
                f.write("\n".join(w for w in wc if w != "Wikisource-bot"))
            time.sleep(1.3 + random.random())

if __name__ == "__main__":
    download_book(dry_run=False)
    
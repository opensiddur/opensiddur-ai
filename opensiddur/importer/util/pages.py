from typing import Optional

from opensiddur.importer.util.constants import CREDITS_PATH, TEXT_PATH, Page


def get_page(page_number: str | int) -> Optional[Page]:
    """Return the wikitext of the given Page, or None if it does not exist"""
    page_num = int(page_number)
    page_file_name = f"{page_num:04d}.txt"
    try:
        with open(TEXT_PATH / page_file_name, "r") as f:
            return Page.model_validate(dict(number=page_num, content=f.read()))
    except FileNotFoundError:
        return None

def get_credits(page_number: str | int) -> Optional[list[str]]:
    """ Return the credits of the given Page, or None if it does not exist """
    page_num = int(page_number)
    page_file_name = f"{page_num:04d}.txt"
    try:
        with open(CREDITS_PATH / page_file_name, "r") as f:
            return [line.strip() for line in f.read().split("\n") if line.strip()]
    except FileNotFoundError:
        return None
from pydantic import BaseModel, Field

from pathlib import Path
BASE_PATH = Path(".").absolute().parent.parent.parent
DATA_PATH = BASE_PATH / "sources" / "1917jps-wikisource"
TEXT_PATH = DATA_PATH / "text"
CREDITS_PATH = DATA_PATH / "credits"
SCHEMA_PATH = BASE_PATH / "schema"
SCHEMA_DOCUMENTATION_PATH = SCHEMA_PATH / "JLPTEI-3.md"
SCHEMA_ODD_PATH = SCHEMA_PATH / "jlptei.odd.xml"
SCHEMA_RNG_PATH = SCHEMA_PATH / "jlptei.odd.xml.relaxng"
SCHEMA_SCH_PATH = SCHEMA_PATH / "jlptei.odd.xml.schematron"
SCHEMA_SCH_XSLT_PATH = SCHEMA_PATH / "jlptei.odd.xml.schematron.xslt"
VECTOR_DB_PATH = BASE_PATH / "private" /"jlptei_vector_db"

LLM_BASE_URL = "https://api.deepinfra.com/v1/openai"
with open(BASE_PATH / "opensiddur" / "private" / "api_key.txt", "r") as f:
    API_KEY = f.read().strip()


class Page(BaseModel):
    number: int = Field(description = "Page sequence number")
    content: str = Field(description = "Page content")

class OutlineItem(BaseModel):
    section_title: str = Field(description="Title of the section")
    start_page: int = Field(description="Page number of the first page of the section")


class Outline(BaseModel):
    outline: list[OutlineItem] = Field(description="Outline of the book")
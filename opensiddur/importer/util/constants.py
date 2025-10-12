from pathlib import Path

BASE_PATH = Path(__file__).absolute().parent.parent.parent.parent
DATA_PATH = BASE_PATH / "sources" / "jps1917"
TEXT_PATH = DATA_PATH / "text"
CREDITS_PATH = DATA_PATH / "credits"
SCHEMA_PATH = BASE_PATH / "schema"
SCHEMA_DOCUMENTATION_PATH = SCHEMA_PATH / "JLPTEI-3.md"
SCHEMA_ODD_PATH = SCHEMA_PATH / "jlptei.odd.xml"
SCHEMA_RNG_PATH = SCHEMA_PATH / "jlptei.odd.xml.relaxng"
SCHEMA_SCH_PATH = SCHEMA_PATH / "jlptei.odd.xml.schematron"
SCHEMA_SCH_XSLT_PATH = SCHEMA_PATH / "jlptei.odd.xml.schematron.xslt"

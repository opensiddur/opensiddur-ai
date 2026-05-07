"""Shared exporter constants (kept dependency-light to avoid circular imports)."""

JLPTEI_NAMESPACE = "http://jewishliturgy.org/ns/jlptei/2"
PROCESSING_NAMESPACE = "http://jewishliturgy.org/ns/processing"

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

STRUCTURAL_BLOCKS = frozenset(
    {
        f"{{{TEI_NS}}}div",
        f"{{{TEI_NS}}}p",
        f"{{{TEI_NS}}}ab",
        f"{{{TEI_NS}}}lg",
        f"{{{TEI_NS}}}l",
    }
)


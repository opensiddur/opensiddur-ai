"""Shared exporter constants (kept dependency-light to avoid circular imports)."""

from lxml.etree import ElementBase

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


def is_element_node(node: ElementBase) -> bool:
    """True for element nodes.

    lxml sets the tag of a comment to the etree.Comment factory function and of a processing
    instruction to etree.PI, so anything that rebuilds a node from its tag must filter them out.
    """
    return isinstance(node.tag, str)


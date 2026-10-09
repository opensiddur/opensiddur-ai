"""Resolve page pointers against content surviving compilation, before typesetting or rendering."""
import hashlib
from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
P = "http://jewishliturgy.org/ns/processing"


def _remove_preserving_tail(node):
    parent = node.getparent()
    previous = node.getprevious()
    if previous is None:
        parent.text = (parent.text or "") + (node.tail or "")
    else:
        previous.tail = (previous.tail or "") + (node.tail or "")
    parent.remove(node)


def resolve_page_references(root):
    """Replace edition-qualified text URNs with labels in the compiled edition.

    Optional spans disappear when any of their destinations is absent. Repeated
    content uses the first surviving occurrence in the requested source edition.
    """
    ns = {"tei": TEI}
    if not root.xpath(".//tei:ref[@type='page']", namespaces=ns):
        return
    destinations = {}
    for node in root.iter():
        project = next((a.get("{" + P + "}project") for a in
                        [node, *node.iterancestors()] if a.get("{" + P + "}project")), None)
        for urn in node.get("corresp", "").split():
            if project and node.tag != "{" + TEI + "}note":
                destinations.setdefault(urn + "@" + project, node)
    for span in list(root.xpath(".//tei:seg[@type='optional-page-reference']", namespaces=ns)):
        if any(ref.get("target") not in destinations for ref in
               span.xpath(".//tei:ref[@type='page']", namespaces=ns)):
            note = span.getparent()
            _remove_preserving_tail(span)
            if (note.tag == "{" + TEI + "}note" and note.get("type") == "instruction"
                    and not len(note) and not (note.text or "").strip()):
                _remove_preserving_tail(note)
    labelled = set()
    for ref in root.xpath(".//tei:ref[@type='page']", namespaces=ns):
        target = ref.get("target")
        node = destinations.get(target)
        if node is None:
            raise ValueError(f"Page reference destination absent: {target}")
        label = "os-page-" + hashlib.sha256(target.encode()).hexdigest()[:20]
        ref.set("target", label)
        if target not in labelled:
            anchor = etree.Element("{" + TEI + "}anchor", type="page-label", n=label)
            if node.tag in {"{" + TEI + "}milestone", "{" + TEI + "}anchor"}:
                anchor.tail, node.tail = node.tail, None
                node.addnext(anchor)
            else:
                anchor.tail, node.text = node.text, None
                node.insert(0, anchor)
            labelled.add(target)

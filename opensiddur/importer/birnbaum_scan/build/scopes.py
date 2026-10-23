"""Keep a whole section's headings inside the condition governing its text.

The hand-authored units put their printed heading ahead of the body. When the
body is entirely conditional, that heading has the same eligibility. Mixed
sections keep their independent headings and conditions unchanged.
"""

from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
J = "http://jewishliturgy.org/ns/jlptei/2"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
HEAD, PB = f"{{{TEI}}}head", f"{{{TEI}}}pb"
DECLARE, END_DECLARE = f"{{{J}}}declare", f"{{{J}}}endDeclare"
CONDITIONAL, END_CONDITIONAL = f"{{{J}}}conditional", f"{{{J}}}endConditional"


def scope_section_headings(body: str) -> str:
    root = etree.fromstring(
        f'<root xmlns:tei="{TEI}" xmlns:j="{J}">{body}</root>'.encode())
    changed = False
    for div in root.findall(f"{{{TEI}}}div"):
        children = list(div)
        first = next((i for i, child in enumerate(children)
                      if child.tag == CONDITIONAL), None)
        if first is None:
            continue
        prefix = children[:first]
        if (not any(child.tag == HEAD for child in prefix)
                or any(child.tag not in {HEAD, PB, DECLARE} for child in prefix)):
            continue
        conditional = children[first]
        target = "#" + conditional.get(XML_ID, "")
        last = next((i for i, child in enumerate(children)
                     if child.tag == END_CONDITIONAL and child.get("target") == target), None)
        if last is None or any(child.tag not in {PB, END_DECLARE}
                               for child in children[last + 1:]):
            continue
        # Non-whitespace text outside the markers makes this a mixed section too.
        outside = [div.text, *(child.tail for child in prefix),
                   *(child.tail for child in children[last:])]
        if any(text and text.strip() for text in outside):
            continue
        div.remove(conditional)
        div.insert(0, conditional)
        # Enclose declarations completely; their end markers must also be skipped
        # when the condition rejects the section.
        declarations = [child for child in children[last + 1:]
                        if child.tag == END_DECLARE]
        if declarations:
            closer = children[last]
            div.remove(closer)
            declarations[-1].addnext(closer)
        changed = True
    if not changed:
        return body
    result = (root.text or "") + "".join(
        etree.tostring(child, encoding="unicode") for child in root)
    # The document envelope already declares these namespaces.
    return result.replace(f' xmlns:tei="{TEI}"', "").replace(f' xmlns:j="{J}"', "")

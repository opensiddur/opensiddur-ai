"""Anchor a structural annotation on the first words of the element it annotates.

A standoff ``tei:note`` whose target is a whole structural element used to be inserted
as that element's first child. That is ahead of the element's ``tei:head`` and, more
damagingly, ahead of its first ``tei:milestone[@corresp]`` — the boundary parallel
alignment cuts on. The anchor then landed in a different row from the words it
annotates, and reledmac spent a line, or a whole one-sided row, on the mark alone.

So the note is placed at the target's *first substantive text slot* instead: the
position immediately before the first non-whitespace character of the target's own
body text. The search walks the target's content in document order and

* skips a ``tei:head`` whole — a heading is not the annotated text, and the stylesheet
  hoists it out of the flow anyway (see the ``tei:div`` leaves template in
  reledmac.xslt);
* does not descend into a ``tei:milestone``, whose children may be apparatus parked
  there by the compiler for :mod:`opensiddur.exporter.milestone_annotations`, but does
  consider its tail — which is what carries the anchor across the first alignment
  boundary and into the right row;
* stops in front of any other ``tei:note``. A rubric is a block of its own, so the
  anchor belongs before it, not inside it;
* gives up at a transclusion or a ``p:suspend`` carrier, which would take the anchor
  across a row boundary into content the target does not own.

When there is no such slot — an empty target, a heading-only target, a target whose
whole content is an external transclusion — the caller keeps the placement it used
before, so an apparatus is never lost.

The target's subtree is complete at every insertion site, so this resolves during
compilation and needs no deferred pass; contrast ``place_milestone_annotations``,
where the scope ends at a later milestone that may be in another file.
"""
from lxml import etree

from opensiddur.exporter.constants import (
    JLPTEI_NAMESPACE,
    PROCESSING_NAMESPACE,
    TEI_NS,
    is_element_node,
)

HEAD = f"{{{TEI_NS}}}head"
MILESTONE = f"{{{TEI_NS}}}milestone"
NOTE = f"{{{TEI_NS}}}note"

P_SUSPEND = f"{{{PROCESSING_NAMESPACE}}}suspend"

# Content the target does not own: crossing one of these would anchor the note in a
# different alignment row, or inside another document's text.
_BOUNDARY_TAGS = frozenset({
    f"{{{PROCESSING_NAMESPACE}}}transclude",
    f"{{{PROCESSING_NAMESPACE}}}transcludeInline",
    f"{{{PROCESSING_NAMESPACE}}}parallel",
    f"{{{JLPTEI_NAMESPACE}}}transclude",
})

# Returned by the scan when it ran into a boundary, as distinct from finding nothing:
# both mean "no slot", but keeping them apart documents why.
_ABORT = object()


def _has_text(value) -> bool:
    return bool(value) and bool(value.strip())


def _scan(nodes):
    for node in nodes:
        if is_element_node(node):
            if node.tag in _BOUNDARY_TAGS or node.get(P_SUSPEND) is not None:
                return _ABORT
            if node.tag == NOTE:
                return (node, 'before')
            if node.tag not in (HEAD, MILESTONE):
                if _has_text(node.text):
                    return (node, 'text')
                found = _scan(list(node))
                if found is not None:
                    return found
        if _has_text(node.tail):
            return (node, 'tail')
    return None


def find_text_slot(nodes, owner=None, owner_attr='text'):
    """Locate the first substantive text slot in ``nodes``.

    ``owner`` is the element whose content ``nodes`` is, when there is one: its
    ``text`` (a tree target) or its ``tail`` (the ``p:start`` carrier of a flat marker
    stream) is the first candidate. Returns a ``(node, attr)`` pair where ``attr`` is
    ``'text'``, ``'tail'`` or ``'before'``, or ``None`` when there is no slot.
    """
    if owner is not None and _has_text(getattr(owner, owner_attr, None)):
        return (owner, owner_attr)
    found = _scan(list(nodes))
    return None if found is _ABORT or found is None else found


def insert_at_slot(slot, notes, container=None):
    """Put ``notes``, in order, at ``slot``.

    The slot's leading whitespace stays in front of the anchor and the rest of the text
    follows it, so the mark sits against the first word rather than against the source
    indentation. ``container`` is the flat element list to fall back on when the slot's
    node has no parent, as happens at the top level of a marker stream.
    """
    node, attr = slot

    def place_siblings(offset_of_first):
        # A node the flat stream holds directly is positioned in the list, whether or
        # not it also happens to have a parent; only a nested one is positioned in the
        # tree. Marker-stream carriers are built detached, so the two never disagree in
        # the compiler — but a caller should not have to know that.
        in_container = container is not None and any(n is node for n in container)
        parent = None if in_container else node.getparent()
        if parent is None:
            index = ([n is node for n in container].index(True) + offset_of_first)
            container[index:index] = notes
        else:
            index = parent.index(node) + offset_of_first
            for offset, note in enumerate(notes):
                parent.insert(index + offset, note)

    if attr == 'before':
        place_siblings(0)
        return

    value = getattr(node, attr) or ''
    leading = value[:len(value) - len(value.lstrip())]
    rest = value.lstrip()
    setattr(node, attr, leading)
    if attr == 'text':
        for offset, note in enumerate(notes):
            node.insert(offset, note)
    else:
        place_siblings(1)
    notes[-1].tail = (notes[-1].tail or '') + rest


def place_structural_annotations(nodes, notes, owner=None, owner_attr='text',
                                 container=None):
    """Anchor ``notes`` on the first words of the target described by ``nodes``.

    Returns True when a slot was found and the notes were placed, False when the caller
    should fall back to its own placement.
    """
    if not notes:
        return False
    slot = find_text_slot(nodes, owner=owner, owner_attr=owner_attr)
    if slot is None:
        return False
    insert_at_slot(slot, notes, container=container)
    return True


def place_structural_annotations_in_tree(target: etree.ElementBase, notes) -> bool:
    """Tree form: ``target`` is the compiled element the notes annotate."""
    return place_structural_annotations(list(target), notes, owner=target,
                                        owner_attr='text')


def place_structural_annotations_in_stream(stream, start_marker, notes) -> bool:
    """Flat marker form: ``stream`` opens with ``start_marker`` and holds its scope."""
    index = stream.index(start_marker)
    return place_structural_annotations(stream[index + 1:], notes,
                                        owner=start_marker, owner_attr='tail',
                                        container=stream)

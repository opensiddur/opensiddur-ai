"""
Reconstruct flattened p:start / p:suspend / p:resume / p:end streams inside
parallel export columns into nested TEI, then prune empty segments and set p:part.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

from opensiddur.exporter.constants import PROCESSING_NAMESPACE, STRUCTURAL_BLOCKS

_P_START = f"{{{PROCESSING_NAMESPACE}}}start"
_P_END = f"{{{PROCESSING_NAMESPACE}}}end"
_P_SUSPEND = f"{{{PROCESSING_NAMESPACE}}}suspend"
_P_RESUME = f"{{{PROCESSING_NAMESPACE}}}resume"
_P_LOGICAL = f"{{{PROCESSING_NAMESPACE}}}logical-id"
_P_PART = f"{{{PROCESSING_NAMESPACE}}}part"
_PARALLEL_ITEM = f"{{{PROCESSING_NAMESPACE}}}parallelItem"
_PARALLEL = f"{{{PROCESSING_NAMESPACE}}}parallel"


def _structural_marker_map(el: etree.ElementBase) -> dict[str, str]:
    out = {}
    for key, pname in (
        (_P_START, "start"),
        (_P_END, "end"),
        (_P_SUSPEND, "suspend"),
        (_P_RESUME, "resume"),
    ):
        if val := el.get(key):
            out[pname] = val
    return out


def substantive_content(el: etree.ElementBase) -> bool:
    def walk(x: etree.ElementBase) -> bool:
        if (x.text or "").strip():
            return True
        for c in x:
            if walk(c):
                return True
            if (c.tail or "").strip():
                return True
        return False

    return walk(el)


@dataclass
class _Frame:
    pid: str
    tag: str
    attrs: dict[str, str]
    buffer: list[etree.ElementBase] = field(default_factory=list)
    #: Text serialized before structural children (marker text/tails from compiler)
    text_chunks: list[str] = field(default_factory=list)


def _absorb_marker_strings(frame: _Frame, el: etree.ElementBase) -> None:
    if el.text:
        frame.text_chunks.append(el.text)
    if el.tail:
        frame.text_chunks.append(el.tail)


def _carrier_attrs_from_marker_el(el: etree.ElementBase) -> dict[str, str]:
    p_pref = f"{{{PROCESSING_NAMESPACE}}}"
    xml_id_key = "{http://www.w3.org/XML/1998/namespace}id"
    return {k: v for k, v in el.attrib.items() if k != xml_id_key and not k.startswith(p_pref)}


def _new_wrapped_segment(
    tag: str,
    attrs: dict[str, str],
    children: list[etree.ElementBase],
    *,
    logical_id: str | None,
    leading_text_chunks: list[str],
) -> etree.ElementBase:
    nsmap = dict(children[0].nsmap) if children else {}
    wrapped = etree.Element(tag, nsmap=nsmap) if nsmap else etree.Element(tag)
    for k, v in attrs.items():
        wrapped.set(k, v)
    prefix = "".join(leading_text_chunks)
    leading_text_chunks.clear()
    if prefix:
        wrapped.text = prefix
    for c in children:
        wrapped.append(c)

    marker_keys = (_P_START, _P_SUSPEND, _P_RESUME, _P_END, _P_LOGICAL, _P_PART)
    for mk in marker_keys:
        if mk in wrapped.attrib:
            del wrapped.attrib[mk]

    if logical_id:
        wrapped.set(_P_LOGICAL, logical_id)
    return wrapped


def _close_open_segment(
    stack: list[_Frame],
    fragments: list[etree.ElementBase],
    pid_state: dict[str, dict[str, Any]],
    *,
    pid: str,
    kind: str,
) -> None:
    if not stack:
        raise ValueError(f"p:{kind} for {pid=} with empty reconstruction stack")

    frame = stack.pop()
    if frame.pid != pid:
        raise ValueError(f"p:{kind} expected top frame pid={pid}, got {frame.pid}")

    st = pid_state.setdefault(pid, {})
    suspended_before = st.get("suspended", False)
    logical_id: str | None = None

    if kind == "suspend":
        st["suspended"] = True
        logical_id = pid
    elif kind == "end":
        if suspended_before:
            logical_id = pid
        pid_state.pop(pid, None)
    else:
        raise ValueError(kind)

    wrapped = _new_wrapped_segment(
        frame.tag,
        frame.attrs,
        frame.buffer,
        logical_id=logical_id,
        leading_text_chunks=frame.text_chunks,
    )

    if stack:
        stack[-1].buffer.append(wrapped)
    else:
        fragments.append(wrapped)


def _move_plain_content(
    el: etree.ElementBase,
    stack: list[_Frame],
    fragments: list[etree.ElementBase],
) -> None:
    if stack:
        stack[-1].buffer.append(el)
    else:
        fragments.append(el)


def reconstruct_parallel_item(
    pi: etree.ElementBase,
    pid_state: defaultdict[str, dict[str, Any]],
) -> None:
    """Rebuild pi's direct linear stream into nested TEI fragments (mutating pi)."""
    fragments: list[etree.ElementBase] = []
    stack: list[_Frame] = []

    while len(pi) > 0:
        el = pi[0]
        pi.remove(el)

        mmap = _structural_marker_map(el)

        if el.tag not in STRUCTURAL_BLOCKS:
            _move_plain_content(el, stack, fragments)
            continue

        if not mmap:
            _move_plain_content(el, stack, fragments)
            continue

        if "start" in mmap:
            pid = mmap["start"]
            fr = _Frame(pid, el.tag, _carrier_attrs_from_marker_el(el), [])
            _absorb_marker_strings(fr, el)
            stack.append(fr)
            continue

        if "resume" in mmap:
            pid = mmap["resume"]
            fr = _Frame(pid, el.tag, _carrier_attrs_from_marker_el(el), [])
            _absorb_marker_strings(fr, el)
            stack.append(fr)
            continue

        if "suspend" in mmap:
            _close_open_segment(stack, fragments, pid_state, pid=mmap["suspend"], kind="suspend")
            continue

        if "end" in mmap:
            _close_open_segment(stack, fragments, pid_state, pid=mmap["end"], kind="end")
            continue

        _move_plain_content(el, stack, fragments)

    if stack:
        raise ValueError(f"unclosed structural frames remain in parallelItem: {[f.pid for f in stack]}")

    for frag in fragments:
        pi.append(frag)


def _collect_logical_buckets(root: etree.ElementBase) -> dict[str, list[etree.ElementBase]]:
    buckets: dict[str, list[etree.ElementBase]] = defaultdict(list)
    for el in root.iter():
        lid = el.get(_P_LOGICAL)
        if lid:
            buckets[lid].append(el)
    return buckets


def normalize_segment_parts(root: etree.ElementBase) -> None:
    buckets = _collect_logical_buckets(root)
    stray_markers = {_P_START, _P_SUSPEND, _P_RESUME, _P_END}

    for _lid, elems in buckets.items():
        for e in list(elems):
            if substantive_content(e):
                continue
            parent = e.getparent()
            if parent is not None:
                parent.remove(e)

        surviving = [e for e in elems if e.getparent() is not None]

        for e in surviving:
            for mk in stray_markers:
                if mk in e.attrib:
                    del e.attrib[mk]

        for e in surviving:
            if _P_PART in e.attrib:
                del e.attrib[_P_PART]

        if len(surviving) == 1:
            el = surviving[0]
            el.attrib.pop(_P_LOGICAL, None)
        elif len(surviving) > 1:
            for i, el in enumerate(surviving):
                if i == 0:
                    el.set(_P_PART, "first")
                elif i == len(surviving) - 1:
                    el.set(_P_PART, "last")
                else:
                    el.set(_P_PART, "middle")
                el.attrib.pop(_P_LOGICAL, None)


def _strip_stray_processing_markers_under(element: etree.ElementBase) -> None:
    for el in element.iter():
        keys_to_strip = (_P_START, _P_SUSPEND, _P_RESUME, _P_END, _P_LOGICAL)
        for mk in keys_to_strip:
            if mk in el.attrib:
                del el.attrib[mk]


def doc_needs_marker_reconstruction(root: etree.ElementBase) -> bool:
    if root.find(f".//{{{PROCESSING_NAMESPACE}}}parallel") is not None:
        return True
    for el in root.iter():
        if el.tag not in STRUCTURAL_BLOCKS:
            continue
        if any(el.get(attr) for attr in (_P_START, _P_END, _P_SUSPEND, _P_RESUME)):
            return True
    return False


def reconstruct_markered_document(root: etree.ElementBase) -> None:
    pid_state: defaultdict[str, dict[str, Any]] = defaultdict(dict)

    for parallel in root.iter():
        if parallel.tag != _PARALLEL:
            continue
        for pi in parallel:
            if pi.tag == _PARALLEL_ITEM:
                reconstruct_parallel_item(pi, pid_state)

    normalize_segment_parts(root)

    header = root.find(".//{http://www.tei-c.org/ns/1.0}teiHeader")
    if header is not None:
        _strip_stray_processing_markers_under(header)


"""External compiler processor for processing specific ranges of XML files."""

import re
from contextlib import contextmanager
from typing import Any, Optional
from lxml.etree import ElementBase

from opensiddur.exporter.compiler import (
    CompilerProcessor,
    _ProcessingCommand,
    _ProcessingContext,
    _AnnotationCommand,
)
from opensiddur.exporter.conditional_settings import CONDITIONAL_CONTROL_TAGS
from opensiddur.exporter.constants import (
    JLPTEI_NAMESPACE,
    PROCESSING_NAMESPACE,
    STRUCTURAL_BLOCKS,
    TEI_NS,
    XML_NS,
)
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase
from opensiddur.exporter.urn import ResolvedUrnRange, UrnResolver
from lxml import etree

from opensiddur.exporter.marker_reconstruct import (
    doc_needs_marker_reconstruction,
    reconstruct_markered_document,
)


def _attrs_structural_original(source: ElementBase) -> dict[str, str]:
    """Structural node attrs copied onto exporter carriers; never duplicate xml:id."""
    xml_id_key = f"{{{XML_NS}}}id"
    return {k: v for k, v in source.attrib.items() if k != xml_id_key}


def _carrier_attrs_from_marker_el(el: ElementBase, p_ns: str) -> dict[str, str]:
    """Attrs from flattened marker TEI nodes: drop xml:id and p:* markers."""
    xml_id_key = f"{{{XML_NS}}}id"
    p_pref = f"{{{p_ns}}}"
    return {
        k: v
        for k, v in el.attrib.items()
        if k != xml_id_key and not k.startswith(p_pref)
    }


class ExternalCompilerProcessor(CompilerProcessor):
    def _get_deepest_common_ancestor(self,
        from_start: Optional[str] = None,
        to_end: Optional[str] = None,
        include_tail_after_end: bool = False
    ) -> tuple[Optional[ElementBase], Optional[ElementBase], Optional[ElementBase], bool]:
        """
        Get the deepest common ancestor,
        the start element,
        the end element,
        a flag indicating whether to include the tail after the end element

        There is one exception: if start and end are siblings, return the start element.
        We do this because then we don't need the surrounding elements to be copied.
        """
        start_element, end_element = self._get_start_and_end_elements_from_ranges(from_start, to_end)

        if start_element is None or end_element is None:
            return None, None, None, include_tail_after_end

        if start_element is end_element:
            return start_element, start_element, end_element, include_tail_after_end
        if start_element.getparent() is end_element.getparent():
            # siblings... no need to go deeper
            return start_element, start_element, end_element, include_tail_after_end
        end_element_ancestors = set(end_element.iterancestors())
        for element in start_element.iterancestors():
            if element in end_element_ancestors:
                return element, start_element, end_element, include_tail_after_end
        raise ValueError(f"No common ancestor found for {from_start=} and {to_end=}")

    def __init__(
        self,
        project: str,
        file_name: str,
        from_start: Optional[str] = None,
        to_end: Optional[str] = None,
        include_tail_after_end: bool = False,
        linear_data: Optional[LinearData] = None,
        reference_database: Optional[ReferenceDatabase] = None,
        _in_parallel_compilation: bool = False):
        """ Process the given file/project.
        Only start from the given start and end, inclusive.
        Start and end must be in the same file.

        Arguments:
            from_start: the start element path, or None to process the entire file
            to_end: the end element path, or None to process the entire file; always inclusive
            include_tail_after_end: whether to include the tail after the end element
            linear_data: the linear data
            reference_database: the reference database
            _in_parallel_compilation: if True, suppress nested parallel triggers
        """
        super().__init__(project, file_name, linear_data=linear_data, reference_database=reference_database)

        if (from_start is None and to_end is not None) or (from_start is not None and to_end is None):
            raise ValueError("Either from_start or to_end must be None, but not both")
        self.from_start = from_start
        self.to_end = to_end

        self.deepest_common_ancestor, self.start_element, self.end_element, self.include_tail_after_end = self._get_deepest_common_ancestor(from_start, to_end, include_tail_after_end)

        self._in_parallel_compilation = _in_parallel_compilation
        # None = marker mode off; [] = marker mode active
        self.marker_stack: list[tuple[str, ElementBase]] | None = None

    # ── Marker-mode helpers ─────────────────────────────────────────────────

    def _process_element_as_marker(
        self,
        element: ElementBase,
        root: Optional[ElementBase] = None,
        *,
        copy_text: bool = True,
    ) -> list[ElementBase]:
        """Compile element as a marker-ified structural element.

        Emits empty start/end tags with p:start/p:end attributes.
        At external transclusion boundaries, emits p:suspend before and p:resume after.
        """
        p_id = self._get_path_hash(element=element)
        p_ns = PROCESSING_NAMESPACE

        xml_id_key = f"{{{XML_NS}}}id"
        start_marker = etree.Element(element.tag, nsmap=self.ns_map)
        for key, value in element.attrib.items():
            if key == xml_id_key:
                continue
            start_marker.set(key, value)
        start_marker.set(f"{{{p_ns}}}start", p_id)
        # text before first child moves to start_marker.tail
        start_marker.tail = element.text if copy_text else None

        self.marker_stack.append((p_id, element))
        result = [start_marker]

        for child in element:
            is_external_transclude = (
                child.tag == f"{{{JLPTEI_NAMESPACE}}}transclude"
                and child.get('type', 'external') == 'external'
            )
            if is_external_transclude:
                # Suspend: LIFO, no pop
                for sid, selem in reversed(self.marker_stack):
                    suspend = etree.Element(selem.tag, nsmap=self.ns_map)
                    suspend.set(f"{{{p_ns}}}suspend", sid)
                    result.append(suspend)

                transcluded = self._transclude(child, type_override='external')
                if transcluded is not None:
                    result.append(transcluded)

                # Resume: FIFO (copy TEI/XML attrs like xml:lang, not xml:id)
                for sid, selem in self.marker_stack:
                    resume = etree.Element(selem.tag, nsmap=self.ns_map)
                    for k, v in _attrs_structural_original(selem).items():
                        resume.set(k, v)
                    resume.set(f"{{{p_ns}}}resume", sid)
                    result.append(resume)

                if child.tail and result:
                    result[-1].tail = (result[-1].tail or '') + child.tail
            else:
                child_result = self._process_element(child, root)
                result.extend(child_result)
                if child.tail and child_result:
                    last = child_result[-1]
                    last.tail = (last.tail or '') + child.tail

        self.marker_stack.pop()

        end_marker = etree.Element(element.tag, nsmap=self.ns_map)
        end_marker.set(f"{{{p_ns}}}end", p_id)
        end_marker.tail = element.tail
        result.append(end_marker)

        return result

    # ── Parallel-mode helpers ───────────────────────────────────────────────

    @staticmethod
    def _build_parallel_urn(target: str, parallel_project: str) -> str:
        """Replace or append @project suffix to point at parallel_project."""
        if re.search(r'@[\w-]+$', target):
            return re.sub(r'@[\w-]+$', f'@{parallel_project}', target)
        return f"{target}@{parallel_project}"

    @staticmethod
    def _split_at_milestones(
        elements: list[ElementBase],
        ns_map: dict,
    ) -> list[tuple[Optional[str], list[ElementBase]]]:
        """Split a flat marker stream at tei:milestone[@corresp] boundaries.

        Returns a list of (corresp_or_None, [elements]) tuples.
        corresp_or_None is None for content before the first milestone.
        At each milestone, open structural markers are suspended (LIFO) into the
        current sub-segment and resumed (FIFO) into the new sub-segment.
        """
        p_ns = PROCESSING_NAMESPACE
        tei_milestone_tag = f"{{{TEI_NS}}}milestone"

        open_stack: list[dict[str, Any]] = []  # id, tag, attrs (no xml:id, no p:*)
        result: list[tuple[Optional[str], list]] = [(None, [])]

        for el in elements:
            p_start = el.get(f"{{{p_ns}}}start")
            p_end = el.get(f"{{{p_ns}}}end")
            p_suspend = el.get(f"{{{p_ns}}}suspend")
            p_resume = el.get(f"{{{p_ns}}}resume")

            if el.tag == tei_milestone_tag and el.get('corresp'):
                corresp = el.get('corresp')

                # Close current sub-segment: emit suspends LIFO (carry TEI/XML attrs)
                for item in reversed(open_stack):
                    s = etree.Element(item["tag"], nsmap=ns_map)
                    for ak, av in item["attrs"].items():
                        s.set(ak, av)
                    s.set(f"{{{p_ns}}}suspend", item["id"])
                    result[-1][1].append(s)

                # Start new sub-segment
                result.append((corresp, []))

                # Open new sub-segment: emit resumes FIFO
                for item in open_stack:
                    r = etree.Element(item["tag"], nsmap=ns_map)
                    for ak, av in item["attrs"].items():
                        r.set(ak, av)
                    r.set(f"{{{p_ns}}}resume", item["id"])
                    result[-1][1].append(r)

                result[-1][1].append(el)
            else:
                if p_start:
                    open_stack.append({
                        "id": p_start,
                        "tag": el.tag,
                        "attrs": _carrier_attrs_from_marker_el(el, p_ns),
                    })
                elif p_resume:
                    open_stack.append({
                        "id": p_resume,
                        "tag": el.tag,
                        "attrs": _carrier_attrs_from_marker_el(el, p_ns),
                    })
                elif p_end:
                    open_stack = [x for x in open_stack if x["id"] != p_end]
                elif p_suspend:
                    open_stack = [x for x in open_stack if x["id"] != p_suspend]

                result[-1][1].append(el)

        result = [(c, els) for c, els in result if els]
        return result if result else [(None, [])]

    @staticmethod
    def _assemble_parallel_streams(
        primary: list[ElementBase],
        primary_lang: Optional[str],
        primary_project: str,
        primary_file: str,
        parallel: list[ElementBase],
        parallel_lang: Optional[str],
        parallel_project: str,
        parallel_file: str,
        column_order: str,
        ns_map: dict,
    ) -> list[ElementBase]:
        """Zip primary and parallel flat streams into p:parallel / p:transclude pairs.

        Splits each stream at p:transclude elements and at tei:milestone[@corresp]
        boundaries. Returns a list: [p:parallel, p:transclude, p:parallel, ...].
        """
        p_ns = PROCESSING_NAMESPACE
        xml_lang = '{http://www.w3.org/XML/1998/namespace}lang'

        def split_at_transcludes(elements):
            segments = [[]]
            transcludes = []
            for el in elements:
                if el.tag == f"{{{p_ns}}}transclude":
                    transcludes.append(el)
                    segments.append([])
                else:
                    segments[-1].append(el)
            return segments, transcludes

        def make_item(role, lang, project, file_name, elements):
            pi = etree.Element(f"{{{p_ns}}}parallelItem", nsmap=ns_map)
            pi.set("role", role)
            if lang:
                pi.set(xml_lang, lang)
            pi.set(f"{{{p_ns}}}project", project)
            pi.set(f"{{{p_ns}}}file_name", file_name)
            for el in elements:
                pi.append(el)
            return pi

        def make_parallel(col_order, pi_prim, pi_par):
            parallel_el = etree.Element(f"{{{p_ns}}}parallel", nsmap=ns_map)
            parallel_el.set("column-order", col_order)
            parallel_el.append(pi_prim)
            parallel_el.append(pi_par)
            return parallel_el

        def make_rows(prim_flat, par_flat):
            prim_sub = ExternalCompilerProcessor._split_at_milestones(prim_flat, ns_map)
            par_sub = ExternalCompilerProcessor._split_at_milestones(par_flat, ns_map)

            prim_by_c: dict[Optional[str], list] = {}
            for c, els in prim_sub:
                if c not in prim_by_c:
                    prim_by_c[c] = els

            par_by_c: dict[Optional[str], list] = {}
            for c, els in par_sub:
                if c not in par_by_c:
                    par_by_c[c] = els

            seen: set = set()
            ordered = []
            for c, _ in prim_sub:
                if c not in seen:
                    seen.add(c)
                    ordered.append(c)
            for c, _ in par_sub:
                if c not in seen:
                    seen.add(c)
                    ordered.append(c)

            rows = []
            for c in ordered:
                p_elems = prim_by_c.get(c, [])
                q_elems = par_by_c.get(c, [])
                if not p_elems and not q_elems:
                    continue
                rows.append(make_parallel(
                    column_order,
                    make_item("primary", primary_lang, primary_project, primary_file, p_elems),
                    make_item("parallel", parallel_lang, parallel_project, parallel_file, q_elems),
                ))
            return rows

        primary_segments, primary_transcludes = split_at_transcludes(primary)
        parallel_segments, parallel_transcludes = split_at_transcludes(parallel)

        max_segments = max(len(primary_segments), len(parallel_segments))
        while len(primary_segments) < max_segments:
            primary_segments.append([])
        while len(parallel_segments) < max_segments:
            parallel_segments.append([])

        max_transcludes = max(len(primary_transcludes), len(parallel_transcludes))

        output = []
        for i in range(max_segments):
            output.extend(make_rows(primary_segments[i], parallel_segments[i]))

            if i < max_transcludes:
                prim_t = primary_transcludes[i] if i < len(primary_transcludes) else None
                par_t = parallel_transcludes[i] if i < len(parallel_transcludes) else None

                if prim_t is not None:
                    combined = etree.Element(f"{{{p_ns}}}transclude", nsmap=ns_map)
                    for key, val in prim_t.attrib.items():
                        combined.set(key, val)

                    inner_rows = make_rows(list(prim_t), list(par_t) if par_t is not None else [])
                    for row in inner_rows:
                        combined.append(row)

                    output.append(combined)

        return output

    def _resolve_parallel_range(self, target: str, target_end: Optional[str], parallel_project: str):
        """Resolve a parallel URN to (project, file_name, from_start, to_end, include_tail).

        Returns None if the URN cannot be resolved in parallel_project.
        """
        parallel_target = self._build_parallel_urn(target, parallel_project)
        try:
            p_list = self._urn_resolver.resolve_range(parallel_target)
            if not p_list:
                return None
            p_resolved = UrnResolver.prioritize_range(p_list, [parallel_project])
            if not p_resolved:
                return None

            if isinstance(p_resolved, ResolvedUrnRange):
                if target_end is not None:
                    return None  # ambiguous; skip
                p_project = p_resolved.start.project
                p_file = p_resolved.start.file_name
                p_start = p_resolved.start.element_path
                p_end = p_resolved.end.end_element_path or p_resolved.end.element_path
                p_tail = p_resolved.end.end_includes_tail
            else:
                p_project = p_resolved.project
                p_file = p_resolved.file_name
                p_start = p_resolved.element_path
                if target_end is not None:
                    parallel_target_end = self._build_parallel_urn(target_end, parallel_project)
                    pe_list = self._urn_resolver.resolve_range(parallel_target_end)
                    if not pe_list:
                        return None
                    pe_resolved = UrnResolver.prioritize_range(pe_list, [parallel_project])
                    if not pe_resolved:
                        return None
                    p_end = (pe_resolved.end_element_path or pe_resolved.element_path
                             if not isinstance(pe_resolved, ResolvedUrnRange)
                             else pe_resolved.end.end_element_path or pe_resolved.end.element_path)
                    p_tail = (pe_resolved.end_includes_tail
                              if not isinstance(pe_resolved, ResolvedUrnRange)
                              else pe_resolved.end.end_includes_tail)
                else:
                    p_end = p_resolved.end_element_path or p_resolved.element_path
                    p_tail = p_resolved.end_includes_tail

            return p_project, p_file, p_start, p_end, p_tail
        except Exception:
            return None

    def _transclude_parallel(self, element: ElementBase, transclude_range: ResolvedUrnRange, transclusion_type: str) -> Optional[ElementBase]:
        """Compile a transclusion in parallel mode, returning p:transclude(p:parallel(...)).

        Returns None if no parallel project resolves, signalling caller to fall back.
        """
        target = element.get('target')
        target_end = element.get('targetEnd')

        primary_project = transclude_range.start.project
        primary_file = transclude_range.start.file_name
        primary_start = transclude_range.start.element_path
        primary_end = transclude_range.end.end_element_path or transclude_range.end.element_path
        include_tail = transclude_range.end.end_includes_tail

        primary_proc = ExternalCompilerProcessor(
            primary_project, primary_file,
            from_start=primary_start,
            to_end=primary_end,
            include_tail_after_end=include_tail,
            linear_data=self.linear_data,
            reference_database=self._refdb,
            _in_parallel_compilation=True)
        primary_proc.marker_stack = []
        primary_result = primary_proc.process()

        parallel_result = None
        parallel_project = None
        parallel_file = None
        parallel_proc = None

        for proj in self.linear_data.parallel_projects:
            # Never parallelize a project against itself; doing so duplicates streams and
            # can introduce duplicate xml:id values (e.g., anchors) into the assembled output.
            if proj == primary_project:
                continue
            resolved = self._resolve_parallel_range(target, target_end, proj)
            if resolved is None:
                continue
            p_project, p_file, p_start, p_end, p_tail = resolved
            try:
                with self._parallel_priority(p_project):
                    parallel_proc = ExternalCompilerProcessor(
                        p_project, p_file,
                        from_start=p_start,
                        to_end=p_end,
                        include_tail_after_end=p_tail,
                        linear_data=self.linear_data,
                        reference_database=self._refdb,
                        _in_parallel_compilation=True)
                    parallel_proc.marker_stack = []
                    parallel_result = parallel_proc.process()
                parallel_project = p_project
                parallel_file = p_file
                break
            except Exception:
                continue

        if parallel_result is None:
            return None

        assembled = self._assemble_parallel_streams(
            primary_result, primary_proc.root_language,
            primary_project, primary_file,
            parallel_result, parallel_proc.root_language,
            parallel_project, parallel_file,
            str(self.linear_data.parallel_column_order),
            self.ns_map,
        )

        processing_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transclude", nsmap=self.ns_map)
        processing_element.set('target', target)
        if target_end:
            processing_element.set('targetEnd', target_end)
        processing_element.set('type', transclusion_type)
        processing_element.set(f"{{{PROCESSING_NAMESPACE}}}project", primary_project)
        processing_element.set(f"{{{PROCESSING_NAMESPACE}}}file_name", primary_file)

        context_lang = self._get_in_scope_language(element)
        if primary_proc.root_language and context_lang != primary_proc.root_language:
            processing_element.set('{http://www.w3.org/XML/1998/namespace}lang', primary_proc.root_language)

        for child in assembled:
            processing_element.append(child)

        return processing_element

    @contextmanager
    def _parallel_priority(self, parallel_project: str):
        """Temporarily set project_priority and instruction_priority to [parallel_project]."""
        saved_priority = self.linear_data.project_priority
        saved_instr = self.linear_data.instruction_priority
        try:
            self.linear_data.project_priority = [parallel_project]
            self.linear_data.instruction_priority = [parallel_project]
            yield
        finally:
            self.linear_data.project_priority = saved_priority
            self.linear_data.instruction_priority = saved_instr

    def _process_parallel_root(self) -> list[ElementBase]:
        """Compile this file in parallel mode, replacing tei:body with p:parallel content."""
        primary_proc = ExternalCompilerProcessor(
            self.project, self.file_name,
            linear_data=self.linear_data,
            reference_database=self._refdb,
            _in_parallel_compilation=True)
        primary_proc.marker_stack = []
        primary_result = primary_proc.process()

        parallel_result = None
        parallel_project = None
        parallel_file = self.file_name
        parallel_proc = None

        for proj in self.linear_data.parallel_projects:
            # Never parallelize a project against itself.
            if proj == self.project:
                continue
            try:
                with self._parallel_priority(proj):
                    parallel_proc = ExternalCompilerProcessor(
                        proj, self.file_name,
                        linear_data=self.linear_data,
                        reference_database=self._refdb,
                        _in_parallel_compilation=True)
                    parallel_proc.marker_stack = []
                    parallel_result = parallel_proc.process()
                parallel_project = proj
                break
            except Exception:
                continue

        if parallel_result is None:
            return primary_result

        def _body_children(result):
            for el in result:
                if el.tag == f"{{{TEI_NS}}}TEI":
                    body = el.find(f"{{{TEI_NS}}}text/{{{TEI_NS}}}body")
                    if body is None:
                        body = el.find(f".//{{{TEI_NS}}}body")
                    if body is not None:
                        return list(body)
            return result

        assembled = self._assemble_parallel_streams(
            _body_children(primary_result), primary_proc.root_language,
            self.project, self.file_name,
            _body_children(parallel_result), parallel_proc.root_language,
            parallel_project, parallel_file,
            str(self.linear_data.parallel_column_order),
            self.ns_map,
        )

        tei_ns = TEI_NS
        tei_root = None
        for element in primary_result:
            if element.tag == f"{{{tei_ns}}}TEI":
                tei_root = element
                break
        if tei_root is None and primary_result:
            tei_root = primary_result[0]

        if tei_root is not None:
            tei_body = tei_root.find(f"{{{tei_ns}}}text/{{{tei_ns}}}body")
            if tei_body is None:
                tei_body = tei_root.find(f".//{{{tei_ns}}}body")
            if tei_body is not None:
                for child in list(tei_body):
                    tei_body.remove(child)
                tei_body.text = None
                for child in assembled:
                    tei_body.append(child)

        if primary_result:
            self._mark_file_source(primary_result[0])
        return primary_result

    # ── Standard compiler overrides ─────────────────────────────────────────

    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        context = self.linear_data.processing_context[-1]

        # always reset the include_tail_after_end flag
        context['include_tail_after_end'] = False

        context['element_path'] = element.getroottree().getpath(element)
        # Possible contexts:
        #    before the deepest common ancestor has been reached, RECURSE
        #    deepest common ancestor has been reached,
        #      check if this element is the start
        #       if yes, set before_start to False and return COPY_AND_RECURSE,
        #       else
        #           before start? COPY_ELEMENT_AND_RECURSE
        #           after start? COPY_AND_RECURSE
        #    after end, SKIP

        if context['after_end']:
            context['command'] = _ProcessingCommand.SKIP
            return context

        corresp = element.attrib.get("corresp", "")
        xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")

        # is start
        if corresp or xml_id:
            if element is self.start_element:
                context['before_start'] = False
                context['command'] = _ProcessingCommand.COPY_AND_RECURSE
                return context

        # is after start?
        if context['before_start']:
            if element is self.deepest_common_ancestor:
                context['inside_deepest_common_ancestor'] = True
                context['command'] = _ProcessingCommand.COPY_ELEMENT_AND_RECURSE
                return context
            elif context['inside_deepest_common_ancestor']:
                context['command'] = _ProcessingCommand.COPY_ELEMENT_AND_RECURSE
                return context
            else:
                context['command'] = _ProcessingCommand.RECURSE
                return context

        # must be after start and before end
        context['command'] = _ProcessingCommand.COPY_AND_RECURSE
        return context

    def _update_processing_context_after(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        if element is self.deepest_common_ancestor:
            context['inside_deepest_common_ancestor'] = False
            return context


        # always reset the include_tail_after_end flag except for the one case where we are processing the end element
        context["include_tail_after_end"] = False

        if not context['before_start'] and not context['after_end']:
            # between start and end
            if element is self.end_element:
                context['after_end'] = True
                context["include_tail_after_end"] = self.include_tail_after_end

        context['element_path'] = None
        return context

    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> list[ElementBase]:
        """
        Process the given element and return the list of processed elements.
        """
        context = self._update_processing_context_before(element)

        processed = []

        if context["command"] == _ProcessingCommand.SKIP:
            return []

        if (
            self._should_skip_conditional_content()
            and element.tag not in CONDITIONAL_CONTROL_TAGS
        ):
            self._update_processing_context_after(element)
            return []

        if self._handle_settings_element(element):
            self._update_processing_context_after(element)
            return []

        handled, conditional_copy = self._handle_conditional_element(element)
        if handled:
            self._update_processing_context_after(element)
            if conditional_copy is not None:
                return [self._rewrite_ids(conditional_copy)]
            return []

        # In marker mode, all structural blocks use start/end marker pairs
        if self.marker_stack is not None and element.tag in STRUCTURAL_BLOCKS:
            result = self._process_element_as_marker(
                element,
                root,
                copy_text=(context["command"] == _ProcessingCommand.COPY_AND_RECURSE),
            )
            self._update_processing_context_after(element)
            return result

        transcluded = self._transclude(element)
        if transcluded is not None:
            return [transcluded]

        annotations, annotation_command = self._annotate(element, root)
        if annotation_command == _AnnotationCommand.REPLACE:
            return [annotations[0]]

        if context["command"] == _ProcessingCommand.RECURSE:
            append_to = processed
        elif context["command"] == _ProcessingCommand.COPY_ELEMENT_AND_RECURSE:
            copied = etree.Element(element.tag, nsmap=self.ns_map)
            for key, value in element.attrib.items():
                copied.set(key, value)
            processed.append(copied)
            append_to = copied
        elif context["command"] == _ProcessingCommand.COPY_AND_RECURSE:
            copied = etree.Element(element.tag, nsmap=self.ns_map)
            for key, value in element.attrib.items():
                copied.set(key, value)
            copied.text = element.text
            processed.append(copied)
            append_to = copied

        for child in element:
            child_result = self._process_element(child, root)
            append_to.extend(child_result)
            if (
                context["command"] == _ProcessingCommand.COPY_AND_RECURSE
                or context["include_tail_after_end"]):
                if child.tail and child_result:
                    # Only copy tail if we're not after the end marker
                    if context["include_tail_after_end"] or not context['after_end']:
                        if child_result[-1].tail is None:
                            child_result[-1].tail = child.tail
                        else:
                            child_result[-1].tail += child.tail

        if annotation_command == _AnnotationCommand.INSERT:
            for annotation in reversed(annotations):
                # ExternalCompilerProcessor returns a list[Element]; insertion is at the
                # sequence level, not as a child of an element.
                processed.insert(0, annotation)

        processed = self._rewrite_ids(processed)

        self._update_processing_context_after(element)
        return processed

    def process(self, root: Optional[ElementBase] = None) -> list[ElementBase]:
        if root is None:
            root = self.root_tree

        # Root parallel trigger
        is_root = len(self.linear_data.processing_context) == 0
        def _reconstruct_if_needed(processed: list[ElementBase]) -> None:
            if processed and doc_needs_marker_reconstruction(processed[0]):
                reconstruct_markered_document(processed[0])

        if is_root and self.linear_data.parallel_projects and not self._in_parallel_compilation:
            processed = self._process_parallel_root()
            _reconstruct_if_needed(processed)
            return processed

        # set the root language to the language of the deepest common ancestor if present, else root
        self.root_language = self._get_in_scope_language(
            self.deepest_common_ancestor if self.deepest_common_ancestor is not None else root)

        with self._conditional_settings_checkpoint():
            self.linear_data.processing_context.append(_ProcessingContext(
                project=self.project,
                file_name=self.file_name,
                from_start=self.from_start,
                to_end=self.to_end,
                before_start=self.from_start is not None,
                after_end=False,  # We haven't processed anything yet, so we're not after end
                include_tail_after_end=False,
                command=_ProcessingCommand.RECURSE,
                inside_deepest_common_ancestor=False,
            ))

            processed = self._process_element(root, root)

            # pop the processing context
            self.linear_data.processing_context.pop()

        # When processing the full file (not a range transclusion), mark the file source on the root element
        # so that get_file_references() can find source files for metadata extraction
        if self.from_start is None and processed:
            self._mark_file_source(processed[0])

        if is_root:
            _reconstruct_if_needed(processed)

        return processed

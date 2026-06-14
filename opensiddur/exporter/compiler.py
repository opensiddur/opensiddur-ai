""" The JLPTEI compiler has the following responsibilities:

1. Take a single root file as input. This file will always be valid JLPTEI,
and may have transclusions.
2. Compile the file such that the output is a valid XML file that can be
processed linearly by the exporters. The output file need not be valid TEI.

The things that need to be done:
(1) process internal and external transclusions
(1a) remap xml:ids to make sure they are unique globally after being transcluded
(2) process conditions that result in yes/no answers. Leave maybe answers with
their instructions.
(3) process out of line annotations
(4) include relevant header information like licenses, sources, and contributor credits
"""

import argparse
from contextlib import contextmanager
from enum import Enum
import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Literal, Optional, TypedDict
from lxml.etree import ElementBase
from lxml import etree

from opensiddur.exporter.constants import JLPTEI_NAMESPACE, PROCESSING_NAMESPACE
from opensiddur.exporter.derived_settings import SettingChangeTrigger, recalculate_derived_settings
from opensiddur.exporter.linear import (
    ConditionalScope,
    ConditionalSettingEntry,
    LinearData,
    get_linear_data,
    reset_linear_data,
)
from opensiddur.exporter.conditional_settings import (
    CONDITIONAL_CONTROL_TAGS,
    J_CONDITIONAL,
    J_DECLARE,
    J_END_CONDITIONAL,
    J_END_DECLARE,
    XML_ID,
    parse_declare_element,
)
from opensiddur.exporter.condition_eval import (
    TriState,
    evaluate_condition,
    parse_condition_element,
)
from opensiddur.exporter.refdb import ReferenceDatabase
from opensiddur.exporter.urn import ResolvedUrnRange, UrnResolver
from opensiddur.common.constants import PROJECT_DIRECTORY

class _ProcessingCommand(Enum):
    """ Possible ways the compiler can process an element """
    # copy the element and recurse into its children, copying its text content
    COPY_AND_RECURSE = "copy_and_recurse"
    # copy the element and recurse into its children, without copying its text content
    COPY_ELEMENT_AND_RECURSE = "copy_element_and_recurse"
    # recurse into the children without copying the element
    RECURSE = "recurse"
    # skip the element and its children
    SKIP = "skip"
    # copy the element's text content but not the element and recurse into its children
    COPY_TEXT_AND_RECURSE = "text_and_recurse"

class _AnnotationCommand(Enum):
    """ Possible ways the compiler can annotate an element """
    # insert the annotated element after the original element
    INSERT = "insert"
    # replace the original annotation with the annotated element
    REPLACE = "replace"
    # keep the element, despite instructions for inlining
    # outside of inline mode, equivalent to NONE
    KEEP = "keep"
    # no action needed
    NONE = "none"

class _ProcessingContext(TypedDict):
    project: str
    file_name: str
    element_path: Optional[str]
    from_start: Optional[str]
    to_end: Optional[str]
    before_start: bool
    after_end: bool
    include_tail_after_end: bool
    inside_deepest_common_ancestor: bool
    command: _ProcessingCommand
    
class CompilerProcessor:
    def __init__(
        self, 
        project: str,
        file_name: str,
        linear_data: Optional[LinearData] = None,
        reference_database: Optional[ReferenceDatabase] = None):
        """ Process the given file/project.
        Args:
            project: The project name
            file_name: The file name
            linear_data: The linear data (will use the default singleton if not given)
            reference_database: The reference database (will use the default if not given)
        
        Public data:
        self.root_tree: The root element of the tree being processed
        self.project: The project name
        self.file_name: The file name
        self.ns_map: The namespace map
        self.root_language: The language of the first processed element
            (if the processed text needs to be included in something, use this language)
        """
        self.linear_data = linear_data or get_linear_data()

        self.root_tree = self.linear_data.xml_cache.parse_xml(project, file_name)
        
        self.root_tree = self.root_tree.getroot()

        self.project = project
        self.file_name = file_name

        # Extract namespaces from root_tree and save to self.ns_map
        # lxml stores nsmap at the Element level, not the whole tree for parsed objects
        if hasattr(self.root_tree, 'nsmap'):
            self.ns_map = dict(self.root_tree.nsmap) if self.root_tree.nsmap else {}
        else:
            self.ns_map = {}
        self.ns_map["p"] = PROCESSING_NAMESPACE

        self._refdb = reference_database or ReferenceDatabase()
        self._urn_resolver = UrnResolver(self._refdb)

        self.root_language = None
        self._in_parallel_compilation = False

    def _get_in_scope_language(self, element: ElementBase) -> Optional[str]:
        """ Get the xml:lang attribute from the element or its ancestors.
        Returns the first xml:lang found walking up the ancestor chain, or None if not found.
        """
        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        for ancestor in [element] + list(element.iterancestors()):
            lang = ancestor.attrib.get(lang_attr)
            if lang:
                return lang
        return None

    def _get_path_hash(self, element: Optional[ElementBase] = None) -> str:
        """ Get a hash of the path taken to get to the current processing context and element if available """
        context_path_elements = []
        num_contexts = len(self.linear_data.processing_context)
        for i, context in enumerate(self.linear_data.processing_context):
            if i < num_contexts - 1:
                # For outer contexts include element_path (the range entry point)
                context_path_element = (
                    context['project'] + '/' +
                    context['file_name'] + ':' +
                    (context.get('element_path') or "")
                )
            else:
                # For the current context include project/file but not element_path —
                # element_path varies per element and would break ID-rewriting consistency.
                # When a specific element is needed it is appended separately below.
                context_path_element = context['project'] + '/' + context['file_name']
            context_path_elements.append(context_path_element)
        if element is not None:
            element_path = element.getroottree().getpath(element)
            context_path_elements.append(':' + element_path)
        full_context_path ='+'.join(context_path_elements)
        path_hash = hashlib.sha256(full_context_path.encode('utf-8')).hexdigest()[:8]
        return path_hash

    def _rewrite_ids(self, element_or_list) -> ElementBase | list[ElementBase]:
        """ Rewrite the ids of the given element(s), rewrite local targets """
        if isinstance(element_or_list, list):
            # Handle list of elements (ExternalCompilerProcessor case)
            for element in element_or_list:
                self._rewrite_single_element_ids(element)
            return element_or_list
        else:
            # Handle single element (CompilerProcessor case)
            return self._rewrite_single_element_ids(element_or_list)
    
    def _rewrite_single_element_ids(self, element: ElementBase) -> ElementBase:
        """ Rewrite the ids of a single element """
        xml_id = element.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
        target = element.attrib.get('target')
        target_end = element.attrib.get('targetEnd')
        if not xml_id and not target and not target_end:
            return element
        path_hash = self._get_path_hash()
        if xml_id:
            new_xml_id = f"{xml_id}_{path_hash}"
            element.set('{http://www.w3.org/XML/1998/namespace}id', new_xml_id)
        
        rewrite_target = lambda target: ' '.join([
                (target_part 
                if not target_part.startswith('#') 
                else target_part.replace(f"#{target_part[1:]}", f"#{target_part[1:]}_{path_hash}"))
                for target_part in re.split(r'\s+', target)
            ])

        if target:
            new_target = rewrite_target(target)
            element.set('target', new_target)
        if target_end:
            new_target_end = rewrite_target(target_end)
            element.set('targetEnd', new_target_end)
        return element

    def _get_start_and_end_elements_from_ranges(self,
        from_start: Optional[str] = None,
        to_end: Optional[str] = None
    ) -> tuple[Optional[ElementBase], Optional[ElementBase]]:
        """ Get the start and end elements from element XPath paths.
        Args:
            from_start: The start element path, if available
            to_end: The end element path, if available
        Returns:
            The start and end elements
        """
        if from_start:
            start_element = self.root_tree.xpath(from_start, namespaces=self.ns_map)
            if not start_element:
                raise ValueError(f"Start element {from_start=} not found")
            start_element = start_element[0]
        else:
            start_element = None

        if to_end:
            end_element = self.root_tree.xpath(to_end, namespaces=self.ns_map)
            if not end_element:
                raise ValueError(f"End element {to_end=} not found")
            end_element = end_element[0]
        else:
            end_element = None

        return start_element, end_element

    def _transclude(self, 
        element: ElementBase, 
        type_override: Optional[Literal['external', 'inline']] = None
    ) -> Optional[ElementBase]:
        """
        Transclude a new root tree from the given transclusion element
        """

        if element.tag == f"{{{JLPTEI_NAMESPACE}}}transclude":
            target = element.get('target')
            target_end = element.get('targetEnd')
            # Default transclusion type is external (schema default)
            transclusion_type = type_override or element.get('type') or 'external'

            processing_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transclude", nsmap=self.ns_map)
            
            processing_element.set('target', target)
            if target_end:
                processing_element.set('targetEnd', target_end)
            processing_element.set('type', transclusion_type)

            transclude_range = self._get_start_and_end_from_ranges(target, target_end)

            # Parallel trigger: delegate to subclass if parallel projects are configured
            if (transclusion_type == 'external'
                    and self.linear_data.parallel_projects
                    and not self._in_parallel_compilation
                    and hasattr(self, '_transclude_parallel')):
                result = self._transclude_parallel(element, transclude_range, transclusion_type)
                if result is not None:
                    return result
                # result is None → no parallel found, fall through to normal transclusion

            context_lang = self._get_in_scope_language(element)

            end_element_path = transclude_range.end.end_element_path or transclude_range.end.element_path
            if transclusion_type == 'external':
                from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
                processor = ExternalCompilerProcessor(
                    transclude_range.start.project,
                    transclude_range.start.file_name,
                    from_start=transclude_range.start.element_path,
                    to_end=end_element_path,
                    include_tail_after_end=transclude_range.end.end_includes_tail,
                    linear_data=self.linear_data,
                    reference_database=self._refdb)
                # Propagate marker mode to nested processor
                if hasattr(self, 'marker_stack') and self.marker_stack is not None:
                    processor.marker_stack = []
                processed_list = processor.process()
                # External transclusions should contribute textual content only (tei:text),
                # never teiHeader/sourceDesc metadata.
                tei_ns = self.ns_map.get("tei", "http://www.tei-c.org/ns/1.0")
                tei_root_tag = f"{{{tei_ns}}}TEI"
                for processed in processed_list:
                    if processed.tag == tei_root_tag:
                        text_el = processed.find(f"{{{tei_ns}}}text")
                        if text_el is None:
                            text_el = processed.find(f".//{{{tei_ns}}}text")
                        if text_el is not None:
                            for child in list(text_el):
                                processing_element.append(child)
                            continue
                        # fallback: older/invalid trees
                        body = processed.find(f"{{{tei_ns}}}text/{{{tei_ns}}}body")
                        if body is None:
                            body = processed.find(f".//{{{tei_ns}}}body")
                        if body is not None:
                            for child in list(body):
                                processing_element.append(child)
                        continue
                    processing_element.append(processed)
            else:
                from opensiddur.exporter.inline_compiler import InlineCompilerProcessor
                processor = InlineCompilerProcessor(
                    transclude_range.start.project,
                    transclude_range.start.file_name,
                    from_start=transclude_range.start.element_path,
                    to_end=end_element_path,
                    include_tail_after_end=transclude_range.end.end_includes_tail,
                    linear_data=self.linear_data,
                    reference_database=self._refdb)
                processed = processor.process()
                processing_element.text = processed.text
                for child in processed:
                    processing_element.append(child)
            
            # Mark the file source using the transcluded file's project and file_name
            processing_element = processor._mark_file_source(processing_element)
            
            # Check if language differs and add xml:lang if needed
            # Get language of transcluded start element
            if processor.root_language and context_lang != processor.root_language:
                processing_element.set('{http://www.w3.org/XML/1998/namespace}lang', processor.root_language)
            
            return processing_element

    def _annotate(self, element: ElementBase, root: Optional[ElementBase] = None) -> tuple[list[ElementBase], _AnnotationCommand]:
        """
        Annotate the given element with the file source and project.

        There are two possible cases for what we need to do with annotations:
        1. If the element is an instructional note, we need to determine which project's
        instruction set should be used to provide the corresponding instruction. 
        If no other instruction set is available, we
        will continue to use this instruction as-is. 

        2. If the element has standoff annotation (a commentary or editorial note),
        we need to determine which project's commentary set should be used to provide
        the corresponding commentary. All selected commentaries should be loaded and
        returned.

        Args:
            element: The element to annotate
            root: The root element of the iteration, avoids infinite recursion
        Returns:
            A list of annotated elements,
            annotation command: one of INSERT or REPLACE

        """
        if root is element:  # avoid infinite recursion
            return [], _AnnotationCommand.NONE
        corresp = element.get("corresp")
        xml_id = element.get("{http://www.w3.org/XML/1998/namespace}id")

        # Assume a utility function (maybe xml namespace ns_map) is present
        tei_ns = self.ns_map.get("tei")
        tag_note = f"{{{tei_ns}}}note"
        is_note = (element.tag == tag_note)

        if not is_note and not corresp and not xml_id:
            return [], _AnnotationCommand.NONE
        project = self.project if xml_id else None
        file_name = self.file_name if xml_id else None

        # Determine whether this is an instructional note (tei:note with @type='instruction' and has a URN)
        # or otherwise select all annotations for corresp/xml_id.
        result_elements = []
        annotation_command = _AnnotationCommand.NONE

        is_instruction_note = (
            is_note
            and element.get("type", "") == "instruction"
        )

        if is_instruction_note:
            # Find all instructional notes for this instruction URN
            # Find the highest priority instruction and select it
            if corresp:
                other_instruction_notes = self._urn_resolver.resolve(corresp)
                # need to make sure they are notes!
                prioritized_instruction = self._urn_resolver.prioritize_range(
                    other_instruction_notes, self.linear_data.instruction_priority)
                if prioritized_instruction:
                    # need to get the element, transclude it in place 
                    replacement_instruction = prioritized_instruction
                    replacement_processor = CompilerProcessor(
                        replacement_instruction.project,
                        replacement_instruction.file_name,
                        linear_data=self.linear_data,
                        reference_database=self._refdb
                    )
                    replacement_element = replacement_processor.root_tree.xpath(replacement_instruction.element_path, namespaces=self.ns_map)
                    if not replacement_element:
                        raise ValueError(f"Replacement instruction element {replacement_instruction.element_path=} not found")
                    replacement_element = replacement_element[0]
                    processed_replacement_element = replacement_processor.process(replacement_element)
                    if not(replacement_instruction.project == self.project and replacement_instruction.file_name == self.file_name):
                        self._mark_file_source(processed_replacement_element, project=replacement_instruction.project, file_name=replacement_instruction.file_name)
                    
                    # Check if language differs and add xml:lang if needed
                    annotation_lang = replacement_processor.root_language
                    insertion_context_lang = self._get_in_scope_language(element)
                    if annotation_lang and annotation_lang != insertion_context_lang:
                        processed_replacement_element.set('{http://www.w3.org/XML/1998/namespace}lang', annotation_lang)
                    
                    result_elements = [processed_replacement_element]
                    annotation_command = _AnnotationCommand.REPLACE
                else:
                    # No alternative found, keep as is
                    result_elements = []
                    annotation_command = _AnnotationCommand.KEEP
            else:
                result_elements = []
                annotation_command = _AnnotationCommand.KEEP
        elif corresp or xml_id:
            # For commentary/editorial notes, select all annotations for corresp or xml_id
            # May be standoff annotation, or inline.
            references = self._refdb.get_references_to(corresp, xml_id, project, file_name)
            note_references = [r for r in references
                if r.element_tag =="{http://www.tei-c.org/ns/1.0}note"]
            limited_references = self._urn_resolver.prioritize_range(
                note_references, self.linear_data.annotation_projects, return_all=True)

            result_elements = []
            if limited_references:
                for reference in limited_references:
                    processor = CompilerProcessor(
                        reference.project,
                        reference.file_name,
                        linear_data=self.linear_data,
                        reference_database=self._refdb
                    )
                    reference_element = processor.root_tree.xpath(reference.element_path, namespaces=self.ns_map)
                    if not reference_element:
                        raise ValueError(f"Reference element {reference.element_path=} not found")
                    reference_element = reference_element[0]
                    processed_element = processor.process(reference_element)
                    if not(reference.project == self.project and reference.file_name == self.file_name):
                        self._mark_file_source(processed_element, project=reference.project, file_name=reference.file_name)

                    annotation_lang = processor.root_language
                    insertion_context_lang = self._get_in_scope_language(element)
                    if annotation_lang and annotation_lang != insertion_context_lang:
                        processed_element.set('{http://www.w3.org/XML/1998/namespace}lang', annotation_lang)

                    result_elements.append(processed_element)
            if result_elements:
                annotation_command = _AnnotationCommand.INSERT
            else:
                annotation_command = _AnnotationCommand.NONE
        return result_elements, annotation_command

    @staticmethod
    def _insert_first_element(element: ElementBase, new_child: ElementBase) -> ElementBase:
        """
        Insert the new child as the first child of the element.
        Return the base element as modified.
        """
        element.insert(0, new_child)
        if element.text:
            if new_child.tail:
                new_child.tail = element.text + " " + new_child.tail
            else:
                new_child.tail = element.text
            element.text = None
        
        return element

    def _mark_file_source(self, element: ElementBase, 
        project: Optional[str] = None,
        file_name: Optional[str] = None, 
        ) -> ElementBase:
        """
        Mark the file source of the given element if the processing context has changed
        """
        mark_source = False
        if len(self.linear_data.processing_context) > 1:
            previous_context = self.linear_data.processing_context[-2]
            mark_source = not(previous_context['project'] == self.project and previous_context['file_name'] == self.file_name)
        else:
            mark_source = True   # first context
        
        if mark_source:
            element.set(f"{{{PROCESSING_NAMESPACE}}}file_name", file_name or self.file_name)
            element.set(f"{{{PROCESSING_NAMESPACE}}}project", project or self.project)
        return element

    def _get_start_and_end_from_ranges(
        self, 
        target: str, 
        target_end: Optional[str] = None,
        ) -> ResolvedUrnRange:
        """ Return start and end, inclusive """
        start, end = None, None
        resolver = self._urn_resolver
        
        range_start = resolver.resolve_range(target)
        if not range_start:
            raise ValueError(f"Target URN {target=} not found")
        project_priority = self.linear_data.project_priority
        
        range_start = UrnResolver.prioritize_range(range_start, project_priority)
        if not range_start:
            raise ValueError(f"No prioritized URNs found: {target=} {project_priority=}")
        
        if isinstance(range_start, ResolvedUrnRange):
            if target_end is not None:
                raise ValueError(f"If target {target=} is a range, target_end {target_end=} cannot be provided")
            start = range_start.start
            end = range_start.end
        else:   # target is ResolvedUrn
            start = range_start
            if target_end is not None:
                range_end = resolver.resolve_range(target_end)
                if not range_end:
                    raise ValueError(f"Target URN {target_end=} not found")
                range_end = UrnResolver.prioritize_range(range_end, [start.project])
                if not range_end:
                    raise ValueError(f"No prioritized URNs found: {target_end=} in project {range_start.project}")
                
                end = range_end
                if start.file_name != end.file_name:
                    raise ValueError(f"In a range, the start and end of a range must be in the same file: {start.file_name=} != {end.file_name=}")
            else:
                end = range_start
            
        return ResolvedUrnRange(start=start, end=end)


    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        context['element_path'] = element.getroottree().getpath(element)
        context['command'] = _ProcessingCommand.COPY_AND_RECURSE
        return context
        
    def _update_processing_context_after(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        context['element_path'] = None
        return context

    def _scoped_declare_id(self, xml_id: str, declare_element: ElementBase) -> str:
        """Path-scoped declaration identity, parallel to output ID rewriting."""
        return f"{xml_id}_{self._get_path_hash(declare_element)}"

    def _find_declare_element_by_xml_id(self, xml_id: str) -> ElementBase | None:
        for el in self.root_tree.iter(J_DECLARE):
            if el.get(XML_ID) == xml_id:
                return el
        return None

    def _find_conditional_element_by_xml_id(self, xml_id: str) -> ElementBase | None:
        for el in self.root_tree.iter(J_CONDITIONAL):
            if el.get(XML_ID) == xml_id:
                return el
        return None

    def _copy_element_subtree(self, element: ElementBase) -> ElementBase:
        """Deep-copy an element subtree for retained conditional markers."""
        return etree.fromstring(etree.tostring(element))

    def _push_conditional_scope(self, scoped_id: str, result: TriState) -> None:
        self.linear_data.conditional_scope_stack.append(
            ConditionalScope(scoped_id=scoped_id, result=result.value)
        )

    def _pop_conditional_scope(self, scoped_id: str) -> ConditionalScope:
        stack = self.linear_data.conditional_scope_stack
        for i in range(len(stack) - 1, -1, -1):
            if stack[i].scoped_id == scoped_id:
                return stack.pop(i)
        raise ValueError(f"No conditional scope found for scoped_id={scoped_id!r}")

    def _should_skip_conditional_content(self) -> bool:
        return any(
            scope.result == TriState.FALSE.value
            for scope in self.linear_data.conditional_scope_stack
        )

    def _rebuild_derived_dependency_index(self) -> None:
        """Rebuild reverse index after conditional_settings stack mutation."""
        self.linear_data.derived_dependency_index = {}
        for i, entry in enumerate(self.linear_data.conditional_settings):
            if entry.source == "derived":
                for contributor in entry.contributors:
                    self.linear_data.derived_dependency_index.setdefault(
                        contributor, set()
                    ).add(i)

    def _register_derived_entry(self, entry: ConditionalSettingEntry) -> None:
        """Push a derived entry and update the dependency index."""
        self.linear_data.conditional_settings.append(entry)
        idx = len(self.linear_data.conditional_settings) - 1
        for contributor in entry.contributors:
            self.linear_data.derived_dependency_index.setdefault(contributor, set()).add(idx)

    def _remove_derived_entries_for_contributor(self, declare_id: str) -> list[int]:
        """Remove derived entries that depend on declare_id."""
        removed_indices = [
            i
            for i, entry in enumerate(self.linear_data.conditional_settings)
            if entry.source == "derived" and declare_id in entry.contributors
        ]
        if not removed_indices:
            return removed_indices
        self.linear_data.conditional_settings = [
            entry
            for entry in self.linear_data.conditional_settings
            if not (entry.source == "derived" and declare_id in entry.contributors)
        ]
        self._rebuild_derived_dependency_index()
        return removed_indices

    def _push_declare(self, declare_id: str, entries: list[ConditionalSettingEntry]) -> None:
        """Push declared entries and trigger derived-settings recalculation."""
        self.linear_data.conditional_settings.extend(entries)
        recalculate_derived_settings(
            self.linear_data,
            trigger=SettingChangeTrigger.DECLARE,
            declare_id=declare_id,
        )

    def _end_declare(self, declare_id: str) -> None:
        """Remove declared entries for declare_id and invalidate dependent derivations."""
        declared = [
            e
            for e in self.linear_data.conditional_settings
            if e.source == "declared" and e.declare_id == declare_id
        ]
        if not declared:
            raise ValueError(f"No declared settings found for declare_id={declare_id!r}")

        self.linear_data.conditional_settings = [
            e
            for e in self.linear_data.conditional_settings
            if not (e.source == "declared" and e.declare_id == declare_id)
        ]
        self._remove_derived_entries_for_contributor(declare_id)
        recalculate_derived_settings(
            self.linear_data,
            trigger=SettingChangeTrigger.END_DECLARE,
            declare_id=declare_id,
        )

    @staticmethod
    def load_init_settings(
        linear_data: LinearData,
        entries: list[ConditionalSettingEntry],
    ) -> None:
        """Push YAML init entries onto linear_data (used before compile starts)."""
        linear_data.conditional_settings.extend(entries)
        recalculate_derived_settings(linear_data, trigger=SettingChangeTrigger.INIT)

    def get_active_setting_entry(
        self,
        fs_type: str,
        feature_name: str,
    ) -> ConditionalSettingEntry | None:
        """Return the winning stack entry for a feature (latest on stack)."""
        for entry in reversed(self.linear_data.conditional_settings):
            if entry.fs_type == fs_type and entry.feature_name == feature_name:
                return entry
        return None

    def get_active_setting(self, fs_type: str, feature_name: str) -> Any | None:
        """Return the active value for a feature, or None if not set."""
        entry = self.get_active_setting_entry(fs_type, feature_name)
        return entry.value if entry is not None else None

    def get_active_fs_settings(self, fs_type: str) -> dict[str, Any]:
        """Merged view of all features for an FS type."""
        feature_names: set[str] = set()
        for entry in self.linear_data.conditional_settings:
            if entry.fs_type == fs_type:
                feature_names.add(entry.feature_name)
        return {
            name: self.get_active_setting(fs_type, name)
            for name in feature_names
        }

    @contextmanager
    def _conditional_settings_checkpoint(self):
        """Truncate conditional_settings and scope stack to pre-process depth on exit."""
        settings_depth = len(self.linear_data.conditional_settings)
        scope_depth = len(self.linear_data.conditional_scope_stack)
        try:
            yield
        finally:
            del self.linear_data.conditional_settings[settings_depth:]
            del self.linear_data.conditional_scope_stack[scope_depth:]
            self._rebuild_derived_dependency_index()

    def _handle_settings_element(self, element: ElementBase) -> bool:
        """Process j:declare / j:endDeclare. Returns True if handled (strip from output)."""
        if element.tag == J_DECLARE:
            xml_id = element.get(XML_ID)
            if not xml_id:
                raise ValueError("j:declare requires an xml:id attribute")
            scoped_id = self._scoped_declare_id(xml_id, element)
            entries = parse_declare_element(element, scoped_id)
            self._push_declare(scoped_id, entries)
            return True

        if element.tag == J_END_DECLARE:
            target = element.get("target")
            if not target or not target.startswith("#"):
                raise ValueError("j:endDeclare requires a fragment target attribute (e.g. #id)")
            bare_id = target[1:]
            declare_el = self._find_declare_element_by_xml_id(bare_id)
            if declare_el is None:
                raise ValueError(
                    f"j:endDeclare target {target!r} does not match a j:declare in this file"
                )
            scoped_id = self._scoped_declare_id(bare_id, declare_el)
            self._end_declare(scoped_id)
            return True

        return False

    def _handle_conditional_element(self, element: ElementBase) -> tuple[bool, ElementBase | None]:
        """Process j:conditional / j:endConditional.

        Returns (handled, result). result is None when stripped, or an element copy when retained.
        """
        if element.tag == J_CONDITIONAL:
            xml_id = element.get(XML_ID)
            if not xml_id:
                raise ValueError("j:conditional requires an xml:id attribute")
            scoped_id = self._scoped_declare_id(xml_id, element)
            node = parse_condition_element(element)
            result = evaluate_condition(node, self)
            self._push_conditional_scope(scoped_id, result)
            if result == TriState.UNDEFINED:
                return True, self._copy_element_subtree(element)
            return True, None

        if element.tag == J_END_CONDITIONAL:
            target = element.get("target")
            if not target or not target.startswith("#"):
                raise ValueError("j:endConditional requires a fragment target attribute (e.g. #id)")
            bare_id = target[1:]
            conditional_el = self._find_conditional_element_by_xml_id(bare_id)
            if conditional_el is None:
                raise ValueError(
                    f"j:endConditional target {target!r} does not match a j:conditional in this file"
                )
            scoped_id = self._scoped_declare_id(bare_id, conditional_el)
            scope = self._pop_conditional_scope(scoped_id)
            if scope.result == TriState.UNDEFINED.value:
                return True, self._copy_element_subtree(element)
            return True, None

        return False, None

    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> ElementBase:
        self._update_processing_context_before(element)

        if (
            self._should_skip_conditional_content()
            and element.tag not in CONDITIONAL_CONTROL_TAGS
        ):
            self._update_processing_context_after(element)
            return None  # type: ignore[return-value]

        if self._handle_settings_element(element):
            self._update_processing_context_after(element)
            return None  # type: ignore[return-value]

        handled, conditional_copy = self._handle_conditional_element(element)
        if handled:
            self._update_processing_context_after(element)
            if conditional_copy is not None:
                return self._rewrite_ids(conditional_copy)
            return None  # type: ignore[return-value]

        transcluded = self._transclude(element)
        if transcluded is not None:
            return transcluded

        annotated, annotation_command = self._annotate(element, root)
        if annotation_command == _AnnotationCommand.REPLACE:
            return annotated[0]

        copied = etree.Element(element.tag, nsmap=self.ns_map)
        
        # Copy attributes
        for key, value in element.attrib.items():
            copied.set(key, value)
        copied.text = element.text

        for child in element:
            processed = self._process_element(child, root)
            if processed is None:
                continue
            if child.tail:
                processed.tail = child.tail
            copied.append(processed)

        if annotation_command == _AnnotationCommand.INSERT:
            for annotated_element in reversed(annotated):
                self._insert_first_element(copied, annotated_element)

        copied = self._rewrite_ids(copied)
        
        self._update_processing_context_after(element)
        return copied

    def process(self, root: Optional[ElementBase] = None):
        """
        Recursively process elements and text nodes of root_tree as an identity transform.
        If root is not provided, use self.root_tree.
        Yields elements and string text nodes (identity traversal).

        Set the root language.
        """
        if root is None:
            root = self.root_tree

        self.root_language = self._get_in_scope_language(root)

        with self._conditional_settings_checkpoint():
            # set up the processing context
            self.linear_data.processing_context.append(_ProcessingContext(
                project=self.project,
                file_name=self.file_name,
                from_start=None,
                to_end=None,
                before_start=False,
                after_end=False,
                command=_ProcessingCommand.COPY_AND_RECURSE,
                inside_deepest_common_ancestor=False,
                include_tail_after_end=False,
            ))

            copied = self._process_element(root, root)
            copied = self._mark_file_source(copied)
            # pop the processing context
            self.linear_data.processing_context.pop()

        return copied


def main(argv: list[str] | None = None):  # pragma: no cover
    parser = argparse.ArgumentParser(description="Compile a TEI file with external references to a single file.")
    parser.add_argument("--project", "-p", type=str, help="The project name.", required=True)
    parser.add_argument("--file_name", "-f", type=str, help="The file name (relative to the project).", required=True)
    parser.add_argument("--output_file", "-o", type=str, help="The output XML file.")
    parser.add_argument("--settings", "-s", type=Path, help="YAML file with compiler settings. See README.md for more details.")
    parser.add_argument(
        "--project-directory",
        type=Path,
        default=PROJECT_DIRECTORY,
        help="Base directory containing project subdirectories (default: <repo>/project).",
    )
    args = parser.parse_args(argv)

    from opensiddur.exporter.settings import load_default_settings, load_settings

    project_directory = args.project_directory.resolve()
    reset_linear_data()
    linear_data = get_linear_data()

    if args.settings:
        linear_data = load_settings(
            args.settings,
            linear_data=linear_data,
            project_directory=project_directory,
        )
    else:
        linear_data = load_default_settings(
            args.project,
            args.file_name,
            linear_data=linear_data,
            project_directory=project_directory,
        )

    from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
    compiler = ExternalCompilerProcessor(args.project, args.file_name, linear_data=linear_data)
    result = compiler.process()[0]
    etree.ElementTree(result).write(
        args.output_file if args.output_file else sys.stdout,
        pretty_print=True,
        encoding='utf-8')


if __name__ == "__main__":  # pragma: no cover
    main()
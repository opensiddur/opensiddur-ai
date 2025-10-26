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
from enum import Enum
from pathlib import Path
import sys
from typing import Annotated, Literal, Optional, TypedDict
from unittest import result
from lxml.etree import ElementBase
from lxml import etree

from opensiddur.exporter.linear import LinearData, get_linear_data
from opensiddur.exporter.refdb import ReferenceDatabase
from opensiddur.exporter.urn import ResolvedUrnRange, UrnResolver

JLPTEI_NAMESPACE = 'http://jewishliturgy.org/ns/jlptei/2'
PROCESSING_NAMESPACE = 'http://jewishliturgy.org/ns/processing'

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
    from_start: Optional[str]
    to_end: Optional[str]
    before_start: bool
    after_end: bool
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
            transclusion_type = type_override or element.get('type')

            processing_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transclude", nsmap=self.ns_map)
            
            processing_element.set('target', target)
            if target_end:
                processing_element.set('targetEnd', target_end)
            processing_element.set('type', transclusion_type)

            transclude_range = self._get_start_and_end_from_ranges(target, target_end)
            
            if transclusion_type == 'external':
                processor = ExternalCompilerProcessor(
                    transclude_range.start.project, 
                    transclude_range.start.file_name, 
                    from_start=transclude_range.start.urn, 
                    to_end=transclude_range.end.urn, 
                    linear_data=self.linear_data,
                    reference_database=self._refdb)
                processed_list = processor.process()
                for processed in processed_list:
                    processing_element.append(processed)
            else:
                processor = InlineCompilerProcessor(
                    transclude_range.start.project, 
                    transclude_range.start.file_name, 
                    from_start=transclude_range.start.urn, 
                    to_end=transclude_range.end.urn, 
                    linear_data=self.linear_data,
                    reference_database=self._refdb)
                processed = processor.process()
                processing_element.text = processed.text
                for child in processed:
                    processing_element.append(child)
            
            # Mark the file source using the transcluded file's project and file_name
            processing_element = processor._mark_file_source(processing_element)
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
        we need to determine which project's commentary set should be used to provide the corresponding commentary.
        All selected commentaries should be loaded and returned.

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
            limited_references = self._urn_resolver.prioritize_range(note_references, self.linear_data.annotation_projects, return_all=True)
            
            result_elements = []
            if limited_references:  # Handle case where prioritize_range returns None
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


    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingCommand:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        return _ProcessingCommand.COPY_AND_RECURSE
        
    def _update_processing_context_after(self, element: ElementBase) -> None:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        pass    

    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> ElementBase:
        context = self.linear_data.processing_context[-1]
        context["command"] = self._update_processing_context_before(element)
        
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
            if child.tail:
                processed.tail = child.tail
            copied.append(processed)

        if annotation_command == _AnnotationCommand.INSERT:
            for annotated_element in reversed(annotated):
                self._insert_first_element(copied, annotated_element)

        self._update_processing_context_after(element)
        return copied

    def process(self, root: Optional[ElementBase] = None):
        """
        Recursively process elements and text nodes of root_tree as an identity transform.
        If root is not provided, use self.root_tree.
        Yields elements and string text nodes (identity traversal).
        """
        if root is None:
            root = self.root_tree

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
        ))

        copied = self._process_element(root, root)
        copied = self._mark_file_source(copied)
        # pop the processing context
        self.linear_data.processing_context.pop()

        return copied

class ExternalCompilerProcessor(CompilerProcessor):
    def _get_deepest_common_ancestor(self, from_start: str, to_end: str) -> ElementBase:
        """
        Get the deepest common ancestor of the given start and end.

        There is one exception: if start and end are siblings, return the start element.
        We do this because then we don't need the surrounding elements to be copied.
        """
        start_xpath = (
            f"./descendant::*[@corresp='{from_start}']" if from_start.startswith('urn:') 
            else f"./descendant::*[@xml:id='{from_start.split('#')[1]}']"
        )
        end_xpath = (
            f"./descendant::*[@corresp='{to_end}']" if to_end.startswith('urn:') 
            else f"./descendant::*[@xml:id='{to_end.split('#')[1]}']"
        )
        start_element = self.root_tree.xpath(start_xpath)
        if not start_element:
            raise ValueError(f"Start URN {from_start=} not found")
        start_element = start_element[0]
        end_element = self.root_tree.xpath(end_xpath)
        if not end_element:
            raise ValueError(f"End URN {to_end=} not found")
        end_element = end_element[0]
        if start_element is end_element:
            return start_element
        if start_element.getparent() is end_element.getparent():
            # siblings... no need to go deeper
            return start_element
        for element in start_element.iterancestors():
            if element.xpath(end_xpath):
                return element
        raise ValueError(f"No common ancestor found for {from_start=} and {to_end=}")

    def __init__(
        self,
        project: str,
        file_name: str,
        from_start: str,
        to_end: str,
        linear_data: Optional[LinearData] = None,
        reference_database: Optional[ReferenceDatabase] = None):
        """ Process the given file/project. 
        Only start from the given start and end, inclusive.
        Start and end must be in the same file
        """
        super().__init__(project, file_name, linear_data=linear_data, reference_database=reference_database)
        self.from_start = from_start
        self.to_end = to_end

        self.deepest_common_ancestor = self._get_deepest_common_ancestor(from_start, to_end)


    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingCommand:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        context = self.linear_data.processing_context[-1]

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
            return _ProcessingCommand.SKIP
        
        corresp = element.attrib.get("corresp", "")
        xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")

        # is start
        if corresp or xml_id:
            is_start = (corresp == self.from_start or 
                       (self.from_start.startswith('#') and xml_id == self.from_start.split('#')[1]))
            if is_start:
                context['before_start'] = False
                return _ProcessingCommand.COPY_AND_RECURSE

        # is after start?
        if context['before_start']:
            if element is self.deepest_common_ancestor:
                context['inside_deepest_common_ancestor'] = True
                return _ProcessingCommand.COPY_ELEMENT_AND_RECURSE
            elif context['inside_deepest_common_ancestor']:
                return _ProcessingCommand.COPY_ELEMENT_AND_RECURSE
            else:
                return _ProcessingCommand.RECURSE
            
        # must be after start and before end
        return _ProcessingCommand.COPY_AND_RECURSE
    
    def _update_processing_context_after(self, element: ElementBase) -> None:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        if element is self.deepest_common_ancestor:
            context['inside_deepest_common_ancestor'] = False
            return

        if not context['before_start'] and not context['after_end']:
            corresp = element.attrib.get("corresp", "")
            xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")
            # between start and end
            is_end = (self.to_end == corresp or 
                     (self.to_end.startswith('#') and xml_id == self.to_end.split('#')[1]))
            if is_end:
                context['after_end'] = True
    

    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> list[ElementBase]:
        """
        Process the given element and return the list of processed elements.
        """
        context = self.linear_data.processing_context[-1]
        context["command"] = self._update_processing_context_before(element)
        
        processed = []

        if context["command"] == _ProcessingCommand.SKIP:
            return []

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
        if context["command"] == _ProcessingCommand.COPY_AND_RECURSE:
            copied = etree.Element(element.tag, nsmap=self.ns_map)
            for key, value in element.attrib.items():
                copied.set(key, value)
            copied.text = element.text
            processed.append(copied)
            append_to = copied
        
        for child in element:
            child_result = self._process_element(child, root)
            append_to.extend(child_result)
            if context["command"] == _ProcessingCommand.COPY_AND_RECURSE:
                if child.tail and child_result:
                    # Only copy tail if we're not after the end marker
                    if not context['after_end']:
                        if child_result[-1].tail is None:
                            child_result[-1].tail = child.tail
                        else:
                            child_result[-1].tail += child.tail
        
        if annotation_command == _AnnotationCommand.INSERT:
            for annotation in reversed(annotations):
                self._insert_first_element(processed, annotation)

        self._update_processing_context_after(element)
        return processed

    def process(self, root: Optional[ElementBase] = None) -> list[ElementBase]:
        if root is None:
            root = self.root_tree

        self.linear_data.processing_context.append(_ProcessingContext(
            project=self.project,
            file_name=self.file_name,
            from_start=self.from_start,
            to_end=self.to_end,
            before_start=self.from_start is not None,
            after_end=False,  # We haven't processed anything yet, so we're not after end
            command=_ProcessingCommand.RECURSE,
            inside_deepest_common_ancestor=False,
        ))

        processed = self._process_element(root, root)

        # pop the processing context
        self.linear_data.processing_context.pop()

        return processed

class InlineCompilerProcessor(CompilerProcessor):
    def __init__(
        self,
        project: str,
        file_name: str,
        from_start: str,
        to_end: str,
        linear_data: Optional[LinearData] = None,
        reference_database: Optional[ReferenceDatabase] = None):
        """ Process the given file/project.
        Only start from the given start and end, inclusive.
        Start and end must be in the same file
        """
        super().__init__(project, file_name, linear_data=linear_data, reference_database=reference_database)
        self.from_start = from_start
        self.to_end = to_end

    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingCommand:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        context = self.linear_data.processing_context[-1]

        # Possible contexts:
        #    after end? SKIP 
        #    before start?
        #       check if this element is start? if yes, set before_start to False and return COPY_TEXT_AND_RECURSE
        #       else RECURSE
        #    between start and end? COPY_TEXT_AND_RECURSE
        
        if context['after_end']:
            return _ProcessingCommand.SKIP
        
        corresp = element.attrib.get("corresp", "")
        xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")

        # is start
        if corresp or xml_id:
            is_start = (corresp == self.from_start) or (self.from_start.startswith('#') and xml_id == self.from_start[1:])
            if is_start:
                context['before_start'] = False
                return _ProcessingCommand.COPY_TEXT_AND_RECURSE

        # is after start?
        if context['before_start']:
            return _ProcessingCommand.RECURSE
            
        # must be after start and before end
        return _ProcessingCommand.COPY_TEXT_AND_RECURSE
    
    def _update_processing_context_after(self, element: ElementBase) -> None:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        if not context['before_start'] and not context['after_end']:
            corresp = element.attrib.get("corresp", "")
            xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")
            # between start and end - check if this is the end element
            is_end = (self.to_end == corresp) or (self.to_end.startswith('#') and xml_id == self.to_end[1:])
            if is_end:
                context['after_end'] = True
    
    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> ElementBase:
        """
        Process the given element and return the text content.
        """
        context = self.linear_data.processing_context[-1]
        context["command"] = self._update_processing_context_before(element) 


        text_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transcludeInline", nsmap=self.ns_map)
        text_element.text = ""

        if context["command"] == _ProcessingCommand.SKIP:
            return text_element

        # Check if this element itself is a transclusion
        transcluded = self._transclude(element, type_override='inline')
        if transcluded is not None:
            # Don't process children of j:transclude elements - just return the p:transclude
            # The tail will be handled by the parent's processing
            return transcluded

        annotations, annotation_command = self._annotate(element, root)
        if annotation_command == _AnnotationCommand.REPLACE:
            # This is a case of an instructional notation that needs to replace the current element
            # and *not* be treated as inline text
            return annotations[0]
        elif annotation_command == _AnnotationCommand.KEEP:
            # This is a case of an instructional notation that needs to be kept as is
            processor =CompilerProcessor(
                self.project,
                self.file_name,
                linear_data=self.linear_data,
                reference_database=self._refdb
            )
            return processor.process(element)

        if context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE:
            if element.text:
                text_element.text += element.text

        # the command is some kind of recursion now, COPY_TEXT_AND_RECURSE or RECURSE
        
        previous_child = None
        for child in element:
            processed = self._process_element(child, root)
            if processed.tag == f"{{{PROCESSING_NAMESPACE}}}transcludeInline":
                # Extract text from nested p:transcludeInline elements
                text_element.text += processed.text or ""
                # Also extract any p:transclude children (nested transclusions)
                for nested_child in processed:
                    text_element.append(nested_child)
                    previous_child = nested_child
            elif processed.tag == f"{{{PROCESSING_NAMESPACE}}}transclude":
                # p:transclude elements are kept as children (for inline transclusions)
                # Add the p:transclude element as a child
                text_element.append(processed)
                previous_child = processed
            else:
                # Other element types (shouldn't normally happen in InlineCompilerProcessor)
                text_element.append(processed)
                previous_child = processed
            if context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE:
                if child.tail:
                    if previous_child is not None:
                        previous_child.tail = (previous_child.tail or "") + " " + child.tail
                    else:
                        text_element.text += " " + child.tail
        
        if annotation_command == _AnnotationCommand.INSERT:
            for annotation in reversed(annotations):
                self._insert_first_element(text_element, annotation)

        self._update_processing_context_after(element)
        return text_element
        
    def process(self, root: Optional[ElementBase] = None) -> ElementBase:
        if root is None:
            root = self.root_tree

        self.linear_data.processing_context.append(_ProcessingContext(
            project=self.project,
            file_name=self.file_name,
            from_start=self.from_start,
            to_end=self.to_end,
            before_start=self.from_start is not None,
            after_end=False,  # We haven't processed anything yet, so we're not after end
            command=_ProcessingCommand.RECURSE,
            inside_deepest_common_ancestor=False,
        ))

        element = self._process_element(root, root)

        # pop the processing context
        self.linear_data.processing_context.pop()

        return element


def main():
    parser = argparse.ArgumentParser(description="Compile a TEI file with external references to a single file.")
    parser.add_argument("--project", "-p", type=str, help="The project name.", required=True)
    parser.add_argument("--file_name", "-f", type=str, help="The file name (relative to the project).", required=True)
    parser.add_argument("--output_file", "-o", type=str, help="The output XML file.")
    args = parser.parse_args()
    
    compiler = CompilerProcessor(args.project, args.file_name)
    result = compiler.process()
    etree.ElementTree(result).write(
        args.output_file if args.output_file else sys.stdout, 
        pretty_print=True,
        encoding='utf-8')
    

if __name__ == "__main__":
    main()
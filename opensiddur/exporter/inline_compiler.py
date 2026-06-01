"""Inline compiler processor for processing text content between start and end markers."""

from typing import Optional
from lxml.etree import ElementBase

from opensiddur.exporter.compiler import (
    CompilerProcessor,
    _ProcessingCommand,
    _ProcessingContext,
    _AnnotationCommand,
)
from opensiddur.exporter.constants import PROCESSING_NAMESPACE
from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase
from lxml import etree


class InlineCompilerProcessor(CompilerProcessor):
    def __init__(
        self,
        project: str,
        file_name: str,
        from_start: str,
        to_end: str,
        include_tail_after_end: bool = False,
        linear_data: Optional[LinearData] = None,
        reference_database: Optional[ReferenceDatabase] = None):
        """ Process the given file/project.
        Only start from the given start and end, inclusive.
        Start and end must be in the same file
        """
        super().__init__(project, file_name, linear_data=linear_data, reference_database=reference_database)
        self.from_start = from_start
        self.to_end = to_end
        self.include_tail_after_end = include_tail_after_end
        self.start_element, self.end_element = self._get_start_and_end_elements_from_ranges(from_start, to_end)

    def _update_processing_context_before(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, before the element has been processed.
        """
        context = self.linear_data.processing_context[-1]

        # always reset the include_tail_after_end flag
        context['include_tail_after_end'] = False

        context['element_path'] = element.getroottree().getpath(element)
        # Possible contexts:
        #    after end? SKIP
        #    before start?
        #       check if this element is start? if yes, set before_start to False and return COPY_TEXT_AND_RECURSE
        #       else RECURSE
        #    between start and end? COPY_TEXT_AND_RECURSE

        if context['after_end']:
            context['command'] = _ProcessingCommand.SKIP
            return context

        corresp = element.attrib.get("corresp", "")
        xml_id = element.attrib.get("{http://www.w3.org/XML/1998/namespace}id", "")

        # is start
        if corresp or xml_id:
            if element is self.start_element:
                context['before_start'] = False
                context['command'] = _ProcessingCommand.COPY_TEXT_AND_RECURSE
                return context

        # is after start?
        if context['before_start']:
            context['command'] = _ProcessingCommand.RECURSE
            return context

        # must be after start and before end
        context['command'] = _ProcessingCommand.COPY_TEXT_AND_RECURSE
        return context

    def _update_processing_context_after(self, element: ElementBase) -> _ProcessingContext:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        context = self.linear_data.processing_context[-1]
        context['element_path'] = None
        context["include_tail_after_end"] = False
        if not context['before_start'] and not context['after_end']:
            # between start and end - check if this is the end element
            if element is self.end_element:
                context['after_end'] = True
                context["include_tail_after_end"] = self.include_tail_after_end
        elif context['after_end']:
            # force exclusion of tails after the end element
            context["command"] = _ProcessingCommand.SKIP

        return context

    def _process_element(self, element: ElementBase, root: Optional[ElementBase] = None) -> ElementBase:
        """
        Process the given element and return the text content.
        """
        context = self._update_processing_context_before(element)

        text_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transcludeInline", nsmap=self.ns_map)
        text_element.text = ""

        if context["command"] == _ProcessingCommand.SKIP:
            return text_element

        if self._handle_settings_element(element):
            self._update_processing_context_after(element)
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
            processor = ExternalCompilerProcessor(
                self.project,
                self.file_name,
                linear_data=self.linear_data,
                reference_database=self._refdb
            )
            processed_element = processor.process(element)[0]
            context_lang = self._get_in_scope_language(element)
            if (processor.root_language
                and processor.root_language != context_lang
                and not processed_element.get('{http://www.w3.org/XML/1998/namespace}lang')):
                processed_element.set('{http://www.w3.org/XML/1998/namespace}lang', processor.root_language)
            return processed_element

        element_lang = element.get('{http://www.w3.org/XML/1998/namespace}lang')
        if element_lang:
            text_element.set('{http://www.w3.org/XML/1998/namespace}lang', element_lang)

        if context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE:
            if element.text:
                text_element.text += element.text

        # the command is some kind of recursion now, COPY_TEXT_AND_RECURSE or RECURSE
        context_lang = self._get_in_scope_language(element)
        previous_child = None
        for child in element:
            processed = self._process_element(child, root)
            # Check if this child has a language different from the root
            child_lang = self._get_in_scope_language(child)
            if processed.tag == f"{{{PROCESSING_NAMESPACE}}}transcludeInline":
                # If language differs, keep as nested element
                if child_lang and child_lang != context_lang:
                    text_element.append(processed)
                    previous_child = processed
                else:
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
            if (
                context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE
                or context["include_tail_after_end"]):
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

        self.root_language = self._get_in_scope_language(root)

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

            element = self._process_element(root, root)

            # pop the processing context
            self.linear_data.processing_context.pop()

        return element

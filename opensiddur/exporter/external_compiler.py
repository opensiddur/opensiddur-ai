"""External compiler processor for processing specific ranges of XML files."""

from typing import Optional
from lxml.etree import ElementBase

from opensiddur.exporter.compiler import (
    CompilerProcessor,
    PROCESSING_NAMESPACE,
    _ProcessingCommand,
    _ProcessingContext,
    _AnnotationCommand,
)
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase
from lxml import etree


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
        reference_database: Optional[ReferenceDatabase] = None):
        """ Process the given file/project.
        Only start from the given start and end, inclusive.
        Start and end must be in the same file.

        Arguments:
            from_start: the start element path, or None to process the entire file
            to_end: the end element path, or None to process the entire file; always inclusive
            include_tail_after_end: whether to include the tail after the end element
            linear_data: the linear data
            reference_database: the reference database
        """
        super().__init__(project, file_name, linear_data=linear_data, reference_database=reference_database)

        if (from_start is None and to_end is not None) or (from_start is not None and to_end is None):
            raise ValueError("Either from_start or to_end must be None, but not both")
        self.from_start = from_start
        self.to_end = to_end

        self.deepest_common_ancestor, self.start_element, self.end_element, self.include_tail_after_end = self._get_deepest_common_ancestor(from_start, to_end, include_tail_after_end)


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
                self._insert_first_element(processed, annotation)

        processed = self._rewrite_ids(processed)

        self._update_processing_context_after(element)
        return processed

    def process(self, root: Optional[ElementBase] = None) -> list[ElementBase]:
        if root is None:
            root = self.root_tree

        # set the root language to the language of the deepest common ancestor if present, else root
        self.root_language = self._get_in_scope_language(
            self.deepest_common_ancestor if self.deepest_common_ancestor is not None else root)

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

        return processed

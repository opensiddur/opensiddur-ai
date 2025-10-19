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

from enum import Enum
from pathlib import Path
from typing import Literal, Optional, TypedDict
from lxml.etree import ElementBase
from lxml import etree

from opensiddur.exporter.linear import LinearData, get_linear_data
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

class _ProcessingContext(TypedDict):
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
        linear_data: Optional[LinearData] = None):
        """ Process the given file/project.
        """
        self.linear_data = linear_data or get_linear_data()

        self.root_tree = self.linear_data.xml_cache.parse_xml(project, file_name)
        
        self.root_tree = self.root_tree.getroot()

        # Extract namespaces from root_tree and save to self.ns_map
        # lxml stores nsmap at the Element level, not the whole tree for parsed objects
        if hasattr(self.root_tree, 'nsmap'):
            self.ns_map = dict(self.root_tree.nsmap) if self.root_tree.nsmap else {}
        else:
            self.ns_map = {}
        self.ns_map["p"] = PROCESSING_NAMESPACE

    def _transclude(self, 
        element: ElementBase, 
        type_override: Optional[Literal['external', 'inline']] = None
    ) -> Optional[ElementBase]:
        """
        Transclude a new root tree from the given transclusion element
        """

        if element.tag == 'transclude' and element.namespace == JLPTEI_NAMESPACE:
            target = element.get('target')
            target_end = element.get('targetEnd')
            transclusion_type = type_override or element.get('type')

            processing_element = etree.Element('p:transclude', nsmap=self.ns_map)
            
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
                    linear_data=self.linear_data)
                processed_list = processor.process()
                for processed in processed_list:
                    processing_element.append(processed)
            else:
                processor = InlineCompilerProcessor(
                    transclude_range.start.project, 
                    transclude_range.start.file_name, 
                    from_start=transclude_range.start.urn, 
                    to_end=transclude_range.end.urn, 
                    linear_data=self.linear_data)
                processed = processor.process()
                processing_element.text = processed.text
                for child in processed:
                    processing_element.append(child)
            
            return processing_element

    def _get_start_and_end_from_ranges(
        self, 
        target: str, 
        target_end: Optional[str] = None,
        ) -> ResolvedUrnRange:
        """ Return start and end, inclusive """
        start, end = None, None
        resolver = UrnResolver()
        
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

    def _process_element(self, element: ElementBase) -> ElementBase:
        command = self._update_processing_context_before(element)
        

        if (transcluded := self._transclude(element)):
            return transcluded

        copied = etree.Element(element.tag, nsmap=self.ns_map)

        # Copy attributes
        for key, value in element.attrib.items():
            copied.set(key, value)
        copied.text = element.text

        for child in element:
            processed = self._process_element(child)
            if child.tail:
                processed.tail = child.tail
            copied.append(processed)

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
            from_start=None,
            to_end=None,
            before_start=False,
            after_end=False,
            command=_ProcessingCommand.COPY_AND_RECURSE,
            inside_deepest_common_ancestor=False,
        ))

        copied = self._process_element(root)
        # pop the processing context
        self.linear_data.processing_context.pop()

        return copied

class ExternalCompilerProcessor(CompilerProcessor):
    def _get_deepest_common_ancestor(self, from_start: str, to_end: str) -> ElementBase:
        """
        Get the deepest common ancestor of the given start and end.
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
        if start_element.parent is end_element.parent:
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
        linear_data: Optional[LinearData] = None):
        """ Process the given file/project. 
        Only start from the given start and end, inclusive.
        Start and end must be in the same file
        """
        super().__init__(project, file_name, linear_data=linear_data)
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
        xml_id = element.attrib.get("xml:id", "")

        # is start
        if corresp or xml_id:
            if corresp == self.from_start or xml_id == self.from_start.split('#')[1]:
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
            xml_id = element.attrib.get("xml:id", "")
            # between start and end
            if self.to_end == corresp or xml_id == self.to_end.split('#')[1]:
                context['after_end'] = True
    

    def _process_element(self, element: ElementBase) -> list[ElementBase]:
        """
        Process the given element and return the list of processed elements.
        """
        context = self.linear_data.processing_context[-1]
        context["command"] = self._update_processing_context_before(element)
        processed = []

        if context["command"] == _ProcessingCommand.SKIP:
            return []
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
            append_to.extend(self._process_element(child))
            if context["command"] == _ProcessingCommand.COPY_AND_RECURSE:
                if child.tail:
                    append_to[-1].tail += child.tail
                
        self._update_processing_context_after(element)
        return processed

    # TODO: figure out return type and logic for external transclusions
    def process(self, root: Optional[ElementBase] = None) -> ElementBase:
        if root is None:
            root = self.root_tree

        self.linear_data.processing_context.append(_ProcessingContext(
            from_start=self.from_start,
            to_end=self.to_end,
            before_start=self.from_start is not None,
            after_end=self.to_end is not None,
            command=_ProcessingCommand.RECURSE,
        ))
        element = etree.Element("__TRANSCLUSION__", nsmap=self.ns_map)

        for processed in self._process_element(root):
            element.append(processed)

        # pop the processing context
        self.linear_data.processing_context.pop()

        return element

class InlineCompilerProcessor(CompilerProcessor):
    def __init__(
        self,
        project: str,
        file_name: str,
        from_start: str,
        to_end: str,
        linear_data: Optional[LinearData] = None):
        """ Process the given file/project.
        Only start from the given start and end, inclusive.
        Start and end must be in the same file
        """
        super().__init__(project, file_name, linear_data=linear_data)
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
    
    # TODO: figure out how to do transclusions in internal transclusions
    def _process_element(self, element: ElementBase) -> ElementBase:
        """
        Process the given element and return the text content.
        """
        context = self.linear_data.processing_context[-1]
        context["command"] = self._update_processing_context_before(element) 


        text_element = etree.Element(f"{{{PROCESSING_NAMESPACE}}}transcludeInline", nsmap=self.ns_map)
        text_element.text = ""

        if context["command"] == _ProcessingCommand.SKIP:
            return text_element

        if (transcluded := self._transclude(element, type_override='inline')):
            return transcluded

        if context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE:
            if element.text:
                text_element.text += element.text

        # the command is some kind of recursion now, COPY_TEXT_AND_RECURSE or RECURSE
        
        previous_child = None
        for child in element:
            processed = self._process_element(child)
            if processed.tag == f"{{{PROCESSING_NAMESPACE}}}transcludeInline":
                text_element.text += processed.text
            else:   # not a text element, transclusion probably happened
                text_element.append(processed)
                previous_child = processed
            if context["command"] == _ProcessingCommand.COPY_TEXT_AND_RECURSE:
                if child.tail:
                    if previous_child:
                        previous_child.tail += " " + child.tail
                    else:
                        text_element.text += " " + child.tail
        
        self._update_processing_context_after(element)
        return text_element
        
    def process(self, root: Optional[ElementBase] = None) -> ElementBase:
        if root is None:
            root = self.root_tree

        self.linear_data.processing_context.append(_ProcessingContext(
            from_start=self.from_start,
            to_end=self.to_end,
            before_start=self.from_start is not None,
            after_end=False,  # We haven't processed anything yet, so we're not after end
            command=_ProcessingCommand.RECURSE,
            inside_deepest_common_ancestor=False,
        ))

        element = self._process_element(root)

        # pop the processing context
        self.linear_data.processing_context.pop()

        return element
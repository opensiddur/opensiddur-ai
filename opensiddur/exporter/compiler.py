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
from typing import Optional, TypedDict
from lxml.etree import ElementBase
from lxml import etree

from opensiddur.exporter.linear import LinearData, get_linear_data
from opensiddur.exporter.urn import ResolvedUrnRange, UrnResolver

JLPTEI_NAMESPACE = 'http://jewishliturgy.org/ns/jlptei/2'
PROCESSING_NAMESPACE = 'http://jewishliturgy.org/ns/processing'

class _ProcessingCommand(Enum):
    """ Possible ways the compiler can process an element """
    # copy the element and recurse into its children
    COPY_AND_RECURSE = "copy_and_recurse"
    # recurse into the children without copying the element
    RECURSE = "recurse"
    # skip the element and its children
    SKIP = "skip"
    # copy the element's text content but not the element and recurse into its children
    TEXT_AND_RECURSE = "text_and_recurse"

class _ProcessingContext(TypedDict):
    from_start: Optional[str]
    to_end: Optional[str]
    before_start: bool
    after_end: bool

class CompilerProcessor:
    def __init__(
        self, 
        project: str,
        file_name: str,
        from_start: Optional[str] = None,
        to_end: Optional[str] = None,
        inline: bool = False,
        linear_data: Optional[LinearData] = None):
        """ Process root_file. Only start from the given start and end, inclusive.
        If start and end are not provided, process the entire file.
        Start and end must be in the file. 
        They must be URNs that are not qualified by the project 
        or be hashed xml:ids (#id_name) that exist in the file.
        """
        self.linear_data = linear_data or get_linear_data()
        self.from_start = from_start
        self.to_end = to_end
        self.inline = inline

        self.root_tree = self.linear_data.xml_cache.parse_xml(project, file_name)
        
        self.root_tree = self.root_tree.getroot()

        # Extract namespaces from root_tree and save to self.ns_map
        # lxml stores nsmap at the Element level, not the whole tree for parsed objects
        if hasattr(self.root_tree, 'nsmap'):
            self.ns_map = dict(self.root_tree.nsmap) if self.root_tree.nsmap else {}
        else:
            self.ns_map = {}
        self.ns_map["p"] = PROCESSING_NAMESPACE

    def _transclude(self, transclusion_element: ElementBase):
        """
        Transclude a new root tree from the given transclusion element
        """
        assert (
            transclusion_element.tag == 'transclude' and 
            transclusion_element.namespace == JLPTEI_NAMESPACE
        )
        target = transclusion_element.get('target')
        target_end = transclusion_element.get('targetEnd')
        transclusion_type = transclusion_element.get('type')

        processing_element = etree.Element('p:transclude', nsmap=self.ns_map)
        
        processing_element.set('target', target)
        if target_end:
            processing_element.set('targetEnd', target_end)
        processing_element.set('type', transclusion_type)

        transclude_range = self._get_start_and_end_from_ranges(target, target_end)
        processor = CompilerProcessor(
            transclude_range.start.project, 
            transclude_range.start.file_name, 
            from_start=transclude_range.start.urn, 
            to_end=transclude_range.end.urn, 
            inline=self.inline or transclusion_type == 'inline', 
            linear_data=self.linear_data)
        processed = processor.process()

        processing_element.append(processed)
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

        (NOTE: for now, this will only work for inline transclusions)

        """
        context = self.linear_data.processing_context[-1]

        # Possible contexts: 
        # There is no start or end, always copy and recurse
        # There is a start/end and
        #    start has not yet been reached, 
        #      check if this element is the start 
        #       if yes, set before_start to False and return COPY_AND_RECURSE, 
        #       else 
        #         if in inline mode:
        #           check if start is contained in element; 
        #             if yes, RECURSE, 
        #             else SKIP.
        #         if not in inline mode:
        #           check if start is contained in the element:
        #             check if end is contained in the element:
        #               if yes, COPY_AND_RECURSE,
        #               else RECURSE
        #             else SKIP.
        #    after end, SKIP
        if self.from_start is None and self.to_end is None:
            return _ProcessingCommand.COPY_AND_RECURSE

        if context['after_end']:
            return _ProcessingCommand.SKIP
        
        corresp = element.attrib.get("corresp", "")
        
        if context['before_start']:
            if corresp == self.from_start:
                context['before_start'] = False
                return _ProcessingCommand.COPY_AND_RECURSE
            else:
                start_in_element = element.xpath(f"./descendant::*[@corresp='{self.from_start}']")
                if start_in_element:
                    if self.inline:
                        return _ProcessingCommand.RECURSE
                    else:
                        end_in_element = element.xpath(f"./descendant::*[@corresp='{self.to_end}']")
                        if end_in_element:
                            return _ProcessingCommand.COPY_AND_RECURSE
                        else:
                            return _ProcessingCommand.RECURSE
                return _ProcessingCommand.SKIP
        # must be between start and end here
        return _ProcessingCommand.COPY_AND_RECURSE
    
    def _update_processing_context_after(self, element: ElementBase) -> None:
        """
        Update the processing context for the given element, after the element has been processed.
        """
        if self.from_start is None and self.to_end is None:
            return

        context = self.linear_data.processing_context[-1]
        if not context['before_start'] and not context['after_end']:
            corresp = element.attrib.get("corresp", "")
            # between start and end
            if self.to_end == corresp:
                context['after_end'] = True
            

    def _process_element(self, element: ElementBase) -> ElementBase:
        self._update_processing_context_before(element)

        copied = etree.Element(element.tag, nsmap=self.ns_map)

        if element.tag == 'transclude' and element.namespace == JLPTEI_NAMESPACE:
            transcluded = self._transclude(element)
            return transcluded

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
            from_start=self.from_start,
            to_end=self.to_end,
            before_start=self.from_start is not None,
            after_end=self.to_end is not None,
        ))

        copied = self._process_element(root)
        # pop the processing context
        self.linear_data.processing_context.pop()

        return copied

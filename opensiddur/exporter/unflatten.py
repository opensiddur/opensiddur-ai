"""Unflattening processor for XML structures marked with p:start and p:end attributes."""

from typing import Optional
from lxml.etree import ElementBase

from opensiddur.exporter.compiler import PROCESSING_NAMESPACE


class UnflatteningProcessor:
    """Processor that unflattens XML structures marked with p:start and p:end attributes.
    
    When an element has a p:start attribute, it collects all following siblings
    (and their descendants) until a matching p:end attribute is found, then
    moves that content as children of the element with p:start. The element's
    tail becomes its text content.
    """
    
    def __init__(self, root_element: ElementBase, ns_map: Optional[dict] = None):
        """Initialize the unflattening processor.
        
        Args:
            root_element: The root element to process
            ns_map: Namespace map (will extract from root_element if not provided)
        """
        self.root_element = root_element
        if ns_map is None:
            if hasattr(root_element, 'nsmap'):
                self.ns_map = dict(root_element.nsmap) if root_element.nsmap else {}
            else:
                self.ns_map = {}
        else:
            self.ns_map = ns_map
        
        # Ensure processing namespace is in the map
        if "p" not in self.ns_map:
            self.ns_map["p"] = PROCESSING_NAMESPACE
    
    def _get_start_attr(self, element: ElementBase) -> Optional[str]:
        """Get the p:start attribute value from an element."""
        start_attr = f"{{{PROCESSING_NAMESPACE}}}start"
        return element.get(start_attr)
    
    def _get_end_attr(self, element: ElementBase) -> Optional[str]:
        """Get the p:end attribute value from an element."""
        end_attr = f"{{{PROCESSING_NAMESPACE}}}end"
        return element.get(end_attr)
    
    def _remove_start_attr(self, element: ElementBase):
        """Remove the p:start attribute from an element."""
        start_attr = f"{{{PROCESSING_NAMESPACE}}}start"
        if start_attr in element.attrib:
            del element.attrib[start_attr]
    
    def _remove_end_attr(self, element: ElementBase):
        """Remove the p:end attribute from an element."""
        end_attr = f"{{{PROCESSING_NAMESPACE}}}end"
        if end_attr in element.attrib:
            del element.attrib[end_attr]
    
    def _is_parallel_element(self, element: ElementBase) -> bool:
        """Check if element is p:parallelBlock or p:parallelInternal."""
        parallel_block_tag = f"{{{PROCESSING_NAMESPACE}}}parallelBlock"
        parallel_internal_tag = f"{{{PROCESSING_NAMESPACE}}}parallelInternal"
        return element.tag in (parallel_block_tag, parallel_internal_tag)
    
    def _is_external_transclusion(self, element: ElementBase) -> bool:
        """Check if element is p:transclude with type='external' or no type."""
        transclude_tag = f"{{{PROCESSING_NAMESPACE}}}transclude"
        if element.tag != transclude_tag:
            return False
        transclude_type = element.get("type")
        # External if type is "external" or type is not specified (None)
        return transclude_type == "external" or transclude_type is None
    
    def _should_pause_hierarchy(self, element: ElementBase) -> bool:
        """Returns True if element is parallel block or external transclusion."""
        return self._is_parallel_element(element) or self._is_external_transclusion(element)
    
    def _process_element(self, element: ElementBase, parent: Optional[ElementBase] = None, 
                        inside_parallel: bool = False, hierarchy_tag: Optional[str] = None,
                        hierarchy_marked: bool = False) -> ElementBase:
        """Process a single element, handling unflattening if needed.
        
        Args:
            element: The element to process
            parent: The parent element (used to access siblings)
            inside_parallel: Whether we're currently inside a parallel block
            hierarchy_tag: The tag of the hierarchy being processed (if any)
            hierarchy_marked: Whether the hierarchy has been marked with part=first
            
        Returns:
            The processed element
        """
        start_uuid = self._get_start_attr(element)
        
        # Check if this is a parallel element
        is_parallel = self._is_parallel_element(element)
        is_external_trans = self._is_external_transclusion(element)
        
        # Update inside_parallel state
        if is_parallel:
            # We're entering a parallel block
            inside_parallel = True
        
        # If this element has a p:start attribute, we need to collect siblings
        if start_uuid is not None:
            # The element's tail becomes its text
            if element.tail:
                if element.text:
                    element.text = element.text + element.tail
                else:
                    element.text = element.tail
                element.tail = None
            
            # Determine if this is a hierarchy element (not a parallel block)
            is_hierarchy = not is_parallel and not is_external_trans
            current_hierarchy_tag = element.tag if is_hierarchy else hierarchy_tag
            current_hierarchy_marked = hierarchy_marked
            
            # If this is a hierarchy element inside a parallel block, mark it with part=continue
            if is_hierarchy and inside_parallel and hierarchy_tag == element.tag:
                element.set("part", "continue")
                current_hierarchy_marked = True
            # If this is a hierarchy element and we haven't marked it yet, we'll mark it later
            # if we encounter a parallel block or external transclusion
            
            # Collect all following siblings until we find the matching p:end
            if parent is not None:
                collected_children = []
                
                # Find all siblings after this element
                siblings = list(parent)
                try:
                    element_index = siblings.index(element)
                except ValueError:
                    # Element not found in siblings (shouldn't happen, but handle gracefully)
                    element_index = -1
                
                if element_index >= 0:
                    # Collect siblings to process (from element_index+1 onwards)
                    siblings_to_process = siblings[element_index + 1:]
                    current_inside_parallel = inside_parallel
                    
                    for sibling in siblings_to_process:
                        # Check if sibling is still a child of parent (it might have been removed
                        # during recursive processing if it had nested p:start/p:end)
                        if sibling.getparent() is not parent:
                            # Sibling was already removed, skip it
                            continue
                        
                        # Check if sibling is a parallel block or external transclusion
                        sibling_is_parallel = self._is_parallel_element(sibling)
                        sibling_is_external_trans = self._is_external_transclusion(sibling)
                        sibling_should_pause = sibling_is_parallel or sibling_is_external_trans
                        
                        # If we encounter a parallel block or external transclusion while processing a hierarchy
                        if sibling_should_pause and is_hierarchy and not current_hierarchy_marked:
                            # Mark the hierarchy with part=first
                            element.set("part", "first")
                            current_hierarchy_marked = True
                        
                        # Check if sibling is the end marker for this element
                        end_uuid = self._get_end_attr(sibling)
                        
                        if end_uuid == start_uuid:
                            # Found the matching end marker
                            # Save its tail to become the tail of the unflattened element
                            end_tail = sibling.tail
                            # Remove the end marker (check again that it's still a child)
                            if sibling.getparent() is parent:
                                parent.remove(sibling)
                            # Set the element's tail to the end marker's tail
                            if end_tail:
                                element.tail = end_tail
                            break
                        else:
                            # This sibling is part of the content to collect
                            # If it's a parallel block or external transclusion, process it with priority
                            if sibling_should_pause:
                                # Process the parallel block/transclusion first (priority)
                                # Pass the hierarchy info so elements inside can be marked
                                # For parallel blocks, we enter them, so inside_parallel=True
                                # For external transclusions, we don't enter a parallel block
                                processed_sibling = self._process_element(
                                    sibling, parent, 
                                    inside_parallel=sibling_is_parallel,  # True if parallel block
                                    hierarchy_tag=current_hierarchy_tag,
                                    hierarchy_marked=current_hierarchy_marked
                                )
                                # After processing, add to collected children
                                collected_children.append(processed_sibling)
                                # Remove from parent (we'll add it as child of element)
                                if sibling.getparent() is parent:
                                    parent.remove(sibling)
                            else:
                                # Regular sibling processing
                                processed_sibling = self._process_element(
                                    sibling, parent,
                                    inside_parallel=current_inside_parallel,
                                    hierarchy_tag=current_hierarchy_tag,
                                    hierarchy_marked=current_hierarchy_marked
                                )
                                collected_children.append(processed_sibling)
                                # Remove from parent (we'll add it as child of element)
                                if sibling.getparent() is parent:
                                    parent.remove(sibling)
                    
                    # Add collected children to the element
                    for child in collected_children:
                        element.append(child)
            
            # Remove the p:start attribute
            self._remove_start_attr(element)
        
        # Process children recursively (they may have their own p:start/p:end)
        # Make a copy of children list since we'll be modifying it during recursion
        children = list(element)
        for child in children:
            # Determine if we're still inside a parallel block
            child_inside_parallel = inside_parallel
            if is_parallel:
                # We're inside this parallel block
                child_inside_parallel = True
            
            # Check if child is a hierarchy element that should get part=continue
            child_start_uuid = self._get_start_attr(child)
            if (child_start_uuid is not None and 
                not self._is_parallel_element(child) and 
                not self._is_external_transclusion(child) and
                child_inside_parallel and 
                hierarchy_tag is not None and
                child.tag == hierarchy_tag):
                # This is a continuation of the hierarchy inside a parallel block
                child.set("part", "continue")
            
            self._process_element(
                child, element,
                inside_parallel=child_inside_parallel,
                hierarchy_tag=hierarchy_tag if not is_parallel else None,
                hierarchy_marked=hierarchy_marked
            )
        
        return element
    
    def process(self) -> ElementBase:
        """Process the root element and unflatten the structure.
        
        Returns:
            The processed root element (modified in place)
        """
        return self._process_element(self.root_element, None)


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

from pathlib import Path
from typing import Optional
from lxml.etree import ElementBase
from lxml import etree

from opensiddur.exporter.linear import get_linear_data


class CompilerProcessor:
    def __init__(self, root_file: Path | str):
        self.root_file = root_file
        self.linear_data = get_linear_data()
        if isinstance(self.root_file, Path):
            self.root_tree = etree.parse_xml(self.root_file)
        else:
            self.root_tree = etree.fromstring(self.root_file)
        # Extract namespaces from root_tree and save to self.ns_map
        # lxml stores nsmap at the Element level, not the whole tree for parsed objects
        if hasattr(self.root_tree, 'nsmap'):
            self.ns_map = dict(self.root_tree.nsmap) if self.root_tree.nsmap else {}
        else:
            self.ns_map = {}

    def process(self, root: Optional[ElementBase] = None):
        """
        Recursively process elements and text nodes of root_tree as an identity transform.
        If root is not provided, use self.root_tree.
        Yields elements and string text nodes (identity traversal).
        """
        if root is None:
            root = self.root_tree

        copied = etree.Element(root.tag, nsmap=self.ns_map)

        # Copy attributes
        for key, value in root.attrib.items():
            copied.set(key, value)
        copied.text = root.text

        for child in root:
            processed = self.process(child)
            if child.tail:
                processed.tail = child.tail
            copied.append(processed)

        return copied

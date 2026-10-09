"""A resolved conditional rubric still uses the edition's instruction selection."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from lxml import etree
from opensiddur.exporter.compiler import CompilerProcessor
from opensiddur.exporter.external_compiler import ExternalCompilerProcessor
from opensiddur.exporter.inline_compiler import InlineCompilerProcessor
from opensiddur.exporter.linear import LinearData
from opensiddur.exporter.refdb import ReferenceDatabase, UrnMapping

TEI='http://www.tei-c.org/ns/1.0'
J='http://jewishliturgy.org/ns/jlptei/2'
URN='urn:x-opensiddur:instruction:aseret_yemei_teshuvah/add'


class ConditionalInstructionSelectionTests(unittest.TestCase):
    def compile(self, selected, processor_class):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        base=Path(temp.name)
        for project in ['book','instructions']:(base/project).mkdir()
        body=f'''<tei:p>Before <j:declare xml:id="d"><tei:fs type="test"><tei:f name="include"><tei:binary value="true"/></tei:f></tei:fs></j:declare>
          <j:conditional xml:id="c"><tei:note type="instruction" corresp="{URN}">Original rubric</tei:note>
          <tei:fs type="test"><tei:f name="include"><tei:binary value="true"/></tei:f></tei:fs></j:conditional>Included
          <j:endConditional target="#c"/> After<j:endDeclare target="#d"/></tei:p>'''
        wrapper=lambda content:f'<tei:TEI xmlns:tei="{TEI}" xmlns:j="{J}" xml:lang="en"><tei:text><tei:body>{content}</tei:body></tei:text></tei:TEI>'
        (base/'book'/'text.xml').write_text(wrapper(body))
        replacement=etree.fromstring(wrapper(f'<tei:note type="instruction" corresp="{URN}">{selected}</tei:note>').encode())
        (base/'instructions'/'text.xml').write_bytes(etree.tostring(replacement))
        note=replacement.find('.//{'+TEI+'}note')
        refdb=MagicMock(spec=ReferenceDatabase)
        refdb.get_references_to.return_value=[]
        refdb.get_urn_mappings.return_value=[UrnMapping(urn=URN,project='instructions',file_name='text.xml',element_path=note.getroottree().getpath(note),element_tag=note.tag,element_type='instruction')]
        data=LinearData(instruction_priority=['instructions','book']);data.xml_cache.base_path=base
        kwargs={'from_start':None,'to_end':None} if processor_class is InlineCompilerProcessor else {}
        result=processor_class('book','text.xml',linear_data=data,reference_database=refdb,**kwargs).process()
        roots=result if isinstance(result,list) else [result]
        return ' '.join(' '.join(''.join(n.itertext()).split()) for n in roots),roots

    def test_true_conditional_uses_selected_instruction(self):
        for cls in [CompilerProcessor,ExternalCompilerProcessor,InlineCompilerProcessor]:
            with self.subTest(processor=cls.__name__):
                text,_=self.compile('Selected rubric',cls)
                self.assertIn('Selected rubric',text)
                self.assertNotIn('Original rubric',text)
                self.assertIn('Included',text);self.assertIn('After',text)

    def test_selected_empty_instruction_omits_fulfilled_rubric_and_keeps_tail(self):
        for cls in [CompilerProcessor,ExternalCompilerProcessor,InlineCompilerProcessor]:
            with self.subTest(processor=cls.__name__):
                text,roots=self.compile('',cls)
                self.assertEqual(text,'Before Included After')
                self.assertFalse(any(n.findall('.//{'+TEI+'}note') for n in roots))

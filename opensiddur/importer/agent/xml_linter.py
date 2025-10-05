# XML Linter agent
# Will lint a whole document or a fragment of a document
# Returns a list of errors or a no-error signal
import re
from pydantic import BaseModel, Field
from saxonche import PySaxonProcessor


from common import SCHEMA_RNG_PATH, SCHEMA_SCH_PATH, SCHEMA_SCH_XSLT_PATH
from util import validate


class XMLLinterInput(BaseModel):
    xml: str = Field(description = "The XML to lint")
    start_element: str = Field(description = "The start element of the fragment to lint")

class XMLLinterOutput(BaseModel):
    errors: list[str] = Field(default_factory = list, 
        description = "A list of errors")
    explanation: str = Field(description = "A textual explanation of the errors")

def rng_with_start(start_element: str) -> str:
    # make sure the new start exists. It may be named s/:/_/

    start_element_ref = start_element.replace(":", "_")
    with open(SCHEMA_RNG_PATH, "r") as f:
        schema = f.read()
        # Replace the start element in the RelaxNG schema with the given start_element
        # This assumes the schema uses <start>...</start> as the entry point
        # and replaces its contents with <ref name="start_element"/>

    xslt = f'''
<xsl:stylesheet version="2.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rng="http://relaxng.org/ns/structure/1.0"
    exclude-result-prefixes="rng">

  <!-- Identity transform -->
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Patch the <rng:choice> inside <rng:start> -->
  <xsl:template match="rng:start/rng:choice">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
      <rng:ref name="{start_element_ref}"/>
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
'''

    with PySaxonProcessor(license=False) as proc:
        # Use Saxon/C XPath processor to check for rng:define[@name='{start_element_ref}']
        xpath_expr = f"//rng:define[@name='{start_element_ref}']"
        xpath_proc = proc.new_xpath_processor()
        xpath_proc.declare_namespace("rng", "http://relaxng.org/ns/structure/1.0")
        doc = proc.parse_xml(xml_text=schema)
        xpath_proc.set_context(xdm_item=doc)
        result_nodes = xpath_proc.evaluate(xpath_expr)
        if not result_nodes or (hasattr(result_nodes, 'count') and result_nodes.count == 0):
            raise ValueError(f"RelaxNG schema does not define an element with name {start_element}='{start_element_ref}'")
        xslt_proc = proc.new_xslt30_processor()
        
        # Compile the XSLT from string
        executable = xslt_proc.compile_stylesheet(stylesheet_text=xslt)
        if executable is None:
            raise RuntimeError("Failed to compile XSLT for patching RelaxNG start element.")
        # Transform the schema string
        document = proc.parse_xml(xml_text=schema)
        result = executable.transform_to_string(xdm_node=document)
        return result

def xml_linter(
    input: XMLLinterInput
) -> XMLLinterOutput:
    relaxng_schema = rng_with_start(input.start_element)
    is_valid, errors = validate(input.xml, schema=relaxng_schema, schematron=SCHEMA_SCH_XSLT_PATH)
    if is_valid:
        return XMLLinterOutput(errors=[], explanation="The XML is valid")
    else:
        return XMLLinterOutput(errors=errors, explanation="The XML is invalid")
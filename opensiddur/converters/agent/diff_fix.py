from langchain.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import ChatOpenAI
from pydantic import BaseModel
from pydantic import Field

from common import API_KEY, LLM_BASE_URL
try:
    from opensiddur.converters.agent.source_file import SourceFileInput, SourceFileOutput
except ImportError:
    from source_file import SourceFileInput, SourceFileOutput
import diff_match_patch as dmp_module

DIFF_FIX_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct"

class DiffFixInput(BaseModel):
    source_xml: str = Field(description = "The source XML that has an error")
    error_message: str = Field(description = "The error message that indicates what is wrong with the source XML")
    messages: list[tuple[str, str]] = Field(description = "A list of roles and messages in the prior conversation, including instructions about this source")

class DiffFixOutput(BaseModel):
    explanation: str = Field(description = "A textual explanation of the header you produced. If you made any choices, explain them.")
    patch: str = Field(description = "A patch that can be run on the source XML to fix the error")


def diff_fix(
    input: DiffFixInput
) -> DiffFixOutput:
# TODO: this needs to be able to look up XML schema elements
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
# Role
You are an expert in XML encoding, TEI, in correcting errors, and in the diff format as used by patch.

# Goal
You will be given a source XML file or fragment and an error message that indicates what is wrong with it.
Your goal is to produce a patch that can be run on the source file to fix the error.

"""),
        ("user", """
# Source XML:
{source_xml}

# Error message:
{error_message}
"""),
("placeholder", "{messages}")
    ]).partial(**input.model_dump())
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=API_KEY,
        model=DIFF_FIX_MODEL)
    llm = llm.with_structured_output(DiffFixOutput)
    llm = prompt | llm
    response = llm.invoke(input.model_dump())
    return response

def apply_patch(
    input: SourceFileOutput,
    patch: DiffFixOutput
) -> SourceFileOutput:
    # Use diff-match-patch to apply the patch to input.source_tei
    
    dmp = dmp_module.diff_match_patch()
    # The patch is expected to be in unified diff format as a string
    patches = dmp.patch_fromText(patch.patch)
    patched_text, results = dmp.patch_apply(patches, input.source_tei)
    # Optionally, check if all patches applied successfully
    if not all(results):
        raise ValueError("Not all patches could be applied successfully.")

    # Return a new SourceFileOutput with the patched source_tei and the original explanation
    return SourceFileOutput(
        explanation=input.explanation,
        source_tei=patched_text
    )
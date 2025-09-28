from langchain.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import ChatOpenAI
from pydantic import BaseModel
from pydantic import Field

from common import API_KEY, LLM_BASE_URL

SOURCE_FILE_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct"

class SourceFileInput(BaseModel):
    name_of_section: str = Field(description = "The name of the section you are encoding")
    name_of_the_source_text: str = Field(description = "The name of the source text")
    namespace: str = Field(description = "The namespace of the project (eg, bible, siddur)")
    project_id: str = Field(description = "The ID of the project")
    previous_encoding: str = Field(description = "The prior encoding of the source text")
    previous_page: str = Field(description = "The previous page of the source text")
    next_page: str = Field(description = "The next page of the source text")
    page_content: str = Field(description = "The content of the page you are encoding")
    messages: list[tuple[str, str]] = Field(description = "A list of roles and messages in the prior conversation, including instructions about this source")

class SourceFileOutput(BaseModel):
    explanation: str = Field(description = "A textual explanation of the header you produced. If you made any choices, explain them.")
    source_tei: str = Field(description = "TEI XML fragment representing the source text.")
    

def source_file(
    input: SourceFileInput
) -> SourceFileOutput:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
# Role
You are an expert in digital humanities and in XML encoding and TEI.

# Goal
Your goal is to take the given source text and produce a fragment of a TEI XML tei:text section that fits the given template according to the subset of TEI XML used by Open Siddur.
The source text you are given may include another project's XML, MediaWiki or HTML markup, or other textual representation.
The final result must be well-formed XML and valid according to a subset of the TEI specification.
If you make an errors, your answer will be returned to you with an error message and
you will correct the error.

# Examples
<tei:text xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:j="http://jewishliturgy.org/ns/jlptei/2">
    <tei:front>
        <tei:p>This is the front matter of the source text. If there is no front matter (prefaces, title or copyright pages, for example), omit the front element.</tei:p>
    </tei:front>
    <tei:body>
        <tei:div type="book" n="Name" corresp="urn:x-opensiddur:text:bible:book_name">
            <tei:head>Name</tei:head>
            <tei:milestone unit="chapter" n="1" corresp="urn:x-opensiddur:text:bible:book_name/1"/>
            <tei:p>
                <tei:milestone unit="verse" n="1" corresp="urn:x-opensiddur:text:bible:book_name/1/1"/>
                This is a paragraph inside a biblical text, and this is the first verse.
                <tei:milestone unit="verse" n="2" corresp="urn:x-opensiddur:text:bible:book_name/1/2"/>
                This is a paragraph inside a biblical text, and this is the second verse.
                <tei:milestone unit="verse" n="3" corresp="urn:x-opensiddur:text:bible:book_name/1/3"/>
                This verse has <j:divineName>God's</j:divineName> name.
                <tei:milestone unit="verse" n="4" corresp="urn:x-opensiddur:text:bible:book_name/1/4"/>
                This verse has a word rendered in <tei:hi rend="small-caps">small caps</tei:hi>.
            </tei:p>
            <tei:lg>
                <tei:l>
                    <tei:milestone unit="verse" n="5" corresp="urn:x-opensiddur:text:bible:book_name/1/5"/>
                    This verse has a line of poetry.</tei:l>
                    <tei:l>Use it instead of a paragraph when the poem is the primary structure.</tei:l>
            </tei:lg>
        </tei:div>
    </tei:body>
    <tei:back>
        <tei:p>This is the back matter of the source text. If there is no back matter, omit the back element.</tei:p>
    </tei:back>
</tei:text>

# Instructions
- Write the XML code according to the example.
- If you have any textual explanation, include it in the explanation section
- Do not write XML comments.
- Only include text that is in the current page. Do not make up any text or add commentary or explanation to the source_tei. Do add explanations in the explanation field.
- The namespaces and prefixes you ahould use are:
  - tei: http://www.tei-c.org/ns/1.0
  - j: http://jewishliturgy.org/ns/jlptei/2
- You will be encoding from the named section {name_of_section} from {name_of_the_source_text}. 
- Stop encoding when you have finished the section, then close all open XML tags.
- Do not stop encoding the text from the current page until the named section is finished or you have finished the currentpage.
- Do not close open XML tags until you are sure that the paragraph (tei:p), line/line group (tei:l, tei:lg) is finished.
- You may REFERENCE, but NOT ENCODE FROM, the previous page and the next page.
- Reference the previous page to see if you are continuing a section or starting a new one.
- Reference the next page to see if you need to end the section at the end of the current page. DO NOT encode text from the next page.
"""),
        ("user", """
# Previous page:
{previous_page}

# Next page:
{next_page}

# Current page you are encoding:
{page_content}

# The last part you encoded (do not repeat it in your output):
{previous_encoding}
"""),
("placeholder", "{messages}")
    ]).partial(**input.model_dump())
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=API_KEY,
        model=SOURCE_FILE_MODEL)
    llm = llm.with_structured_output(SourceFileOutput)
    llm = prompt | llm
    response = llm.invoke({ "messages":[{"role": "user", "content": "Go."}]})
    return response

class CompletionCheckOutput(BaseModel):
    explanation: str = Field(description = "A textual explanation of why you decided that the page is complete or not.")
    is_complete: bool = Field(description = "Whether the section is complete")

def completion_check(
    input: SourceFileInput,
    output: SourceFileOutput
) -> CompletionCheckOutput:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
# Role
You are a careful reader and a fair and accurate judge.

# Goal
Your goal is to tell whether the given XML fragment that corresponds to part of the given named section, corresponds to the text given from the source it was encoded from.
If it is missing any textual content from the source text, tell what is missing and return False.
If they represent the same textual content and that content is complete, return True.
Only judge based on the exact content of the source text as given. Do not use external knowledge.
Only judge text and the elements of the source and XML encoding that are semantically relevant to the text. Do not judge metadata.
Only judge textual content from the source text that is part of the named section. If the section ends in the middle of the source text and is fully represented in the encoded text, it is complete.
"""),
        ("user", """
# Section name:
{section_name}

# Source text:
{source_text}

# XML fragment:
{xml_fragment}
"""),
("placeholder", "{messages}")
    ]).partial(
        section_name=input.name_of_section,
        xml_fragment=output.source_tei,
        source_text=input.page_content,
        messages=input.messages
    )
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=API_KEY,
        model=SOURCE_FILE_MODEL)
    llm = llm.with_structured_output(CompletionCheckOutput)
    llm = prompt | llm
    response = llm.invoke({})
    return response


class SectionCompletionCheckOutput(BaseModel):
    explanation: str = Field(description = "A textual explanation of why you decided that the section is complete or not.")
    is_complete: bool = Field(description = "Whether the section is complete")


def section_completion_check(
    input: SourceFileInput,
    output: SourceFileOutput
) -> SectionCompletionCheckOutput:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
# Role
You are a careful reader and a fair and accurate judge.

# Goal
Your goal is to tell whether the given XML fragment contains the end of a 
named section. You will look at the content of the fragment and the next page
of the source text. If the next page continues the same section, return is_complete=False.
If the next page starts or continues a new section, return is_complete=True. 
"""),
        ("user", """
# Section name:
{section_name}

# XML fragment:
{xml_fragment}

# Next page:
{next_page}
"""),
("placeholder", "{messages}")
    ]).partial(
        section_name=input.name_of_section,
        xml_fragment=output.source_tei,
        next_page=input.next_page,
        messages=input.messages
    )
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=API_KEY,
        model=SOURCE_FILE_MODEL)
    llm = llm.with_structured_output(SectionCompletionCheckOutput)
    llm = prompt | llm
    response = llm.invoke({})
    return response

from langchain.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import ChatOpenAI
from pydantic import BaseModel
from pydantic import Field

from common import API_KEY, LLM_BASE_URL

PROJECT_HEADER_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct"

class ProjectHeaderInput(BaseModel):
    namespace: str = Field(description = "The namespace of the project (eg, bible, siddur)")
    top_level_entrypoint: str = Field(description = "The top level entry point of the project (eg, tanakh, siddur)")
    front_matter: str = Field(description = "The front matter of the project, such as text, HTML, or MediaWiki title or copyright page")
    project_id: str = Field(description = "The ID of the project")
    about_transcription: str = Field(description = "A description of the transcription source")
    messages: list[tuple[str, str]] = Field(description = "A list of roles and messages in the prior conversation")

class ProjectHeaderOutput(BaseModel):
    explanation: str = Field(description = "A textual explanation of the header you produced. If you made any choices, explain them.")
    header: str = Field(description = "The TEI header of the project. Must be valid TEI XML.")
    

def project_header(
    input: ProjectHeaderInput
) -> ProjectHeaderOutput:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
# Role
You are an expert in digital humanities and in XML encoding and TEI.

# Goal
Your goal is to take the given front matter and produce a valid TEI header that fits the given template.
The front matter you are given may include another project's metadata or TEI header, MediaWiki or HTML markup of the title or copyright page, or other textual representation.
Your result must be well-formed XML and valid according to a subset of the TEI specification.
If you make an errors, your answer will be returned to you with an error message and
you will correct the error.

# Template
<tei:teiHeader>
    <tei:fileDesc>
        <tei:titleStmt>
            <tei:title type="main" xml:lang="{{LANGUAGE}}">{{MAIN TITLE}}</tei:title>
            <tei:title type="sub" xml:lang="{{LANGUAGE}}">{{COMBINE ALL SUBTITLES INTO ONE CONTAINER HERE}}</tei:title>
            <tei:title type="alt" xml:lang="{{LANGUAGE}}">{{ ALTERNATE/TRANSLATED TITLE}}</tei:title>
            <tei:title type="alt" xml:lang="{{LANGUAGE}}">{{COMBINE ALL ALTERNATE/TRANSLATED SUBTITLES INTO ONE CONTAINER HERE}}</tei:title>
         </tei:titleStmt>
         <tei:publicationStmt>
            <tei:distributor>
               <tei:ref target="http://opensiddur.org">Open Siddur Project</tei:ref>
            </tei:distributor>
            <tei:idno type="urn">urn:x-opensiddur:text:{namespace}:{top_level_entrypoint}@{project_id}</tei:idno>
            <tei:availability status="free">
               <tei:licence target="{{LICENSE_URL}}">{{LICENSE_NAME}}</tei:licence>
            </tei:availability>
         </tei:publicationStmt>
         <tei:sourceDesc>
            <tei:bibl>
               <tei:title>{{FIRST_SOURCE_TITLE}}</tei:title>
               <tei:editor>{{FIRST_SOURCE_EDITOR}}</tei:editor>
               <tei:edition>{{FIRST_SOURCE_EDITION}}</tei:edition>
               <tei:publisher>{{FIRST_SOURCE_PUBLISHER}}</tei:publisher>
               <tei:pubPlace>
                  {{FIRST_SOURCE_PHYSICAL_PUBLICATION_PLACE_FOR_PHYSICAL_BOOKS}}
                  <tei:ref target="{{FIRST_SOURCE_WEBSITE_URL_FOR_WEBSITES}}">{{FIRST_SOURCE_WEBSITE_NAME_FOR_WEBSITES}}</tei:ref>
               </tei:pubPlace>
               <tei:date>{{FIRST_SOURCE_PUBLICATION_DATE}}</tei:date>
               {{ ANY_OTHER_FIRST_SOURCE_DETAILS }}
            </tei:bibl>
            {{ INCLUDE ALL THE OTHER SOURCES FROM THE FRONT MATTER, IF APPLICABLE }}
        </tei:sourceDesc>
    </tei:fileDesc>
</tei:teiHeader>
   
# Instructions
- Write the XML code in the given structure.
- If you have any textual explanation, include it in the explanation section
- Do not write XML comments.
- The namespaces and prefixes you ahould use are:
  - tei: http://www.tei-c.org/ns/1.0
  - j: http://jewishliturgy.org/ns/jlptei/2
- Every document has a main title. Subtitles and alternate titles may be present.
- If the document does not explicitly reference a license, assume it is in the public domain and use the Creative Commons Zero Public Domain Declaration (http://www.creativecommons.org/publicdomain/zero/1.0/).
- Fill in as much bibliographic information as you can from the information you have. The project must have at least one bibliographic source. Some projects declare their own sources, and these should be included in the sourceDesc bibliography. Omit irrelevant details. For example, exclude the tei:author element if there is no author. Include all the known details. For example: include multiple tei:editor elements if there is more than on editor. 
- If applicable, provide a separate citation for the transcription source and the original text.
"""),
        ("user", """
# Project front matter:
{front_matter}

# About the transcription:
{about_transcription}
"""),
("placeholder", "{messages}")
    ])
    llm = ChatOpenAI(
        base_url=LLM_BASE_URL,
        api_key=API_KEY,
        model=PROJECT_HEADER_MODEL)
    llm = llm.with_structured_output(ProjectHeaderOutput)
    llm = prompt | llm
    response = llm.invoke(input.model_dump())
    return response
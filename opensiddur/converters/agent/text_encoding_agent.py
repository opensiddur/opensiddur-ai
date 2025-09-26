from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
import json

try:
    from .common import Page
    from .source_file import SourceFileInput, SourceFileOutput, source_file, completion_check, section_completion_check
    from .xml_linter import XMLLinterInput, XMLLinterOutput, xml_linter
    from .diff_fix import DiffFixInput, DiffFixOutput, diff_fix, apply_patch
    from .tools import get_page
except ImportError:
    # Handle direct execution
    from common import Page
    from source_file import SourceFileInput, SourceFileOutput, source_file, completion_check, section_completion_check
    from xml_linter import XMLLinterInput, XMLLinterOutput, xml_linter
    from diff_fix import DiffFixInput, DiffFixOutput, diff_fix, apply_patch
    from tools import get_page


class TextEncodingAgentState(TypedDict):
    """State for the text encoding agent"""
    # Input parameters
    name_of_section: str
    name_of_source_text: str
    namespace: str
    project_id: str
    start_page: int
    end_page: int
    
    # Processing state
    current_page: int
    previous_page_content: str
    current_page_content: str
    next_page_content: str
    current_encoding: str
    messages: list[tuple[str, str]]
    
    # Results
    final_xml: str
    encoding_errors: list[str]
    is_complete: bool
    completion_explanation: str
    
    # Control flow
    error_count: int
    max_errors: int
    next_action: Literal["encode_page", "validate_xml", "fix_errors", "check_completion", "check_section_completion", "done"]
    
    # Checkpointing
    session_id: Optional[str]
    last_checkpoint_time: Optional[str]


class TextEncodingAgentInput(BaseModel):
    """Input for the text encoding agent"""
    name_of_section: str = Field(description="The name of the section to encode")
    name_of_source_text: str = Field(description="The name of the source text")
    namespace: str = Field(description="The namespace of the project (e.g., bible, siddur)")
    project_id: str = Field(description="The ID of the project")
    start_page: int = Field(description="Starting page number (inclusive)")
    end_page: int = Field(description="Ending page number (inclusive)")
    max_errors: int = Field(default=5, description="Maximum number of error correction attempts")
    session_id: Optional[str] = Field(default=None, description="Session ID to resume from")
    enable_checkpointing: bool = Field(default=True, description="Enable checkpointing for this session")


def create_session_id(input_data: TextEncodingAgentInput) -> str:
    """Create a unique session ID for this encoding session"""
    import hashlib
    import time
    
    # Create a hash based on the input parameters
    content = f"{input_data.name_of_section}_{input_data.name_of_source_text}_{input_data.namespace}_{input_data.project_id}_{input_data.start_page}_{input_data.end_page}"
    hash_id = hashlib.md5(content.encode()).hexdigest()[:8]
    timestamp = int(time.time())
    return f"encoding_{hash_id}_{timestamp}"


def save_checkpoint_to_file(state: TextEncodingAgentState, checkpoint_file: str) -> None:
    """Save the current state to a checkpoint file"""
    import datetime
    
    checkpoint_data = {
        "state": dict(state),
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": state.get("session_id", "unknown")
    }
    
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f, indent=2)


def load_checkpoint_from_file(checkpoint_file: str) -> Optional[TextEncodingAgentState]:
    """Load state from a checkpoint file"""
    try:
        with open(checkpoint_file, "r") as f:
            checkpoint_data = json.load(f)
        return checkpoint_data["state"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def encode_page(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Encode the current page using the source_file function"""
    print(f"Encoding page {state['current_page']}...")
    
    # Prepare input for source_file
    source_input = SourceFileInput(
        name_of_section=state['name_of_section'],
        name_of_the_source_text=state['name_of_source_text'],
        namespace=state['namespace'],
        project_id=state['project_id'],
        previous_encoding=state['current_encoding'],
        previous_page=state['previous_page_content'],
        next_page=state['next_page_content'],
        page_content=state['current_page_content'],
        messages=state['messages']
    )
    
    try:
        # Encode the page
        source_output = source_file(source_input)
        
        # Update state with encoding results
        new_state = {
            **state,
            "current_encoding": source_output.source_tei,
            "messages": state['messages'] + [
                ("assistant", f"Encoded page {state['current_page']}: {source_output.explanation}")
            ]
        }
        
        return new_state
        
    except Exception as e:
        print(f"Error encoding page {state['current_page']}: {str(e)}")
        return {
            **state,
            "encoding_errors": [f"Error encoding page {state['current_page']}: {str(e)}"]
        }


def check_completion(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Check if the current page encoding is complete"""
    print(f"Checking completion for page {state['current_page']}...")
    
    # Prepare input for completion check
    source_input = SourceFileInput(
        name_of_section=state['name_of_section'],
        name_of_the_source_text=state['name_of_source_text'],
        namespace=state['namespace'],
        project_id=state['project_id'],
        previous_encoding=state['current_encoding'],
        previous_page=state['previous_page_content'],
        next_page=state['next_page_content'],
        page_content=state["current_page_content"],
        messages=state['messages']
    )
    
    # Create a mock output for completion check
    mock_output = SourceFileOutput(
        explanation="Mock output for completion check",
        source_tei=state['current_encoding']
    )
    
    try:
        completion_result = completion_check(source_input, mock_output)
        print(f"Completion check ({completion_result.is_complete}): {completion_result.explanation}")
        if completion_result.is_complete:
            return {
                **state,
                "next_action": "check_section_completion"
            }
        else:
            # Continue encoding the same page
            return {
                **state,
                "messages": state['messages'] + [
                    ("assistant", f"Completion check failed: {completion_result.explanation}")
                ],
                "next_action": "encode_page"
            }
            
    except Exception as e:
        # If completion check fails, continue encoding the same page
        print(f"Completion check error: {str(e)}")
        
        return {
            **state,
            "messages": state['messages'] + [
                ("system", f"Completion check error: {str(e)}")
            ],
            "next_action": "encode_page"
        }


def check_section_completion(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Check if the entire section encoding is complete"""
    print(f"Checking section completion...")
    
    # Check if we've reached the end page
    if state['current_page'] >= state['end_page']:
        return {
            **state,
            "next_action": "validate_xml"
        }
    
    # Use section_completion_check to see if we should terminate early
    try:
        # Prepare input for section completion check
        source_input = SourceFileInput(
            name_of_section=state['name_of_section'],
            name_of_the_source_text=state['name_of_source_text'],
            namespace=state['namespace'],
            project_id=state['project_id'],
            previous_encoding=state['current_encoding'],
            previous_page=state['previous_page_content'],
            next_page=state['next_page_content'],
            page_content="",  # Not needed for section completion check
            messages=state['messages']
        )
        
        # Create a mock output for section completion check
        mock_output = SourceFileOutput(
            explanation="Mock output for section completion check",
            source_tei=state['current_encoding']
        )
        
        section_result = section_completion_check(source_input, mock_output)
        
        print(f"Section completion check ({section_result.is_complete}): {section_result.explanation}")
        if section_result.is_complete:
            print(f"Section completion check: {section_result.explanation}")
            return {
                **state,
                "final_xml": state['final_xml'] + state['current_encoding'],
                "messages": state['messages'] + [
                    ("assistant", f"Section completion check: {section_result.explanation}")
                ],
                "next_action": "validate_xml"
            }
        else:
            print(f"Section not complete, continuing: {section_result.explanation}")
            return {
                **state,
                "final_xml": state['final_xml'] + state['current_encoding'],
                "messages": state['messages'] + [
                    ("assistant", f"Section not complete: {section_result.explanation}")
                ],
                "next_action": "advance_page"
            }
            
    except Exception as e:
        print(f"Section completion check error: {e}")
        # If section completion check fails, continue to next page
        return {
            **state,
            "final_xml": state['final_xml'] + state['current_encoding'],
            "messages": state['messages'] + [
                ("system", f"Section completion check error: {str(e)}")
            ],
            "next_action": "advance_page"
        }


def advance_page(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Advance to the next page"""

    if not state['current_page_content']:
        print(f"Setting page to {state['current_page']}...")
        new_page = state['current_page']
        previous_page_content = ""
        current_page_obj = get_page.invoke({"page_number": new_page})
        current_page_content = current_page_obj.content if current_page_obj else ""

    else:
        print(f"Advancing from page {state['current_page']} to page {state['current_page'] + 1}...")
        new_page = state['current_page'] + 1
            
        # Update previous page content
        previous_page_content = state["current_page_content"]
        current_page_content = state["next_page_content"]
    
    # Update next page content
    next_page_obj = get_page.invoke({"page_number": new_page + 1})
    next_page_content = next_page_obj.content if next_page_obj else ""
    
    return {
        **state,
        "current_page": new_page,
        "previous_page_content": previous_page_content,
        "current_page_content": current_page_content,
        "next_page_content": next_page_content,
        "next_action": "encode_page"
    }


def validate_xml(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Validate the complete XML using xml_linter"""
    print("Validating complete XML...")
    
    # Prepare input for XML linter
    linter_input = XMLLinterInput(
        xml=state['final_xml'],
        start_element="tei:text"
    )
    
    try:
        linter_output = xml_linter(linter_input)
        print(f"XML validation ({not(linter_output.errors)}): {linter_output.errors}")
        if linter_output.errors:
            return {
                **state,
                "encoding_errors": linter_output.errors,
                "error_count": state['error_count'] + 1
            }
        else:
            return {
                **state,
                "encoding_errors": [],
            }
            
    except Exception as e:
        print(f"XML validation error: {str(e)}")
        return {
            **state,
            "encoding_errors": [f"XML validation error: {str(e)}"]
        }


def fix_errors(state: TextEncodingAgentState) -> TextEncodingAgentState:
    """Fix XML errors using diff_fix"""
    print(f"Fixing errors (attempt {state['error_count']}/{state['max_errors']})...")
    
    if state['error_count'] >= state['max_errors']:
        return {
            **state,
            "next_action": "done",
            "encoding_errors": state['encoding_errors'] + [f"Maximum error correction attempts ({state['max_errors']}) exceeded"]
        }
    
    # Prepare input for diff fix
    diff_input = DiffFixInput(
        source_xml=state['final_xml'],
        error_message="\n".join(state['encoding_errors']),
        messages=state['messages']
    )
    
    try:
        diff_output = diff_fix(diff_input)
        
        # Apply the patch
        source_output = SourceFileOutput(
            explanation="Fixed XML",
            source_tei=state['final_xml']
        )
        
        fixed_output = apply_patch(source_output, diff_output)
        print(f"Fixed XML: {fixed_output.explanation}")
        return {
            **state,
            "final_xml": fixed_output.source_tei,
            "encoding_errors": [],
            "messages": state['messages'] + [
                ("assistant", f"Applied error fixes: {diff_output.explanation}")
            ]
        }
        
    except Exception as e:
        print(f"Error fixing errors: {str(e)}")
        return {
            **state,
            "encoding_errors": state['encoding_errors'] + [f"Error fixing failed: {str(e)}"]
        }


def route_next_action(state: TextEncodingAgentState) -> str:
    """Route to the next action based on state"""
    return state.get("next_action", "encode_page")


def should_fix_errors(state: TextEncodingAgentState) -> str:
    """Check if we should fix errors or finish"""
    if state["encoding_errors"] and state["error_count"] < state["max_errors"]:
        return "fix_errors"
    else:
        return END


def create_text_encoding_agent(enable_checkpointing: bool = True) -> StateGraph:
    """Create the text encoding agent workflow with optional checkpointing"""
    
    # Create the state graph
    workflow = StateGraph(TextEncodingAgentState)
    
    # Add nodes
    workflow.add_node("encode_page", encode_page)
    workflow.add_node("check_completion", check_completion)
    workflow.add_node("check_section_completion", check_section_completion)
    workflow.add_node("advance_page", advance_page)
    workflow.add_node("validate_xml", validate_xml)
    workflow.add_node("fix_errors", fix_errors)
    
    # Add edges according to the specified flow:
    # encode_page -> check_completion (always)
    workflow.add_edge("encode_page", "check_completion")
    
    # check_completion -> encode_page (if false) or check_section_completion (if true)
    workflow.add_conditional_edges(
        "check_completion",
        route_next_action,
        {
            "encode_page": "encode_page",
            "check_section_completion": "check_section_completion"
        }
    )
    
    # check_section_completion -> advance_page (if false) or validate_xml (if true)
    workflow.add_conditional_edges(
        "check_section_completion",
        route_next_action,
        {
            "advance_page": "advance_page",
            "validate_xml": "validate_xml"
        }
    )
    
    # advance_page -> encode_page (always)
    workflow.add_edge("advance_page", "encode_page")
    
    # validate_xml -> END (if success) or fix_errors (if fails)
    workflow.add_conditional_edges(
        "validate_xml",
        should_fix_errors,
        {
            "fix_errors": "fix_errors",
            END: END
        }
    )
    
    # fix_errors -> validate_xml (always, repeat until success)
    workflow.add_edge("fix_errors", "validate_xml")
    
    # Set entry point
    workflow.set_entry_point("advance_page")
    
    # Compile with checkpointing if enabled
    if enable_checkpointing:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    else:
        return workflow.compile()


def run_text_encoding_agent(input_data: TextEncodingAgentInput) -> TextEncodingAgentState:
    """Run the text encoding agent with the given input"""
    
    # Create session ID
    session_id = input_data.session_id or create_session_id(input_data)
    
    # Initialize state
    initial_state = {
        "name_of_section": input_data.name_of_section,
        "name_of_source_text": input_data.name_of_source_text,
        "namespace": input_data.namespace,
        "project_id": input_data.project_id,
        "start_page": input_data.start_page,
        "end_page": input_data.end_page,
        "current_page": input_data.start_page,
        "previous_page_content": "",
        "current_page_content": "",
        "next_page_content": "",
        "current_encoding": "",
        "messages": [
            ("system", f"Encoding section '{input_data.name_of_section}' from '{input_data.name_of_source_text}' (pages {input_data.start_page}-{input_data.end_page})")
        ],
        "final_xml": "",
        "encoding_errors": [],
        "is_complete": False,
        "completion_explanation": "",
        "error_count": 0,
        "max_errors": input_data.max_errors,
        "session_id": session_id,
        "last_checkpoint_time": None
    }
    
    # Create and run the agent with checkpointing
    agent = create_text_encoding_agent(enable_checkpointing=input_data.enable_checkpointing)
    
    if input_data.enable_checkpointing:
        # Run with checkpointing
        config = {"configurable": {"thread_id": session_id}}
        result = agent.invoke(initial_state, config=config)
    else:
        # Run without checkpointing
        result = agent.invoke(initial_state)
    
    return result


def resume_text_encoding_agent(session_id: str) -> Optional[TextEncodingAgentState]:
    """Resume a text encoding agent from a checkpoint"""
    
    # Create agent with checkpointing
    agent = create_text_encoding_agent(enable_checkpointing=True)
    
    # Try to resume from checkpoint
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Get the current state from the checkpoint
        current_state = agent.get_state(config)
        if current_state and not current_state.next:
            # Workflow is complete
            return current_state.values
        elif current_state:
            # Continue from where we left off
            result = agent.invoke(None, config=config)
            return result
        else:
            return None
    except Exception as e:
        print(f"Error resuming from session {session_id}: {e}")
        return None


def list_checkpoints() -> list[dict]:
    """List available checkpoints (placeholder - would need persistent storage)"""
    # This is a placeholder - in a real implementation, you'd query your checkpoint storage
    return []


def save_checkpoint_manually(state: TextEncodingAgentState, filename: str) -> None:
    """Manually save a checkpoint to a file"""
    save_checkpoint_to_file(state, filename)


def load_checkpoint_manually(filename: str) -> Optional[TextEncodingAgentState]:
    """Manually load a checkpoint from a file"""
    return load_checkpoint_from_file(filename)

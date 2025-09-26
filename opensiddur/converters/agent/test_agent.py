#!/usr/bin/env python3
"""
Simple test for the text encoding agent.

This test verifies that the agent can be instantiated and basic workflow
components work correctly.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent))

from text_encoding_agent import (
    TextEncodingAgentInput,
    TextEncodingAgentState,
    create_text_encoding_agent,
    should_fix_errors,
    route_next_action
)


def test_input_model():
    """Test that the input model works correctly"""
    print("Testing TextEncodingAgentInput model...")
    
    input_data = TextEncodingAgentInput(
        name_of_section="Test Section",
        name_of_source_text="Test Source",
        namespace="test",
        project_id="test_project",
        start_page=1,
        end_page=3,
        max_errors=2
    )
    
    assert input_data.name_of_section == "Test Section"
    assert input_data.start_page == 1
    assert input_data.end_page == 3
    assert input_data.max_errors == 2
    
    print("✅ Input model test passed")


def test_workflow_creation():
    """Test that the workflow can be created"""
    print("Testing workflow creation...")
    
    try:
        workflow = create_text_encoding_agent()
        assert workflow is not None
        print("✅ Workflow creation test passed")
    except Exception as e:
        print(f"❌ Workflow creation failed: {e}")
        raise


def test_routing_functions():
    """Test the routing functions"""
    print("Testing routing functions...")
    
    # Test should_fix_errors
    state_with_errors_to_fix = {
        "encoding_errors": ["test error"],
        "error_count": 1,
        "max_errors": 3
    }
    assert should_fix_errors(state_with_errors_to_fix) == "fix_errors"
    
    state_max_errors = {
        "encoding_errors": ["test error"],
        "error_count": 3,
        "max_errors": 3
    }
    assert should_fix_errors(state_max_errors) == "__end__"
    
    state_no_errors = {
        "encoding_errors": [],
        "error_count": 0,
        "max_errors": 3
    }
    assert should_fix_errors(state_no_errors) == "__end__"
    
    # Test route_next_action
    state_with_action = {"next_action": "encode_page"}
    assert route_next_action(state_with_action) == "encode_page"
    
    print("✅ Routing functions test passed")


def test_state_model():
    """Test that the state model works correctly"""
    print("Testing state model...")
    
    state: TextEncodingAgentState = {
        "name_of_section": "Test",
        "name_of_source_text": "Test Source",
        "namespace": "test",
        "project_id": "test",
        "start_page": 1,
        "end_page": 3,
        "current_page": 1,
        "previous_page_content": "",
        "next_page_content": "",
        "current_encoding": "",
        "messages": [],
        "final_xml": "",
        "encoding_errors": [],
        "is_complete": False,
        "completion_explanation": "",
        "error_count": 0,
        "max_errors": 5
    }
    
    assert state["name_of_section"] == "Test"
    assert state["current_page"] == 1
    assert len(state["messages"]) == 0
    
    print("✅ State model test passed")


def main():
    """Run all tests"""
    print("Running text encoding agent tests...")
    print("=" * 50)
    
    try:
        test_input_model()
        test_workflow_creation()
        test_routing_functions()
        test_state_model()
        
        print("=" * 50)
        print("🎉 All tests passed!")
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

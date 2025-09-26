#!/usr/bin/env python3
"""
Example demonstrating checkpointing functionality in the text encoding agent.

This script shows how to:
1. Start an encoding session with checkpointing
2. Save manual checkpoints
3. Resume from checkpoints
4. Handle interrupted sessions
"""

from text_encoding_agent import (
    TextEncodingAgentInput, 
    run_text_encoding_agent,
    resume_text_encoding_agent,
    save_checkpoint_manually,
    load_checkpoint_manually
)
import time
import os


def demo_checkpointing():
    """Demonstrate checkpointing functionality"""
    
    print("=" * 60)
    print("TEXT ENCODING AGENT - CHECKPOINTING DEMO")
    print("=" * 60)
    
    # Example 1: Start a new encoding session with checkpointing
    print("\n1. Starting new encoding session with checkpointing...")
    
    input_data = TextEncodingAgentInput(
        name_of_section="Genesis Chapter 1",
        name_of_source_text="1917 Jewish Publication Society Bible",
        namespace="bible",
        project_id="jps1917",
        start_page=25,
        end_page=27,
        max_errors=3,
        enable_checkpointing=True  # Enable checkpointing
    )
    
    print(f"Session ID: {input_data.session_id or 'Will be generated'}")
    print(f"Encoding: {input_data.name_of_section}")
    print(f"Pages: {input_data.start_page}-{input_data.end_page}")
    
    # Run the agent
    result = run_text_encoding_agent(input_data)
    
    print(f"\n✅ Encoding completed!")
    print(f"Final XML length: {len(result.get('final_xml', ''))}")
    print(f"Pages processed: {result.get('current_page', 0)}")
    print(f"Session ID: {result.get('session_id', 'N/A')}")
    
    # Example 2: Manual checkpoint saving
    print("\n2. Demonstrating manual checkpoint saving...")
    
    checkpoint_file = "manual_checkpoint.json"
    save_checkpoint_manually(result, checkpoint_file)
    print(f"✅ Checkpoint saved to {checkpoint_file}")
    
    # Example 3: Load checkpoint manually
    print("\n3. Loading checkpoint manually...")
    
    loaded_state = load_checkpoint_manually(checkpoint_file)
    if loaded_state:
        print(f"✅ Checkpoint loaded successfully")
        print(f"Loaded state - Pages processed: {loaded_state.get('current_page', 0)}")
        print(f"Loaded state - XML length: {len(loaded_state.get('final_xml', ''))}")
    else:
        print("❌ Failed to load checkpoint")
    
    # Example 4: Resume from checkpoint (simulated)
    print("\n4. Demonstrating resume functionality...")
    
    if result.get('session_id'):
        print(f"Attempting to resume from session: {result['session_id']}")
        
        # In a real scenario, this would resume from where it left off
        # For this demo, we'll just show the concept
        resumed_result = resume_text_encoding_agent(result['session_id'])
        
        if resumed_result:
            print("✅ Successfully resumed from checkpoint")
            print(f"Resumed state - Pages processed: {resumed_result.get('current_page', 0)}")
        else:
            print("ℹ️  No active checkpoint to resume from (workflow completed)")
    
    # Cleanup
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"\n🧹 Cleaned up {checkpoint_file}")
    
    print("\n" + "=" * 60)
    print("CHECKPOINTING DEMO COMPLETE")
    print("=" * 60)


def demo_interrupted_session():
    """Demonstrate handling an interrupted session"""
    
    print("\n" + "=" * 60)
    print("INTERRUPTED SESSION DEMO")
    print("=" * 60)
    
    # Simulate starting a long encoding task
    print("Starting a long encoding task...")
    
    input_data = TextEncodingAgentInput(
        name_of_section="Long Document",
        name_of_source_text="Test Source",
        namespace="test",
        project_id="test_long",
        start_page=1,
        end_page=5,  # Simulate a longer task
        max_errors=3,
        enable_checkpointing=True
    )
    
    print(f"Session ID: {input_data.session_id}")
    print("This would normally run for a long time...")
    print("In a real scenario, you could:")
    print("1. Start the encoding process")
    print("2. If interrupted, use the checkpoint ID to resume")
    print("3. Call resume_text_encoding_agent(checkpoint_id)")
    
    # Simulate saving progress
    checkpoint_file = f"interrupted_session_{input_data.session_id}.json"
    print(f"\nSaving progress to {checkpoint_file}...")
    
    # In a real scenario, this would be the state when interrupted
    simulated_state = {
        "name_of_section": input_data.name_of_section,
        "name_of_source_text": input_data.name_of_source_text,
        "namespace": input_data.namespace,
        "project_id": input_data.project_id,
        "start_page": input_data.start_page,
        "end_page": input_data.end_page,
        "current_page": 3,  # Simulate being interrupted at page 3
        "current_encoding": "<tei:text>...partial encoding...</tei:text>",
        "session_id": input_data.session_id,
        "encoding_errors": [],
        "final_xml": "",
        "is_complete": False,
        "completion_explanation": "",
        "next_action": "encode_page",
        "error_count": 0,
        "max_errors": input_data.max_errors,
        "messages": [("system", "Encoding interrupted at page 3")],
        "previous_page_content": "",
        "next_page_content": "",
        "last_checkpoint_time": None
    }
    
    save_checkpoint_manually(simulated_state, checkpoint_file)
    print(f"✅ Progress saved to {checkpoint_file}")
    
    # Simulate resuming
    print(f"\nResuming from checkpoint...")
    loaded_state = load_checkpoint_manually(checkpoint_file)
    
    if loaded_state:
        print(f"✅ Resumed from page {loaded_state.get('current_page', 0)}")
        print(f"Current encoding length: {len(loaded_state.get('current_encoding', ''))}")
        print("Would continue encoding from here...")
    
    # Cleanup
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"\n🧹 Cleaned up {checkpoint_file}")


if __name__ == "__main__":
    # Run the checkpointing demo
    demo_checkpointing()
    
    # Run the interrupted session demo
    demo_interrupted_session()

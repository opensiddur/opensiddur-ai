#!/usr/bin/env python3
"""
Example usage of the text encoding agent.

This script demonstrates how to use the text encoding agent to encode
a section of text from a source document.
"""

from text_encoding_agent import TextEncodingAgentInput, run_text_encoding_agent


def main():
    """Example usage of the text encoding agent"""
    
    # Example input for encoding a section of the 1917 JPS Bible
    input_data = TextEncodingAgentInput(
        name_of_section="Genesis Chapter 1",
        name_of_source_text="1917 Jewish Publication Society Bible",
        namespace="bible",
        project_id="jps1917",
        start_page=25,
        end_page=27,  
        max_errors=3,  # Allow up to 3 error correction attempts
        enable_checkpointing=True,
        session_id="session_1"
    )
    
    print("Starting text encoding agent...")
    print(f"Encoding: {input_data.name_of_section}")
    print(f"Source: {input_data.name_of_source_text}")
    print(f"Pages: {input_data.start_page}-{input_data.end_page}")
    print(f"Max error correction attempts: {input_data.max_errors}")
    print("-" * 50)
    
    # Run the agent
    result = run_text_encoding_agent(input_data)
    
    # Display results
    print("\n" + "=" * 50)
    print("ENCODING COMPLETE")
    print("=" * 50)
    
    if result["final_xml"]:
        print("✅ Encoding successful!")
        print(f"Final XML length: {len(result['final_xml'])} characters")
        print("\nFirst 500 characters of encoded XML:")
        print("-" * 30)
        print(result["final_xml"][:500] + "..." if len(result["final_xml"]) > 500 else result["final_xml"])
        with open("example_usage.xml", "w") as f:
            f.write(result["final_xml"])
    else:
        print("❌ Encoding failed!")
        print("Errors encountered:")
        for error in result["encoding_errors"]:
            print(f"  - {error}")
    
    print(f"\nPages processed: {result['current_page']}")
    print(f"Error correction attempts: {result['error_count']}")
    
    if result["messages"]:
        print("\nProcessing messages:")
        for role, message in result["messages"][-5:]:  # Show last 5 messages
            print(f"  [{role}]: {message[:100]}{'...' if len(message) > 100 else ''}")


if __name__ == "__main__":
    main()

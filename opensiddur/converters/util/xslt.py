from argparse import ArgumentParser
import sys
from pathlib import Path
from typing import Optional
from saxonche import PySaxonProcessor

def xslt_transform(
    xslt_file: Path,
    input_file: Path, 
    output_file: Optional[Path] = None):
    
    try:
        # Read the input XML
        with open(input_file, 'r', encoding='utf-8') as input_fd:
            input_xml = input_fd.read()        
        
        with PySaxonProcessor(license=False) as proc:
            # Create XSLT processor
            xslt_proc = proc.new_xslt30_processor()
            
            # Compile the stylesheet
            executable = xslt_proc.compile_stylesheet(stylesheet_file=str(xslt_file))
            if executable is None:
                raise ValueError(f"Failed to compile XSLT: {xslt_proc.error_message}")
            
            # Parse the input XML
            document = proc.parse_xml(xml_text=input_xml)
            
            # Transform the document
            result = executable.transform_to_string(xdm_node=document)
            
            # Write the result to the output file
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as output_fd:
                    output_fd.write(result)
            else:
                sys.stdout.write(result)
            
    except Exception as e:
        print(f"Error in index function: {e}", file=sys.stderr)
        raise


def main():
    parser = ArgumentParser()
    parser.add_argument("-o", "--output", type=Path, required=False, default=None)
    parser.add_argument("transform_file", type=Path)
    parser.add_argument("input_file", type=Path)
    
    args = parser.parse_args()

    xslt_transform(args.transform_file, args.input_file, args.output)


if __name__ == "__main__":
    main()
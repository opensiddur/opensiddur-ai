#!/usr/bin/env python3
"""
JLPTEI to PDF Exporter

This script converts JLPTEI XML files to PDF format by first generating XeLaTeX,
then compiling it to PDF using XeLaTeX.
"""

import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from opensiddur.exporter.tex.xelatex import transform_xml_to_tex


def generate_tex(input_file, temp_tex_file):
    """
    Generate TeX file from JLPTEI XML using the existing XeLaTeX exporter.
    
    Args:
        input_file (Path): Path to the input TEI XML file
        temp_tex_file (Path): Path to the temporary TeX file to create
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Generating TeX from {input_file}...", file=sys.stderr)
        transform_xml_to_tex(str(input_file), output_file=str(temp_tex_file))
        print(f"TeX file generated: {temp_tex_file}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Error generating TeX: {e}", file=sys.stderr)
        return False


def compile_tex_to_pdf(tex_file, output_pdf):
    """
    Compile TeX file to PDF using XeLaTeX.
    
    Args:
        tex_file (Path): Path to the TeX file
        output_pdf (Path): Path to the output PDF file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Compiling {tex_file} to PDF...", file=sys.stderr)
        
        # Change to the directory containing the TeX file
        tex_dir = tex_file.parent
        tex_name = tex_file.stem
        
        # Run XeLaTeX
        cmd = [
            'xelatex',
            '-interaction=nonstopmode',
            '-output-directory', str(tex_dir),
            str(tex_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=tex_dir)
        
        if result.returncode != 0:
            print(f"XeLaTeX compilation failed:", file=sys.stderr)
            print(f"STDOUT: {result.stdout}", file=sys.stderr)
            print(f"STDERR: {result.stderr}", file=sys.stderr)
            return False
        
        # The PDF should be in the same directory as the TeX file
        generated_pdf = tex_dir / f"{tex_name}.pdf"
        
        if not generated_pdf.exists():
            print(f"PDF file not found: {generated_pdf}", file=sys.stderr)
            return False
        
        # Copy the generated PDF to the desired output location
        if generated_pdf != output_pdf:
            import shutil
            shutil.copy2(generated_pdf, output_pdf)
            print(f"PDF copied to: {output_pdf}", file=sys.stderr)
        else:
            print(f"PDF generated: {output_pdf}", file=sys.stderr)
        
        return True
        
    except FileNotFoundError:
        print("Error: XeLaTeX not found. Please install XeLaTeX.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error compiling TeX to PDF: {e}", file=sys.stderr)
        return False


def export_to_pdf(input_file, output_pdf):
    """
    Convert JLPTEI XML file to PDF.
    
    Args:
        input_file (Path): Path to the input TEI XML file
        output_pdf (Path): Path to the output PDF file
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate input file exists
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' does not exist", file=sys.stderr)
        return False
    
    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_tex_file = Path(temp_dir) / f"output.tex"
        
        # Step 1: Generate TeX file
        if not generate_tex(input_file, temp_tex_file):
            return False
        
        # Step 2: Compile TeX to PDF
        if not compile_tex_to_pdf(temp_tex_file, output_pdf):
            return False
        
        print(f"Successfully generated PDF: {output_pdf}", file=sys.stderr)
        return True


def main():
    """Main function to handle command line arguments and run the PDF generation."""
    parser = argparse.ArgumentParser(
        description="Convert JLPTEI XML files to PDF format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml output.pdf
        """
    )
    
    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to the input TEI XML file'
    )
    
    parser.add_argument(
        'output_pdf',
        type=Path,
        help='Path to the output PDF file'
    )
    

    args = parser.parse_args()
    
    # Run the PDF generation
    success = export_to_pdf(args.input_file, args.output_pdf)
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()

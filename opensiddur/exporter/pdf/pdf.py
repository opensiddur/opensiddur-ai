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


def compile_tex_to_pdf(tex_file, output_pdf, max_runs=7):
    """
    Compile TeX file to PDF using XeLaTeX with bibliography support.
    Runs xelatex -> bibtex -> xelatex until no more reruns are needed.
    
    Args:
        tex_file (Path): Path to the TeX file
        output_pdf (Path): Path to the output PDF file
        max_runs (int): Maximum number of xelatex runs to prevent infinite loops
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Compiling {tex_file} to PDF...", file=sys.stderr)
        
        # Change to the directory containing the TeX file
        tex_dir = tex_file.parent
        tex_name = tex_file.stem
        def run_xelatex(temp_dir):
            """Run XeLaTeX and return (success, output, needs_rerun)"""
            cmd = [
                'xelatex',
                '-interaction=nonstopmode',
                '-output-directory', str(temp_dir),
                str(tex_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=tex_dir)
            
            if result.returncode != 0:
                return False, result.stdout + result.stderr, False
            
            # Check if we need to rerun
            output = result.stdout + result.stderr
            # Look for common LaTeX rerun indicators
            # Avoid false positives from biblatex's "Please rerun LaTeX" which appears even on final run
            needs_rerun = any(pattern in output for pattern in [
                'Rerun to get cross-references right',
                'Rerun to get outlines right',
                'There were undefined references',
                'Label(s) may have changed',
                'Rerun to get citations correct'
            ])
            
            return True, output, needs_rerun
        
        def run_bibtex():
            """Run BibTeX and return success status"""
            cmd = ['bibtex', str(tex_name)]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=tex_dir)
            
            # BibTeX may return non-zero even on success with warnings
            # Check for actual errors in output
            if 'error message' in result.stdout.lower():
                print(f"BibTeX errors: {result.stdout}", file=sys.stderr)
                return False
            
            return True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # First XeLaTeX run
            print("Running XeLaTeX (pass 1)...", file=sys.stderr)
            success, output, needs_rerun = run_xelatex(temp_dir)
            
            if not success:
                print(f"XeLaTeX compilation failed:", file=sys.stderr)
                print(output, file=sys.stderr)
                return False
            
            # Check if bibliography exists and run BibTeX
            aux_file = Path(temp_dir) / f"{tex_name}.aux"
            if aux_file.exists():
                aux_content = aux_file.read_text()
                if '\\bibdata' in aux_content or '\\citation' in aux_content:
                    print("Running BibTeX...", file=sys.stderr)
                    if not run_bibtex():
                        print("Warning: BibTeX encountered errors", file=sys.stderr)
                    # After BibTeX, we definitely need to rerun XeLaTeX
                    needs_rerun = True
            
            # Continue running XeLaTeX until no more reruns are needed
            run_count = 1
            while needs_rerun and run_count < max_runs:
                run_count += 1
                print(f"Running XeLaTeX (pass {run_count})...", file=sys.stderr)
                success, output, needs_rerun = run_xelatex(temp_dir)
                
                if not success:
                    print(f"XeLaTeX compilation failed:", file=sys.stderr)
                    print(output, file=sys.stderr)
                    return False
            
            if run_count >= max_runs:
                print(f"Warning: Reached maximum number of runs ({max_runs})", file=sys.stderr)
            
            # The PDF should be in the same directory as the TeX file
            generated_pdf = Path(temp_dir) / f"{tex_name}.pdf"
            
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
        
        print(f"Compilation completed in {run_count} XeLaTeX pass(es)", file=sys.stderr)
        return True
        
    except FileNotFoundError as e:
        if 'xelatex' in str(e):
            print("Error: XeLaTeX not found. Please install XeLaTeX.", file=sys.stderr)
        elif 'bibtex' in str(e):
            print("Error: BibTeX not found. Please install BibTeX.", file=sys.stderr)
        else:
            print(f"Error: Command not found: {e}", file=sys.stderr)
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

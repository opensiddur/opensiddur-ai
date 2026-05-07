#!/usr/bin/env python3
"""
JLPTEI to PDF Exporter (LuaLaTeX + reledmac/reledpar pipeline).

Compilation strategy
====================
The reledmac/reledpar packages produce auxiliary files (``.<n>.aux`` files,
``.lineenum``, etc.) that need multiple LaTeX passes to converge. ``latexmk``
already understands these patterns and is the canonical tool for getting the
right number of passes in the right order, so we use it whenever it's
available::

    latexmk -lualatex -interaction=nonstopmode <file>.tex

When ``latexmk`` is not installed we fall back to a manual loop that runs
``lualatex`` up to ``max_runs`` times, invoking ``bibtex`` once between passes
when the ``.aux`` indicates a bibliography is needed.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from opensiddur.exporter.tex.latex import transform_xml_to_tex  # noqa: E402


def generate_tex(
    input_file: Path,
    temp_tex_file: Path,
    settings_file: Optional[Path] = None,
) -> bool:
    """Generate a LuaLaTeX file from compiled JLPTEI XML.

    Args:
        input_file: Path to the compiled JLPTEI XML file.
        temp_tex_file: Path to the temporary .tex file to create.
        settings_file: Optional settings.yaml whose ``typography`` section
            drives the LuaLaTeX preamble.

    Returns:
        True on success, False otherwise.
    """
    try:
        print(f"Generating LuaLaTeX from {input_file}...", file=sys.stderr)
        transform_xml_to_tex(
            str(input_file),
            output_file=str(temp_tex_file),
            settings_file=settings_file,
        )
        print(f"TeX file generated: {temp_tex_file}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Error generating TeX: {e}", file=sys.stderr)
        return False


def _have_command(name: str) -> bool:
    """Return True iff ``name`` resolves on $PATH."""
    return shutil.which(name) is not None


def _run_latexmk(tex_file: Path, output_dir: Path) -> bool:
    """Drive the LaTeX build with latexmk -lualatex.

    latexmk reruns lualatex/biber as many times as needed for reledmac's
    ``.<n>.aux`` files and the bibliography to converge. We disable
    interaction so a malformed source can't hang the build.
    """
    cmd = [
        "latexmk",
        "-lualatex",
        "-bibtex",
        "-nobiber",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        str(tex_file),
    ]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=tex_file.parent)
    if result.returncode != 0:
        print("latexmk reported errors:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        # Don't bail unconditionally: we still want to keep going if the PDF
        # was produced (over-strict reledpar warnings can mask successful runs).
        return False
    return True


def _run_lualatex(tex_file: Path, output_dir: Path) -> tuple[bool, str, bool]:
    """Run a single ``lualatex`` pass.

    Returns ``(succeeded, output, needs_rerun)``. ``succeeded`` reflects exit
    code; ``needs_rerun`` is True when the log contains rerun indicators
    (which reledmac/reledpar emit on every non-final pass).
    """
    cmd = [
        "lualatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={output_dir}",
        str(tex_file),
    ]
    log_path = output_dir / f"{tex_file.stem}.log"
    print(f"(LuaLaTeX log: {log_path})", file=sys.stderr)

    # Stream output live so long passes are observable. We later parse the .log
    # file for rerun markers (more reliable than stdout).
    result = subprocess.run(cmd, text=True, cwd=tex_file.parent)
    output = ""
    if log_path.exists():
        try:
            output = log_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            output = ""
    needs_rerun = any(
        marker in output
        for marker in (
            "Rerun to get cross-references right",
            "Rerun to get outlines right",
            "There were undefined references",
            "Label(s) may have changed",
            "Rerun to get citations correct",
            # reledmac/reledpar specific
            "Reledmac will work only after",
            "reledpar may not have created",
        )
    )
    return result.returncode == 0, output, needs_rerun


def _run_bibtex(tex_stem: str, output_dir: Path) -> bool:
    """Run bibtex if the .aux indicates a bibliography is needed."""
    aux = output_dir / f"{tex_stem}.aux"
    if not aux.exists():
        return True
    aux_content = aux.read_text(encoding="utf-8", errors="ignore")
    if "\\bibdata" not in aux_content and "\\citation" not in aux_content:
        return True

    cmd = ["bibtex", tex_stem]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
    if "error message" in (result.stdout or "").lower():
        print(f"BibTeX errors: {result.stdout}", file=sys.stderr)
        return False
    return True


def _run_manual_loop(tex_file: Path, output_dir: Path, max_runs: int) -> bool:
    """Fallback build loop when latexmk isn't available.

    Runs lualatex once, then biber if a ``.bcf`` shows up, then keeps running
    lualatex until the rerun markers stop appearing or ``max_runs`` is hit.
    """
    tex_stem = tex_file.stem

    print("Running lualatex (pass 1)...", file=sys.stderr)
    success, output, needs_rerun = _run_lualatex(tex_file, output_dir)
    if not success:
        print("lualatex reported errors (pass 1):", file=sys.stderr)
        print(output, file=sys.stderr)

    # Run bibtex once after the first pass when needed; force a rerun afterwards
    # because bibtex updates the .bbl that lualatex needs to read.
    aux = output_dir / f"{tex_stem}.aux"
    if aux.exists():
        aux_content = aux.read_text(encoding="utf-8", errors="ignore")
        if "\\bibdata" in aux_content or "\\citation" in aux_content:
            print("Running bibtex...", file=sys.stderr)
            _run_bibtex(tex_stem, output_dir)
            needs_rerun = True

    run_count = 1
    while needs_rerun and run_count < max_runs:
        run_count += 1
        print(f"Running lualatex (pass {run_count})...", file=sys.stderr)
        success, output, needs_rerun = _run_lualatex(tex_file, output_dir)
        if not success:
            print(f"lualatex reported errors (pass {run_count}):", file=sys.stderr)
            print(output, file=sys.stderr)
            break

    if run_count >= max_runs:
        print(
            f"Warning: reached max_runs ({max_runs}); reledmac/reledpar may not be settled",
            file=sys.stderr,
        )

    print(f"Manual loop completed in {run_count} lualatex pass(es)", file=sys.stderr)
    return True


def compile_tex_to_pdf(
    tex_file: Path,
    output_pdf: Path,
    max_runs: int = 6,
) -> bool:
    """Compile a LuaLaTeX .tex file to PDF.

    Uses ``latexmk -lualatex`` when available (recommended), otherwise falls
    back to a manual lualatex/biber loop. Either way, the output PDF is
    copied from a temp build directory to ``output_pdf``.

    ``max_runs`` only applies to the manual fallback; latexmk handles its
    own loop.
    """
    try:
        if not _have_command("lualatex"):
            print(
                "Error: lualatex not found. Install texlive-luatex.",
                file=sys.stderr,
            )
            return False

        print(f"Compiling {tex_file} to PDF...", file=sys.stderr)
        tex_stem = tex_file.stem

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            # latexmk can attempt to invoke biber based on .bcf detection even when
            # biblatex is configured for BibTeX. Since biber is frequently broken or
            # unavailable on minimal systems, prefer a deterministic manual loop.
            if not _have_command("bibtex"):
                print(
                    "Error: bibtex not found. Install texlive-bibtex-extra.",
                    file=sys.stderr,
                )
                return False
            _run_manual_loop(tex_file, temp_dir, max_runs)

            generated_pdf = temp_dir / f"{tex_stem}.pdf"
            if not generated_pdf.exists():
                print(f"PDF file not found: {generated_pdf}", file=sys.stderr)
                return False

            if generated_pdf != output_pdf:
                shutil.copy2(generated_pdf, output_pdf)
                print(f"PDF copied to: {output_pdf}", file=sys.stderr)
            else:
                print(f"PDF generated: {output_pdf}", file=sys.stderr)

        return True

    except FileNotFoundError as e:
        # Either lualatex/latexmk/biber went missing mid-build.
        print(f"Error: command not found: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error compiling TeX to PDF: {e}", file=sys.stderr)
        return False


def export_to_pdf(
    input_file: Path,
    output_pdf: Path,
    settings_file: Optional[Path] = None,
    tex_output: Optional[Path] = None,
) -> bool:
    """Convert a compiled JLPTEI XML file to PDF.

    Args:
        input_file: Path to the input compiled JLPTEI XML file.
        output_pdf: Path to the output PDF file.
        settings_file: Optional settings.yaml whose ``typography`` section
            drives the LuaLaTeX preamble.

    Returns:
        True on success, False otherwise.
    """
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' does not exist", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_tex_file = tex_output or (Path(temp_dir) / "output.tex")
        if tex_output is not None:
            tex_output.parent.mkdir(parents=True, exist_ok=True)

        if not generate_tex(input_file, temp_tex_file, settings_file=settings_file):
            return False

        if not compile_tex_to_pdf(temp_tex_file, output_pdf):
            return False

        print(f"Successfully generated PDF: {output_pdf}", file=sys.stderr)
        if tex_output is not None:
            print(f"Intermediate TeX saved to: {tex_output}", file=sys.stderr)
        return True


def main():  # pragma: no cover
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Convert compiled JLPTEI XML files to PDF (LuaLaTeX + reledmac)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.xml output.pdf
  %(prog)s -s settings.yaml input.xml output.pdf
        """,
    )

    parser.add_argument("input_file", type=Path, help="Path to the input compiled JLPTEI XML file")
    parser.add_argument("output_pdf", type=Path, help="Path to the output PDF file")
    parser.add_argument(
        "-s",
        "--settings",
        dest="settings_file",
        type=Path,
        default=None,
        help=(
            "Path to a settings.yaml whose `typography` section drives "
            "fonts, layout, paper, and font size. Defaults are used when omitted."
        ),
    )
    parser.add_argument(
        "--keep-tex",
        action="store_true",
        help=(
            "Save the intermediate TeX file next to the output PDF "
            "as <output>.tex."
        ),
    )
    parser.add_argument(
        "--tex-output",
        type=Path,
        default=None,
        help="Path to write the intermediate TeX file (implies --keep-tex).",
    )

    args = parser.parse_args()

    if args.keep_tex and args.tex_output is not None:
        print("Error: --keep-tex and --tex-output are mutually exclusive.", file=sys.stderr)
        sys.exit(2)

    tex_output: Optional[Path] = None
    if args.tex_output is not None:
        tex_output = args.tex_output
    elif args.keep_tex:
        tex_output = args.output_pdf.with_suffix(".tex")

    if not export_to_pdf(
        args.input_file,
        args.output_pdf,
        settings_file=args.settings_file,
        tex_output=tex_output,
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Tests for the PDF exporter module (LuaLaTeX + reledmac/reledpar pipeline)."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from opensiddur.exporter.pdf.pdf import (
    compile_tex_to_pdf,
    export_to_pdf,
    generate_tex,
)


class TestGenerateTex(unittest.TestCase):
    """Test the generate_tex function."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def test_generate_tex_success(self):
        """generate_tex calls transform_xml_to_tex and propagates success."""
        input_file = self.test_dir / "input.xml"
        output_file = self.test_dir / "output.tex"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        def write_tex(path, output_file=None, **kwargs):
            if output_file:
                Path(output_file).write_text(r"\documentclass{book}")
            return r"\documentclass{book}"

        with patch(
            "opensiddur.exporter.pdf.pdf.transform_xml_to_tex",
            side_effect=write_tex,
        ) as mock_transform:
            result = generate_tex(input_file, output_file)

        self.assertTrue(result)
        self.assertTrue(output_file.exists())
        mock_transform.assert_called_once_with(
            str(input_file),
            output_file=str(output_file),
            settings_file=None,
        )

    def test_generate_tex_forwards_settings_file(self):
        """A settings_file argument is forwarded to transform_xml_to_tex unchanged."""
        input_file = self.test_dir / "input.xml"
        output_file = self.test_dir / "output.tex"
        settings_file = self.test_dir / "settings.yaml"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch("opensiddur.exporter.pdf.pdf.transform_xml_to_tex") as mock_transform:
            generate_tex(input_file, output_file, settings_file=settings_file)

        mock_transform.assert_called_once_with(
            str(input_file),
            output_file=str(output_file),
            settings_file=settings_file,
        )

    def test_generate_tex_handles_exception(self):
        """generate_tex returns False when transform_xml_to_tex raises."""
        input_file = self.test_dir / "input.xml"
        output_file = self.test_dir / "output.tex"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch(
            "opensiddur.exporter.pdf.pdf.transform_xml_to_tex",
            side_effect=RuntimeError("boom"),
        ):
            result = generate_tex(input_file, output_file)

        self.assertFalse(result)
        self.assertFalse(output_file.exists())


class TestCompileTexToPdfLatexmk(unittest.TestCase):
    """Tests for the latexmk-driven path of compile_tex_to_pdf.

    When ``latexmk`` is present on $PATH, compile_tex_to_pdf shells out once
    to ``latexmk -lualatex`` and copies the resulting PDF out of the temp
    build directory.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)
        self.tex_file = self.test_dir / "test.tex"
        self.tex_file.write_text(r"\documentclass{book}\begin{document}Test\end{document}")
        self.output_pdf = self.test_dir / "out.pdf"

    def _have_command(self, name):
        return name in {"lualatex", "latexmk", "bibtex"}

    def _latexmk_run(self, cmd, **kwargs):
        """Simulate latexmk producing a PDF in -output-directory."""
        out_dir = next(
            Path(arg.split("=", 1)[1])
            for arg in cmd
            if arg.startswith("-output-directory=")
        )
        (out_dir / f"{self.tex_file.stem}.pdf").write_bytes(b"%PDF-1.4 fake")
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    def test_uses_latexmk_when_available(self):
        """When tools resolve on $PATH, we still produce a PDF successfully."""
        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            side_effect=self._have_command,
        ):
            with patch(
                "subprocess.run", side_effect=self._latexmk_run
            ) as mock_run:
                result = compile_tex_to_pdf(self.tex_file, self.output_pdf)

        self.assertTrue(result)
        self.assertTrue(self.output_pdf.exists())
        cmds = [c.args[0][0] for c in mock_run.call_args_list]
        self.assertIn("lualatex", cmds)

    def test_fails_when_lualatex_missing(self):
        """Without lualatex on $PATH, compile_tex_to_pdf returns False up-front."""
        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            return_value=False,
        ):
            with patch("subprocess.run") as mock_run:
                result = compile_tex_to_pdf(self.tex_file, self.output_pdf)

        self.assertFalse(result)
        mock_run.assert_not_called()

    def test_returns_false_when_pdf_not_produced(self):
        """A run that doesn't write a PDF is treated as a failed build."""
        def latexmk_no_pdf(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            side_effect=self._have_command,
        ):
            with patch("subprocess.run", side_effect=latexmk_no_pdf):
                result = compile_tex_to_pdf(self.tex_file, self.output_pdf)

        self.assertFalse(result)


class TestCompileTexToPdfManualLoop(unittest.TestCase):
    """Tests for the manual fallback path (no latexmk on the system)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)
        self.tex_file = self.test_dir / "test.tex"
        self.tex_file.write_text(r"\documentclass{book}\begin{document}Test\end{document}")
        self.output_pdf = self.test_dir / "out.pdf"

    def _only_lualatex(self, name):
        # Pretend lualatex is installed but latexmk is not.
        return name in {"lualatex", "bibtex"}

    def _make_lualatex_run(self, aux_bib=False, rerun_passes=0):
        """Return a subprocess.run side_effect that simulates lualatex (and bibtex)."""
        call_count = [0]

        def side_effect(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            if cmd[0] == "lualatex":
                call_count[0] += 1
                out_dir = next(
                    Path(arg.split("=", 1)[1])
                    for arg in cmd
                    if arg.startswith("-output-directory=")
                )
                if call_count[0] == 1 and aux_bib:
                    (out_dir / f"{self.tex_file.stem}.aux").write_text("\\bibdata{job}\\n")
                if call_count[0] <= rerun_passes:
                    r.stdout = "Rerun to get cross-references right"
                (out_dir / f"{self.tex_file.stem}.pdf").write_bytes(b"%PDF fake")
            elif cmd[0] == "bibtex":
                r.stdout = ""
            return r

        return side_effect, call_count

    def test_manual_loop_runs_lualatex(self):
        side_effect, call_count = self._make_lualatex_run()
        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            side_effect=self._only_lualatex,
        ):
            with patch("subprocess.run", side_effect=side_effect):
                result = compile_tex_to_pdf(self.tex_file, self.output_pdf)

        self.assertTrue(result)
        self.assertGreaterEqual(call_count[0], 1)

    def test_manual_loop_invokes_bibtex_when_aux_indicates_bibliography(self):
        """A first-pass .aux with \\bibdata triggers bibtex + at least one extra lualatex pass."""
        side_effect, _ = self._make_lualatex_run(aux_bib=True)
        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            side_effect=self._only_lualatex,
        ):
            with patch("subprocess.run", side_effect=side_effect) as mock_run:
                compile_tex_to_pdf(self.tex_file, self.output_pdf)

        bibtex_calls = [c for c in mock_run.call_args_list if c.args[0][0] == "bibtex"]
        lualatex_calls = [
            c for c in mock_run.call_args_list if c.args[0][0] == "lualatex"
        ]
        self.assertEqual(len(bibtex_calls), 1)
        # At least 2 lualatex passes: the initial one plus the post-bibtex rerun.
        self.assertGreaterEqual(len(lualatex_calls), 2)

    def test_manual_loop_caps_at_max_runs(self):
        """The loop must not run lualatex more than max_runs times."""
        side_effect, call_count = self._make_lualatex_run(rerun_passes=99)
        with patch(
            "opensiddur.exporter.pdf.pdf._have_command",
            side_effect=self._only_lualatex,
        ):
            with patch("subprocess.run", side_effect=side_effect):
                compile_tex_to_pdf(self.tex_file, self.output_pdf, max_runs=3)

        self.assertLessEqual(call_count[0], 3)


class TestExportToPdf(unittest.TestCase):
    """Test the export_to_pdf function."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.test_dir = Path(self.temp_dir.name)

    def test_export_to_pdf_success(self):
        input_file = self.test_dir / "input.xml"
        output_pdf = self.test_dir / "out.pdf"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch(
            "opensiddur.exporter.pdf.pdf.generate_tex", return_value=True
        ) as mock_gen:
            with patch(
                "opensiddur.exporter.pdf.pdf.compile_tex_to_pdf", return_value=True
            ) as mock_compile:
                result = export_to_pdf(input_file, output_pdf)

        self.assertTrue(result)
        mock_gen.assert_called_once()
        mock_compile.assert_called_once()

    def test_export_to_pdf_forwards_settings_file_to_generate(self):
        """settings_file is forwarded to generate_tex (the consumer of typography)."""
        input_file = self.test_dir / "input.xml"
        output_pdf = self.test_dir / "out.pdf"
        settings_file = self.test_dir / "settings.yaml"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch(
            "opensiddur.exporter.pdf.pdf.generate_tex", return_value=True
        ) as mock_gen:
            with patch(
                "opensiddur.exporter.pdf.pdf.compile_tex_to_pdf", return_value=True
            ):
                export_to_pdf(input_file, output_pdf, settings_file=settings_file)

        kwargs = mock_gen.call_args.kwargs
        self.assertEqual(kwargs.get("settings_file"), settings_file)

    def test_export_to_pdf_writes_intermediate_tex_when_requested(self):
        """When tex_output is provided, generate_tex writes to that path and it is kept."""
        input_file = self.test_dir / "input.xml"
        output_pdf = self.test_dir / "out.pdf"
        tex_output = self.test_dir / "intermediate.tex"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch("opensiddur.exporter.pdf.pdf.generate_tex", return_value=True) as mock_gen:
            with patch("opensiddur.exporter.pdf.pdf.compile_tex_to_pdf", return_value=True):
                result = export_to_pdf(input_file, output_pdf, tex_output=tex_output)

        self.assertTrue(result)
        self.assertEqual(mock_gen.call_args.args[1], tex_output)

    def test_export_to_pdf_input_file_not_found(self):
        input_file = self.test_dir / "nope.xml"
        output_pdf = self.test_dir / "out.pdf"

        result = export_to_pdf(input_file, output_pdf)

        self.assertFalse(result)

    def test_export_to_pdf_generate_tex_failure(self):
        input_file = self.test_dir / "input.xml"
        output_pdf = self.test_dir / "out.pdf"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch(
            "opensiddur.exporter.pdf.pdf.generate_tex", return_value=False
        ):
            result = export_to_pdf(input_file, output_pdf)

        self.assertFalse(result)

    def test_export_to_pdf_compile_failure(self):
        input_file = self.test_dir / "input.xml"
        output_pdf = self.test_dir / "out.pdf"
        input_file.write_text("<tei:TEI xmlns:tei='http://www.tei-c.org/ns/1.0'/>")

        with patch(
            "opensiddur.exporter.pdf.pdf.generate_tex", return_value=True
        ):
            with patch(
                "opensiddur.exporter.pdf.pdf.compile_tex_to_pdf", return_value=False
            ):
                result = export_to_pdf(input_file, output_pdf)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

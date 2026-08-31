import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.generate_summer_course_markdown import (
    compress_pdf,
    inferred_day,
    main,
    pdf_filename,
    plan_pdf_move,
    prompt_positive_integer,
    render_course,
    write_course,
)


VALUES = {
    "title": "A New Lecture",
    "slug": "2027-01-jane-doe",
    "year": "2027",
    "number": "1",
    "day": "Thursday",
    "date": "July 1",
    "course_date": "July 1",
    "time": "1:00 to 2:00 PM",
    "location": "FAES Room 4",
    "topic": "A New Lecture",
    "video_link": "",
    "pdf_link": "",
    "speaker": "Jane Doe",
    "body": "A New Lecture",
}


def complete_course_args(content_dir, source_pdf):
    return [
        "--content-dir",
        str(content_dir),
        "--year",
        "2027",
        "--number",
        "1",
        "--title",
        "A New Lecture",
        "--slug",
        "2027-01-jane-doe",
        "--day",
        "Thursday",
        "--date",
        "July 1",
        "--course-date",
        "July 1",
        "--time",
        "1:00 to 2:00 PM",
        "--location",
        "FAES Room 4",
        "--topic",
        "A New Lecture",
        "--video-link",
        "",
        "--pdf-file",
        str(source_pdf),
        "--speaker",
        "Jane Doe",
        "--body",
        "A New Lecture",
    ]


class WriteCourseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "2027" / "2027_01_jane-doe.md"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_missing_year_directory_and_file(self):
        content = render_course(VALUES)

        self.assertTrue(write_course(self.path, content))

        self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_existing_file_is_only_changed_after_approval(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("old\n", encoding="utf-8")
        output = io.StringIO()

        with redirect_stdout(output):
            changed = write_course(self.path, render_course(VALUES), input_fn=lambda _: "yes")

        self.assertTrue(changed)
        self.assertIn("-old", output.getvalue())
        self.assertIn("+Title: A New Lecture", output.getvalue())

    def test_rejection_preserves_existing_file(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("old\n", encoding="utf-8")

        changed = write_course(self.path, render_course(VALUES), input_fn=lambda _: "no")

        self.assertFalse(changed)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "old\n")


class DefaultTests(unittest.TestCase):
    def test_infers_weekday_from_catalogue_date(self):
        self.assertEqual(inferred_day("August 20", 2026), "Thursday")

    def test_invalid_interactive_number_is_requested_again(self):
        answers = iter(["zero", "0", "20"])

        number = prompt_positive_integer("Number", None, 1, input_fn=lambda _: next(answers))

        self.assertEqual(number, 20)

    def test_pdf_filename_uses_existing_asset_convention(self):
        self.assertEqual(pdf_filename(VALUES), "2027_1_jane_doe.pdf")


class PdfInputTests(unittest.TestCase):
    def test_generator_renames_pdf_and_sets_link(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content" / "summer-course"
            source_pdf = root / "Lecture Final Version.pdf"
            source_pdf.write_bytes(b"%PDF-1.7\nexample")

            main(complete_course_args(content_dir, source_pdf))

            renamed_pdf = root / "content" / "pdf" / "2027" / "2027_1_jane_doe.pdf"
            markdown = content_dir / "2027" / "2027_01_jane-doe.md"
            self.assertFalse(source_pdf.exists())
            self.assertEqual(renamed_pdf.read_bytes(), b"%PDF-1.7\nexample")
            self.assertIn(
                "PDF_link: /pdf/2027/2027_1_jane_doe.pdf",
                markdown.read_text(encoding="utf-8"),
            )

    def test_existing_pdf_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_pdf = root / "incoming.pdf"
            target_pdf = root / "pdf" / "2027" / "2027_1_jane_doe.pdf"
            source_pdf.write_bytes(b"%PDF-1.7\nsource")
            target_pdf.parent.mkdir(parents=True)
            target_pdf.write_bytes(b"%PDF-1.7\ntarget")

            with self.assertRaises(SystemExit):
                plan_pdf_move(str(source_pdf), root / "pdf", VALUES)

            self.assertEqual(source_pdf.read_bytes(), b"%PDF-1.7\nsource")
            self.assertEqual(target_pdf.read_bytes(), b"%PDF-1.7\ntarget")

    def test_rejected_markdown_change_does_not_move_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content_dir = root / "content" / "summer-course"
            markdown = content_dir / "2027" / "2027_01_jane-doe.md"
            source_pdf = root / "incoming.pdf"
            markdown.parent.mkdir(parents=True)
            markdown.write_text("old\n", encoding="utf-8")
            source_pdf.write_bytes(b"%PDF-1.7\nsource")

            main(
                complete_course_args(content_dir, source_pdf),
                input_fn=lambda _: "no",
            )

            target_pdf = root / "content" / "pdf" / "2027" / "2027_1_jane_doe.pdf"
            self.assertTrue(source_pdf.exists())
            self.assertFalse(target_pdf.exists())
            self.assertEqual(markdown.read_text(encoding="utf-8"), "old\n")


class PdfCompressionTests(unittest.TestCase):
    def test_compression_keeps_smaller_output_and_removes_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "incoming.pdf"
            target = root / "pdf" / "2027_1_jane_doe.pdf"
            source.write_bytes(b"%PDF-1.7\n" + b"x" * 1000)

            def fake_run(command, **_kwargs):
                output_arg = next(arg for arg in command if arg.startswith("-sOutputFile="))
                Path(output_arg.split("=", 1)[1]).write_bytes(b"%PDF-1.7\nsmall")
                return subprocess.CompletedProcess(command, 0, "", "")

            with (
                patch(
                    "tools.generate_summer_course_markdown.shutil.which",
                    side_effect=lambda name: "/mock/gs" if name == "gs" else None,
                ),
                patch(
                    "tools.generate_summer_course_markdown.subprocess.run",
                    side_effect=fake_run,
                ),
            ):
                changed = compress_pdf(source, target, 160)

            self.assertTrue(changed)
            self.assertFalse(source.exists())
            self.assertEqual(target.read_bytes(), b"%PDF-1.7\nsmall")

    def test_missing_ghostscript_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "incoming.pdf"
            target = Path(temp_dir) / "output.pdf"
            source.write_bytes(b"%PDF-1.7\nsource")

            with patch(
                "tools.generate_summer_course_markdown.shutil.which",
                return_value=None,
            ):
                with self.assertRaises(SystemExit):
                    compress_pdf(source, target, 160)

            self.assertTrue(source.exists())
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

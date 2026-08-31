#!/usr/bin/env python3
"""Interactively create or update an FMRIF summer-course Markdown file."""

import argparse
import difflib
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path


DEFAULT_CONTENT_DIR = Path(__file__).resolve().parents[1] / "content" / "summer-course"
DEFAULT_TIME = "1:00 to 2:00 PM"
DEFAULT_LOCATION = "FAES Room 4"
METADATA_ORDER = (
    ("title", "Title"),
    ("slug", "Slug"),
    ("year", "Year"),
    ("number", "Number"),
    ("day", "Day"),
    ("date", "Date"),
    ("course_date", "Course_date"),
    ("time", "Time"),
    ("location", "Location"),
    ("topic", "Topic"),
    ("video_link", "Video_link"),
    ("pdf_link", "PDF_link"),
    ("speaker", "Speaker"),
)


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-")


def positive_integer(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def read_course(path):
    metadata = {}
    body_lines = []
    in_body = False

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if in_body:
                body_lines.append(line)
                continue
            if not line.strip():
                in_body = True
                continue
            key, separator, value = line.rstrip("\n").partition(":")
            if separator:
                metadata[key.strip().lower()] = value.strip()

    return metadata, "".join(body_lines).strip()


def existing_course_path(content_dir, year, number):
    matches = sorted((content_dir / str(year)).glob(f"{year}_{number:02d}_*.md"))
    if len(matches) > 1:
        paths = "\n".join(f"  {path}" for path in matches)
        raise SystemExit(
            f"More than one file exists for lecture {year}-{number:02d}:\n{paths}"
        )
    return matches[0] if matches else None


def next_course_number(content_dir, year):
    numbers = []
    for path in (content_dir / str(year)).glob(f"{year}_*_*.md"):
        match = re.match(rf"^{re.escape(str(year))}_(\d+)_", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def inferred_day(date_value, year):
    candidates = (
        (f"{date_value} {year}", "%B %d %Y"),
        (f"{date_value} {year}", "%b %d %Y"),
        (f"{date_value}/{year}", "%m/%d/%Y"),
        (date_value, "%Y-%m-%d"),
        (date_value, "%m/%d/%Y"),
    )
    for candidate, date_format in candidates:
        try:
            return datetime.strptime(candidate, date_format).strftime("%A")
        except ValueError:
            continue
    return ""


def prompt_value(label, supplied, default="", required=False, input_fn=input):
    if supplied is not None:
        value = str(supplied).strip()
        if required and not value:
            raise SystemExit(f"{label} cannot be blank.")
        return value

    while True:
        prompt = f"{label} [{default}]: " if default else f"{label}: "
        try:
            entered = input_fn(prompt).strip()
        except EOFError as error:
            raise SystemExit(f"No value supplied for {label}.") from error
        value = entered or str(default).strip()
        if value or not required:
            return value
        print(f"{label} cannot be blank.")


def prompt_positive_integer(label, supplied, default, input_fn=input):
    if supplied is not None:
        return supplied

    while True:
        value = prompt_value(label, None, default, required=True, input_fn=input_fn)
        try:
            return positive_integer(value)
        except (TypeError, ValueError, argparse.ArgumentTypeError):
            print(f"{label} must be a positive integer.")


def render_course(values):
    lines = [f"{label}: {values[key]}" for key, label in METADATA_ORDER]
    return "\n".join(lines) + f"\n\n{values['body']}\n"


def proposed_path(content_dir, values, existing_path=None):
    if existing_path is not None:
        return existing_path
    speaker_slug = slugify(values["speaker"])
    return (
        content_dir
        / str(values["year"])
        / f"{values['year']}_{int(values['number']):02d}_{speaker_slug}.md"
    )


def pdf_filename(values):
    speaker_name = slugify(values["speaker"]).replace("-", "_")
    return f"{values['year']}_{int(values['number'])}_{speaker_name}.pdf"


def local_pdf_from_link(content_dir, pdf_link):
    if not pdf_link.startswith("/pdf/"):
        return None
    path = content_dir.parent / pdf_link.lstrip("/")
    return path if path.is_file() else None


def plan_pdf_move(source_value, pdf_dir, values):
    if not source_value:
        return None

    source = Path(source_value).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Input PDF does not exist or is not a file: {source}")
    with source.open("rb") as handle:
        signature = handle.read(5)
    if source.suffix.lower() != ".pdf" or signature != b"%PDF-":
        raise SystemExit(f"Input file is not a PDF: {source}")

    target = (pdf_dir / str(values["year"]) / pdf_filename(values)).resolve()
    if source != target and target.exists():
        raise SystemExit(
            f"Refusing to overwrite existing PDF: {target}\n"
            "Move or remove it explicitly, then run the generator again."
        )
    return source, target


def pdf_page_count(path):
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        return None
    result = subprocess.run(
        [pdfinfo, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        return None
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    return int(match.group(1)) if match else None


def compress_pdf(source, target, dpi):
    ghostscript = shutil.which("gs")
    if not ghostscript:
        raise SystemExit(
            "PDF compression requires Ghostscript. Install it with "
            "'brew install ghostscript'."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    source_size = source.stat().st_size
    source_pages = pdf_page_count(source)

    with tempfile.TemporaryDirectory(prefix=".pdf-compress-", dir=target.parent) as temp_dir:
        compressed = Path(temp_dir) / target.name
        command = [
            ghostscript,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-dQUIET",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.6",
            "-dAutoRotatePages=/None",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            "-dDownsampleColorImages=true",
            "-dColorImageDownsampleType=/Bicubic",
            f"-dColorImageResolution={dpi}",
            "-dDownsampleGrayImages=true",
            "-dGrayImageDownsampleType=/Bicubic",
            f"-dGrayImageResolution={dpi}",
            "-dDownsampleMonoImages=true",
            "-dMonoImageResolution=300",
            f"-sOutputFile={compressed}",
            str(source),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            message = "Ghostscript could not compress the PDF."
            if detail:
                message += f"\n{detail}"
            raise SystemExit(message)

        if not compressed.is_file():
            raise SystemExit("Ghostscript did not create a compressed PDF.")
        with compressed.open("rb") as handle:
            signature = handle.read(5)
        if signature != b"%PDF-":
            raise SystemExit("Ghostscript output is not a valid PDF.")

        compressed_pages = pdf_page_count(compressed)
        if (
            source_pages is not None
            and compressed_pages is not None
            and source_pages != compressed_pages
        ):
            raise SystemExit(
                "Compressed PDF page count changed "
                f"from {source_pages} to {compressed_pages}; original preserved."
            )

        compressed_size = compressed.stat().st_size
        if compressed_size >= source_size:
            if source != target:
                shutil.move(str(source), str(target))
            print(
                "Compression produced no savings; kept the original PDF "
                f"({source_size:,} bytes)."
            )
            return False

        compressed.replace(target)

    if source != target:
        source.unlink()
    savings = 100 * (source_size - compressed_size) / source_size
    print(
        f"Compressed PDF: {source_size:,} -> {compressed_size:,} bytes "
        f"({savings:.1f}% smaller)"
    )
    return True


def move_pdf(move_plan, compress=False, dpi=160):
    if move_plan is None:
        return False

    source, target = move_plan
    if compress:
        return compress_pdf(source, target, dpi)
    if source == target:
        print(f"PDF already named correctly: {target}")
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    print(f"Renamed PDF: {source} -> {target}")
    return True


def write_course(path, content, input_fn=input, before_write=None):
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            if before_write:
                before_write()
            print(f"No changes: {path}")
            return False

        diff = difflib.unified_diff(
            current.splitlines(),
            content.splitlines(),
            fromfile=str(path),
            tofile=f"{path} (proposed)",
            lineterm="",
        )
        print("\n".join(diff))
        try:
            approved = input_fn("Apply these changes? [y/N]: ").strip().lower()
        except EOFError:
            approved = ""
        if approved not in {"y", "yes"}:
            print("No changes written.")
            return False

    if before_write:
        before_write()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
    return True


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create or update a summer-course Markdown file. Missing options are "
            "requested interactively with sensible defaults."
        )
    )
    parser.add_argument("--content-dir", type=Path, default=DEFAULT_CONTENT_DIR)
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        help="PDF asset root (default: the content/pdf directory next to summer-course)",
    )
    parser.add_argument("--year", type=positive_integer)
    parser.add_argument("--number", type=positive_integer)
    parser.add_argument("--title")
    parser.add_argument("--slug")
    parser.add_argument("--day")
    parser.add_argument("--date")
    parser.add_argument("--course-date")
    parser.add_argument("--time")
    parser.add_argument("--location")
    parser.add_argument("--topic")
    parser.add_argument("--video-link")
    parser.add_argument("--pdf-link")
    pdf_file_group = parser.add_mutually_exclusive_group()
    pdf_file_group.add_argument(
        "--pdf-file",
        help="PDF to move into the site and rename using the course convention",
    )
    pdf_file_group.add_argument(
        "--no-pdf-file",
        action="store_true",
        help="Do not prompt for a local PDF file",
    )
    parser.add_argument(
        "--compress-pdf",
        action="store_true",
        help="Lossily compress the input PDF with Ghostscript before storing it",
    )
    parser.add_argument(
        "--pdf-dpi",
        type=positive_integer,
        default=160,
        help="Color and grayscale image resolution for --compress-pdf (default: 160)",
    )
    parser.add_argument("--speaker")
    parser.add_argument("--body")
    return parser


def collect_values(args, input_fn=input):
    content_dir = args.content_dir
    pdf_dir = args.pdf_dir or content_dir.parent / "pdf"
    year = prompt_positive_integer(
        "Year", args.year, date.today().year, input_fn=input_fn
    )
    number = prompt_positive_integer(
        "Number",
        args.number,
        next_course_number(content_dir, year),
        input_fn=input_fn,
    )

    existing_path = existing_course_path(content_dir, year, number)
    existing, existing_body = read_course(existing_path) if existing_path else ({}, "")

    speaker = prompt_value(
        "Speaker", args.speaker, existing.get("speaker", ""), required=True, input_fn=input_fn
    )
    title = prompt_value(
        "Title", args.title, existing.get("title", ""), required=True, input_fn=input_fn
    )
    date_value = prompt_value(
        "Date", args.date, existing.get("date", ""), required=True, input_fn=input_fn
    )
    slug = prompt_value(
        "Slug",
        args.slug,
        existing.get("slug", f"{year}-{number:02d}-{slugify(speaker)}"),
        required=True,
        input_fn=input_fn,
    )
    day = prompt_value(
        "Day",
        args.day,
        existing.get("day", inferred_day(date_value, year)),
        required=True,
        input_fn=input_fn,
    )

    existing_pdf = local_pdf_from_link(content_dir, existing.get("pdf_link", ""))
    supplied_pdf = "" if args.no_pdf_file else args.pdf_file
    pdf_source = prompt_value(
        "Input PDF",
        supplied_pdf,
        str(existing_pdf) if existing_pdf else "",
        input_fn=input_fn,
    )
    if pdf_source and args.pdf_link is not None:
        raise SystemExit("--pdf-link cannot be combined with --pdf-file.")

    values = {
        "title": title,
        "slug": slug,
        "year": str(year),
        "number": str(number),
        "day": day,
        "date": date_value,
        "course_date": prompt_value(
            "Course date",
            args.course_date,
            existing.get("course_date", date_value),
            required=True,
            input_fn=input_fn,
        ),
        "time": prompt_value(
            "Time", args.time, existing.get("time", DEFAULT_TIME), required=True, input_fn=input_fn
        ),
        "location": prompt_value(
            "Location",
            args.location,
            existing.get("location", DEFAULT_LOCATION),
            required=True,
            input_fn=input_fn,
        ),
        "topic": prompt_value(
            "Topic", args.topic, existing.get("topic", title), required=True, input_fn=input_fn
        ),
        "video_link": prompt_value(
            "Video link", args.video_link, existing.get("video_link", ""), input_fn=input_fn
        ),
        "speaker": speaker,
        "body": prompt_value(
            "Body", args.body, existing_body or title, required=True, input_fn=input_fn
        ),
    }
    move_plan = plan_pdf_move(pdf_source, pdf_dir, values)
    if move_plan:
        values["pdf_link"] = f"/pdf/{year}/{pdf_filename(values)}"
    else:
        values["pdf_link"] = prompt_value(
            "PDF link", args.pdf_link, existing.get("pdf_link", ""), input_fn=input_fn
        )
    return values, existing_path, move_plan


def main(argv=None, input_fn=input):
    args = build_parser().parse_args(argv)
    values, existing_path, move_plan = collect_values(args, input_fn=input_fn)
    path = proposed_path(args.content_dir, values, existing_path)
    content = render_course(values)
    if args.compress_pdf and move_plan is None:
        raise SystemExit("--compress-pdf requires an input PDF file.")
    write_course(
        path,
        content,
        input_fn=input_fn,
        before_write=lambda: move_pdf(
            move_plan,
            compress=args.compress_pdf,
            dpi=args.pdf_dpi,
        ),
    )


if __name__ == "__main__":
    main()

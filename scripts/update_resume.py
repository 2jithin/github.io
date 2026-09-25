#!/usr/bin/env python3
"""Refresh resume.html from the newest resume and cover-letter DOCX files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from pathlib import Path
import re
import sys
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
HEADINGS = {"SUMMARY", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "SKILLS"}
DATE_RANGE = re.compile(r"(?<!\d)(?:19|20)\d{2}\s*[-–]\s*(?:Present|(?:19|20)\d{2})", re.I)
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE = re.compile(r"^\+?[\d ()-]{10,}$")


@dataclass(frozen=True)
class Paragraph:
    chunks: tuple[str, ...]
    style: str

    @property
    def text(self) -> str:
        return " ".join(self.chunks).strip()


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid .env line: {line}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def choose_file(directory: Path, setting: str, cover_letter: bool) -> Path:
    if setting.lower() != "auto":
        candidate = Path(setting)
        if not candidate.is_absolute():
            candidate = directory / candidate.name
        if candidate.resolve().parent != directory.resolve():
            raise ValueError(f"Document must be inside {directory}: {setting}")
        if not candidate.is_file() or candidate.suffix.lower() != ".docx":
            raise ValueError(f"DOCX file not found: {candidate}")
        return candidate

    files = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".docx"
        and not path.name.startswith("~$")
        and (bool(re.search(r"cover|letter", path.stem, re.I)) == cover_letter)
    ]
    if not files:
        kind = "cover letter" if cover_letter else "resume"
        raise ValueError(f"No {kind} DOCX found in {directory}")
    return max(files, key=lambda path: (path.stat().st_mtime_ns, path.name))


def read_docx(path: Path) -> list[Paragraph]:
    try:
        with ZipFile(path) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
    except (BadZipFile, KeyError, ET.ParseError) as error:
        raise ValueError(f"Cannot read Word document {path}: {error}") from error

    result: list[Paragraph] = []
    for element in document.iter(WORD + "p"):
        style_element = element.find(f"{WORD}pPr/{WORD}pStyle")
        style = style_element.get(WORD + "val", "") if style_element is not None else ""
        chunks: list[str] = []
        current = ""
        for node in element.iter():
            if node.tag == WORD + "t":
                current += node.text or ""
            elif node.tag in (WORD + "br", WORD + "cr"):
                if current.strip():
                    chunks.append(current.strip())
                current = ""
        if current.strip():
            chunks.append(current.strip())
        if chunks:
            result.append(Paragraph(tuple(chunks), style))
    if not result:
        raise ValueError(f"No readable text found in {path}")
    return result


def is_heading(paragraph: Paragraph) -> bool:
    text = paragraph.text
    return "heading" in paragraph.style.lower() or text.upper() in HEADINGS


def contact_item(item: str, subject: str) -> str:
    item = re.sub(r",(?=\S)", ", ", item.strip())
    if EMAIL.fullmatch(item):
        href = f"mailto:{item}?subject={quote(subject, safe='')}"
        return f'<a href="{escape(href, quote=True)}">{escape(item)}</a>'
    if PHONE.fullmatch(item):
        number = re.sub(r"[^\d+]", "", item)
        digits = re.sub(r"\D", "", number)
        prefix = "+91 " if digits.startswith("91") and len(digits) == 12 else ""
        masked = f"{prefix}••••••{digits[-4:]}"
        return f'<a href="tel:{escape(number, quote=True)}">{masked}</a>'
    if item.startswith(("https://", "http://", "www.", "linkedin.com/")):
        href = item if item.startswith(("https://", "http://")) else "https://" + item
        return f'<a href="{escape(href, quote=True)}">{escape(item.removeprefix("https://"))}</a>'
    return escape(item)


def identity(paragraphs: list[Paragraph], subject: str) -> str:
    if not paragraphs:
        raise ValueError("Document has no name or contact details")
    name = escape(paragraphs[0].text)
    details = [
        part
        for paragraph in paragraphs[1:]
        for chunk in paragraph.chunks
        for part in re.split(r"\s{2,}", chunk)
        if part.strip()
    ]
    contact = " · ".join(contact_item(part, subject) for part in details)
    return (
        '<div class="document-identity">'
        f'<div class="document-name">{name}</div>'
        f'<p class="document-contact">{contact}</p>'
        "</div>"
    )


def paragraph_html(text: str, class_name: str = "") -> str:
    attr = f' class="{class_name}"' if class_name else ""
    return f"<p{attr}>{escape(text)}</p>"


def experience_html(paragraphs: list[Paragraph]) -> str:
    if not paragraphs:
        return ""
    parts: list[str] = []
    index = 0
    while index < len(paragraphs):
        if index + 1 < len(paragraphs) and DATE_RANGE.search(paragraphs[index + 1].text):
            title = paragraphs[index].text
            employer = re.sub(
                r"(?<=[A-Za-z.])(?=(?:19|20)\d{2}\s*[-–])",
                " · ",
                paragraphs[index + 1].text,
            )
            index += 2
            bullets: list[str] = []
            while index < len(paragraphs) and not (
                index + 1 < len(paragraphs) and DATE_RANGE.search(paragraphs[index + 1].text)
            ):
                bullets.append(paragraphs[index].text)
                index += 1
            items = "\n".join(f"<li>{escape(line)}</li>" for line in bullets)
            parts.append(
                '<section class="document-job">'
                f"<h4>{escape(title)}</h4>"
                f'<p class="document-employer">{escape(employer)}</p>'
                + (f"<ul>\n{items}\n</ul>" if items else "")
                + "</section>"
            )
        else:
            parts.append(paragraph_html(paragraphs[index].text))
            index += 1
    return "\n".join(parts)


def section_html(heading: str, paragraphs: list[Paragraph]) -> str:
    name = heading.strip()
    if name.upper() == "EXPERIENCE":
        content = experience_html(paragraphs)
    elif name.upper() == "CERTIFICATIONS":
        content = "<ul>\n" + "\n".join(f"<li>{escape(p.text)}</li>" for p in paragraphs) + "\n</ul>"
    elif name.upper() == "EDUCATION" and paragraphs:
        content = f"<h4>{escape(paragraphs[0].text)}</h4>" + "\n".join(
            paragraph_html(p.text) for p in paragraphs[1:]
        )
    elif name.upper() == "SKILLS":
        items = []
        for paragraph in paragraphs:
            if ":" in paragraph.text:
                category, detail = paragraph.text.split(":", 1)
                items.append(
                    '<p class="document-skill">'
                    f"<strong>{escape(category)}:</strong> {escape(detail.strip())}</p>"
                )
            else:
                items.append(paragraph_html(paragraph.text, "document-skill"))
        content = "\n".join(items)
    else:
        content = "\n".join(paragraph_html(p.text) for p in paragraphs)
    return f"<section><h3>{escape(name)}</h3>\n{content}</section>"


def render_resume(paragraphs: list[Paragraph], subject: str) -> str:
    first_heading = next((i for i, paragraph in enumerate(paragraphs) if i > 0 and is_heading(paragraph)), None)
    if first_heading is None:
        raise ValueError("Resume has no section headings; check the uploaded DOCX")
    parts = [identity(paragraphs[:first_heading], subject)]
    index = first_heading
    while index < len(paragraphs):
        heading = paragraphs[index]
        if not is_heading(heading):
            raise ValueError(f"Unexpected content outside a resume section: {heading.text[:80]}")
        next_heading = next((i for i in range(index + 1, len(paragraphs)) if is_heading(paragraphs[i])), len(paragraphs))
        parts.append(section_html(heading.text, paragraphs[index + 1:next_heading]))
        index = next_heading
    return "\n".join(parts)


def render_cover_letter(paragraphs: list[Paragraph], subject: str) -> str:
    start = next(
        (i for i, paragraph in enumerate(paragraphs) if paragraph.text.lower().startswith(("dear ", "to whom"))),
        None,
    )
    if start is None:
        raise ValueError("Cover letter has no salutation; check the uploaded DOCX")
    parts = [identity(paragraphs[:start], subject)]
    blocks = [chunk for paragraph in paragraphs[start:] for chunk in paragraph.chunks if chunk.strip()]
    index = 0
    while index < len(blocks):
        line = blocks[index].strip()
        if re.fullmatch(r"(?i)(best regards|kind regards|sincerely),?", line) and index + 1 < len(blocks):
            parts.append(f'<p class="signature">{escape(line)}<br><strong>{escape(blocks[index + 1].strip())}</strong></p>')
            index += 2
        else:
            parts.append(paragraph_html(line))
            index += 1
    return "\n".join(parts)


def replace_preview(page: str, marker: str, content: str) -> str:
    pattern = re.compile(r"(?<=<!-- " + re.escape(marker) + r":start -->).*?(?=<!-- " + re.escape(marker) + r":end -->)", re.S)
    if len(pattern.findall(page)) != 1:
        raise ValueError(f"Expected one {marker} preview region in resume.html")
    indent = "            "
    replacement = "\n" + "\n".join(indent + line for line in content.splitlines()) + "\n" + indent
    return pattern.sub(lambda _: replacement, page, count=1)


def replace_download(page: str, article_id: str, file: Path, download_name: str) -> str:
    start = page.find(f'id="{article_id}"')
    if start < 0:
        raise ValueError(f"Missing {article_id} in resume.html")
    end = page.find('class="document-body', start)
    if end < 0:
        raise ValueError(f"Missing document preview after {article_id}")
    toolbar = page[start:end]
    pattern = re.compile(r'(<a\s+class="button primary"\s+href=")[^"]+("\s+download=")[^"]+(")', re.S)
    href = escape(quote(file.relative_to(ROOT).as_posix(), safe="/"), quote=True)
    name = escape(download_name, quote=True)
    updated, count = pattern.subn(lambda m: m.group(1) + href + m.group(2) + name + m.group(3), toolbar, count=1)
    if count != 1:
        raise ValueError(f"Expected one download link for {article_id}")
    return page[:start] + updated + page[end:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", help="DOCX filename in the resume folder (default: newest resume DOCX)")
    parser.add_argument("--cover-letter", help="DOCX filename in the resume folder (default: newest cover-letter DOCX)")
    args = parser.parse_args()
    config = load_env(ROOT / ".env")
    directory = (ROOT / config.get("RESUME_DIR", "resume")).resolve()
    output = (ROOT / config.get("OUTPUT_HTML", "resume.html")).resolve()
    if not directory.is_dir() or directory.parent != ROOT:
        raise ValueError(f"RESUME_DIR must be a folder directly inside the portfolio: {directory}")
    if not output.is_file() or output != ROOT / "resume.html":
        raise ValueError(f"OUTPUT_HTML must be the existing resume.html: {output}")
    resume = choose_file(directory, args.resume or config.get("RESUME_FILE", "auto"), False)
    cover = choose_file(directory, args.cover_letter or config.get("COVER_LETTER_FILE", "auto"), True)
    resume_name = config.get("RESUME_DOWNLOAD_NAME", "source")
    if resume_name.lower() == "source":
        resume_name = resume.name
    cover_name = config.get("COVER_LETTER_DOWNLOAD_NAME", "source")
    if cover_name.lower() == "source":
        cover_name = cover.name
    if not resume_name.lower().endswith(".docx") or not cover_name.lower().endswith(".docx"):
        raise ValueError("Download filenames must end in .docx")
    subject = config.get("EMAIL_SUBJECT", "Cloud Platform Engineering Opportunity - Jithin C")
    old = output.read_text(encoding="utf-8")
    new = replace_preview(old, "resume-preview", render_resume(read_docx(resume), subject))
    new = replace_preview(new, "cover-letter-preview", render_cover_letter(read_docx(cover), subject))
    new = replace_download(new, "resume-document", resume, resume_name)
    new = replace_download(new, "cover-letter-document", cover, cover_name)
    if new != old:
        output.write_text(new, encoding="utf-8")
        print(f"Updated {output.name} from {resume.name} and {cover.name}")
    else:
        print(f"{output.name} is already current")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)

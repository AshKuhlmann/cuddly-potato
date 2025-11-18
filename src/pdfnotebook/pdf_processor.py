"""Helpers that split PDF files into per-page neighbors."""
from __future__ import annotations

from pathlib import Path
from typing import List

from PyPDF2 import PdfReader, PdfWriter


def split_pdf_by_page(source: Path, destination: Path) -> List[Path]:
    """Extract each page of ``source`` into ``destination``."""
    reader = PdfReader(source)
    destination.mkdir(parents=True, exist_ok=True)
    page_paths: List[Path] = []

    for index, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        page_file = destination / f"page_{index + 1:03}.pdf"
        with page_file.open("wb") as output_file:
            writer.write(output_file)
        page_paths.append(page_file)

    return page_paths


def find_pages(destination: Path) -> List[Path]:
    """Return the individual page PDFs in alphabetical order."""
    return sorted(destination.glob("page_*.pdf"))


def ensure_page_splits(source: Path, destination: Path) -> List[Path]:
    """Create per-page PDFs in ``destination`` (rebuilding if the count changes)."""
    if not destination.exists():
        return split_pdf_by_page(source, destination)

    reader = PdfReader(source)
    existing_pages = find_pages(destination)
    if len(existing_pages) != len(reader.pages):
        return split_pdf_by_page(source, destination)

    return existing_pages

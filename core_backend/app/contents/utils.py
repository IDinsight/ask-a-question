import os
import tempfile
from pathlib import Path

import pypandoc


def convert_markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """
    Convert markdown text to PDF bytes using pypandoc.

    Parameters
    ----------
    markdown_text
        The markdown content to convert

    Returns
    -------
    pdf_content
        The binary content of the generated PDF file.
    """

    tex_header_path = Path(__file__).parent / "tex_header.tex"
    # Create temporary file for PDF generation
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name
    try:
        pypandoc.convert_text(
            markdown_text,
            "pdf",
            format="markdown",
            outputfile=tmp_pdf_path,
            extra_args=[
                "--pdf-engine=xelatex",
                "-V",
                "mainfont=DejaVu Sans",
                "-V",
                "geometry:margin=1in",
                "--include-in-header",
                str(tex_header_path),
                "-V",
                "linestretch=1.15",
                "-V",
                "tables=no",  # Disable booktabs
            ],
        )

        # Read the generated PDF
        with open(tmp_pdf_path, "rb") as f:
            pdf_content = f.read()

        return pdf_content

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

import os
import tempfile

import pypandoc


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """
    Convert markdown text to PDF bytes.

    Args:
        markdown_text: The markdown content to convert

    Returns:
        PDF file as bytes

    Raises:
        Exception: If PDF generation fails
    """
    # Create temporary file for PDF generation
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf_path = tmp_pdf.name

    try:
        pypandoc.convert_text(
            markdown_text,
            "pdf",
            format="markdown",
            outputfile=tmp_pdf_path,
            extra_args=["--pdf-engine=lualatex"],
        )

        # Read the generated PDF
        with open(tmp_pdf_path, "rb") as f:
            pdf_content = f.read()

        return pdf_content

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

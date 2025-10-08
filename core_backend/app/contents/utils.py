import os
import subprocess
import tempfile
from textwrap import dedent

TABLE_CSS = dedent(
    """\
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
:root { --border:#d0d7de; --thead:#f6f8fa; }
body {
    font-family: system-ui, -apple-system,
        Segoe UI, Roboto, "Noto Sans", Arial, sans-serif;
    font-size: 12px;
    line-height: 1.5;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 16px;
    table-layout: fixed;
}
thead { background: var(--thead); }
table, th, td { border: 1px solid var(--border); }
th, td {
    padding: 6px 8px;
    vertical-align: top;
    word-wrap: break-word;
}
tbody tr:nth-child(even) { background: #fafbfc; }
h1, h2, h3 { page-break-after: avoid; margin: 0 0 8px; }
.pagebreak { break-before: page; }
"""
)


def convert_markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    """
    Convert Markdown text to PDF bytes with CSS-styled tables (cell borders).
    Requires: pandoc + weasyprint CLI (pip install weasyprint) in PATH.
    """
    if not markdown_text.strip():
        raise ValueError("Markdown text is empty")

    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = os.path.join(tmpdir, "input.md")
        css_path = os.path.join(tmpdir, "print.css")
        pdf_path = os.path.join(tmpdir, "output.pdf")

        # Write sources
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(TABLE_CSS)

        # Pandoc: Markdown -> HTML -> PDF (WeasyPrint), apply CSS for borders
        # Use GFM reader for robust pipe tables
        cmd = [
            "pandoc",
            "-f",
            "gfm",  # better for Markdown tables than plain 'markdown'
            "-t",
            "html5",
            "-s",  # standalone HTML (so CSS applies)
            md_path,
            "--css",
            css_path,
            "--pdf-engine=weasyprint",
            "-o",
            pdf_path,
            "--quiet",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(
                f"Pandoc failed:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
            )

        with open(pdf_path, "rb") as f:
            return f.read()

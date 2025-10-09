"""
PDF Report Generator - Converts markdown reports to professional PDFs.
Uses markdown2pdf for easy conversion with styling.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_pdf_report(markdown_path: str, output_path: Optional[str] = None) -> str:
    """
    Generate PDF report from markdown file.
    
    Uses pandoc if available, falls back to markdown2pdf or basic HTML conversion.
    
    Args:
        markdown_path: Path to markdown file
        output_path: Optional output PDF path (defaults to same dir as .md)
    
    Returns:
        Path to generated PDF
    """
    md_path = Path(markdown_path)
    
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
    
    # Default output path
    if output_path is None:
        output_path = md_path.with_suffix('.pdf')
    else:
        output_path = Path(output_path)
    
    logger.info(f"Generating PDF report: {output_path}")
    
    # Try different conversion methods in order of preference
    success = False
    
    # Method 1: Try pandoc (best quality)
    if not success:
        success = _try_pandoc(md_path, output_path)
    
    # Method 2: Try markdown2pdf
    if not success:
        success = _try_markdown2pdf(md_path, output_path)
    
    # Method 3: Try md2pdf
    if not success:
        success = _try_md2pdf(md_path, output_path)
    
    # Method 4: Fallback to basic HTML conversion
    if not success:
        success = _try_html_to_pdf(md_path, output_path)
    
    if success:
        logger.info(f"✅ PDF report generated: {output_path}")
        return str(output_path)
    else:
        logger.error("❌ All PDF generation methods failed. Install pandoc for best results:")
        logger.error("   brew install pandoc (macOS)")
        logger.error("   Or: pip install markdown2pdf")
        raise RuntimeError("PDF generation failed. See logs for installation instructions.")


def _try_pandoc(md_path: Path, output_path: Path) -> bool:
    """Try generating PDF with pandoc (best quality)"""
    try:
        # Check if pandoc is available
        result = subprocess.run(
            ['which', 'pandoc'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.debug("pandoc not available")
            return False
        
        # Generate PDF with pandoc
        cmd = [
            'pandoc',
            str(md_path),
            '-o', str(output_path),
            '--pdf-engine=xelatex',  # Better Unicode support
            '-V', 'geometry:margin=1in',
            '-V', 'fontsize=11pt',
            '--highlight-style=tango',
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and output_path.exists():
            logger.info("Generated PDF using pandoc")
            return True
        else:
            logger.debug(f"pandoc failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.debug(f"pandoc error: {e}")
        return False


def _try_markdown2pdf(md_path: Path, output_path: Path) -> bool:
    """Try generating PDF with markdown2pdf library"""
    try:
        from markdown2pdf import convert
        
        convert(str(md_path), str(output_path))
        
        if output_path.exists():
            logger.info("Generated PDF using markdown2pdf")
            return True
        return False
        
    except ImportError:
        logger.debug("markdown2pdf not installed")
        return False
    except Exception as e:
        logger.debug(f"markdown2pdf error: {e}")
        return False


def _try_md2pdf(md_path: Path, output_path: Path) -> bool:
    """Try generating PDF with md2pdf library"""
    try:
        from md2pdf.core import md2pdf
        
        md2pdf(
            str(output_path),
            md_content=md_path.read_text(),
        )
        
        if output_path.exists():
            logger.info("Generated PDF using md2pdf")
            return True
        return False
        
    except ImportError:
        logger.debug("md2pdf not installed")
        return False
    except Exception as e:
        logger.debug(f"md2pdf error: {e}")
        return False


def _try_html_to_pdf(md_path: Path, output_path: Path) -> bool:
    """Fallback: Convert markdown → HTML → PDF"""
    try:
        import markdown
        from weasyprint import HTML
        
        # Read markdown
        md_content = md_path.read_text()
        
        # Convert to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        # Add CSS styling
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                    color: #333;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #2980b9;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #34495e;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .metric {{
                    font-weight: bold;
                    color: #27ae60;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Convert HTML to PDF
        HTML(string=styled_html).write_pdf(str(output_path))
        
        if output_path.exists():
            logger.info("Generated PDF using HTML conversion")
            return True
        return False
        
    except ImportError as e:
        logger.debug(f"HTML-to-PDF libraries not available: {e}")
        return False
    except Exception as e:
        logger.debug(f"HTML-to-PDF error: {e}")
        return False


def generate_pdf_from_state(state: dict) -> Optional[str]:
    """
    Generate PDF from pipeline state (convenience wrapper).
    
    Args:
        state: Pipeline state dict
    
    Returns:
        Path to PDF or None if failed
    """
    artifacts_dir = state.get("artifacts_dir")
    if not artifacts_dir:
        logger.warning("No artifacts_dir in state, cannot generate PDF")
        return None
    
    md_path = Path(artifacts_dir) / "report.md"
    
    if not md_path.exists():
        logger.warning(f"Markdown report not found: {md_path}")
        return None
    
    try:
        pdf_path = generate_pdf_report(str(md_path))
        return pdf_path
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None


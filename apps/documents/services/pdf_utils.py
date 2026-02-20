import base64
import io
import fitz  # PyMuPDF


def pdf_page_to_base64_png(pdf_path: str, page_number: int = 1, dpi: int = 250) -> str:
    """
    Convert a PDF page to base64-encoded PNG using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file
        page_number: Page number (1-indexed)
        dpi: Resolution for rendering
    
    Returns:
        Base64-encoded PNG string
    """
    doc = fitz.open(pdf_path)
    
    if page_number < 1 or page_number > len(doc):
        raise RuntimeError(f"Page {page_number} does not exist. PDF has {len(doc)} pages.")
    
    page = doc[page_number - 1]  # PyMuPDF uses 0-indexed pages
    
    # Calculate zoom factor for desired DPI (default PDF is 72 DPI)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    # Render page to pixmap
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PNG bytes
    png_bytes = pix.tobytes("png")
    
    doc.close()
    
    return base64.b64encode(png_bytes).decode("utf-8")

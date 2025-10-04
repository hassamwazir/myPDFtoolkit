import fitz  # PyMuPDF
from PIL import Image
import io

def load_pdf(file_path: str) -> list[Image.Image]:
    """Load a PDF file and return its pages as a list of PIL images."""
    pdf_images = []
    
    try:
        # Open the PDF with PyMuPDF
        pdf_document = fitz.open(file_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)  # Load the page
            
            # Render page to a pixmap (image in PyMuPDF terms)
            pix = page.get_pixmap()
            
            # Convert the pixmap to a bytes object and open it as an image using PIL
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            pdf_images.append(img)
        
        pdf_document.close()
    except Exception as e:
        print(f"Error loading PDF: {e}")
    
    return pdf_images

def get_page_count(file_path: str) -> int:
    """Return the total number of pages in the PDF."""
    try:
        pdf_document = fitz.open(file_path)
        page_count = pdf_document.page_count
        pdf_document.close()
        return page_count
    except Exception as e:
        print(f"Error getting page count: {e}")
        return 0

def merge_files(file_paths: list[str], output_path: str) -> None:
    """Merge multiple PDF files into a single PDF file."""
    try:
        merger = fitz.open()  # Empty document to merge into
        
        for pdf in file_paths:
            pdf_document = fitz.open(pdf)
            merger.insert_pdf(pdf_document)
            pdf_document.close()
        
        merger.save(output_path)
        merger.close()
    except Exception as e:
        print(f"Error merging PDFs: {e}")

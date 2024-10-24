import tkinter as tk
import fitz  # PyMuPDF to handle PDF operations
from tkinter import filedialog, messagebox
import pdf_tools  # Import the PDF tools for additional functionality
from PIL import Image
import os
import io

# Global variable to hold the original PDF document
pdf_document = None

def upload_and_load_pdf(file_name_var, images, update_image, update_page_text, remove_button, save_button):
    """Browse, upload and load a PDF file."""
    global pdf_document
    # Browse for a file
    pdf_file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if pdf_file_path:
        # Set the file name in the text bar
        file_name_var.set(pdf_file_path)
        # Open the PDF using PyMuPDF
        pdf_document = fitz.open(pdf_file_path)
        images.clear()
        images.extend(pdf_tools.load_pdf(pdf_file_path))  # Load PDF as images using pdf_tools
        update_image(0)  # Show the first page as an image
        update_page_text(0, len(images))  # Update the page text
        remove_button.config(state="normal")  # Enable the remove page button
        save_button.config(state="normal")    # Enable the save button

def upload_files(file_list_var):
    """Allow the user to upload PDF, JPEG, and PNG files."""
    file_paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf"), ("JPEG files", "*.jpg;*.jpeg"), ("PNG files", "*.png")])
    
    if file_paths:
        for file in file_paths:
            file_list_var.append(file)  # Add files to the list
        return True
    return False

def display_file_list(file_list_var, listbox):
    """Update the listbox to show the selected files in the sequence they were uploaded."""
    listbox.delete(0, tk.END)  # Clear the listbox first
    for idx, file in enumerate(file_list_var):
        listbox.insert(tk.END, f"{idx + 1}. {os.path.basename(file)}")  # Display file names in the listbox

def remove_page(images, current_image_index, update_image, update_page_text, remove_button, save_button):
    """Remove the current page from the PDF and the image list."""
    global pdf_document
    if images and pdf_document:
        del images[current_image_index]  # Remove the image from the list
        pdf_document.delete_page(current_image_index)  # Remove the page from the PDF
        if current_image_index >= len(images):
            current_image_index = len(images) - 1
        if len(images) == 0:  # If no images are left
            update_page_text(None, None)  # Clear the page text
            update_image(None)  # Clear the image display
            remove_button.config(state="disabled")
            save_button.config(state="disabled")
        else:
            update_image(current_image_index)  # Show the new current image
            update_page_text(current_image_index, len(images))

def save_pdf():
    """Save the modified PDF file."""
    global pdf_document
    if pdf_document:
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if save_path:
            pdf_document.save(save_path)
            pdf_document.close()
            pdf_document = None  # Reset the document

# def merge_pdfs():
#     """Merge multiple PDF files into one."""
#     pdf_paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")], title="Select PDF files to merge")
#     if pdf_paths:
#         save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
#         if save_path:
#             pdf_tools.merge_files(pdf_paths, save_path)

def merge_files(file_list_var):
    """Merge uploaded files (PDFs and images) into a single PDF, ensuring images match the page size while maintaining aspect ratio."""
    if not file_list_var:
        messagebox.showerror("Error", "No files selected for merging.")
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not save_path:
        return

    # Create a new PDF document using PyMuPDF
    merger = fitz.open()

    # Variables to store the reference width and height (based on the first PDF page)
    reference_width, reference_height = None, None

    for file in file_list_var:
        file_ext = file.lower().split('.')[-1]
        
        if file_ext == "pdf":
            # Append PDF pages
            with fitz.open(file) as pdf_doc:
                if reference_width is None or reference_height is None:
                    first_page = pdf_doc[0]
                    reference_width, reference_height = first_page.rect.width, first_page.rect.height
                merger.insert_pdf(pdf_doc)
        elif file_ext in ["jpg", "jpeg", "png"]:
            # Convert images to PDFs
            img = Image.open(file)
            img = img.convert("RGB")  # Ensure the image is in RGB format

            # If we have no reference width/height, use standard letter size (612x792 points)
            if reference_width is None or reference_height is None:
                reference_width, reference_height = 612, 792  # Default letter size in points (8.5 x 11 inches)

            # Get the original image size
            img_width, img_height = img.size

            # Calculate the aspect ratio of the image
            img_aspect = img_width / img_height
            page_aspect = reference_width / reference_height

            # Resize while maintaining aspect ratio
            if img_aspect > page_aspect:
                # Image is wider than the page, scale based on width
                new_width = int(reference_width)
                new_height = int(reference_width / img_aspect)
            else:
                # Image is taller than the page, scale based on height
                new_height = int(reference_height)
                new_width = int(reference_height * img_aspect)

            # Resize the image with maintained aspect ratio
            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Create a new blank image with the reference size and paste the resized image onto it (centered)
            new_img = Image.new("RGB", (int(reference_width), int(reference_height)), color="white")
            new_img.paste(img, ((int(reference_width) - new_width) // 2, (int(reference_height) - new_height) // 2))

            # Save the image as a PDF in memory
            img_pdf_bytes = io.BytesIO()
            new_img.save(img_pdf_bytes, format="PDF")  # Save as PDF into memory
            img_pdf_bytes.seek(0)  # Rewind to the beginning of the in-memory file
            
            # Load the PDF from memory and insert it into the merger
            merger.insert_pdf(fitz.open(stream=img_pdf_bytes.read(), filetype="pdf"))

    # Save the merged PDF
    merger.save(save_path)
    merger.close()
    messagebox.showinfo("Success", f"Merged PDF saved as {save_path}")
    file_list_var.clear()  # Clear the file list after merging
import tkinter as tk
from tkinter import Label, Button, Entry, Listbox, Scrollbar
from tkinter import ttk  # Import for tabs
from PIL import Image, ImageTk, ImageOps
import gui_utils  # Import the custom GUI utility functions



# Global variables for images and current page index
images = []
current_image_index = 0

# Global variable to hold the list of uploaded files (PDFs and images)
file_list_var = []

# Function to add files to the list
def add_files():
    """Add files to the file list and update the display."""
    if gui_utils.upload_files(file_list_var):
        gui_utils.display_file_list(file_list_var, file_listbox)

# Function to remove the selected file from the list
def remove_file():
    """Remove the selected file from the listbox and the file list."""
    selected_index = file_listbox.curselection()
    if selected_index:
        # Remove the file from the listbox and the file list
        file_list_var.pop(selected_index[0])
        file_listbox.delete(selected_index)

# Function to update the displayed image and the page text
def update_image(index):
    global current_image_index
    current_image_index = index if index is not None else 0

    # Define the target size for the letter page, scaled down
    target_width, target_height = 204, 264  # Scaled-down letter size (1/3rd of original)

    if index is not None and images:
        img = images[index]
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        total_pages = len(images)
    else:
        img = Image.new('RGB', (target_width, target_height), color='white')
        total_pages = 0

    img_with_border = ImageOps.expand(img, border=1, fill='black')
    img_tk = ImageTk.PhotoImage(img_with_border)
    image_label.config(image=img_tk)
    image_label.image = img_tk

    # Update the page text to reflect the current page
    update_page_text(current_image_index, total_pages)

# Function to update the page text
def update_page_text(current_page:int, total_pages:int):
    if current_page is None or total_pages is None:
        page_text.set("Upload a PDF to view")
    else:
        if total_pages > 0:
            page_text.set(f"Page {current_page + 1} of {total_pages}")

# Initialize the main window
root = tk.Tk()
root.title("PDF Toolkit")
root.geometry("600x400")

# Create a tab control
tab_control = ttk.Notebook(root)

# Tab 1: Remove Pages
remove_tab = ttk.Frame(tab_control)
tab_control.add(remove_tab, text="Remove Pages")

# Tab 2: Merge Files
merge_tab = ttk.Frame(tab_control)
tab_control.add(merge_tab, text="Merge Files")

# Add tab control to the main window
tab_control.pack(expand=1, fill="both")

# --- Remove Pages Tab Setup ---
# Set up the frame for the right side
right_frame = tk.Frame(remove_tab)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Variable to hold the PDF file path
file_name_var = tk.StringVar()

# Entry field to display the file name
file_name_entry = Entry(remove_tab, textvariable=file_name_var, width=40)
file_name_entry.pack(pady=10)

# Upload button (Combining browse and upload)
upload_button_remove = Button(remove_tab, text="Upload", command=lambda: gui_utils.upload_and_load_pdf(file_name_var, images, update_image, update_page_text, remove_button, save_button))
upload_button_remove.pack(pady=5)

# Create a label to hold the image
image_label = Label(right_frame)
image_label.pack()

# Create a frame for page navigation (<<, page number, >>)
nav_frame = tk.Frame(right_frame)
nav_frame.pack(pady=10)

# Create the page navigation buttons and text
back_button = Button(nav_frame, text="<<", command=lambda: update_image(max(0, current_image_index - 1)))
back_button.grid(row=0, column=0)

page_text = tk.StringVar()
page_label = Label(nav_frame, textvariable=page_text, font=("Helvetica", 12))
page_label.grid(row=0, column=1, padx=10)

forward_button = Button(nav_frame, text=">>", command=lambda: update_image(min(len(images) - 1, current_image_index + 1)))
forward_button.grid(row=0, column=2)

# Create a Remove Page button
remove_button = Button(remove_tab, text="Remove Page", command=lambda: gui_utils.remove_page(images, current_image_index, update_image, update_page_text, remove_button, save_button), state="disabled")
remove_button.pack(pady=5)

# Create a Save button
save_button = Button(remove_tab, text="Save", command=gui_utils.save_pdf, state="disabled")
save_button.pack(pady=5)

# Initialize the first image display (white image if no images available)
update_image(None)
update_page_text(None, None)

# --- Merge Files Tab Setup ---
merge_instruction = Label(merge_tab, text="Select PDFs, JPEGs, or PNGs to merge:")
merge_instruction.pack(pady=10)

# Create a listbox to display uploaded files
file_listbox = Listbox(merge_tab, height=8, width=50)
file_listbox.pack(pady=5)

# Add a scrollbar to the listbox
scrollbar = Scrollbar(merge_tab)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
file_listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=file_listbox.yview)

# Add and Remove buttons
button_frame = tk.Frame(merge_tab)
button_frame.pack(pady=5)

# + button to add files
add_file_button = Button(button_frame, text="+", command=add_files)
add_file_button.grid(row=0, column=0, padx=5)

# - button to remove the selected file
remove_file_button = Button(button_frame, text="-", command=remove_file)
remove_file_button.grid(row=0, column=1, padx=5)

# Merge button (to merge files in the order they were uploaded)
merge_button = Button(merge_tab, text="Merge Files", command=lambda: gui_utils.merge_files(file_list_var, file_listbox))
merge_button.pack(pady=5)

# Start the tkinter loop
root.mainloop()
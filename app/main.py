# app/main.py
# --- make PyMuPDF happy when running as a windowed (no-console) EXE ---
import os, sys
if getattr(sys, "frozen", False):  # running from PyInstaller bundle
    if not sys.stdout:
        sys.stdout = open(os.devnull, "w")
    if not sys.stderr:
        sys.stderr = open(os.devnull, "w")
# ----------------------------------------------------------------------

# robust imports: work in package mode and in frozen script mode
try:
    from . import gui_utils, pdf_tools
except ImportError:
    import gui_utils, pdf_tools

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps

import ttkbootstrap as tb
from ttkbootstrap.constants import *

# IMPORTANT: app package structure should be:
# app/
#   __init__.py
#   main.py
#   gui_utils.py
#   pdf_tools.py
#   assets/app.ico (or .icns on macOS)


class TreeListboxShim:
    """
    Small adapter so we can pass a ttk.Treeview to functions that expect
    a Tk Listbox with .delete(0, END). We just clear all rows.
    """
    def __init__(self, tree: tb.Treeview):
        self.tree = tree

    def delete(self, start=None, end=None):
        # Clear all items in the tree
        for item in self.tree.get_children():
            self.tree.delete(item)


class PDFToolkitApp(tb.Window):
    def __init__(self):
        super().__init__(themename="flatly")  # try "cosmo", "darkly", "solar", etc.
        self.title("PDF Toolkit")
        self.geometry("1000x650")
        self.minsize(900, 550)

        # Optional: app icon (Windows .ico, macOS .icns)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "app.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # App state
        self.images: list[Image.Image] = []
        self.current_image_index: int = 0
        self.file_list: list[str] = []  # merge queue

        self._build_ui()
        self._bind_shortcuts()

    # ----------------------- UI BUILD -----------------------

    def _build_ui(self):
        # Menubar
        menubar = tb.Menu(self)
        filemenu = tb.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open PDF…", accelerator="Ctrl+O", command=self.open_pdf)
        filemenu.add_command(label="Save As…", accelerator="Ctrl+S", command=self.save_pdf)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", accelerator="Ctrl+Q", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        # Paned layout
        paned = tb.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: tabs (Remove Pages / Merge Files)
        left = tb.Frame(paned)
        paned.add(left, weight=1)

        tabs = tb.Notebook(left, bootstyle="secondary")
        tabs.pack(fill="both", expand=True)

        self.remove_tab = tb.Frame(tabs)
        self.merge_tab = tb.Frame(tabs)
        tabs.add(self.remove_tab, text="Remove Pages")
        tabs.add(self.merge_tab, text="Merge Files")

        # Right: live preview
        right = tb.Frame(paned)
        paned.add(right, weight=3)

        # ---------------- Remove Pages tab ----------------
        self.file_name_var = tk.StringVar()
        tb.Entry(self.remove_tab, textvariable=self.file_name_var).pack(pady=8, padx=8, fill="x")

        tb.Button(
            self.remove_tab,
            text="Upload",
            command=lambda: gui_utils.upload_and_load_pdf(
                self.file_name_var,
                self.images,
                self.update_image,
                self.update_page_text,
                self.remove_btn,
                self.save_btn,
            ),
        ).pack(pady=4)

        nav = tb.Frame(self.remove_tab)
        nav.pack(pady=8)

        self.page_text = tk.StringVar(value="Upload a PDF to view")
        tb.Button(nav, text="<<", command=lambda: self.update_image(max(0, self.current_image_index - 1))).grid(
            row=0, column=0, padx=4
        )
        tb.Label(nav, textvariable=self.page_text).grid(row=0, column=1, padx=8)
        tb.Button(
            nav,
            text=">>",
            command=lambda: self.update_image(min(len(self.images) - 1, self.current_image_index + 1)),
        ).grid(row=0, column=2, padx=4)

        self.remove_btn = tb.Button(
            self.remove_tab,
            text="Remove Page",
            state="disabled",
            command=lambda: gui_utils.remove_page(
                self.images,
                self.current_image_index,
                self.update_image,
                self.update_page_text,
                self.remove_btn,
                self.save_btn,
            ),
        )
        self.remove_btn.pack(pady=6)

        self.save_btn = tb.Button(self.remove_tab, text="Save", state="disabled", command=self.save_pdf)
        self.save_btn.pack(pady=6)

        # Preview area
        self.preview = tb.Label(right)
        self.preview.pack(expand=True)

        # ---------------- Merge Files tab (Treeview) ----------------
        tb.Label(self.merge_tab, text="Select PDFs / JPG / PNG to merge:").pack(pady=8)

        self.tree = tb.Treeview(self.merge_tab, columns=("name", "type"), show="headings", height=12, bootstyle="info")
        self.tree.heading("name", text="File")
        self.tree.heading("type", text="Type")
        self.tree.column("name", width=520, anchor="w")
        self.tree.column("type", width=80, anchor="center")
        self.tree.pack(padx=8, pady=4, fill="both", expand=True)

        scroll = tb.Scrollbar(self.merge_tab, orient="vertical", command=self.tree.yview)
        scroll.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")
        self.tree.configure(yscrollcommand=scroll.set)

        btns = tb.Frame(self.merge_tab)
        btns.pack(pady=6)
        tb.Button(btns, text="+", command=self.add_files).grid(row=0, column=0, padx=5)
        tb.Button(btns, text="-", command=self._remove_tree_selected).grid(row=0, column=1, padx=5)
        tb.Button(self.merge_tab, text="Merge Files", command=self._merge_files_threaded).pack(pady=6)

        # Status bar
        self.status = tb.Label(self, text="Ready", anchor="w", bootstyle="inverse")
        self.status.pack(fill="x")

        # Initialize preview
        self.update_image(None)
        self.update_page_text(None, None)

    def _bind_shortcuts(self):
        self.bind_all("<Control-o>", lambda e: self.open_pdf())
        self.bind_all("<Control-s>", lambda e: self.save_pdf())
        self.bind_all("<Control-q>", lambda e: self.destroy())

    # ----------------------- Actions -----------------------

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self.file_name_var.set(path)
        gui_utils.upload_and_load_pdf(
            self.file_name_var, self.images, self.update_image, self.update_page_text, self.remove_btn, self.save_btn
        )
        self._set_status(f"Loaded: {os.path.basename(path)}")

    def save_pdf(self):
        # Use gui_utils.save_pdf; it handles dialogs and messages
        gui_utils.save_pdf()
        self._set_status("Saved PDF")

    def add_files(self):
        if gui_utils.upload_files(self.file_list):
            # Add to the tree for display
            for path in self.file_list[len(self.tree.get_children()) :]:
                self._tree_add(path)
            self._set_status(f"Added {len(self.file_list)} file(s) to merge queue")

    def _tree_add(self, path: str):
        ext = os.path.splitext(path)[1].lower().replace(".", "")
        self.tree.insert("", "end", values=(os.path.basename(path), ext))

    def _remove_tree_selected(self):
        # Remove selected rows from both tree and file_list (keep indices aligned)
        selected = list(self.tree.selection())
        if not selected:
            return

        # Compute indices and remove in reverse order to keep positions consistent
        indices = sorted((self.tree.index(item) for item in selected), reverse=True)
        for idx, item in zip(indices, selected):
            if 0 <= idx < len(self.file_list):
                self.file_list.pop(idx)
            self.tree.delete(item)

        self._set_status("Removed selected file(s)")

    def _merge_files_threaded(self):
        # Put merge in a thread to avoid blocking the UI on large jobs
        self._set_status("Merging…")
        self.configure(cursor="watch")
        t = threading.Thread(target=self._merge_files_safe, daemon=True)
        t.start()

    def _merge_files_safe(self):
        try:
            # Use a shim so gui_utils.merge_files can clear our Treeview after merging
            shim = TreeListboxShim(self.tree)
            gui_utils.merge_files(self.file_list, shim)  # clears file_list and tree via shim
            self._set_status("Merge complete")
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed: {e}")
            self._set_status("Merge failed")
        finally:
            # reset cursor
            self.after(0, lambda: self.configure(cursor=""))

    # ----------------------- Preview helpers -----------------------

    def update_image(self, index):
        """Update right-side preview with current image."""
        self.current_image_index = 0 if index is None else index

        target_w, target_h = 204, 264  # small letter-ish preview
        if index is not None and self.images:
            img = self.images[index].resize((target_w, target_h), Image.Resampling.LANCZOS)
        else:
            img = Image.new("RGB", (target_w, target_h), "white")

        img = ImageOps.expand(img, border=1, fill="black")
        tkimg = ImageTk.PhotoImage(img)
        self.preview.configure(image=tkimg)
        self.preview.image = tkimg

    def update_page_text(self, cur, total):
        if cur is None or total is None or not total:
            self.page_text.set("Upload a PDF to view")
        else:
            self.page_text.set(f"Page {cur + 1} of {total}")

    def _set_status(self, text: str):
        self.status.configure(text=text)


if __name__ == "__main__":
    # Windows HiDPI scaling (no-op elsewhere)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = PDFToolkitApp()
    app.mainloop()

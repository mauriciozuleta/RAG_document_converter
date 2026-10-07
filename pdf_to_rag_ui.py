"""
pdf_to_rag_ui.py
----------------
Simple GUI for the PDF → RAG pipeline.
Drag-and-drop or browse for PDF files, choose an output folder, and convert.

Usage:
    python pdf_to_rag_ui.py

Dependencies:
    pip install pdfminer.six tkinterdnd2
"""

import io
import os
import shutil
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Drag-and-drop support (optional — UI still works without it)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

# Pipeline functions from the CLI module
from pdf_to_rag import detect_chapter_number, process_pdf


def _enable_high_dpi() -> None:
    """Enable crisp rendering on Windows high-DPI displays."""
    if os.name != "nt":
        return
    try:
        import ctypes

        # Windows 10+ preferred: per-monitor DPI awareness v2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Fallback for older Windows versions
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _hide_console_window() -> None:
    """Hide the extra console window on Windows for this GUI app."""
    if os.name != "nt":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        # Non-fatal: GUI should still run even if console can't be hidden.
        pass


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG        = "#1e1e2e"   # dark background
SURFACE   = "#2a2a3e"   # card / zone background
ACCENT    = "#7c6af7"   # purple accent
ACCENT_H  = "#9d8fff"   # accent hover
TEXT      = "#cdd6f4"   # primary text
SUBTEXT   = "#6c7086"   # muted text
SUCCESS   = "#a6e3a1"   # green
WARNING   = "#f9e2af"   # yellow
ERROR     = "#f38ba8"   # red
DROP_IDLE = "#3b3b52"   # drop-zone idle border
DROP_HOV  = "#7c6af7"   # drop-zone hover border


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _clean_dnd_path(raw: str) -> list[str]:
    """Parse the path string returned by tkinterdnd2 (handles spaces & braces)."""
    raw = raw.strip()
    if raw.startswith("{"):
        # Multiple files or path with spaces are wrapped in braces
        parts = []
        depth = 0
        current = ""
        for ch in raw:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    parts.append(current.strip())
                    current = ""
            elif depth:
                current += ch
        return [p for p in parts if p]
    return [raw]


# ---------------------------------------------------------------------------
# Log redirect
# ---------------------------------------------------------------------------

class _TextRedirect(io.TextIOBase):
    """Redirect stdout/stderr to a tkinter ScrolledText widget."""

    def __init__(self, widget: scrolledtext.ScrolledText, tag: str = "normal") -> None:
        self._widget = widget
        self._tag = tag

    def write(self, s: str) -> int:
        self._widget.after(0, self._append, s)
        return len(s)

    def _append(self, s: str) -> None:
        self._widget.configure(state="normal")
        self._widget.insert(tk.END, s, self._tag)
        self._widget.see(tk.END)
        self._widget.configure(state="disabled")

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class App(tk.Tk if not _HAS_DND else TkinterDnD.Tk):  # type: ignore[misc]
    """PDF → RAG Converter GUI."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF → RAG Converter")
        self.resizable(True, True)
        self.minsize(640, 580)
        self.configure(bg=BG)

        self._pdf_paths: list[str] = []
        self._running = False
        self._last_output_paths: list[str] = []
        self._last_out_dir: str = "./rag/"
        self._spinner_chars = ["|", "/", "-", "\\"]
        self._spinner_idx = 0
        self._spinner_after_id: str | None = None

        self._build_scroll_container()
        self._build_ui()
        self._redirect_output()
        self._center_window(720, 700)

    def _build_scroll_container(self) -> None:
        """Create a scrollable host for the full UI (both axes)."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._root_canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self._root_canvas.grid(row=0, column=0, sticky="nsew")

        self._v_scroll = ttk.Scrollbar(self, orient="vertical", command=self._root_canvas.yview)
        self._v_scroll.grid(row=0, column=1, sticky="ns")
        self._h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self._root_canvas.xview)
        self._h_scroll.grid(row=1, column=0, sticky="ew")

        self._root_canvas.configure(
            yscrollcommand=self._v_scroll.set,
            xscrollcommand=self._h_scroll.set,
        )

        self._content = tk.Frame(self._root_canvas, bg=BG)
        self._content_window = self._root_canvas.create_window((0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>", self._on_content_configure)
        self._root_canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel: vertical; Shift+wheel: horizontal.
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.bind_all("<Shift-MouseWheel>", self._on_shift_mouse_wheel)

    def _on_content_configure(self, _event=None) -> None:
        self._root_canvas.configure(scrollregion=self._root_canvas.bbox("all"))

    def _on_canvas_configure(self, _event=None) -> None:
        self._root_canvas.configure(scrollregion=self._root_canvas.bbox("all"))

    def _on_mouse_wheel(self, event) -> None:
        # If pointer is over the log text area, scroll the log instead of the page.
        if str(event.widget) == str(self._log):
            self._log.yview_scroll(int(-event.delta / 120), "units")
            return "break"
        self._root_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_shift_mouse_wheel(self, event) -> None:
        self._root_canvas.xview_scroll(int(-event.delta / 120), "units")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=0)  # header
        self._content.rowconfigure(1, weight=0)  # drop zone
        self._content.rowconfigure(2, weight=0)  # output row
        self._content.rowconfigure(3, weight=0)  # filename row
        self._content.rowconfigure(4, weight=0)  # format row
        self._content.rowconfigure(5, weight=0)  # convert button
        self._content.rowconfigure(6, weight=0)  # action bar (shown after conversion)
        self._content.rowconfigure(7, weight=1)  # log

        # --- Header ---
        hdr = tk.Frame(self._content, bg=BG, pady=14)
        hdr.grid(row=0, column=0, sticky="ew", padx=24)
        tk.Label(
            hdr, text="PDF → RAG Converter",
            font=("Segoe UI", 18, "bold"), fg=ACCENT, bg=BG,
        ).pack(side="left")
        tk.Label(
            hdr, text="FAA handbook edition",
            font=("Segoe UI", 10), fg=SUBTEXT, bg=BG,
        ).pack(side="left", padx=10, pady=(6, 0))

        # --- Drop zone ---
        zone_frame = tk.Frame(self._content, bg=BG)
        zone_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))
        zone_frame.columnconfigure(0, weight=1)

        self._drop_zone = tk.Canvas(
            zone_frame, height=150, bg=SURFACE,
            highlightthickness=2, highlightbackground=DROP_IDLE,
            cursor="hand2",
        )
        self._drop_zone.grid(row=0, column=0, sticky="ew")
        self._draw_drop_zone()

        # Bind click to browse
        self._drop_zone.bind("<Button-1>", lambda _e: self._browse_pdf())
        self._drop_zone.bind("<Enter>", lambda _e: self._zone_hover(True))
        self._drop_zone.bind("<Leave>", lambda _e: self._zone_hover(False))
        self._drop_zone.bind("<Configure>", lambda _e: self._draw_drop_zone())

        # Drag-and-drop registration
        if _HAS_DND:
            self._drop_zone.drop_target_register(DND_FILES)
            self._drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            self._drop_zone.dnd_bind("<<DragEnter>>", lambda _e: self._zone_hover(True))
            self._drop_zone.dnd_bind("<<DragLeave>>", lambda _e: self._zone_hover(False))

        # Browse button below the zone
        btn_row = tk.Frame(zone_frame, bg=BG)
        btn_row.grid(row=1, column=0, pady=(6, 0))
        self._make_button(btn_row, "Browse for PDF(s)", self._browse_pdf, width=18).pack(side="left", padx=4)
        self._make_button(btn_row, "Clear", self._clear_all_fields, width=8, style="flat").pack(side="left", padx=4)

        # --- Output directory row ---
        out_frame = tk.Frame(self._content, bg=BG)
        out_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=6)
        out_frame.columnconfigure(1, weight=1)

        tk.Label(
            out_frame, text="Output folder:", font=("Segoe UI", 10), fg=TEXT, bg=BG,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self._out_var = tk.StringVar(value="")
        out_entry = tk.Entry(
            out_frame, textvariable=self._out_var,
            font=("Segoe UI", 10), bg=SURFACE, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=4,
        )
        out_entry.grid(row=0, column=1, sticky="ew")

        self._make_button(out_frame, "Browse", self._browse_out, width=8).grid(
            row=0, column=2, padx=(8, 0)
        )

        # --- Output file name row ---
        name_frame = tk.Frame(self._content, bg=BG)
        name_frame.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 6))
        name_frame.columnconfigure(1, weight=1)

        tk.Label(
            name_frame,
            text="Output file name:",
            font=("Segoe UI", 10),
            fg=TEXT,
            bg=BG,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self._name_var = tk.StringVar(value="")
        name_entry = tk.Entry(
            name_frame,
            textvariable=self._name_var,
            font=("Segoe UI", 10),
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=4,
        )
        name_entry.grid(row=0, column=1, sticky="ew")

        tk.Label(
            name_frame,
            text="required; for multiple PDFs, this is used as a base name",
            font=("Segoe UI", 8),
            fg=SUBTEXT,
            bg=BG,
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        # --- Output format row ---
        fmt_frame = tk.Frame(self._content, bg=BG)
        fmt_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 6))

        tk.Label(
            fmt_frame,
            text="Output format:",
            font=("Segoe UI", 10),
            fg=TEXT,
            bg=BG,
        ).pack(side="left", padx=(0, 8))

        self._format_var = tk.StringVar(value="json")
        for label, value in (("JSON", "json"), ("Markdown", "md"), ("Both", "both"), ("Tables CSV", "csv"), ("Tables Excel", "xlsx")):
            tk.Radiobutton(
                fmt_frame,
                text=label,
                value=value,
                variable=self._format_var,
                font=("Segoe UI", 10),
                fg=TEXT,
                bg=BG,
                selectcolor=SURFACE,
                activebackground=BG,
                activeforeground=TEXT,
                highlightthickness=0,
            ).pack(side="left", padx=(0, 12))

        # --- Convert button ---
        conv_frame = tk.Frame(self._content, bg=BG)
        conv_frame.grid(row=5, column=0, pady=10)
        self._convert_btn = self._make_button(
            conv_frame, "Convert", self._start_conversion, width=20, big=True
        )
        self._convert_btn.pack()
        self._ocr_var = tk.BooleanVar(value=True)
        tk.Checkbutton(conv_frame, text="Auto OCR missing text and embedded images (slower)",
                       variable=self._ocr_var, bg=BG, fg=TEXT, selectcolor=SURFACE).pack()
        page_frame = tk.Frame(conv_frame, bg=BG)
        page_frame.pack(pady=4)
        tk.Label(page_frame, text="PDF pages (blank = all):", bg=BG, fg=TEXT).pack(side="left")
        tk.Label(page_frame, text="OCR workers:", bg=BG, fg=TEXT).pack(side="left", padx=(8, 0))
        self._ocr_workers_var = tk.StringVar(value="1" if os.environ.get("PDF_RAG_OCR_DEVICE", "cpu").startswith("gpu") else "2")
        ttk.Combobox(page_frame, textvariable=self._ocr_workers_var, values=("1",) if os.environ.get("PDF_RAG_OCR_DEVICE", "cpu").startswith("gpu") else ("1", "2"), state="readonly", width=3).pack(side="left", padx=4)
        self._pages_var = tk.StringVar()
        tk.Entry(page_frame, textvariable=self._pages_var, width=18).pack(side="left", padx=8)


        self._status_var = tk.StringVar(value="Status: Ready")
        self._status_label = tk.Label(
            conv_frame,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            fg=SUBTEXT,
            bg=BG,
        )
        self._status_label.pack(pady=(6, 0))

        # Progress bar (hidden until conversion starts)
        self._progress = ttk.Progressbar(self._content, mode="indeterminate", length=400)

        # --- Action bar (hidden until conversion completes) ---
        self._action_bar = tk.Frame(self._content, bg=SURFACE, pady=8)
        # Not gridded yet — shown in _on_done
        self._action_bar.columnconfigure(0, weight=1)

        tk.Label(
            self._action_bar, text="Output ready:",
            font=("Segoe UI", 9, "bold"), fg=SUBTEXT, bg=SURFACE,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(2, 4))

        self._open_folder_btn = self._make_button(
            self._action_bar, "Open output folder",
            self._open_output_folder, width=18, style="flat",
        )
        self._open_folder_btn.grid(row=1, column=0, padx=(12, 4), pady=4, sticky="e")

        self._save_as_btn = self._make_button(
            self._action_bar, "Save copies to…",
            self._save_copies, width=18,
        )
        self._save_as_btn.grid(row=1, column=1, padx=4, pady=4)

        tk.Label(
            self._action_bar,
            text=(
                "Save copies to… creates duplicate output file(s) in another location. "
                "Your original output files remain in the selected output folder."
            ),
            font=("Segoe UI", 8),
            fg=SUBTEXT,
            bg=SURFACE,
            wraplength=640,
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(2, 2))

        # --- Log area ---
        log_frame = tk.Frame(self._content, bg=BG)
        log_frame.grid(row=7, column=0, sticky="nsew", padx=24, pady=(0, 16))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        tk.Label(
            log_frame, text="Log", font=("Segoe UI", 9, "bold"),
            fg=SUBTEXT, bg=BG, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        self._log = scrolledtext.ScrolledText(
            log_frame, state="disabled", wrap="word",
            font=("Consolas", 9), bg="#13131f", fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0,
        )
        self._log.grid(row=1, column=0, sticky="nsew")

        # Colour tags for log
        self._log.tag_config("normal", foreground=TEXT)
        self._log.tag_config("err",    foreground=ERROR)
        self._log.tag_config("ok",     foreground=SUCCESS)

    # ------------------------------------------------------------------
    # Drop-zone drawing
    # ------------------------------------------------------------------

    def _draw_drop_zone(self, hover: bool = False) -> None:
        self._drop_zone.delete("all")
        w = self._drop_zone.winfo_width() or 680
        h = 150
        color = DROP_HOV if hover else DROP_IDLE

        # Dashed border (simulated with rectangle + dash)
        self._drop_zone.create_rectangle(
            8, 8, w - 8, h - 8,
            outline=color, width=2, dash=(6, 4),
        )

        icon_color = ACCENT if hover else SUBTEXT
        cy = h // 2 - 10

        # Simple "↓" arrow icon
        self._drop_zone.create_text(
            w // 2, cy - 4,
            text="⬇", font=("Segoe UI", 22), fill=icon_color,
        )
        self._drop_zone.create_text(
            w // 2, cy + 28,
            text="Drag & drop PDF(s) here  ·  or click to browse",
            font=("Segoe UI", 10), fill=icon_color,
        )

        # Keep selected files visible inside the drop window.
        if self._pdf_paths:
            names = [Path(p).name for p in self._pdf_paths]
            if len(names) == 1:
                status = names[0]
            else:
                preview = ", ".join(names[:2])
                remaining = len(names) - 2
                status = preview if remaining <= 0 else f"{preview}  (+{remaining} more)"

            max_chars = max(24, (w - 48) // 8)
            if len(status) > max_chars:
                status = status[: max_chars - 3] + "..."

            self._drop_zone.create_text(
                w // 2, h - 28,
                text=f"Selected: {status}",
                font=("Segoe UI", 9, "bold"), fill=TEXT,
                width=w - 28,
            )

        if not _HAS_DND:
            self._drop_zone.create_text(
                w // 2, cy + 48,
                text="(install tkinterdnd2 to enable drag-and-drop)",
                font=("Segoe UI", 8), fill=SUBTEXT,
            )

    def _zone_hover(self, state: bool) -> None:
        self._drop_zone.configure(
            highlightbackground=DROP_HOV if state else DROP_IDLE
        )
        self.after(1, lambda: self._draw_drop_zone(state))

    # ------------------------------------------------------------------
    # Widget factory
    # ------------------------------------------------------------------

    def _make_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        width: int = 12,
        big: bool = False,
        style: str = "accent",
    ) -> tk.Button:
        bg = ACCENT if style == "accent" else SURFACE
        font_size = 12 if big else 10
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", font_size, "bold" if big else "normal"),
            bg=bg, fg=TEXT, activebackground=ACCENT_H, activeforeground=TEXT,
            relief="flat", bd=0, padx=14, pady=8 if big else 4,
            width=width, cursor="hand2",
        )
        # Hover effect
        btn.bind("<Enter>", lambda _e, b=btn: b.configure(bg=ACCENT_H))
        btn.bind("<Leave>", lambda _e, b=btn, c=bg: b.configure(bg=c))
        return btn

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------

    def _browse_pdf(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF file(s)",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if paths:
            self._add_pdfs(list(paths))

    def _browse_out(self) -> None:
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self._out_var.set(d)

    def _on_drop(self, event) -> None:  # type: ignore[override]
        paths = _clean_dnd_path(event.data)
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        if pdfs:
            self._add_pdfs(pdfs)
        else:
            messagebox.showwarning("No PDFs", "Only .pdf files are accepted.")
        self._zone_hover(False)

    def _add_pdfs(self, paths: list[str]) -> None:
        for p in paths:
            if p not in self._pdf_paths:
                self._pdf_paths.append(p)
        self._draw_drop_zone()

    def _clear_selected_pdfs(self) -> None:
        self._pdf_paths.clear()
        self._draw_drop_zone()

    def _clear_all_fields(self) -> None:
        """Clear all user-input fields and reset output actions state."""
        self._clear_selected_pdfs()
        self._out_var.set("")
        self._name_var.set("")
        self._last_output_paths = []
        self._last_out_dir = ""
        self._action_bar.grid_forget()
        self._set_status_ready()

    def _spin_status(self) -> None:
        """Animate a simple ASCII spinner while conversion is running."""
        if not self._running:
            self._spinner_after_id = None
            return
        ch = self._spinner_chars[self._spinner_idx]
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_chars)
        self._status_var.set(f"Status: Converting... {ch}")
        self._spinner_after_id = self.after(120, self._spin_status)

    def _start_status_spinner(self) -> None:
        self._spinner_idx = 0
        self._status_label.configure(fg=WARNING)
        self._spin_status()

    def _stop_status_spinner(self) -> None:
        if self._spinner_after_id is not None:
            try:
                self.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None

    def _set_status_ready(self) -> None:
        self._stop_status_spinner()
        self._status_label.configure(fg=SUCCESS)
        self._status_var.set("Status: Ready. Output available.")

    def _set_status_error(self) -> None:
        self._stop_status_spinner()
        self._status_label.configure(fg=ERROR)
        self._status_var.set("Status: Finished with errors. Check log.")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _start_conversion(self) -> None:
        if self._running:
            return
        if not self._pdf_paths:
            messagebox.showwarning("No files", "Please select at least one PDF.")
            return

        out_dir = self._out_var.get().strip()
        custom_name = self._name_var.get().strip()

        missing_fields: list[str] = []
        if not out_dir:
            missing_fields.append("Output folder")
        if not custom_name:
            missing_fields.append("Output file name")

        if missing_fields:
            fields = ", ".join(missing_fields)
            messagebox.showwarning(
                "Missing required fields",
                (
                    f"Please fill: {fields}.\n\n"
                    "Output file name is required. For multi-PDF conversion, "
                    "it is used as a base name and chapter number is appended."
                ),
            )
            return

        self._running = True
        self._convert_btn.configure(state="disabled", text="Converting…")
        self._progress.grid(row=5, column=0, pady=(0, 6))
        self._progress.start(12)
        self._start_status_spinner()

        output_format = self._format_var.get()

        # Run in background thread so the UI stays responsive
        threading.Thread(
            target=self._run_pipeline,
            args=(list(self._pdf_paths), out_dir, custom_name, output_format,
                  "paddle" if self._ocr_var.get() else "native", self._pages_var.get(), int(self._ocr_workers_var.get())),
            daemon=True,
        ).start()

    def _run_pipeline(
        self,
        pdf_paths: list[str],
        out_dir: str,
        custom_name: str,
        output_format: str,
        engine: str = "native",
        pages: str = "",
        ocr_workers: int = 1,
    ) -> None:
        success, failed = 0, 0
        output_paths: list[str] = []
        for pdf in pdf_paths:
            try:
                if len(pdf_paths) == 1:
                    output_name = custom_name
                else:
                    chapter_num = detect_chapter_number(pdf)
                    output_name = f"{custom_name}_chapter_{chapter_num}"

                out = process_pdf(
                    pdf,
                    out_dir,
                    output_filename=output_name,
                    doc_type="auto",
                    output_format=output_format,
                    engine=engine,
                    pages=pages,
                    ocr_workers=ocr_workers,
                )
                output_paths.extend(out)
                success += 1
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: {Path(pdf).name}: {exc}", file=sys.stderr)
                failed += 1

        # Back to main thread
        self.after(0, self._on_done, success, failed, output_paths, out_dir)

    def _on_done(
        self, success: int, failed: int,
        output_paths: list[str], out_dir: str,
    ) -> None:
        self._progress.stop()
        self._progress.grid_forget()
        self._convert_btn.configure(state="normal", text="Convert")
        self._running = False
        self._last_output_paths = output_paths
        self._last_out_dir = out_dir

        # After conversion, clear selected PDFs from the drop zone.
        self._clear_selected_pdfs()

        if failed == 0:
            self._set_status_ready()
            msg = f"Done!  {success} file(s) converted successfully."
            self._log_ok(msg)
        else:
            self._set_status_error()
            msg = f"Finished with errors: {success} succeeded, {failed} failed."
            self._log_err(msg)
            messagebox.showerror("Errors", msg)

        # Show action bar whenever at least one file was produced
        if output_paths:
            self._action_bar.grid(row=6, column=0, sticky="ew", padx=24, pady=(0, 6))

    # ------------------------------------------------------------------
    # Post-conversion actions
    # ------------------------------------------------------------------

    def _open_output_folder(self) -> None:
        """Open the output folder in the system file explorer."""
        folder = Path(self._last_out_dir).resolve()
        if folder.exists():
            os.startfile(folder)  # Windows; harmless on this platform
        else:
            messagebox.showwarning("Not found", f"Folder not found:\n{folder}")

    def _save_copies(self) -> None:
        """Copy the generated JSON file(s) to a user-chosen location."""
        paths = self._last_output_paths
        if not paths:
            messagebox.showwarning("Nothing to save", "No output files available.")
            return

        if len(paths) == 1:
            # Single file → Save As dialog
            src = Path(paths[0])
            suffix = src.suffix.lower()
            filetypes = (
                [("Markdown files", "*.md"), ("All files", "*.*")]
                if suffix == ".md"
                else [("JSON files", "*.json"), ("All files", "*.*")]
            )
            dest = filedialog.asksaveasfilename(
                title="Save file as…",
                initialfile=src.name,
                defaultextension=suffix,
                filetypes=filetypes,
            )
            if not dest:
                return
            shutil.copy2(src, dest)
            self._log_ok(f"Saved: {dest}")
            messagebox.showinfo("Saved", f"File saved to:\n{dest}")
        else:
            # Multiple files → choose destination folder
            dest_dir = filedialog.askdirectory(title="Save copies to folder…")
            if not dest_dir:
                return
            dest_folder = Path(dest_dir)
            copied: list[str] = []
            for src in paths:
                dst = dest_folder / Path(src).name
                shutil.copy2(src, dst)
                copied.append(str(dst))
                self._log_ok(f"Saved: {dst}")
            messagebox.showinfo(
                "Saved",
                f"{len(copied)} file(s) copied to:\n{dest_dir}",
            )

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_ok(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert(tk.END, text + "\n", "ok")
        self._log.see(tk.END)
        self._log.configure(state="disabled")

    def _log_err(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert(tk.END, text + "\n", "err")
        self._log.see(tk.END)
        self._log.configure(state="disabled")

    # ------------------------------------------------------------------
    # Stdout/Stderr redirect
    # ------------------------------------------------------------------

    def _redirect_output(self) -> None:
        sys.stdout = _TextRedirect(self._log, "normal")
        sys.stderr = _TextRedirect(self._log, "err")

    # ------------------------------------------------------------------
    # Window centering
    # ------------------------------------------------------------------

    def _center_window(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _enable_high_dpi()
    _hide_console_window()
    app = App()
    app.mainloop()

import customtkinter as ctk
from .theme import COLORS, FONTS, RADII

class DownloadsWindow(ctk.CTkToplevel):
    def __init__(self, master, on_cancel=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Downloads")
        self.geometry("440x320")
        self.configure(fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.on_cancel = on_cancel
        
        # Hide on close
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Active Downloads",
            label_font=FONTS["section"],
            label_text_color=COLORS["text"],
            label_fg_color=COLORS["panel"],
            fg_color=COLORS["panel"],
            corner_radius=RADII["card"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=16)
        
        self.active_downloads = {} # id -> widgets dict
        self.withdraw()

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.attributes('-topmost', True) # Keep on top briefly
        self.after(100, lambda: self.attributes('-topmost', False))

    def _handle_cancel(self, d_id):
        widgets = self.active_downloads.get(d_id)
        if widgets and widgets.get("cancel_btn"):
            widgets["cancel_btn"].configure(text="Cancelling...", state="disabled")
        if self.on_cancel:
            self.on_cancel(d_id)

    def add_download(self, d_id, filename):
        if d_id in self.active_downloads:
            return # Already tracking
            
        # Create row
        row = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=COLORS["panel_alt"],
            corner_radius=RADII["button"],
            border_width=1,
            border_color=COLORS["border"],
        )
        row.pack(fill="x", pady=6, padx=6)
        
        # Filename
        ctk.CTkLabel(
            row,
            text=filename,
            anchor="w",
            font=FONTS["body_bold"],
            text_color=COLORS["text"],
        ).pack(side="top", fill="x", padx=10, pady=(8, 0))
        
        # Progress Container
        p_frame = ctk.CTkFrame(row, fg_color="transparent")
        p_frame.pack(fill="x", padx=10, pady=8)
        
        # Progress Bar
        pbar = ctk.CTkProgressBar(
            p_frame,
            progress_color=COLORS["accent"],
        )
        pbar.set(0)
        pbar.pack(side="left", fill="x", expand=True)
        
        # Cancel Button
        cancel_btn = None
        if self.on_cancel:
            cancel_btn = ctk.CTkButton(
                p_frame,
                text="Cancel",
                width=76,
                height=26,
                command=lambda: self._handle_cancel(d_id),
                fg_color=COLORS["panel_highlight"],
                hover_color=COLORS["border"],
                text_color=COLORS["text"],
                corner_radius=RADII["button"],
                font=FONTS["small_bold"],
            )
            cancel_btn.pack(side="right", padx=6)

        # Status Label
        lbl_status = ctk.CTkLabel(
            p_frame,
            text="0%",
            width=44,
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        )
        lbl_status.pack(side="right", padx=6)
        
        self.active_downloads[d_id] = {
            "row": row,
            "pbar": pbar,
            "lbl": lbl_status,
            "cancel_btn": cancel_btn
        }
        self.show_window()

    def update_download(self, d_id, progress):
        if d_id in self.active_downloads:
            widgets = self.active_downloads[d_id]
            # progress is 0-100
            val = progress / 100.0
            widgets["pbar"].set(val)
            widgets["lbl"].configure(text=f"{int(progress)}%")

    def finish_download(self, d_id, success, message=""):
        if d_id in self.active_downloads:
            widgets = self.active_downloads[d_id]
            status_text = "Done" if success else "Error"
            status_color = COLORS["success"] if success else COLORS["danger"]
            if not success and message and "cancel" in message.lower():
                status_text = "Cancelled"
                status_color = COLORS["warning"]

            if success:
                widgets["pbar"].set(1)
            elif status_text == "Error":
                widgets["pbar"].set(0)

            widgets["pbar"].configure(progress_color=status_color)
            widgets["lbl"].configure(text=status_text)

            if widgets.get("cancel_btn"):
                widgets["cancel_btn"].configure(state="disabled")
            
            # Optional: Remove after delay or keep?
            # Keeping it allows user to see history.

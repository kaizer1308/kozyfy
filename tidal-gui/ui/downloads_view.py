import customtkinter as ctk

class DownloadsWindow(ctk.CTkToplevel):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Downloads")
        self.geometry("400x300")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Hide on close
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Active Downloads")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.active_downloads = {} # id -> widgets dict
        self.withdraw()

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.attributes('-topmost', True) # Keep on top briefly
        self.after(100, lambda: self.attributes('-topmost', False))

    def add_download(self, d_id, filename):
        if d_id in self.active_downloads:
            return # Already tracking
            
        # Create row
        row = ctk.CTkFrame(self.scroll_frame)
        row.pack(fill="x", pady=2)
        
        # Filename
        ctk.CTkLabel(row, text=filename, anchor="w", font=("Arial", 11, "bold")).pack(side="top", fill="x", padx=5, pady=(5,0))
        
        # Progress Container
        p_frame = ctk.CTkFrame(row, fg_color="transparent")
        p_frame.pack(fill="x", padx=5, pady=5)
        
        # Progress Bar
        pbar = ctk.CTkProgressBar(p_frame)
        pbar.set(0)
        pbar.pack(side="left", fill="x", expand=True)
        
        # Status Label
        lbl_status = ctk.CTkLabel(p_frame, text="0%", width=40, font=("Arial", 10))
        lbl_status.pack(side="right", padx=5)
        
        self.active_downloads[d_id] = {
            "row": row,
            "pbar": pbar,
            "lbl": lbl_status
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
            widgets["pbar"].set(1 if success else 0)
            widgets["pbar"].configure(progress_color="#00FF00" if success else "#FF0000")
            widgets["lbl"].configure(text="Done" if success else "Error")
            
            # Optional: Remove after delay or keep?
            # Keeping it allows user to see history.

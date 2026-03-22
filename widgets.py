import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

def show_error_popup(title, message):
    messagebox.showerror(title, message)

class NeonLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(master, text=text, font=("Orbitron", 12, "bold"), text_color="#00ffe7", **kwargs)

class GlassPanel(ctk.CTkFrame):
    def __init__(self, master, width=200, height=200, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)
        self.configure(corner_radius=12, fg_color="#1a1f2b", border_width=2, border_color="#00ffe7")
        self._add_tactical_accents()

    def _add_tactical_accents(self):
        self.accent_tl = tk.Frame(self, bg="#00ffe7", width=15, height=2)
        self.accent_tl.place(x=0, y=0)
        self.accent_tlh = tk.Frame(self, bg="#00ffe7", width=2, height=15)
        self.accent_tlh.place(x=0, y=0)

        self.accent_br = tk.Frame(self, bg="#00ffe7", width=15, height=2)
        self.accent_br.place(relx=1, rely=1, x=-15, y=-2)
        self.accent_brh = tk.Frame(self, bg="#00ffe7", width=2, height=15)
        self.accent_brh.place(relx=1, rely=1, x=-2, y=-15)

class SetupWizard(ctk.CTk):
    def __init__(self, callback, interfaces):
        super().__init__()
        self.callback = callback
        self.title("WiFi CyberScan // SETUP")
        self.geometry("400x300")
        self.configure(fg_color="#10131a")
        
        ctk.CTkLabel(self, text="INITIALIZE PROTOCOL", font=("Orbitron", 18, "bold"), text_color="#00ffe7").pack(pady=20)
        
        self.iface_var = ctk.StringVar(value=interfaces[0] if interfaces else "")
        ctk.CTkLabel(self, text="SELECT INTERFACE", text_color="#0fffc0").pack(pady=5)
        self.iface_menu = ctk.CTkOptionMenu(self, values=interfaces, variable=self.iface_var, fg_color="#181c24", button_color="#00ffe7")
        self.iface_menu.pack(pady=5)
        
        self.op_name = ctk.CTkEntry(self, placeholder_text="OPERATOR NAME", fg_color="#181c24", border_color="#00ffe7")
        self.op_name.pack(pady=10)
        
        ctk.CTkButton(self, text="LAUNCH TERMINAL", fg_color="#00ffe7", text_color="#10131a", command=self._on_launch).pack(pady=20)

    def _on_launch(self):
        iface = self.iface_var.get()
        op = self.op_name.get() or "ANONYMOUS"
        self.destroy()
        self.callback(iface, op)

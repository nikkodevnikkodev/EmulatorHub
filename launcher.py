import json
import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import urllib.request
import shutil

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

APP_NAME = "Emulator & Game Hub"
APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "EmulatorLauncher"
COVERS_DIR = APP_DIR / "covers"
DATA_FILE = APP_DIR / "launcher_data.json"

COMMON_DIRS = [
    Path("C:/Emulation"), Path("C:/Emulators"), Path("D:/Emulation"),
    Path("D:/Emulatoren"), Path("D:/Emulators"),
    Path.home() / "Emulators", Path.home() / "Emulatoren",
    Path.home() / "Documents" / "Emulators",
    Path.home() / "Documents" / "Emulatoren",
    Path("C:/Program Files"), Path("C:/Program Files (x86)"),
]

EMU_NAMES = {
    "PCSX2": ["pcsx2-qt.exe", "pcsx2.exe"],
    "Dolphin": ["Dolphin.exe"],
    "RPCS3": ["rpcs3.exe"],
    "Cemu": ["Cemu.exe"],
    "RetroArch": ["retroarch.exe"],
    "PPSSPP": ["PPSSPPWindows64.exe", "PPSSPPWindows.exe"],
    "Citra": ["citra-qt.exe", "citra.exe"],
    "Ryujinx": ["Ryujinx.exe"],
    "Yuzu": ["yuzu.exe"],
    "DuckStation": ["duckstation-qt-x64-ReleaseLTCG.exe", "duckstation.exe"],
    "MAME": ["mame.exe"],
    "melonDS": ["melonDS.exe"],
}

def load_data():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("emulators", [])
                data.setdefault("games", [])
                data.setdefault("folders", [])
                return data
        except Exception:
            pass
    return {"emulators": [], "games": [], "folders": []}

def save_data(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False, width=160, height=38):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, cursor="hand2")
        self.command = command
        self.primary = primary
        self.text = text
        self.width = width
        self.height = height
        
        self.bg_normal = "#6366f1" if primary else "#1e293b"
        self.bg_hover = "#818cf8" if primary else "#334155"
        self.fg_color = "#ffffff"
        
        self.draw()
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", lambda e: self.command())

    def draw(self):
        self.delete("all")
        r = 8
        self.create_rounded_rect(0, 0, self.width, self.height, r, fill=self.bg_normal, outline="")
        self.create_text(self.width / 2, self.height / 2, text=self.text, fill=self.fg_color, font=("Segoe UI", 9, "bold"))

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def on_enter(self, event):
        self.delete("all")
        self.create_rounded_rect(0, 0, self.width, self.height, 8, fill=self.bg_hover, outline="")
        self.create_text(self.width / 2, self.height / 2, text=self.text, fill=self.fg_color, font=("Segoe UI", 9, "bold"))

    def on_leave(self, event):
        self.draw()

class Launcher(tk.Tk):
    BG = "#07090e"
    PANEL = "#0f172a"
    CARD_BG = "#131c31"
    SELECTED_CARD_BG = "#1b2a4a"
    TEXT = "#f8fafc"
    MUTED = "#94a3b8"
    ACCENT = "#8b5cf6"
    GREEN = "#10b981"

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1220x780")
        self.minsize(950, 650)
        self.configure(bg=self.BG)
        self.data = load_data()
        
        self.selected_emu_idx = None
        self.selected_game_idx = None
        self.selected_folder_idx = None
        self.current_tab = "emu"
        
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=self.BG, padx=30, pady=20)
        header.pack(fill="x")
        
        title_frame = tk.Frame(header, bg=self.BG)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="⚡ EMULATOR & GAME HUB", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(title_frame, text="Manage emulators, launch games directly & download covers", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        self.status = tk.Label(header, text="● Ready", bg=self.PANEL, fg=self.GREEN,
                               font=("Segoe UI", 9, "bold"), padx=14, pady=8)
        self.status.pack(side="right")

        bar = tk.Frame(self, bg=self.PANEL, padx=20, pady=12)
        bar.pack(fill="x", padx=30, pady=(0, 15))
        
        ModernButton(bar, "🔍 Scan Emulators", self.auto_scan, primary=True, width=170).pack(side="right", padx=(10, 0))
        ModernButton(bar, "➕ Add Game", self.add_game, width=140).pack(side="right", padx=(10, 0))
        ModernButton(bar, "📁 Add Folder", self.add_folder, width=140).pack(side="right", padx=(10, 0))
        ModernButton(bar, "➕ Add Emulator", self.add_emulator, width=160).pack(side="right")

        footer_bar = tk.Frame(self, bg=self.PANEL, padx=20, pady=12)
        footer_bar.pack(fill="x", side="bottom")
        
        self.action_btn_frame = tk.Frame(footer_bar, bg=self.PANEL)
        self.action_btn_frame.pack(side="left")
        
        tk.Label(footer_bar, text="Click a card to select. Double-click launches directly.",
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="right")

        nav_frame = tk.Frame(self, bg=self.BG, padx=30)
        nav_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_tab_emu = tk.Button(nav_frame, text="🎮 Emulators", command=lambda: self.switch_tab("emu"),
                                     bg=self.PANEL, fg=self.TEXT, relief="flat", bd=0, padx=20, pady=10, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.btn_tab_emu.pack(side="left", padx=(0, 10))

        self.btn_tab_games = tk.Button(nav_frame, text="🎯 Game Library", command=lambda: self.switch_tab("games"),
                                       bg=self.BG, fg=self.MUTED, relief="flat", bd=0, padx=20, pady=10, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.btn_tab_games.pack(side="left", padx=(0, 10))
        
        self.btn_tab_folder = tk.Button(nav_frame, text="📂 Folders", command=lambda: self.switch_tab("folder"),
                                        bg=self.BG, fg=self.MUTED, relief="flat", bd=0, padx=20, pady=10, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.btn_tab_folder.pack(side="left")

        content_container = tk.Frame(self, bg=self.BG, padx=30)
        content_container.pack(fill="both", expand=True, pady=(0, 15))

        self.emu_frame_outer = self.create_scrollable_area(content_container)
        self.games_frame_outer = self.create_scrollable_area(content_container)
        self.folder_frame_outer = self.create_scrollable_area(content_container)

        self.switch_tab("emu")

    def create_scrollable_area(self, parent):
        outer = tk.Frame(parent, bg=self.BG)
        canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        outer.canvas_frame = scrollable_frame
        return outer

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.btn_tab_emu.configure(bg=self.PANEL if tab_name=="emu" else self.BG, fg=self.TEXT if tab_name=="emu" else self.MUTED)
        self.btn_tab_games.configure(bg=self.PANEL if tab_name=="games" else self.BG, fg=self.TEXT if tab_name=="games" else self.MUTED)
        self.btn_tab_folder.configure(bg=self.PANEL if tab_name=="folder" else self.BG, fg=self.TEXT if tab_name=="folder" else self.MUTED)

        self.emu_frame_outer.pack_forget()
        self.games_frame_outer.pack_forget()
        self.folder_frame_outer.pack_forget()

        if tab_name == "emu":
            self.emu_frame_outer.pack(fill="both", expand=True)
        elif tab_name == "games":
            self.games_frame_outer.pack(fill="both", expand=True)
        else:
            self.folder_frame_outer.pack(fill="both", expand=True)

        self.update_footer_buttons(tab_name)

    def update_footer_buttons(self, mode):
        for widget in self.action_btn_frame.winfo_children():
            widget.destroy()

        if mode == "emu":
            ModernButton(self.action_btn_frame, "▶ Launch", self.launch_selected_emu, primary=True, width=110).pack(side="left", padx=(0, 8))
            ModernButton(self.action_btn_frame, "✏️ Rename", self.rename_emulator, width=110).pack(side="left", padx=(0, 8))
            ModernButton(self.action_btn_frame, "📁 Edit Path", self.edit_emulator, width=110).pack(side="left", padx=(0, 8))
            ModernButton(self.action_btn_frame, "🗑️ Remove", self.remove_emulator, width=100).pack(side="left")
        elif mode == "games":
            ModernButton(self.action_btn_frame, "▶ Launch Game", self.launch_selected_game, primary=True, width=130).pack(side="left", padx=(0, 6))
            ModernButton(self.action_btn_frame, "✏️ Path", self.edit_game_path, width=85).pack(side="left", padx=(0, 6))
            ModernButton(self.action_btn_frame, "🖼️ Pick Cover", self.set_custom_cover, width=120).pack(side="left", padx=(0, 6))
            ModernButton(self.action_btn_frame, "🌐 Fetch Cover", self.fetch_game_cover, width=120).pack(side="left", padx=(0, 6))
            ModernButton(self.action_btn_frame, "🗑️ Remove", self.remove_game, width=100).pack(side="left")
        else:
            ModernButton(self.action_btn_frame, "📂 Open Folder", self.open_selected_folder, primary=True, width=140).pack(side="left", padx=(0, 10))
            ModernButton(self.action_btn_frame, "🗑️ Remove", self.remove_folder, width=110).pack(side="left")

    def refresh(self):
        emu_container = self.emu_frame_outer.canvas_frame
        for w in emu_container.winfo_children(): w.destroy()
        emulators = self.data.get("emulators", [])
        if not emulators:
            tk.Label(emu_container, text="No emulators found. Use „Scan Emulators“ above.", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 11), pady=40).pack(anchor="w")
        else:
            grid_e = tk.Frame(emu_container, bg=self.BG)
            grid_e.pack(fill="both", expand=True)
            for i, emu in enumerate(emulators):
                self.create_card(grid_e, i, emu.get("name", "Emulator"), emu.get("path", ""), "emu")

        games_container = self.games_frame_outer.canvas_frame
        for w in games_container.winfo_children(): w.destroy()
        games = self.data.get("games", [])
        if not games:
            tk.Label(games_container, text="No games added. Click „Add Game“.", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 11), pady=40).pack(anchor="w")
        else:
            grid_g = tk.Frame(games_container, bg=self.BG)
            grid_g.pack(fill="both", expand=True)
            for i, game in enumerate(games):
                self.create_game_card(grid_g, i, game)

        folder_container = self.folder_frame_outer.canvas_frame
        for w in folder_container.winfo_children(): w.destroy()
        folders = self.data.get("folders", [])
        if not folders:
            tk.Label(folder_container, text="No folders added.", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 11), pady=40).pack(anchor="w")
        else:
            grid_f = tk.Frame(folder_container, bg=self.BG)
            grid_f.pack(fill="both", expand=True)
            for i, folder in enumerate(folders):
                self.create_card(grid_f, i, folder.get("name", "Folder"), folder.get("path", ""), "folder")

        save_data(self.data)

    def create_card(self, parent, index, title, path_str, kind):
        row = index // 2
        col = index % 2

        is_selected = (self.selected_emu_idx == index) if kind == "emu" else (self.selected_folder_idx == index)
        current_bg = self.SELECTED_CARD_BG if is_selected else self.CARD_BG

        card = tk.Frame(parent, bg=current_bg, relief="flat", bd=0)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        parent.grid_columnconfigure(0, weight=1, uniform="col")
        parent.grid_columnconfigure(1, weight=1, uniform="col")

        if is_selected:
            indicator = tk.Frame(card, bg=self.ACCENT, width=4)
            indicator.pack(side="left", fill="y")

        inner_pad = tk.Frame(card, bg=current_bg, padx=16, pady=14)
        inner_pad.pack(side="left", fill="both", expand=True)

        title_lbl = tk.Label(inner_pad, text=title, bg=current_bg, fg=self.TEXT, font=("Segoe UI", 12, "bold"))
        title_lbl.pack(anchor="w")

        path_lbl = tk.Label(inner_pad, text=path_str, bg=current_bg, fg=self.MUTED, font=("Segoe UI", 8), wraplength=420, justify="left")
        path_lbl.pack(anchor="w", pady=(4, 0))

        def select_card(e):
            if kind == "emu":
                self.selected_emu_idx = index
            else:
                self.selected_folder_idx = index
            self.refresh()

        for widget in (card, inner_pad, title_lbl, path_lbl):
            widget.bind("<Button-1>", select_card)
            widget.bind("<Double-Button-1>", lambda e, k=kind: self.launch_selected_emu() if k=="emu" else self.open_selected_folder())

    def create_game_card(self, parent, index, game):
        row = index // 2
        col = index % 2

        is_selected = (self.selected_game_idx == index)
        current_bg = self.SELECTED_CARD_BG if is_selected else self.CARD_BG

        card = tk.Frame(parent, bg=current_bg, relief="flat", bd=0)
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        parent.grid_columnconfigure(0, weight=1, uniform="col")
        parent.grid_columnconfigure(1, weight=1, uniform="col")

        if is_selected:
            indicator = tk.Frame(card, bg=self.ACCENT, width=4)
            indicator.pack(side="left", fill="y")

        main_layout = tk.Frame(card, bg=current_bg, padx=12, pady=12)
        main_layout.pack(side="left", fill="both", expand=True)

        cover_canvas = tk.Canvas(main_layout, width=65, height=90, bg="#0b1020", highlightthickness=0)
        cover_canvas.pack(side="left", padx=(0, 12))
        
        cover_path = game.get("cover_path")
        loaded_img = False

        if HAS_PIL and cover_path and Path(cover_path).is_file():
            try:
                image = Image.open(cover_path)
                image = image.resize((65, 90), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                cover_canvas.create_image(0, 0, anchor="nw", image=photo)
                cover_canvas.image = photo
                loaded_img = True
            except Exception:
                pass

        if not loaded_img:
            cover_canvas.create_text(32, 45, text="🎮", fill=self.TEXT, font=("Segoe UI", 16))

        info_frame = tk.Frame(main_layout, bg=current_bg)
        info_frame.pack(side="left", fill="both", expand=True)

        title_lbl = tk.Label(info_frame, text=game.get("name", "Game"), bg=current_bg, fg=self.TEXT, font=("Segoe UI", 11, "bold"))
        title_lbl.pack(anchor="w")

        emu_name = "No Emulator"
        emu_idx = game.get("emulator_idx")
        emus = self.data.get("emulators", [])
        if emu_idx is not None and 0 <= emu_idx < len(emus):
            emu_name = emus[emu_idx].get("name", "Emulator")

        emu_lbl = tk.Label(info_frame, text=f"Emulator: {emu_name}", bg=current_bg, fg=self.ACCENT, font=("Segoe UI", 9))
        emu_lbl.pack(anchor="w", pady=(2, 0))

        path_lbl = tk.Label(info_frame, text=game.get("path", ""), bg=current_bg, fg=self.MUTED, font=("Segoe UI", 8), wraplength=340, justify="left")
        path_lbl.pack(anchor="w", pady=(4, 0))

        def select_card(e):
            self.selected_game_idx = index
            self.refresh()

        for widget in (card, main_layout, info_frame, title_lbl, emu_lbl, path_lbl):
            widget.bind("<Button-1>", select_card)
            widget.bind("<Double-Button-1>", lambda e: self.launch_selected_game())

    def set_status(self, text):
        self.status.configure(text="● " + text)

    def auto_scan(self):
        found = []
        existing = {os.path.normcase(os.path.abspath(e.get("path", "")))
                    for e in self.data.get("emulators", [])}
        candidates = []
        for root in COMMON_DIRS:
            if root.exists():
                candidates.append(root)
                try:
                    for child in root.iterdir():
                        if child.is_dir():
                            candidates.append(child)
                            try:
                                for grandchild in child.iterdir():
                                    if grandchild.is_dir():
                                        candidates.append(grandchild)
                            except (PermissionError, OSError):
                                pass
                except (PermissionError, OSError):
                    pass
        for label, exe_names in EMU_NAMES.items():
            match = None
            for folder in candidates:
                for exe in exe_names:
                    p = folder / exe
                    if p.is_file():
                        match = p
                        break
                if match:
                    break
            if match:
                norm = os.path.normcase(os.path.abspath(str(match)))
                if norm not in existing:
                    found.append({"name": label, "path": str(match)})
                    existing.add(norm)
        self.data.setdefault("emulators", []).extend(found)
        self.refresh()
        self.set_status(f"{len(found)} new emulator(s) found")
        messagebox.showinfo("Scan Completed", f"{len(found)} new emulator(s) found.")

    def add_emulator(self):
        path = filedialog.askopenfilename(title="Select Emulator Executable",
                    filetypes=[("Windows Programs", "*.exe"), ("All Files", "*.*")])
        if not path:
            return
        name = Path(path).stem
        self.data.setdefault("emulators", []).append({"name": name, "path": path})
        self.refresh()
        self.set_status(f"{name} added")

    def rename_emulator(self):
        if self.selected_emu_idx is None:
            messagebox.showinfo("Selection", "Please select an emulator first.")
            return
        emus = self.data.get("emulators", [])
        if not (0 <= self.selected_emu_idx < len(emus)):
            return
        current_name = emus[self.selected_emu_idx].get("name", "")
        new_name = simpledialog.askstring("Rename Emulator", "New name for the emulator:", initialvalue=current_name)
        if new_name:
            self.data["emulators"][self.selected_emu_idx]["name"] = new_name.strip()
            self.refresh()
            self.set_status(f"Renamed to '{new_name}'")

    def edit_emulator(self):
        if self.selected_emu_idx is None:
            messagebox.showinfo("Selection", "Please select an emulator first.")
            return
        path = filedialog.askopenfilename(title="Select New Emulator EXE",
                    filetypes=[("Windows Programs", "*.exe"), ("All Files", "*.*")])
        if not path:
            return
        self.data["emulators"][self.selected_emu_idx]["path"] = path
        self.refresh()
        self.set_status("Emulator path updated")

    def remove_emulator(self):
        if self.selected_emu_idx is None:
            messagebox.showinfo("Selection", "Please select an emulator first.")
            return
        del self.data["emulators"][self.selected_emu_idx]
        self.selected_emu_idx = None
        self.refresh()
        self.set_status("Emulator removed")

    def launch_selected_emu(self):
        if self.selected_emu_idx is None:
            messagebox.showinfo("Selection", "Please select an emulator first.")
            return
        emus = self.data.get("emulators", [])
        if not (0 <= self.selected_emu_idx < len(emus)):
            return
        path = emus[self.selected_emu_idx].get("path", "")
        if not Path(path).is_file():
            messagebox.showerror("Error", "The program file was not found.")
            return
        try:
            subprocess.Popen([path], cwd=str(Path(path).parent))
            self.set_status(f"{emus[self.selected_emu_idx].get('name')} launched")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def add_game(self):
        emus = self.data.get("emulators", [])
        if not emus:
            messagebox.showwarning("No Emulator", "Please add at least one emulator first.")
            return

        path = filedialog.askopenfilename(title="Select Game File (ROM / ISO / EXE)",
                    filetypes=[("Games & ROMs", "*.iso *.rom *.bin *.zip *.rar *.nsp *.chd *.exe"), ("All Files", "*.*")])
        if not path:
            return

        default_name = Path(path).stem
        name = simpledialog.askstring("Add Game", "Game Name:", initialvalue=default_name)
        if not name:
            name = default_name

        win = tk.Toplevel(self)
        win.title("Assign Emulator")
        win.geometry("350x250")
        win.configure(bg=self.BG)
        win.grab_set()

        tk.Label(win, text="Which emulator belongs to this game?", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 10, "bold"), pady=15).pack()

        selected_emu_var = tk.IntVar(value=0)
        for i, emu in enumerate(emus):
            tk.Radiobutton(win, text=emu.get("name"), variable=selected_emu_var, value=i,
                           bg=self.BG, fg=self.TEXT, selectcolor=self.PANEL, font=("Segoe UI", 10)).pack(anchor="w", padx=30, pady=2)

        def save_new_game():
            idx = selected_emu_var.get()
            game_entry = {
                "name": name,
                "path": path,
                "emulator_idx": idx,
                "cover_path": None
            }
            self.data.setdefault("games", []).append(game_entry)
            win.destroy()
            self.refresh()
            self.set_status(f"Game '{name}' added")
            self.fetch_cover_for_game(len(self.data["games"]) - 1, name)

        ModernButton(win, "Save", save_new_game, primary=True, width=120, height=34).pack(pady=20)

    def edit_game_path(self):
        if self.selected_game_idx is None:
            messagebox.showinfo("Selection", "Please select a game first.")
            return
        games = self.data.get("games", [])
        if not (0 <= self.selected_game_idx < len(games)):
            return
        
        path = filedialog.askopenfilename(title="Select Correct Game File",
                    filetypes=[("Games & ROMs", "*.iso *.rom *.bin *.zip *.rar *.nsp *.chd *.exe"), ("All Files", "*.*")])
        if not path:
            return
            
        self.data["games"][self.selected_game_idx]["path"] = path
        self.refresh()
        self.set_status("Game path manually corrected!")

    def set_custom_cover(self):
        if self.selected_game_idx is None:
            messagebox.showinfo("Selection", "Please select a game first.")
            return
        games = self.data.get("games", [])
        if not (0 <= self.selected_game_idx < len(games)):
            return
        
        path = filedialog.askopenfilename(title="Select Cover Image",
                    filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All Files", "*.*")])
        if not path:
            return
            
        try:
            COVERS_DIR.mkdir(parents=True, exist_ok=True)
            ext = Path(path).suffix
            dest_path = COVERS_DIR / f"game_{self.selected_game_idx}{ext}"
            
            shutil.copy(path, dest_path)
            self.data["games"][self.selected_game_idx]["cover_path"] = str(dest_path)
            
            self.refresh()
            self.set_status("Manual cover successfully saved!")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save image:\n{exc}")

    def fetch_game_cover(self):
        if self.selected_game_idx is None:
            messagebox.showinfo("Selection", "Please select a game first.")
            return
        games = self.data.get("games", [])
        if not (0 <= self.selected_game_idx < len(games)):
            return
        game_name = games[self.selected_game_idx].get("name", "")
        self.fetch_cover_for_game(self.selected_game_idx, game_name)

    def fetch_cover_for_game(self, game_idx, game_name):
        try:
            self.set_status(f"Fetching cover for '{game_name}'...")
            self.update_idletasks()
            
            import urllib.parse
            query = urllib.parse.quote(game_name + " video game")
            url = f"https://itunes.apple.com/search?term={query}&entity=software&limit=1"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                if results:
                    artwork_url = results[0].get("artworkUrl512") or results[0].get("artworkUrl100")
                    if artwork_url:
                        img_req = urllib.request.Request(artwork_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(img_req, timeout=5) as img_resp:
                            img_bytes = img_resp.read()
                            COVERS_DIR.mkdir(parents=True, exist_ok=True)
                            dest_path = COVERS_DIR / f"game_{game_idx}.jpg"
                            dest_path.write_bytes(img_bytes)
                            
                            self.data["games"][game_idx]["cover_path"] = str(dest_path)
                            self.refresh()
                            self.set_status(f"Cover for '{game_name}' successfully loaded!")
                            return
            self.set_status("No cover found online. Use „Pick Cover“.")
        except Exception:
            self.set_status("Cover search failed. Use „Pick Cover“.")

    def launch_selected_game(self):
        if self.selected_game_idx is None:
            messagebox.showinfo("Selection", "Please select a game first.")
            return
        games = self.data.get("games", [])
        if not (0 <= self.selected_game_idx < len(games)):
            return
        
        game = games[self.selected_game_idx]
        game_path_str = game.get("path", "")
        emu_idx = game.get("emulator_idx")
        
        emus = self.data.get("emulators", [])
        if emu_idx is None or not (0 <= emu_idx < len(emus)):
            messagebox.showerror("Error", "No valid emulator is assigned to this game.")
            return
            
        emu_path_str = emus[emu_idx].get("path", "")
        
        try:
            emu_path = Path(emu_path_str).resolve()
            game_path = Path(game_path_str).resolve()
            
            if not emu_path.is_file():
                messagebox.showerror("Error", f"The emulator EXE was not found:\n{emu_path}")
                return
                
            if not game_path.is_file():
                messagebox.showerror("Error", f"The game file does not exist:\n{game_path}\n\nPlease use the „✏️ Path“ button!")
                return

            if "pcsx2" in emu_path.name.lower():
                cmd = [str(emu_path), "--", str(game_path)]
            else:
                cmd = [str(emu_path), str(game_path)]

            subprocess.Popen(cmd, cwd=str(emu_path.parent))
            self.set_status(f"Game '{game.get('name')}' launched!")
        except Exception as exc:
            messagebox.showerror("Launch failed", str(exc))

    def remove_game(self):
        if self.selected_game_idx is None:
            messagebox.showinfo("Selection", "Please select a game first.")
            return
        del self.data["games"][self.selected_game_idx]
        self.selected_game_idx = None
        self.refresh()
        self.set_status("Game removed")

    def add_folder(self):
        path = filedialog.askdirectory(title="Select Folder")
        if not path:
            return
        name = Path(path).name or path
        self.data.setdefault("folders", []).append({"name": name, "path": path})
        self.refresh()
        self.set_status(f"Folder '{name}' added")

    def open_selected_folder(self):
        if self.selected_folder_idx is None:
            messagebox.showinfo("Selection", "Please select a folder first.")
            return
        folders = self.data.get("folders", [])
        if not (0 <= self.selected_folder_idx < len(folders)):
            return
        path = folders[self.selected_folder_idx].get("path", "")
        if not Path(path).is_dir():
            messagebox.showerror("Error", "This folder no longer exists.")
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def remove_folder(self):
        if self.selected_folder_idx is None:
            messagebox.showinfo("Selection", "Please select a folder first.")
            return
        del self.data["folders"][self.selected_folder_idx]
        self.selected_folder_idx = None
        self.refresh()
        self.set_status("Folder removed")

if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
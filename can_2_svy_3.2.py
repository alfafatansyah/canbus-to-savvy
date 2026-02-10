# === STANDARD LIBRARY ===
import os
import sys
import threading

# === THIRD PARTY ===
import pandas as pd
import requests
from tkinterdnd2 import TkinterDnD, DND_FILES

# === TKINTER ===
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import webbrowser

# === APP METADATA ===
APP_NAME = "CANbus to Savvy"
APP_VERSION = (3, 1)
APP_VERSION_STR = ".".join(map(str, APP_VERSION))
GITHUB_REPO = "username/CANbus-to-Savvy"

CHANNEL_MAP = {
    "Channel 1": "ch1",
    "Channel 2": "ch2",
    "Channel 3": "ch3",
}

CHANNEL_SUFFIX = {
    "Channel 1": "_ch1",
    "Channel 2": "_ch2",
    "Channel 3": "_ch3",
}

def check_for_update():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return

        data = response.json()
        latest_version = tuple(
            map(int, data["tag_name"].lstrip("v").split("."))
        )
        
        if latest_version > APP_VERSION:
            assets = data.get("assets", [])
            if not assets:
                return
            download_url = assets[0]["browser_download_url"]

            if messagebox.askyesno(
                "Update Available",
                f"Versi baru tersedia!\n\n"
                f"Versi saat ini : {APP_VERSION_STR}\n"
                f"Versi terbaru : {'.'.join(map(str, latest_version))}\n\n"
                "Download sekarang?"
            ):
                webbrowser.open(download_url)

    except Exception:
        # Silent fail → tidak ganggu user
        pass

def resource_path(relative_path):
    """Resolve resource path for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === Converter CANrecorder S/N: 20241013XXX ===
def convert_canrecorder_v1(file_path, channel="Automatic", progress_callback=None):
    try:
        df = pd.read_csv(file_path)

        total_steps = 6
        step = 0
        def update_progress():
            if progress_callback:
                progress_callback(int(step / total_steps * 100))

        # 1. Filter channel
        if channel in CHANNEL_MAP:
            df = df[df.iloc[:, 3] == CHANNEL_MAP[channel]]
        
        step += 1
        update_progress()

        # 2. Drop kolom tidak dipakai
        df = df.drop(columns=[
            "Index",
            "System Time",
            "Channel",
            "Direction"
            ],
            errors="ignore")
        
        step += 1
        update_progress()

        # 3. Format ulang kolom
        if "Time Stamp" in df.columns:
            def convert_ts(x):
                try:
                    return str(int(str(x), 16) * 100)
                except Exception:
                    return x
            df["Time Stamp"] = df["Time Stamp"].apply(convert_ts)
        if "ID" in df.columns:
            df["ID"] = df["ID"].astype(str).str[2:]
        if "Type" in df.columns:
            df["Type"] = "True"
        if "Format" in df.columns:
            df["Format"] = "0"
        if "DLC" in df.columns:
            df["DLC"] = df["DLC"].astype(str).str[3:]

        step += 1
        update_progress()

        # 4. Pecah Data jadi 8 kolom
        if "Data" in df.columns:
            data_split = df["Data"].astype(str).str[3:-1].str.split(" ", expand=True)
            data_split = data_split.reindex(columns=range(8), fill_value="")
            data_split.columns = [f"D{i+1}" for i in range(8)]
            df = df.drop(columns=["Data"]).join(data_split)

        step += 1
        update_progress()

        # 5. Rename kolom
        df = df.rename(
            columns={
                "Time Stamp": "Time stamp",
                "Type": "Extended",
                "Format": "Bus",
                "DLC": "LEN"
                }
            )
        step += 1
        update_progress()

        base, _ = os.path.splitext(file_path)
        new_path = f"{base}{CHANNEL_SUFFIX.get(channel, '')}.svy"
        df.to_csv(new_path, index=False)
        step = total_steps; update_progress()
        return True, new_path

    except Exception as e:
        return False, str(e)


# === Converter CANrecorder S/N: 20250305XXX ===
def convert_canrecorder_v2(file_path, channel="Automatic", progress_callback=None):
    try:
        df = pd.read_csv(file_path)
        total_steps = 6
        step = 0
        def update_progress():
            if progress_callback:
                progress_callback(int(step / total_steps * 100))

        if channel in CHANNEL_MAP:
            df = df[df.iloc[:, 3] == CHANNEL_MAP[channel]]

        step += 1
        update_progress()

        df = df.drop(columns=[
            "No.",
            "SysTim",
            "Channel",
            "CanType"
            ],
            errors="ignore")
        
        step += 1
        update_progress()

        if "TimStamp" in df.columns:
            def convert_ts(x):
                try:
                    if isinstance(x, str) and all(c in "0123456789ABCDEFabcdef" for c in x.strip()):
                        return str(int(str(x), 16) * 100)
                    else:
                        return str(int(float(x) * 10_000_000))
                except Exception:
                    return x
            df["TimStamp"] = df["TimStamp"].apply(convert_ts)

        step += 1
        update_progress()

        if "ID" in df.columns:
            df["ID"] = df["ID"].astype(str).str[2:]
        if "FrameType" in df.columns:
            df["FrameType"] = "True"
        if "FrameFormat" in df.columns:
            df["FrameFormat"] = "0"

        step += 1
        update_progress()

        if "Data" in df.columns:
            data_split = df["Data"].astype(str).str[3:-1].str.split(" ", expand=True)
            data_split = data_split.reindex(columns=range(8), fill_value="")
            data_split.columns = [f"D{i+1}" for i in range(8)]
            df = df.drop(columns=["Data"]).join(data_split)

        step += 1
        update_progress()

        df = df.rename(
            columns={
                "TimStamp": "Time stamp",
                "FrameType": "Extended",
                "FrameFormat": "Bus",
                "Length": "LEN"
                }
            )
        
        base, _ = os.path.splitext(file_path)
        new_path = f"{base}{CHANNEL_SUFFIX.get(channel, '')}.svy"
        df.to_csv(new_path, index=False)
        step = total_steps; update_progress()
        return True, new_path

    except Exception as e:
        return False, str(e)

# === Converter CANalyst-II S/N: 31F0001EXXX ===
def convert_canalyst(file_path, progress_callback=None):
    try:
        # CSV ini pakai delimiter ';'
        df = pd.read_csv(file_path, sep=";", engine="python")

        total_steps = 5
        step = 0

        def update_progress():
            if progress_callback:
                progress_callback(int(step / total_steps * 100))

        # 1. Bersihkan spasi nama kolom
        df.columns = [c.strip() for c in df.columns]

        step += 1
        update_progress()

        # 2. Hitung timestamp delta (µs)
        time_series = df["Time"].astype(float)
        t0 = time_series.iloc[0]

        delta_us = (
            (time_series - t0)
            * 1_000_000
        ).round().astype(int)

        df["Time stamp"] = delta_us.apply(lambda x: f"{x:07d}")

        step += 1
        update_progress()

        # 3. ID, Extended, Bus, LEN
        df["ID"] = df["FrameId"].astype(str).str.strip().str.upper()
        df["Extended"] = "True"
        df["Bus"] = "0"
        df["LEN"] = df["Len"]

        step += 1
        update_progress()

        # 4. Pecah data byte
        data_bytes = (
            df["Data"]
            .str.strip()
            .str.split(" ", expand=True)
            .reindex(columns=range(8), fill_value="00")
        )
        data_bytes.columns = [f"D{i+1}" for i in range(8)]

        step += 1
        update_progress()

        # 5. Final dataframe
        out_df = pd.concat(
            [
                df["Time stamp"],
                df["ID"],
                df["Extended"],
                df["Bus"],
                df["LEN"],
                data_bytes
            ],
            axis=1
        )

        base, _ = os.path.splitext(file_path)
        out_path = f"{base}.svy"
        out_df.to_csv(out_path, index=False)

        step = total_steps
        update_progress()
        return True, out_path

    except Exception as e:
        return False, str(e)

# === Converter mapping ===
CONVERTERS = {
    "CANrecorder 20241013XXX": convert_canrecorder_v1,
    "CANrecorder 20250305XXX": convert_canrecorder_v2,
    "CANalyst-II 31F0001EXXX": convert_canalyst,
}

# === GUI Aplikasi ===
class CANConverterApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"CANbus to Savvy v{APP_VERSION_STR}")
        self.file_path = None

        self.after(1500, check_for_update)
        
        # === Set Icon Aplikasi ===
        icon_path = resource_path("can2svy_3.1.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # === Group Unggah File ===
        frame_upload = tk.LabelFrame(self, text="Upload CANbus File")
        frame_upload.pack(fill="x", padx=10, pady=10)

        self.drop_area = tk.Label(
            frame_upload,
            text="Drag and Drop files here or Click to select",
            relief="ridge", width=50, height=5, bg="white"
        )
        self.drop_area.pack(padx=10, pady=10)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<Drop>>", self.on_drop)
        self.drop_area.bind("<Button-1>", self.browse_file)

        self.file_label = tk.Label(frame_upload, text="No files selected yet")
        self.file_label.pack(pady=5)

        # === Selector Jenis File Awal ===
        frame_type = tk.LabelFrame(self, text="CAN logger settings")
        frame_type.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame_type, text="Tools:").pack(anchor="w", padx=5, pady=(5, 0))
        self.file_type_var = tk.StringVar(value="CANrecorder 20241013XXX")
        self.file_type_box = ttk.Combobox(
            frame_type,
            textvariable=self.file_type_var,
            values=[
                "CANrecorder 20241013XXX",
                "CANrecorder 20250305XXX",
                "CANalyst-II 31F0001EXXX"
                ],
            state="readonly",
            width=32
        )
        self.file_type_box.pack(anchor="w", padx=5, pady=(0, 5))
        self.file_type_box.bind("<<ComboboxSelected>>", self.on_file_type_change)

        # === Group Pengaturan Channel ===
        frame_channel = tk.LabelFrame(self, text="Channel Settings")
        frame_channel.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame_channel, text="Select channel:").pack(anchor="w", padx=5, pady=(5, 0))
        self.channel_var = tk.StringVar(value="Automatic")
        self.channel_box = ttk.Combobox(
            frame_channel,
            textvariable=self.channel_var,
            values=[
                "Automatic",
                "Channel 1",
                "Channel 2",
                "Channel 3"
                ],
                state="readonly"
            )
        self.channel_box.pack(anchor="w", padx=5, pady=(0, 5))

        note_text = """Note:
Jika saat record hanya memakai 1 channel (1/2) pilih "Automatic".
Jika saat record menggunakan 2 channel, pilih sesuai channel yang ingin di-export."""
        
        tk.Label(frame_channel, text=note_text, justify="left", fg="gray").pack(anchor="w", padx=5, pady=(0, 5))

        # === Tombol Convert ===
        self.convert_btn = tk.Button(self, text="Convert to Savvy", command=self.start_conversion_thread)
        self.convert_btn.pack(pady=10)

        self.status_label = tk.Label(self, text="")
        self.status_label.pack(pady=5)

        # === Progress Bar ===
        self.progress_bar = ttk.Progressbar(self, length=300, mode="determinate", maximum=100)
        self.progress_bar.pack(pady=3)
        self.progress_label = tk.Label(self, text="")
        self.progress_label.pack()

        self.credit_label = tk.Label(self, text="Developed by Alfa Fatansyah", fg="gray", bg="#f0f0f0")
        self.credit_label.pack(fill="x", pady=(0, 5))

        # === Window Settings ===
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        self.resizable(False, False)

    def on_drop(self, event):
        self.file_path = event.data.strip("{}")
        self.file_label.config(text=os.path.basename(self.file_path))

    def browse_file(self, event=None):
        path = filedialog.askopenfilename(
            filetypes=[
                ("CAN files", "*.can *.asc *.csv *.txt"),
                ("All files", "*.*")
                ]
            )
        
        if path:
            self.file_path = path
            self.file_label.config(text=os.path.basename(path))

    def on_file_type_change(self, event=None):
        if self.file_type_var.get() == "CANalyst-II 31F0001EXXX":
            self.channel_box.set("Automatic")
            self.channel_box.config(state="disabled")
        else:
            self.channel_box.config(state="readonly")

    # === Fungsi Thread agar GUI tidak freeze ===
    def start_conversion_thread(self):
        threading.Thread(target=self.convert_file, daemon=True).start()

    def convert_file(self):
        if not self.file_path:
            messagebox.showwarning(
                "Peringatan",
                "Silakan pilih file terlebih dahulu."
                )
            return

        self.status_label.config(text="Mengkonversi, mohon tunggu...")
        self.progress_bar["value"] = 0
        self.progress_label.config(text="0%")
        self.update_idletasks()

        def update_progress(value):
            self.after(
                0,
                lambda: (
                    self.progress_bar.config(value=value),
                    self.progress_label.config(text=f"{value}%")
                )
            )

        file_type = self.file_type_var.get()
        channel = self.channel_var.get()
        
        converter = CONVERTERS.get(file_type)

        self.convert_btn.config(state="disabled")

        if not converter:
            messagebox.showerror("Error", "Jenis file tidak dikenali.")
            self.convert_btn.config(state="normal")
            return

        if file_type == "CANalyst-II 31F0001EXXX":
            success, result = converter(
                self.file_path,
                progress_callback=update_progress
            )
        else:
            success, result = converter(
                self.file_path,
                channel,
                progress_callback=update_progress
            )

        if success:
            self.status_label.config(text="Selesai", fg="green")
            self.progress_bar["value"] = 100
            self.progress_label.config(text="100%")
            messagebox.showinfo("Berhasil", f"File berhasil diexport:\n{result}")
        else:
            self.status_label.config(text="Gagal", fg="red")
            messagebox.showerror("Error", f"Gagal mengkonversi:\n{result}")

        self.convert_btn.config(state="normal")

if __name__ == "__main__":
    app = CANConverterApp()
    app.mainloop()

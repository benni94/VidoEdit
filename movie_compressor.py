# GPU Movie Compressor Pro — FINAL STABLE VERSION
# Windows | Python 3.10+ | FFmpeg required in PATH

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import subprocess
import threading
import time
from pathlib import Path
import queue

# ---------------- CONSTANTS ----------------

VIDEO_EXTS = (".mkv", ".mp4", ".avi", ".mov", ".wmv")

PRESETS = {
    "Film - Balances encoding quality with file size, suited for most films.":  {"crf": 23, "preset": "slow"},
    "Anime - Optimized for animation, preserving fine lines and details at a higher quality.": {"crf": 20, "preset": "veryslow"},
    "4K - Tailored for 4K videos, allows for a slight reduction in quality to reduce file size.":    {"crf": 22, "preset": "slow"},
    "Plex - Designed for streaming platforms like Plex, balancing quality with a faster encoding speed.":  {"crf": 24, "preset": "medium"},
}

# ---------------- GLOBAL STATE ----------------

task_queue = queue.Queue()
ui_queue = queue.Queue()

current_process = None
cancel_requested = False

# ---------------- GPU DETECTION ----------------


def detect_gpu_encoder():
    try:
        encoders = subprocess.check_output(
            ["ffmpeg", "-encoders"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        if "hevc_nvenc" in encoders:
            return "hevc_nvenc"
        if "hevc_amf" in encoders:
            return "hevc_amf"
        if "hevc_qsv" in encoders:
            return "hevc_qsv"
    except:
        pass
    return "libx265"


GPU_ENCODER = detect_gpu_encoder()

# ---------------- UTILITIES ----------------


def get_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ], text=True)
    return float(out.strip())


def calculate_bitrate(duration, target_gb):
    target_bits = target_gb * 1024**3 * 8
    total_kbps = target_bits / duration / 1000
    return max(int(total_kbps), 500)

# ---------------- ENCODING ----------------


def encode_file(input_file):
    global current_process, cancel_requested

    duration = get_duration(input_file)
    output_file = Path(input_file).with_name(
        Path(input_file).stem + "_compressed.mkv"
    )

    mode = mode_var.get()
    preset = PRESETS[preset_var.get()]

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-map", "0",
        "-c:v", GPU_ENCODER,
        "-profile:v", "main10",
        "-pix_fmt", "p010le",
        "-preset", preset["preset"],
    ]

    if mode == "CRF":
        cmd += ["-crf", str(preset["crf"])]
    else:
        bitrate = calculate_bitrate(duration, float(target_size.get()))
        cmd += [
            "-b:v", f"{bitrate}k",
            "-maxrate", f"{bitrate}k",
            "-bufsize", f"{bitrate * 2}k"
        ]

    cmd += ["-c:a", "copy", "-c:s", "copy"]

    cmd += [
        "-color_primaries", "bt2020",
        "-color_trc", "smpte2084",
        "-colorspace", "bt2020nc",
        "-progress", "pipe:1",
        "-nostats",
        str(output_file)
    ]

    current_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    start = time.time()

    for line in current_process.stdout:
        if cancel_requested:
            current_process.kill()
            return

        if line.startswith("out_time_ms="):
            value = line.split("=", 1)[1].strip()
            if not value.isdigit():
                continue

            current_sec = int(value) / 1_000_000
            progress = min((current_sec / duration) * 100, 100)

            elapsed = time.time() - start
            eta = int((elapsed / current_sec) * (duration -
                      current_sec)) if current_sec > 0 else 0

            # SEND TO UI THREAD
            ui_queue.put(("progress", progress, eta))

    ui_queue.put(("done",))

# ---------------- WORKER THREAD ----------------


def worker():
    global cancel_requested

    while not task_queue.empty():
        if cancel_requested:
            break

        file = task_queue.get()
        ui_queue.put(("status", f"Encoding: {Path(file).name}"))
        encode_file(file)
        task_queue.task_done()

    ui_queue.put(("idle",))
    cancel_requested = False

# ---------------- UI POLLER (MAIN THREAD) ----------------


def poll_ui_queue():
    try:
        while True:
            msg = ui_queue.get_nowait()

            if msg[0] == "progress":
                _, prog, eta = msg
                progress_bar["value"] = prog
                eta_label.config(text=f"ETA: {eta}s")

            elif msg[0] == "status":
                status_label.config(text=msg[1])

            elif msg[0] == "done":
                progress_bar["value"] = 0
                eta_label.config(text="ETA: --")

            elif msg[0] == "idle":
                status_label.config(text="Idle")

    except queue.Empty:
        pass

    root.after(100, poll_ui_queue)

# ---------------- UI ACTIONS ----------------


def add_files():
    for f in filedialog.askopenfilenames():
        if f.lower().endswith(VIDEO_EXTS):
            task_queue.put(f)
            queue_list.insert("end", Path(f).name)


def add_folder():
    folder = filedialog.askdirectory()
    if not folder:
        return
    for f in Path(folder).iterdir():
        if f.suffix.lower() in VIDEO_EXTS:
            task_queue.put(str(f))
            queue_list.insert("end", f.name)


def start():
    if task_queue.empty():
        messagebox.showerror("Error", "Queue is empty")
        return
    threading.Thread(target=worker, daemon=True).start()


def cancel():
    global cancel_requested
    cancel_requested = True
    status_label.config(text="Cancelling...")

# ---------------- GUI ----------------


root = tk.Tk()
root.title("GPU Movie Compressor Pro")

mode_var = tk.StringVar(value="CRF")
preset_var = tk.StringVar(value="Film")
target_size = tk.StringVar(value="5")

frame = ttk.Frame(root, padding=10)
frame.pack(fill="both", expand=True)

ttk.Button(frame, text="Add Files", command=add_files).pack(fill="x")
ttk.Button(frame, text="Add Folder", command=add_folder).pack(fill="x", pady=4)

queue_list = tk.Listbox(frame, height=6)
queue_list.pack(fill="both", pady=5)

ttk.Label(frame, text="Mode").pack(anchor="w")
ttk.Radiobutton(frame, text="CRF", variable=mode_var,
                value="CRF").pack(anchor="w")
ttk.Radiobutton(frame, text="Target Size (GB)",
                variable=mode_var, value="SIZE").pack(anchor="w")
ttk.Entry(frame, textvariable=target_size, width=8).pack(anchor="w")

ttk.Label(frame, text="Presets").pack(anchor="w", pady=6)
for p in PRESETS:
        ttk.Radiobutton(
            frame,
            text=p,
            variable=preset_var,
            value=p
        ).pack(anchor="w")

progress_bar = ttk.Progressbar(frame, length=420)
progress_bar.pack(pady=10)

eta_label = ttk.Label(frame, text="ETA: --")
eta_label.pack()

status_label = ttk.Label(frame, text="Idle")
status_label.pack(pady=3)

ttk.Button(frame, text="START", command=start).pack(fill="x", pady=4)
ttk.Button(frame, text="CANCEL", command=cancel).pack(fill="x")

root.after(100, poll_ui_queue)
root.mainloop()

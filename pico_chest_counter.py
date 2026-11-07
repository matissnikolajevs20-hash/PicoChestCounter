import json
import os
import queue
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from updater import (
    ReleaseInfo,
    UpdateCheckError,
    UpdateNotConfiguredError,
    find_available_update,
    install_update,
)

IS_FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
MODEL_DIR = RESOURCE_DIR / "vosk-model-small-en-us-0.15"
if IS_FROZEN:
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    DATA_DIR /= "DeltaChestCounter"
    COUNT_FILE = DATA_DIR / "chest_count.json"
else:
    COUNT_FILE = APP_DIR / "chest_count.json"

COLORS = {
    "background": "#111820",
    "panel": "#1B2732",
    "text": "#F4F1E8",
    "muted": "#A4B2BC",
    "accent": "#F2C14E",
    "green": "#73D2A0",
    "red": "#F08080",
}


class DeltaChestCounter:
    def __init__(self, root):
        self.root = root
        self.root.title("Delta Chest Counter")
        self.root.geometry("520x480")
        self.root.minsize(440, 440)
        self.root.configure(bg=COLORS["background"])
        self.always_on_top = tk.BooleanVar(value=False)
        self.mini_counter = None
        self.mini_count_label = None
        self.mini_drag_start = None

        self.events = queue.Queue()
        self.audio_queue = queue.Queue(maxsize=24)
        self.stop_event = threading.Event()
        self.listener_thread = None
        self.count = self.load_count()
        self.update_check_running = False
        self.update_install_running = False
        self.update_dialog = None

        self.configure_styles()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(80, self.process_events)
        self.check_for_updates(show_if_none=False)

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(18, 12),
            background=COLORS["accent"],
            foreground=COLORS["background"],
            borderwidth=0,
        )
        style.map("Action.TButton", background=[("active", "#FFD66B")])
        style.configure(
            "Quiet.TButton",
            font=("Segoe UI", 10),
            padding=(12, 9),
            background=COLORS["panel"],
            foreground=COLORS["text"],
            borderwidth=0,
        )
        style.map("Quiet.TButton", background=[("active", "#293845")])

    def build_ui(self):
        outer = tk.Frame(self.root, bg=COLORS["background"], padx=34, pady=26)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="DELTA / CHEST COUNTER",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        self.count_label = tk.Label(
            outer,
            text=f"{self.count:,}",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI Light", 86),
        )
        self.count_label.pack(anchor="w", pady=(16, 0))

        count_details = tk.Frame(outer, bg=COLORS["background"])
        count_details.pack(fill="x", pady=(0, 25))
        tk.Label(
            count_details,
            text="CHESTS OPENED",
            bg=COLORS["background"],
            fg=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        self.mini_counter_button = ttk.Button(
            count_details,
            text="Show mini counter",
            style="Quiet.TButton",
            command=self.toggle_mini_counter,
        )
        self.mini_counter_button.pack(side="right")

        self.listen_button = ttk.Button(
            outer,
            text="Start listening",
            style="Action.TButton",
            command=self.start_listening,
        )
        self.listen_button.pack(fill="x")

        controls = tk.Frame(outer, bg=COLORS["background"])
        controls.pack(fill="x", pady=(12, 22))
        ttk.Button(
            controls,
            text="Reset count",
            style="Quiet.TButton",
            command=self.reset_count,
        ).pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Keep on top",
            variable=self.always_on_top,
            command=lambda: self.root.attributes(
                "-topmost", self.always_on_top.get()
            ),
        ).pack(side="left", padx=(10, 0))
        self.status_label = tk.Label(
            controls,
            text="Ready",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        self.status_label.pack(side="right", padx=4)
        self.update_button = ttk.Button(
            controls,
            text="Check for updates",
            style="Quiet.TButton",
            command=self.check_for_updates,
        )
        self.update_button.pack(side="right", padx=(0, 8))

        tk.Frame(outer, bg="#30404D", height=1).pack(fill="x", pady=(0, 14))
        tk.Label(
            outer,
            text="Last heard",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        self.heard_label = tk.Label(
            outer,
            text="Nothing yet",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI", 12),
            anchor="w",
        )
        self.heard_label.pack(fill="x", pady=(5, 0))

    def load_count(self):
        try:
            COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = json.loads(COUNT_FILE.read_text(encoding="utf-8"))
            return max(0, int(data.get("count", 0)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def save_count(self):
        COUNT_FILE.write_text(
            json.dumps({"count": self.count}, indent=2), encoding="utf-8"
        )

    def start_listening(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return
        if not MODEL_DIR.is_dir():
            messagebox.showerror(
                "Speech model not found",
                "Run setup.bat first to install the offline speech model.",
                parent=self.root,
            )
            return
        self.stop_event.clear()
        self.listen_button.configure(text="Stop listening", command=self.stop_listening)
        self.status_label.configure(text="Starting…", fg=COLORS["accent"])
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def stop_listening(self):
        self.stop_event.set()
        self.listen_button.configure(text="Start listening", command=self.start_listening)
        self.status_label.configure(text="Stopping…", fg=COLORS["muted"])

    def listen(self):
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model

            model = Model(str(MODEL_DIR))
            device_info = sd.query_devices(kind="input")
            sample_rate = int(device_info["default_samplerate"])
            recognizer = KaldiRecognizer(model, sample_rate, '["delta", "[unk]"]')
            self.events.put(("status", "Listening", COLORS["green"]))

            def audio_callback(indata, frames, time_info, status):
                try:
                    self.audio_queue.put_nowait(bytes(indata))
                except queue.Full:
                    pass

            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=4000,
                device=None,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                while not self.stop_event.is_set():
                    try:
                        audio = self.audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(audio):
                        result = json.loads(recognizer.Result())
                        self.handle_recognition(result.get("text", ""))
                self.handle_recognition(
                    json.loads(recognizer.FinalResult()).get("text", "")
                )
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("stopped",))

    def handle_recognition(self, text):
        if not text:
            return
        matches = count_delta_matches(text)
        self.events.put(("heard", text, matches))

    def process_events(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break

            if event[0] == "status":
                self.status_label.configure(text=event[1], fg=event[2])
            elif event[0] == "heard":
                _, text, matches = event
                self.heard_label.configure(text=text)
                if matches:
                    self.count += matches
                    self.update_count_display()
                    try:
                        self.save_count()
                    except OSError as error:
                        messagebox.showerror("Couldn't save count", str(error), parent=self.root)
            elif event[0] == "error":
                self.status_label.configure(text="Microphone unavailable", fg=COLORS["red"])
                messagebox.showerror(
                    "Could not start listening",
                    f"{event[1]}\n\nCheck that a microphone is connected and allowed in Windows privacy settings.",
                    parent=self.root,
                )
            elif event[0] == "stopped":
                self.listen_button.configure(text="Start listening", command=self.start_listening)
                if self.status_label.cget("text") != "Microphone unavailable":
                    self.status_label.configure(text="Ready", fg=COLORS["muted"])
            elif event[0] == "update-check-started":
                self.status_label.configure(
                    text="Checking for updates…", fg=COLORS["muted"]
                )
            elif event[0] == "update-unconfigured":
                self.update_check_running = False
                self.update_button.configure(state="normal")
                self.status_label.configure(
                    text="Updates not configured", fg=COLORS["muted"]
                )
            elif event[0] == "update-check-finished":
                _, release, show_if_none = event
                self.update_check_running = False
                self.update_button.configure(state="normal")
                if release is None:
                    self.status_label.configure(
                        text="Up to date", fg=COLORS["green"]
                    )
                    if show_if_none:
                        messagebox.showinfo(
                            "No updates available",
                            "You're using the latest version.",
                            parent=self.root,
                        )
                else:
                    self.status_label.configure(
                        text=f"Update {release.version} available",
                        fg=COLORS["accent"],
                    )
                    self.show_update_dialog(release)
            elif event[0] == "update-check-failed":
                _, error, show_if_none = event
                self.update_check_running = False
                self.update_button.configure(state="normal")
                self.status_label.configure(
                    text="Update check failed", fg=COLORS["red"]
                )
                if show_if_none:
                    messagebox.showwarning(
                        "Update check failed",
                        str(error),
                        parent=self.root,
                    )
            elif event[0] == "update-install-started":
                self.status_label.configure(
                    text="Installing update…", fg=COLORS["accent"]
                )
            elif event[0] == "update-install-finished":
                self.update_install_running = False
                self.update_button.configure(state="normal")
                if IS_FROZEN:
                    self.root.after_idle(self.root.destroy)
                    return
                try:
                    executable = sys.executable
                    os.execv(
                        executable,
                        [executable, str(Path(__file__).resolve())],
                    )
                except OSError as error:
                    self.status_label.configure(
                        text="Restart required", fg=COLORS["accent"]
                    )
                    messagebox.showinfo(
                        "Update installed",
                        "The update was installed, but the app could not restart "
                        f"automatically. Close and reopen the app.\n\n{error}",
                        parent=self.root,
                    )
            elif event[0] == "update-install-failed":
                self.update_install_running = False
                self.update_button.configure(state="normal")
                self.status_label.configure(
                    text="Update failed", fg=COLORS["red"]
                )
                messagebox.showerror(
                    "Could not install update",
                    str(event[1]),
                    parent=self.root,
                )

        self.root.after(80, self.process_events)

    def check_for_updates(self, show_if_none=True):
        if self.update_check_running or self.update_install_running:
            return
        self.update_check_running = True
        self.update_button.configure(state="disabled")
        self.events.put(("update-check-started",))

        def check():
            try:
                release = find_available_update(APP_DIR)
            except UpdateNotConfiguredError:
                self.events.put(("update-unconfigured",))
            except UpdateCheckError as error:
                self.events.put(("update-check-failed", error, show_if_none))
            else:
                self.events.put(
                    ("update-check-finished", release, show_if_none)
                )

        threading.Thread(target=check, daemon=True).start()

    def show_update_dialog(self, release):
        if self.update_dialog is not None and self.update_dialog.winfo_exists():
            self.update_dialog.lift()
            return

        dialog = tk.Toplevel(self.root)
        self.update_dialog = dialog
        dialog.title("Update available")
        dialog.geometry("600x460")
        dialog.minsize(480, 360)
        dialog.configure(bg=COLORS["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        tk.Label(
            dialog,
            text=f"Version {release.version} is available",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=22, pady=(20, 4))
        tk.Label(
            dialog,
            text="Would you like to install this update now?",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=22, pady=(0, 8))
        tk.Label(
            dialog,
            text=f"Changes since your installed version {release.current_version}:",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=22, pady=(0, 12))

        notes = tk.Text(
            dialog,
            wrap="word",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            padx=12,
            pady=10,
            font=("Segoe UI", 10),
        )
        notes.pack(fill="both", expand=True, padx=22)
        notes.insert("1.0", release.notes)
        notes.configure(state="disabled")

        buttons = tk.Frame(dialog, bg=COLORS["background"])
        buttons.pack(fill="x", padx=22, pady=18)
        ttk.Button(
            buttons,
            text="No",
            style="Quiet.TButton",
            command=dialog.destroy,
        ).pack(side="right")
        ttk.Button(
            buttons,
            text="Yes",
            style="Action.TButton",
            command=lambda: self.confirm_update(dialog, release),
        ).pack(side="right", padx=(0, 10))

    def confirm_update(self, dialog, release):
        dialog.destroy()
        self.update_install_running = True
        self.update_button.configure(state="disabled")
        self.events.put(("update-install-started",))

        def install():
            try:
                install_update(APP_DIR, release)
            except UpdateCheckError as error:
                self.events.put(("update-install-failed", error))
            else:
                self.events.put(("update-install-finished",))

        threading.Thread(target=install, daemon=True).start()

    def reset_count(self):
        if messagebox.askyesno("Reset count", "Reset the chest count to zero?", parent=self.root):
            self.count = 0
            self.update_count_display()
            self.save_count()

    def update_count_display(self):
        formatted_count = f"{self.count:,}"
        self.count_label.configure(text=formatted_count)
        if self.mini_count_label is not None:
            self.mini_count_label.configure(text=formatted_count)

    def toggle_mini_counter(self):
        if self.mini_counter is not None:
            self.mini_counter.destroy()
            self.mini_counter = None
            self.mini_count_label = None
            self.mini_counter_button.configure(text="Show mini counter")
            return

        mini_counter = tk.Toplevel(self.root)
        self.mini_counter = mini_counter
        mini_counter.overrideredirect(True)
        mini_counter.attributes("-topmost", True)
        mini_counter.configure(bg=COLORS["panel"])
        self.mini_count_label = tk.Label(
            mini_counter,
            text=f"{self.count:,}",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 30, "bold"),
            padx=18,
            pady=10,
        )
        self.mini_count_label.pack()
        mini_counter.geometry("+40+40")
        for widget in (mini_counter, self.mini_count_label):
            widget.bind("<ButtonPress-1>", self.start_mini_counter_drag)
            widget.bind("<B1-Motion>", self.move_mini_counter)
        self.mini_counter_button.configure(text="Hide mini counter")

    def start_mini_counter_drag(self, event):
        self.mini_drag_start = (
            event.x_root,
            event.y_root,
            self.mini_counter.winfo_x(),
            self.mini_counter.winfo_y(),
        )

    def move_mini_counter(self, event):
        if self.mini_drag_start is None:
            return
        start_x, start_y, window_x, window_y = self.mini_drag_start
        x = window_x + event.x_root - start_x
        y = window_y + event.y_root - start_y
        self.mini_counter.geometry(f"+{x}+{y}")

    def close(self):
        if self.update_install_running:
            messagebox.showinfo(
                "Update in progress",
                "Please wait for the update to finish before closing the app.",
                parent=self.root,
            )
            return
        self.stop_event.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    DeltaChestCounter(root)
    root.mainloop()


def count_delta_matches(text):
    return len(re.findall(r"\bdelta\b", text.casefold()))


if __name__ == "__main__":
    main()

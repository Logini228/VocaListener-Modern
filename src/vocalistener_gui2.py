import sys
import os
import json
import shutil
import subprocess
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QFileDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor, QFont, QCursor

# --- Constants & Colors ---
COLOR_BG = "#1e293b"       # Dark Blue-ish
COLOR_TEXT = "#f8fafc"    # White-ish
COLOR_WAITING = QColor(255, 193, 7)   # Yellow
COLOR_ACTIVE = QColor(56, 189, 248)   # Cyan/Blue Glow
COLOR_DONE = QColor(74, 222, 128)     # Green Glow
COLOR_ERROR = QColor(248, 113, 113)   # Red

STEPS = [
    {"id": 1, "name": "Extract Pitch"},
    {"id": 2, "name": "MFA Align"},
    {"id": 3, "name": "Parse TextGrid"},
    {"id": 4, "name": "Remap Phones"},
    {"id": 5, "name": "Convert SVP"}
]

# --- UI Components ---

class DiodeWidget(QWidget):
    """Small circle LED widget"""
    clicked = pyqtSignal(int)

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.status = "waiting"
        self.setFixedSize(20, 20)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def set_status(self, status):
        self.status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.status == "waiting": color = COLOR_WAITING
        elif self.status == "active": color = COLOR_ACTIVE
        elif self.status == "done": color = COLOR_DONE
        else: color = COLOR_ERROR

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.rect().center()
        radius = 8
        painter.drawEllipse(center, radius, radius)

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)

class WorkerThread(QThread):
    """Executes main.py steps via subprocess"""
    log_signal = pyqtSignal(str)
    step_started = pyqtSignal(int)
    step_finished = pyqtSignal(int)
    step_error = pyqtSignal(int, str)
    step4_warnings_found = pyqtSignal(list, str) # Signal: (list_of_phonemes, dict_path)
    all_done = pyqtSignal()
    process_stopped = pyqtSignal()

    def __init__(self, start_index, profile_data, tmp_dir):
        super().__init__()
        self.start_index = start_index
        self.profile = profile_data
        self.tmp_dir = tmp_dir
        self._is_running = True

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.main_script = os.path.join(self.script_dir, 'main.py')

    def run(self):
        for i in range(self.start_index, 5):
            if not self._is_running:
                self.process_stopped.emit()
                return

            self.step_started.emit(i)
            step_name = STEPS[i]['name']
            self.log_signal.emit(f"--- Starting Step {i+1}: {step_name} ---")

            try:
                cmd = [
                    sys.executable, "-u",
                    self.main_script,
                    "--input_dir", os.path.join(self.tmp_dir, "input"),
                    "--output_svp", os.path.join(self.tmp_dir, "output.svp"),
                    "--tmp_dir", self.tmp_dir,
                    "--dict_file", self.get_dict_path(),
                    "--language", self.profile['language'],
                    "--step", str(i + 1)
                ]

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=self.script_dir
                )

                # Step 4 specific logic
                missing_phonemes = []

                while True:
                    output = process.stdout.readline()
                    if not output:
                        break

                    stripped_output = output.strip()
                    self.log_signal.emit(stripped_output)

                    # Only check for warnings in Step 4 (Index 3)
                    if i == 3:
                        if "Warning: Phoneme '" in output and "not found in dictionary" in output:
                            try:
                                # Regex to extract phoneme inside single quotes
                                # Example: Warning: Phoneme 'dʲ' not found...
                                match = re.search(r"Phoneme '([^']+)' not found", output)
                                if match:
                                    missing_phonemes.append(match.group(1))
                            except Exception:
                                pass

                # Wait for process to terminate
                process.wait()

                if process.returncode != 0:
                    raise Exception(f"Process exited with code {process.returncode}")

                self.log_signal.emit(f"--- Step {i+1} Finished ---")

                # Special Handling for Step 4 Warnings
                if i == 3 and missing_phonemes:
                    # Unique phonemes
                    unique_phones = list(set(missing_phonemes))
                    dict_path = self.get_dict_path()

                    # Emit signal to UI to handle file writing and stop
                    self.step4_warnings_found.emit(unique_phones, dict_path)
                    return # Stop execution here, do not go to step 5

                self.step_finished.emit(i)
                self.msleep(500)

            except Exception as e:
                self.step_error.emit(i, str(e))
                return

        self.all_done.emit()

    def get_dict_path(self):
        lang = self.profile['language'].lower()
        engine = "Vocaloid" if self.profile['engine'] == "Vocaloid" else "SynthV"
        root_dir = os.path.dirname(self.tmp_dir)
        res_dir = os.path.join(root_dir, 'res')
        dict_file_name = "Vocaloid.txt" if engine == "Vocaloid" else "synthV.txt"
        return os.path.join(res_dir, lang, dict_file_name)

    def stop(self):
        self._is_running = False

class Screen2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VocalListener Modern - Screen 2")
        self.resize(600, 500)

        self.profile = self.load_profile()
        self.tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmp')

        self.circles = []
        self.status_labels = []
        self.current_step = 0
        self.worker = None

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
            QLabel {{ color: {COLOR_TEXT}; font-family: Segoe UI, sans-serif; }}
            QTextEdit {{
                background-color: #0f172a; color: #38bdf8; font-family: Consolas, monospace;
                border: 1px solid #334155; border-radius: 4px;
            }}
            QPushButton {{
                background-color: #334155; color: white; border: 1px solid #475569;
                border-radius: 4px; padding: 6px 12px;
            }}
            QPushButton:hover {{ background-color: #475569; }}
            QPushButton:disabled {{ background-color: #1e293b; color: #64748B; border: 1px solid #334155; }}
            QPushButton#Primary {{ background-color: {COLOR_DONE.name()}; color: #0f172a; font-weight: bold; }}
        """)

        self.setup_ui()

    def load_profile(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)
        path = os.path.join(root_dir, 'tmp', 'profile.json')
        if os.path.exists(path):
            with open(path, 'r') as f: return json.load(f)
        return {}

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("VocalListener Modern")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Timeline (Diodes)
        timeline_widget = QWidget()
        tl_layout = QHBoxLayout(timeline_widget)
        tl_layout.setSpacing(10)

        for i in range(5):
            c_layout = QVBoxLayout()
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl = QLabel("")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(20)
            lbl.setFixedWidth(70)
            lbl.setStyleSheet("font-size: 11px; color: #94a3b8; margin-bottom: 5px;")

            self.status_labels.append(lbl)
            c_layout.addWidget(lbl)

            diode = DiodeWidget(i)
            diode.clicked.connect(self.on_diode_click)
            self.circles.append(diode)
            c_layout.addWidget(diode)

            tl_layout.addLayout(c_layout)

        layout.addWidget(timeline_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        layout.addWidget(self.log_console)

        ctrl_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Processing")
        self.btn_start.setObjectName("Primary")
        self.btn_start.clicked.connect(self.start_process)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_stop.setEnabled(False)

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        footer_layout = QHBoxLayout()

        self.btn_help = QPushButton("Get Help")
        self.btn_tutorial = QPushButton("Tutorial")

        self.btn_save = QPushButton("Save Output File")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_output_file)

        self.btn_clear = QPushButton("Clear Tmp")
        self.btn_clear.clicked.connect(self.clear_tmp_folder)

        btn_exit = QPushButton("Exit")
        btn_exit.clicked.connect(self.close)

        footer_layout.addWidget(self.btn_help)
        footer_layout.addWidget(self.btn_tutorial)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_save)
        footer_layout.addWidget(self.btn_clear)
        footer_layout.addWidget(btn_exit)

        layout.addLayout(footer_layout)

        self.update_ui(0)

    def on_diode_click(self, index):
        self.current_step = index
        self.update_ui(index)
        step_name = STEPS[index]['name']
        self.append_log(f"Selected: {step_name} (Step {index+1}). Click 'Start Processing' to run from here.")

        self.btn_start.setEnabled(True)
        self.btn_start.setText("Resume Processing")
        self.btn_save.setEnabled(False)

    def update_ui(self, active_idx):
        for i in range(5):
            if i < active_idx:
                self.circles[i].set_status("done")
                self.status_labels[i].setText("")
                self.status_labels[i].setStyleSheet("font-size: 11px; color: #94a3b8; margin-bottom: 5px;")
            elif i == active_idx:
                self.circles[i].set_status("active")
                self.status_labels[i].setText(STEPS[i]['name'])
                self.status_labels[i].setStyleSheet("font-size: 11px; color: white; margin-bottom: 5px; font-weight: bold;")
            else:
                self.circles[i].set_status("waiting")
                self.status_labels[i].setText("")
                self.status_labels[i].setStyleSheet("font-size: 11px; color: #94a3b8; margin-bottom: 5px;")

    def start_process(self):
        if self.worker and self.worker.isRunning(): return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_start.setText("Processing...")
        self.log_console.clear()
        self.append_log(f"Starting process from Step {self.current_step + 1}...")

        self.worker = WorkerThread(self.current_step, self.profile, self.tmp_dir)
        self.worker.step_started.connect(self.update_ui)
        self.worker.step_finished.connect(self.handle_step_completion)
        self.worker.step_error.connect(self.on_error)
        self.worker.all_done.connect(self.on_finished)
        self.worker.process_stopped.connect(self.on_process_stopped)
        self.worker.log_signal.connect(self.append_log)
        # Connect the new warning signal
        self.worker.step4_warnings_found.connect(self.handle_step4_warnings)

        self.worker.start()

    def stop_process(self):
        if self.worker:
            self.worker.stop()
            self.append_log("Stop signal sent. Will finish current step, then halt.")

    def handle_step_completion(self, step_idx):
        self.update_ui(step_idx + 1)
        if step_idx == 4:
            self.on_finished()

    def handle_step4_warnings(self, phonemes, dict_path):
        """
        Called when Step 4 finishes but found missing phonemes.
        Writes to dictionary and alerts user.
        """
        try:
            # Append unique phonemes to dictionary
            with open(dict_path, 'a', encoding='utf-8') as f:
                for phone in phonemes:
                    f.write(f"{phone}\n")

            self.append_log(f"Found {len(phonemes)} unset phonemes.")
            self.append_log(f"Added to dictionary at: {dict_path}")

            # UI Cleanup
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Resume Processing")
            self.btn_stop.setEnabled(False)
            self.worker = None

            # Alert User
            msg = (
                f"Found {len(phonemes)} unset phonemes and added them to:\n{dict_path}\n\n"
                "Please open the file and fill them in format:\n"
                "(phoneme | synthv/vocaloid phoneme | language)\n\n"
                "Then press 'Resume Processing' to continue."
            )
            QMessageBox.warning(self, "Phonemes Added", msg)

        except Exception as e:
            self.append_log(f"Error updating dictionary: {e}")
            QMessageBox.critical(self, "Dictionary Error", f"Failed to add phonemes to dictionary:\n{e}")

    def on_process_stopped(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Resume Processing")
        self.btn_stop.setEnabled(False)
        self.append_log("Processing halted by user.")
        self.worker = None

    def on_error(self, idx, msg):
        self.circles[idx].set_status("error")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Continue")
        self.btn_stop.setEnabled(False)
        self.append_log(f"ERROR: {msg}")
        QMessageBox.critical(self, f"Step {idx+1} Failed", msg)
        self.worker = None

    def on_finished(self):
        if self.btn_start.text() == "Done":
            return

        self.btn_start.setEnabled(False)
        self.btn_start.setText("Done")
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(True)
        self.append_log("All steps completed successfully.")
        self.worker = None

    def append_log(self, msg):
        self.log_console.append(msg)
        sb = self.log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def save_output_file(self):
        source = os.path.join(self.tmp_dir, "output.svp")
        default_ext = ".svp"
        file_filter = "SynthV Project (*.svp);;All Files (*)"

        if self.profile.get('engine') == "Vocaloid":
            file_filter = "Vocaloid Project (*.vsqx *.ust *.mid);;SynthV Project (*.svp);;All Files (*)"
            default_ext = ".vsqx"

        if not os.path.exists(source):
            QMessageBox.warning(self, "File Missing", "Output file not found in tmp.")
            return

        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output File",
            os.path.join(self.tmp_dir, f"output{default_ext}"),
            file_filter
        )

        if dest:
            try:
                shutil.copy(source, dest)
                QMessageBox.information(self, "Saved", f"Output saved to {dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def clear_tmp_folder(self):
        reply = QMessageBox.question(
            self, "Clear Tmp",
            "Clear all temporary files except profile and inputs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for item in os.listdir(self.tmp_dir):
                item_path = os.path.join(self.tmp_dir, item)
                if item == "profile.json" or item == "input":
                    continue
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Failed to delete {item}: {e}")

            self.current_step = 0
            self.update_ui(0)
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Start Processing")
            self.btn_save.setEnabled(False)
            self.log_console.clear()
            self.append_log("Tmp cleared.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Screen2()
    window.show()
    sys.exit(app.exec())

import sys
import os
import shutil
import json
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QLineEdit, QTextEdit,
    QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class VocalListenerModern(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Path Setup ---
        # Get the directory where this script is located (src/)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # Get the root directory (parent of src/)
        self.root_dir = os.path.dirname(self.script_dir)

        # Define resource and temp paths
        self.res_dir = os.path.join(self.root_dir, 'res')
        self.tmp_dir = os.path.join(self.root_dir, 'tmp')
        self.input_dir = os.path.join(self.tmp_dir, 'input')

        # Create directories if they don't exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.res_dir, exist_ok=True)

        # State variables
        self.selected_audio_file = None
        self.selected_text_file = None
        self.copied_audio_filename = None

        # Window Setup
        self.setWindowTitle("VocalListener Modern")

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Vertical Layout
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(25, 25, 25, 25)

        self.setup_ui()

        # FIX: Minimal vertical size when launched
        self.adjustSize()

    def setup_ui(self):
        # --- Header ---
        title_label = QLabel("VocalListener Modern")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title_label)

        # --- Engine Selection ---
        engine_layout = QHBoxLayout()
        self.engine_group_label = QLabel("Engine:")
        self.radio_synth_v = QRadioButton("Synth V")
        self.radio_vocaloid = QRadioButton("Vocaloid")

        self.radio_synth_v.setChecked(True)
        self.radio_synth_v.toggled.connect(self.check_dictionary_status)
        self.radio_vocaloid.toggled.connect(self.check_dictionary_status)

        engine_layout.addWidget(self.engine_group_label)
        engine_layout.addWidget(self.radio_synth_v)
        engine_layout.addWidget(self.radio_vocaloid)
        engine_layout.addStretch()
        self.main_layout.addLayout(engine_layout)

        # --- Language Setup ---
        lang_container = QWidget()
        lang_layout = QVBoxLayout(lang_container)
        lang_layout.setContentsMargins(0,0,0,0)

        lang_input_layout = QHBoxLayout()
        lang_label = QLabel("Language:")
        self.lang_input = QLineEdit("Russian")
        self.lang_input.textChanged.connect(self.on_lang_text_changed)

        lang_input_layout.addWidget(lang_label)
        lang_input_layout.addWidget(self.lang_input)

        status_row = QHBoxLayout()
        self.btn_create_dict = QPushButton("Create Dict")
        self.btn_create_dict.setEnabled(False)
        self.btn_create_dict.setFixedWidth(90)
        self.btn_create_dict.clicked.connect(self.create_dictionary_manually)

        self.lang_status = QLabel("Checking dictionary...")
        self.lang_status.setStyleSheet("color: gray; font-size: 10px;")

        status_row.addWidget(self.btn_create_dict)
        status_row.addWidget(self.lang_status)
        status_row.addStretch()

        lang_layout.addLayout(lang_input_layout)
        lang_layout.addLayout(status_row)
        self.main_layout.addWidget(lang_container)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(line)

        # --- Audio Input Section ---
        audio_widget = QWidget()
        audio_layout = QVBoxLayout(audio_widget)
        audio_layout.setContentsMargins(0,0,0,0)

        audio_btn_row = QHBoxLayout()
        audio_label = QLabel("Audio:")
        self.btn_audio_choose = QPushButton("Choose for file")
        self.btn_audio_record = QPushButton("Record")

        self.btn_audio_choose.clicked.connect(self.open_audio_file)
        self.btn_audio_record.clicked.connect(self.record_audio_stub)

        audio_btn_row.addWidget(audio_label)
        audio_btn_row.addWidget(self.btn_audio_choose)
        audio_btn_row.addWidget(self.btn_audio_record)
        audio_btn_row.addStretch()

        self.lbl_audio_status = QLabel("No file selected")
        self.lbl_audio_status.setStyleSheet("color: gray; font-style: italic;")

        audio_layout.addLayout(audio_btn_row)
        audio_layout.addWidget(self.lbl_audio_status)
        self.main_layout.addWidget(audio_widget)

        # --- Text Input Section ---
        text_group_layout = QVBoxLayout()

        text_top_row = QHBoxLayout()
        text_label = QLabel("Text:")
        self.btn_text_choose = QPushButton("Choose for file")
        or_label = QLabel("Or")

        self.btn_text_choose.clicked.connect(self.open_text_file)

        text_top_row.addWidget(text_label)
        text_top_row.addWidget(self.btn_text_choose)
        text_top_row.addWidget(or_label)
        text_top_row.addStretch()

        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("or write here...")
        self.text_area.setFixedHeight(90)

        text_group_layout.addLayout(text_top_row)
        text_group_layout.addWidget(self.text_area)
        self.main_layout.addLayout(text_group_layout)

        # --- Footer Buttons ---
        footer_layout = QHBoxLayout()
        self.btn_help = QPushButton("Get help")
        self.btn_tutorial = QPushButton("Tutorial")
        self.btn_next = QPushButton("Next")

        self.btn_next.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_next.clicked.connect(self.transition_to_screen_2)

        footer_layout.addWidget(self.btn_help)
        footer_layout.addWidget(self.btn_tutorial)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_next)
        self.main_layout.addLayout(footer_layout)

        # Initial Check
        self.on_lang_text_changed(self.lang_input.text())

    # --- Logic ---

    def on_lang_text_changed(self, text):
        if text != text.lower():
            self.lang_input.blockSignals(True)
            self.lang_input.setText(text.lower())
            self.lang_input.blockSignals(False)
        self.check_dictionary_status()

    def get_dict_path(self):
        language = self.lang_input.text().strip().lower()
        if not language: return None
        lang_folder = os.path.join(self.res_dir, language)
        if self.radio_vocaloid.isChecked():
            return os.path.join(lang_folder, "Vocaloid.txt")
        else:
            return os.path.join(lang_folder, "synthV.txt")

    def check_dictionary_status(self):
        if not hasattr(self, 'lang_status'): return
        dict_path = self.get_dict_path()

        if not dict_path:
            self.lang_status.setText("- Invalid language input")
            self.lang_status.setStyleSheet("color: gray; font-size: 10px;")
            self.btn_create_dict.setEnabled(False)
            return

        if os.path.exists(dict_path):
            self.lang_status.setText(f"- Found the dict at {dict_path}")
            self.lang_status.setStyleSheet("color: green; font-size: 10px;")
            self.btn_create_dict.setEnabled(False)
        else:
            self.lang_status.setText(f"- Missing dict at {dict_path}")
            self.lang_status.setStyleSheet("color: red; font-size: 10px;")
            self.btn_create_dict.setEnabled(True)

    def create_dictionary_manually(self):
        dict_path = self.get_dict_path()
        if dict_path:
            reply = QMessageBox.question(
                self, "Create Dictionary", f"Create placeholder dictionary at:\n{dict_path}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                lang_folder = os.path.dirname(dict_path)
                os.makedirs(lang_folder, exist_ok=True)
                with open(dict_path, 'w') as f: f.write("")
                self.check_dictionary_status()

    def open_audio_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a)")
        if file_name:
            self.selected_audio_file = file_name
            base_name = os.path.basename(file_name)
            dest_path = os.path.join(self.input_dir, base_name)
            try:
                shutil.copy(file_name, dest_path)
                self.copied_audio_filename = base_name
                self.lbl_audio_status.setText(f"Loaded: {base_name} (Copied to tmp/input)")
                self.lbl_audio_status.setStyleSheet("color: green;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to copy file: {e}")

    def record_audio_stub(self):
        QMessageBox.information(self, "Record", "Recording functionality would start here.\nFor now, please use 'Choose for file'.")

    def open_text_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Text File", "", "Text Files (*.txt)")
        if file_name:
            self.selected_text_file = file_name
            self.btn_text_choose.setText(f"Loaded: {os.path.basename(file_name)}")

    def transition_to_screen_2(self):
        """Validates data, saves profile, and launches screen 2"""

        # 1. Validation
        if not self.copied_audio_filename:
            QMessageBox.warning(self, "Missing Audio", "Please select an audio file first.")
            return

        dict_path = self.get_dict_path()
        if not dict_path or not os.path.exists(dict_path):
            QMessageBox.warning(self, "Missing Dictionary", "Dictionary file not found. Please create it or select a valid language.")
            return

        has_text = bool(self.selected_text_file) or bool(self.text_area.toPlainText().strip())
        if not has_text:
            QMessageBox.warning(self, "Missing Text", "Please select a text file or write text manually.")
            return

        # 2. Process Text (Copy/Rename logic)
        audio_name_only = os.path.splitext(self.copied_audio_filename)[0]
        final_text_filename = f"{audio_name_only}.txt"

        if self.selected_text_file:
            # Copy to input dir then rename
            text_filename = os.path.basename(self.selected_text_file)
            current_text_in_tmp = os.path.join(self.input_dir, text_filename)
            if not os.path.exists(current_text_in_tmp):
                shutil.copy(self.selected_text_file, current_text_in_tmp)

            new_text_path = os.path.join(self.input_dir, final_text_filename)
            try:
                os.rename(current_text_in_tmp, new_text_path)
            except OSError: pass # Handle potential overwrite issues silently or warn
        else:
            # Save manual text
            new_text_path = os.path.join(self.input_dir, final_text_filename)
            with open(new_text_path, 'w', encoding='utf-8') as f:
                f.write(self.text_area.toPlainText())

        # 3. Save Profile to tmp
        profile = {
            "language": self.lang_input.text(),
            "engine": "Vocaloid" if self.radio_vocaloid.isChecked() else "Synth V",
            "audio_filename": self.copied_audio_filename,
            "text_filename": final_text_filename,
            "input_dir": self.input_dir,
            "dict_path": dict_path
        }

        profile_path = os.path.join(self.tmp_dir, 'profile.json')
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=4)

        print(f"Profile saved to {profile_path}")

        # 4. Launch Screen 2 and Close Screen 1
        screen2_path = os.path.join(self.script_dir, "vocalistener_gui2.py")

        if os.path.exists(screen2_path):
            try:
                # Popen runs the script in a new process, allowing this one to close
                subprocess.Popen([sys.executable, screen2_path])
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not launch Screen 2: {e}")
        else:
            QMessageBox.warning(self, "Screen 2 Missing", f"Could not find 'vocalistener_gui2.py' in {self.script_dir}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VocalListenerModern()
    window.show()
    sys.exit(app.exec())

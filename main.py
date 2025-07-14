import sys
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)
from llama_cpp import Llama

GOLD = "#d4af37"
BG_DARK = "#111318"
BG_PANEL = "#1a1d23"
TEXT_PLACEHOLDER = "#e5e5e5"
BG_TOP = "#14161c"
BG_BOTTOM = "#0e0f13"


def add_shadow(
    widget: QWidget,
    blur: int = 32,
    x: int = 0,
    y: int = 4,
    opacity: float = 0.5,
):
    """
    Helper. Create shadow for widgets
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setOffset(x, y)
    shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
    widget.setGraphicsEffect(shadow)


class ChatWindow(QWidget):
    """
    Dark‑themed chat UI for interacting with the model
    """

    def __init__(self, model_loader):
        super().__init__()
        self.setWindowTitle("💬 LLaMA Chat (local)")
        self.resize(740, 520)
        self.model_loader = model_loader
        self._llama = None

        font = QFont("Poppins", 11)
        self.setFont(font)

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
        pal.setColor(QPalette.ColorRole.Base, QColor(BG_PANEL))
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.setPalette(pal)

        self.display = QTextEdit(readOnly=True)
        self.display.setStyleSheet(
            f"background: {BG_PANEL}; border: none; border-radius: 12px; padding: 12px;"
        )

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Введите сообщение…")
        self.input_line.setMinimumHeight(44)
        self.input_line.setStyleSheet(
            f"""
            QLineEdit {{
                background: {BG_PANEL};
                border: 1px solid #33393f;
                border-radius: 22px;
                padding: 0 16px;
                color: {TEXT_PLACEHOLDER};
                selection-background-color: {GOLD};
                selection-color: {BG_DARK};
            }}
            QLineEdit::placeholder {{ color: {TEXT_PLACEHOLDER}; }}
            """
        )

        self.send_btn = QPushButton("Отправить")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setMinimumHeight(44)
        self._stylize_button(self.send_btn)

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_line, 1)
        input_row.addWidget(self.send_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.display, 1)
        layout.addLayout(input_row)

        self.input_line.returnPressed.connect(self._on_send)
        self.send_btn.clicked.connect(self._on_send)

        add_shadow(self.display, 40, 0, 6, 0.35)
        add_shadow(self.send_btn, 40, 0, 4, 0.5)

    def _stylize_button(self, btn: QPushButton):
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #282c34, stop:1 #1f2229);
                color: {GOLD};
                border: 1px solid {GOLD};
                border-radius: 22px;
                font: 500 14px 'Poppins';
                padding: 0 28px;
            }}
            QPushButton:hover {{ background: #2e333c; }}
            QPushButton:pressed {{ background: #202227; }}
            """
        )

    def _ensure_model(self):
        """
        Ensure the model is loaded, or load it if not already done
        """
        if self._llama is None:
            self._llama = self.model_loader()

    def _on_send(self):
        """
        Handle sending user input to the model and displaying the response
        """
        user_text = self.input_line.text().strip()
        if not user_text:
            return
        self.input_line.clear()
        self.display.append(
            f"<span style='color:{GOLD};'><b>Вы:</b></span> "
            f"<span style='color:{TEXT_PLACEHOLDER};'>{user_text}</span>"
        )
        try:
            self._ensure_model()
            response = self._llama(user_text, max_tokens=256, temperature=0.7)[
                "choices"
            ][0]["text"].strip()
        except Exception as exc:
            response = f"<span style='color:#e74c3c'>[Ошибка] {exc}</span>"

        self.display.append(
            f"<span style='color:{TEXT_PLACEHOLDER};'><b>LLM:</b></span> "
            f"<span style='color:{TEXT_PLACEHOLDER};'>{response}</span><br><br>"
        )
        sb = self.display.verticalScrollBar()
        sb.setValue(sb.maximum())


class MainWindow(QMainWindow):
    """
    Launcher with two buttons (Load models/Chat)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLaMA Launcher")
        self.resize(520, 420)
        self.setMinimumSize(420, 360)

        self.setFont(QFont("Poppins", 12))

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(BG_BOTTOM))
        pal.setColor(QPalette.ColorRole.Base, QColor(BG_BOTTOM))
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.setPalette(pal)

        title = QLabel(
            f"<span style='color:{TEXT_PLACEHOLDER};'>LLaMA</span> <span style='color:{GOLD};'>Launcher</span>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setFont(QFont("Poppins", 22, QFont.Weight.Bold))

        launch_btn = QPushButton("📂 Загрузить / запустить модель")
        chat_btn = QPushButton("💬 Открыть чат")

        for btn in (launch_btn, chat_btn):
            btn.setMinimumHeight(56)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._stylize_button(btn)
            add_shadow(btn, 40, 0, 6, 0.45)

        central = QWidget()
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(36, 48, 36, 48)
        vbox.setSpacing(32)
        vbox.addWidget(title)
        vbox.addStretch(1)
        vbox.addWidget(launch_btn)
        vbox.addWidget(chat_btn)
        vbox.addStretch(2)
        self.setCentralWidget(central)

        launch_btn.clicked.connect(self._choose_and_load)
        chat_btn.clicked.connect(self._open_chat)

        # Fancy fade‑in animation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(800)
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_anim.start()

    def _stylize_button(self, btn: QPushButton):
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 #20232b, stop:1 #1c1e24);
                color: {GOLD};
                border: 2px solid transparent;
                border-radius: 28px;
                font: 500 15px 'Poppins';
                padding: 0 36px;
            }}
            QPushButton:hover {{
                border: 2px solid {GOLD};
            }}
            QPushButton:pressed {{
                background: #17191f;
            }}
            """
        )

    def _choose_and_load(self):
        """
        Open file dialog to select GGUF model and load it
        """
        filters = "GGUF / GGML Models (*.gguf *.ggml);;All files (*)"
        start_dir = str(Path(__file__).resolve().parent)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите модель", start_dir, filters
        )
        if not file_path:
            return
        self.model_path = Path(file_path)

        reply = QMessageBox.question(
            self,
            "Квантовать?",
            "Запустить модель в 4‑битном квантованном режиме? (быстрее, меньше точности)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        self.quantized = reply == QMessageBox.StandardButton.Yes
        if self.quantized:
            qtype, ok = QInputDialog.getItem(
                self,
                "Метод квантования",
                "Выберите степень квантования:",
                ["Q4_K_M (баланс)", "Q3_K_S (ещё компактнее)", "Q2_K (макс. сжатие)"],
                0,
                False,
            )
            if not ok:
                return
            qtype = qtype.split()[0]
            try:
                self.model_path = self._quantize_model(self.model_path, qtype)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка квантования", str(e))
                return
        try:
            self._load_model()
            QMessageBox.information(self, "Готово", "Модель успешно загружена!")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def _quantize_model(self, src: Path, qtype: str = "Q4_K_M") -> Path:
        """
        Конвертирует GGUF-файл в указанный формат (qtype) с помощью утилиты
        quantize из llama.cpp.  Повторно не квантует, если файл уже есть.
        """
        if ".Q" in src.stem:
            raise RuntimeError(
                f"Файл {src.name} уже содержит квантовку; повторное "
                "квантование не поддерживается.\n"
                "Скачайте FP16-версию модели (.gguf без Q-суффикса)."
            )

        dst = src.with_name(f"{src.stem}.{qtype}.gguf")
        if dst.exists():
            return dst
        dst = src.with_name(f"{src.stem}.{qtype}.gguf")
        if dst.exists():
            return dst

        quant_bin = (
            Path(__file__).resolve().parent
            / "llama_app"
            / (
                "llama-quantize.exe"
                if sys.platform.startswith("win")
                else "llama-quantize"
            )
        ).resolve()

        if not quant_bin.exists():
            raise RuntimeError(f"Не найден quantize: {quant_bin}")

        cmd = [str(quant_bin), str(src), str(dst), qtype]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

        return dst

    def _open_chat(self):
        """
        Open the chat window with the model loader
        """
        self.chat_window = ChatWindow(self._load_model)
        self.chat_window.show()

    def _load_model(self):
        """
        Load the model, or return existing instance if already loaded
        """
        if hasattr(self, "_llama") and self._llama is not None:
            return self._llama
        if not hasattr(self, "model_path"):
            raise RuntimeError("Сначала выберите модель.")
        self._llama = Llama(model_path=str(self.model_path))
        return self._llama


def main():
    """
    Entry point for the application
    """
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("LLaMA GUI")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

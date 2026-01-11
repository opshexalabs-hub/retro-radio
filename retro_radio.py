import sys
import csv
import json
import time
import random
import platform
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QFont, QPainter, QColor, QFontInfo


CSV_FILE = "streams.csv"
SETTINGS_FILE = "settings.json"
DEFAULT_META_DEBOUNCE_SEC = 3.0


# -----------------------------
# VLC detection
# -----------------------------
def check_vlc_and_libvlc():
    try:
        import vlc
    except ImportError:
        return False, "python_vlc_missing"

    if platform.system() == "Darwin":
        if not Path("/Applications/VLC.app").exists():
            return False, "vlc_missing"
    else:
        if not shutil.which("vlc"):
            return False, "vlc_missing"

    try:
        vlc.Instance("--no-video")
    except Exception:
        return False, "libvlc_init_failed"

    return True, None


def show_vlc_error_dialog():
    QMessageBox.critical(
        None,
        "VLC Required",
        "VLC Media Player and python-vlc are required.",
    )
def mono_font(size=13, weight=QFont.Normal):
    for name in (
        "JetBrains Mono",
        "Menlo",          # macOS default monospace
        "SF Mono",
        "Courier New",
    ):
        f = QFont(name, size, weight)
        if QFontInfo(f).family() == name:
            return f
    return QFont(size=size, weight=weight)

# -----------------------------
# Neon Equalizer (visual only)
# -----------------------------
class NeonEqualizer(QWidget):
    def __init__(self, bars=28):
        super().__init__()
        self.bars = bars
        self.levels = [0.0] * bars
        self.volume = 0.8
        self.active = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick_safe)
        self.timer.start(80)

        self.setFixedHeight(48)

    def set_volume(self, value):
        self.volume = max(0.0, min(1.0, value / 100.0))

    def set_active(self, active):
        self.active = active

    def _tick_safe(self):
        try:
            if not self.active:
                self.levels = [l * 0.85 for l in self.levels]
            else:
                for i in range(self.bars):
                    target = random.uniform(0.25, 1.0) * self.volume
                    self.levels[i] += (target - self.levels[i]) * 0.4
            self.update()
        except Exception:
            pass  # NEVER allow Qt slot exceptions on macOS

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        bar_w = rect.width() // self.bars
        on = QColor("#39ff14")
        off = QColor("#0b1f0b")

        for i, level in enumerate(self.levels):
            h = int(level * rect.height())
            r = QRect(
                i * bar_w + 2,
                rect.height() - h,
                bar_w - 4,
                h,
            )
            painter.fillRect(r, on if h > 2 else off)


# -----------------------------
# Main Application
# -----------------------------
class RetroRadio(QMainWindow):
    def __init__(self):
        super().__init__()
        import vlc

        self.setWindowTitle("Retro Radio")
        self.setFixedSize(440, 360)

        self.streams = self.load_streams(CSV_FILE)
        if not self.streams:
            raise RuntimeError("No streams found")

        self.settings = self.load_settings()
        self.current_index = self.restore_last_station()

        self.vlc_instance = vlc.Instance("--no-video")
        self.player = self.vlc_instance.media_player_new()

        # Metadata state
        self.last_played = None
        self.now_playing = None
        self._pending_meta = None
        self._pending_since = 0.0

        self.playing = False

        self.init_ui()

        self.volume_slider.setValue(self.settings.get("volume", 80))
        self.eq.set_volume(self.volume_slider.value())

        self.meta_timer = QTimer(self)
        self.meta_timer.timeout.connect(self._update_metadata_safe)
        self.meta_timer.start(1500)

    # ---------- CSV ----------
    def load_streams(self, filename):
        streams = []
        with Path(filename).open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("url"):
                    continue
                try:
                    debounce = float(row.get("debounce", DEFAULT_META_DEBOUNCE_SEC))
                except Exception:
                    debounce = DEFAULT_META_DEBOUNCE_SEC
                streams.append({
                    "name": row.get("name", row["url"]),
                    "url": row["url"],
                    "debounce": debounce,
                })
        return streams

    @property
    def meta_debounce(self):
        return self.streams[self.current_index]["debounce"]

    # ---------- Settings ----------
    def load_settings(self):
        if Path(SETTINGS_FILE).exists():
            try:
                return json.loads(Path(SETTINGS_FILE).read_text())
            except Exception:
                pass
        return {}

    def restore_last_station(self):
        last = self.settings.get("last_url")
        for i, s in enumerate(self.streams):
            if s["url"] == last:
                return i
        return 0

    def save_settings(self):
        Path(SETTINGS_FILE).write_text(json.dumps({
            "last_url": self.streams[self.current_index]["url"],
            "volume": self.volume_slider.value(),
        }, indent=2))

    # ---------- UI ----------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.last_label = QLabel("")
        self.now_label = QLabel("Tuned to station")
        self.next_label = QLabel("")

        for lbl in (self.last_label, self.now_label, self.next_label):
            lbl.setAlignment(Qt.AlignCenter)

        self.last_label.setStyleSheet("color:#9aa4b2;font-size:10px;")
        self.now_label.setStyleSheet("color:#e6f1ff;font-size:15px;font-weight:600;")
        self.next_label.setStyleSheet("color:#9aa4b2;font-size:10px;")

        # self.now_label.setFont(QFont("JetBrains Mono", 13))
        self.now_label.setFont(mono_font(13, QFont.DemiBold))


        layout.addWidget(self.last_label)
        layout.addWidget(self.now_label)
        layout.addWidget(self.next_label)

        self.eq = NeonEqualizer()
        layout.addWidget(self.eq)

        controls = QHBoxLayout()
        self.prev_btn = QPushButton("⏮")
        self.toggle_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.mute_btn = QPushButton("🔇")

        for b in (self.prev_btn, self.toggle_btn, self.next_btn, self.mute_btn):
            b.setFixedSize(60, 42)

        self.prev_btn.clicked.connect(self.prev_stream)
        self.next_btn.clicked.connect(self.next_stream)
        self.toggle_btn.clicked.connect(self.toggle_playback)
        self.mute_btn.clicked.connect(self.toggle_mute)

        for b in (self.prev_btn, self.toggle_btn, self.next_btn, self.mute_btn):
            controls.addWidget(b)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(self.set_volume)

        layout.addLayout(controls)
        layout.addWidget(self.volume_slider)

        central.setLayout(layout)
        central.setStyleSheet("background:#0b0f14;")

    # ---------- Playback ----------
    def toggle_playback(self):
        self.stop_stream() if self.playing else self.play_stream()

    def play_stream(self):
        self.reset_metadata()
        stream = self.streams[self.current_index]
        media = self.vlc_instance.media_new(stream["url"])
        self.player.set_media(media)
        self.player.play()
        self.set_volume(self.volume_slider.value())

        self.playing = True
        self.toggle_btn.setText("⏹")
        self.eq.set_active(True)

    def stop_stream(self):
        self.player.stop()
        self.playing = False
        self.toggle_btn.setText("▶")
        self.eq.set_active(False)
        self.reset_metadata()

    def next_stream(self):
        self.current_index = (self.current_index + 1) % len(self.streams)
        if self.playing:
            self.play_stream()

    def prev_stream(self):
        self.current_index = (self.current_index - 1) % len(self.streams)
        if self.playing:
            self.play_stream()

    def set_volume(self, value):
        self.player.audio_set_volume(value)
        self.eq.set_volume(value)

    def toggle_mute(self):
        muted = self.player.audio_get_mute()
        self.player.audio_set_mute(not muted)
        self.mute_btn.setText("🔊" if not muted else "🔇")

    # ---------- Metadata ----------
    def reset_metadata(self):
        self.last_played = None
        self.now_playing = None
        self._pending_meta = None
        self._pending_since = 0.0
        self.last_label.setText("")
        self.now_label.setText("Tuning…")
        self.next_label.setText("")

    def _update_metadata_safe(self):
        try:
            self.update_metadata()
        except Exception as e:
            print("Metadata error:", e)

    def update_metadata(self):
        import vlc

        if not self.playing:
            return

        media = self.player.get_media()
        if media is None:
            return

        media.parse_with_options(vlc.MediaParseFlag.network, timeout=300)
        title = media.get_meta(vlc.Meta.NowPlaying)
        if not title:
            return

        now = time.time()

        if self.now_playing is None:
            self.now_playing = title
            self.now_label.setText(title)
            return

        if title == self.now_playing:
            self.next_label.setText("")
            self._pending_meta = None
            return

        if title != self._pending_meta:
            self._pending_meta = title
            self._pending_since = now
            self.next_label.setText(f"Next: {title}")
            return

        if now - self._pending_since >= self.meta_debounce:
            self.last_played = self.now_playing
            self.now_playing = title
            self._pending_meta = None

            self.last_label.setText(f"Last: {self.last_played}")
            self.now_label.setText(self.now_playing)
            self.next_label.setText("")

    # ---------- Exit ----------
    def closeEvent(self, event):
        try:
            self.meta_timer.stop()
            self.eq.timer.stop()
        except Exception:
            pass

        self.save_settings()
        self.player.stop()
        event.accept()


# -----------------------------
# Entry Point
# -----------------------------
def main():
    app = QApplication(sys.argv)

    app.setStyleSheet("""
    QPushButton {
        background:#121821;
        border:1px solid #2de2e6;
        color:#2de2e6;
        border-radius:8px;
        font-size:14px;
    }
    QPushButton:hover { background:#2de2e6; color:#0b0f14; }
    QSlider::groove:horizontal { height:4px; background:#1c2430; }
    QSlider::handle:horizontal { width:14px; background:#2de2e6; }
    """)

    ok, _ = check_vlc_and_libvlc()
    if not ok:
        show_vlc_error_dialog()
        sys.exit(1)

    w = RetroRadio()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

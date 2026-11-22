import os
import sys
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSystemTrayIcon, QMenu, QGraphicsOpacityEffect,
    QDialog, QLineEdit, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QRect, QEvent, QUrl,
    QPropertyAnimation, QParallelAnimationGroup, QEasingCurve
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QDesktopServices
from checker import cek_fakta, muat_api_key, simpan_api_key

# Kode tombol virtual Windows (Ctrl + Shift + H)
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_C = 0x43
VK_H = 0x48
KEYEVENTF_KEYUP = 0x0002


def dapatkan_resource_path(nama_file: str) -> str:
    """Mencari file aset baik saat dijalankan via Python maupun setelah dibungkus PyInstaller."""
    kandidat = []
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            kandidat.append(os.path.join(sys._MEIPASS, nama_file))
        kandidat.append(os.path.join(os.path.dirname(sys.executable), nama_file))
    kandidat.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), nama_file))

    for path in kandidat:
        if os.path.exists(path):
            return path
    return ""


class ApiKeyDialog(QDialog):
    """Jendela pengaturan flat agar pengguna dapat memasukkan atau mengganti Groq API Key."""
    def __init__(self, parent=None, ikon_app: QIcon | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan Groq API Key - HoaxIsland")
        if ikon_app:
            self.setWindowIcon(ikon_app)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181B;
                color: #F4F4F5;
                font-family: 'Segoe UI';
            }
            QLabel {
                color: #F4F4F5;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1.5px solid #3F3F46;
                border-radius: 8px;
                padding: 8px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1.5px solid #3B82F6;
            }
            QPushButton {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
            QPushButton#primaryBtn {
                background-color: #2563EB;
                border: 1px solid #3B82F6;
                color: #FFFFFF;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1D4ED8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        judul = QLabel("Masukkan atau Ganti Groq API Key")
        judul.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(judul)

        deskripsi = QLabel(
            "HoaxIsland menggunakan Groq AI untuk memverifikasi klaim berita. "
            "Anda bisa mendapatkan API Key gratis di console.groq.com dan menyimpannya "
            "secara lokal di perangkat ini."
        )
        deskripsi.setWordWrap(True)
        deskripsi.setStyleSheet("color: #A1A1AA; font-size: 11.5px;")
        layout.addWidget(deskripsi)

        link_btn = QPushButton("Buka console.groq.com/keys (Buat API Key Gratis)")
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://console.groq.com/keys"))
        )
        layout.addWidget(link_btn)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("Tempel API Key baru di sini (diawali gsk_...)")
        self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
        kunci_sekarang = muat_api_key()
        if kunci_sekarang:
            self.input_key.setText(kunci_sekarang)

        self.toggle_btn = QPushButton("Lihat")
        self.toggle_btn.setFixedWidth(64)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_visibilitas)

        input_row.addWidget(self.input_key)
        input_row.addWidget(self.toggle_btn)
        layout.addLayout(input_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        batal_btn = QPushButton("Batal")
        batal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        batal_btn.clicked.connect(self.reject)

        simpan_btn = QPushButton("Simpan API Key")
        simpan_btn.setObjectName("primaryBtn")
        simpan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        simpan_btn.clicked.connect(self._simpan_dan_tutup)

        btn_row.addWidget(batal_btn)
        btn_row.addWidget(simpan_btn)
        layout.addLayout(btn_row)

    def _toggle_visibilitas(self):
        if self.input_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Tutup")
        else:
            self.input_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Lihat")

    def _simpan_dan_tutup(self):
        nilai = self.input_key.text().strip()
        if not nilai:
            QMessageBox.warning(self, "Kolom Kosong", "Silakan tempel Groq API Key Anda terlebih dahulu.")
            return
        if not nilai.startswith("gsk_"):
            konfirmasi = QMessageBox.question(
                self,
                "Format API Key",
                "Groq API Key umumnya diawali dengan 'gsk_'. Tetap simpan kunci ini?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if konfirmasi != QMessageBox.StandardButton.Yes:
                return

        if simpan_api_key(nilai):
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal Menyimpan", "Tidak dapat menulis file konfigurasi ke AppData.")


class FactCheckWorker(QThread):
    """Menjalankan riset berita & AI di latar belakang agar UI tetap responsif."""
    selesai = pyqtSignal(dict)

    def __init__(self, teks: str):
        super().__init__()
        self.teks = teks

    def run(self):
        hasil = cek_fakta(self.teks)
        self.selesai.emit(hasil)


class DynamicIslandWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.sedang_memproses = False
        self.menampilkan_hasil = False
        self.mode_poni = True
        self.dialog_terbuka = False
        self.titik_loading = 0
        self.hotkey_ditahan = False
        self.hasil_terakhir = {}
        self.ikon_app = QIcon()
        self.worker = None

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_animasi_loading)

        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self._cek_lipat_otomatis)

        self.init_ui()
        self.init_animations()
        self.init_tray()
        self.init_hotkey_listener()

        # Mulai langsung dalam wujud poni tipis minimalis
        self.set_notch_state(animasi=False)

        # Jika API Key belum pernah diisi pengguna, buka dialog pengaturan saat pertama dijalankan
        if not muat_api_key():
            QTimer.singleShot(250, self.buka_pengaturan_api_key)

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        # Kanvas luar transparan berukuran tetap agar animasi berjalan mulus 60fps
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.x(), screen.y(), 480, 620)

        # Wadah kapsul internal yang ukurannya dianimasikan secara bebas
        self.container = QWidget(self)
        self.container.setObjectName("capsule")
        self.container.installEventFilter(self)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(16, 10, 16, 12)
        self.container_layout.setSpacing(8)

        # Indikator garis biru ultra-tipis saat mode poni
        self.notch_bar = QWidget(self.container)
        self.notch_bar.setFixedSize(36, 2)
        self.notch_bar.setStyleSheet("""
            background-color: #3B82F6;
            border-radius: 1px;
        """)

        # Wadah konten teks (untuk animasi fade-in/out yang mulus)
        self.content_widget = QWidget(self.container)
        self.content_widget.setStyleSheet("background: transparent;")
        self.opacity_effect = QGraphicsOpacityEffect(self.content_widget)
        self.opacity_effect.setOpacity(0.0)
        self.content_widget.setGraphicsEffect(self.opacity_effect)

        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Baris atas: Status, tombol Ganti API, & tombol keluar aplikasi
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        self.status_label = QLabel("")

        self.header_api_btn = QPushButton("⚙ Ganti API")
        self.header_api_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_api_btn.setToolTip("Ubah atau masukkan Groq API Key")
        self.header_api_btn.setStyleSheet("""
            QPushButton {
                background-color: #27272A;
                color: #D4D4D8;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 2px 8px;
                font-family: 'Segoe UI';
                font-size: 10.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
            }
        """)
        self.header_api_btn.clicked.connect(self.buka_pengaturan_api_key)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Keluar dari aplikasi")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A1A1AA;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { color: #EF4444; }
        """)
        self.close_btn.clicked.connect(QApplication.quit)

        top_row.addWidget(self.status_label)
        top_row.addStretch()
        top_row.addWidget(self.header_api_btn)
        top_row.addWidget(self.close_btn)
        content_layout.addLayout(top_row)

        # Label ringkasan hasil analisis
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary_label.setStyleSheet(
            "color: #F4F4F5; font-family: 'Segoe UI'; font-size: 12px;"
        )
        self.summary_label.hide()
        content_layout.addWidget(self.summary_label)

        # Label sumber rujukan
        self.source_label = QLabel("")
        self.source_label.setWordWrap(True)
        self.source_label.setStyleSheet(
            "color: #A1A1AA; font-family: 'Segoe UI'; font-size: 11px;"
        )
        self.source_label.hide()
        content_layout.addWidget(self.source_label)

        # Label indikator kuota token real-time
        self.quota_label = QLabel("")
        self.quota_label.setWordWrap(True)
        self.quota_label.setStyleSheet(
            "color: #71717A; font-family: 'Segoe UI'; font-size: 10.5px;"
        )
        self.quota_label.hide()
        content_layout.addWidget(self.quota_label)

        # Baris tombol aksi di bagian bawah hasil
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(6)

        gaya_tombol_sekunder = """
            QPushButton {
                background-color: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 7px;
                padding: 5px 10px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3F3F46; }
        """

        self.api_btn = QPushButton("Atur API Key")
        self.api_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.api_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #DBEAFE;
                border: 1px solid #2563EB;
                border-radius: 7px;
                padding: 5px 10px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.api_btn.clicked.connect(self.buka_pengaturan_api_key)
        self.api_btn.hide()

        self.copy_btn = QPushButton("Salin Hasil")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet(gaya_tombol_sekunder)
        self.copy_btn.clicked.connect(self.salin_hasil)
        self.copy_btn.hide()

        self.source_btn = QPushButton("Kunjungi Sumber")
        self.source_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.source_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #DBEAFE;
                border: 1px solid #2563EB;
                border-radius: 7px;
                padding: 5px 10px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.source_btn.clicked.connect(self.kunjungi_sumber)
        self.source_btn.hide()

        self.reset_btn = QPushButton("Lipat ke Poni")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet(gaya_tombol_sekunder)
        self.reset_btn.clicked.connect(self.tutup_hasil_ke_poni)
        self.reset_btn.hide()

        self.action_row.addWidget(self.api_btn)
        self.action_row.addWidget(self.copy_btn)
        self.action_row.addWidget(self.source_btn)
        self.action_row.addWidget(self.reset_btn)
        content_layout.addLayout(self.action_row)

        self.container_layout.addWidget(self.content_widget)

    def init_animations(self):
        self.anim_group = QParallelAnimationGroup(self)

        self.geo_anim = QPropertyAnimation(self.container, b"geometry", self)
        self.geo_anim.setDuration(260)
        self.geo_anim.setEasingCurve(QEasingCurve.Type.OutQuint)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setDuration(200)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_group.addAnimation(self.geo_anim)
        self.anim_group.addAnimation(self.fade_anim)
        self.anim_group.finished.connect(self._on_animasi_selesai)

    def _on_animasi_selesai(self):
        if self.mode_poni:
            self.content_widget.hide()
            self.notch_bar.show()

    def init_tray(self):
        path_ikon = dapatkan_resource_path("icon.png")
        if path_ikon:
            self.ikon_app = QIcon(path_ikon)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#3B82F6"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 24, 24)
            painter.end()
            self.ikon_app = QIcon(pixmap)

        self.setWindowIcon(self.ikon_app)
        self.tray_icon = QSystemTrayIcon(self.ikon_app, self)
        self.tray_icon.setToolTip("HoaxIsland (Seret teks ke poni kiri atas atau tekan Ctrl+Shift+H)")

        menu = QMenu()
        aksi_cek_clipboard = QAction("Periksa Teks di Clipboard (Ctrl+Shift+H)", self)
        aksi_cek_clipboard.triggered.connect(self._baca_clipboard_dan_proses)

        aksi_api = QAction("Atur / Ganti Groq API Key...", self)
        aksi_api.triggered.connect(self.buka_pengaturan_api_key)

        aksi_manual = QAction("Buka Manual Book", self)
        aksi_manual.triggered.connect(self.buka_manual_book)

        aksi_buka = QAction("Buka Kapsul", self)
        aksi_buka.triggered.connect(self.set_standby_state)

        aksi_poni = QAction("Lipat ke Poni", self)
        aksi_poni.triggered.connect(self.tutup_hasil_ke_poni)

        aksi_keluar = QAction("Keluar", self)
        aksi_keluar.triggered.connect(QApplication.quit)

        menu.addAction(aksi_cek_clipboard)
        menu.addAction(aksi_api)
        menu.addAction(aksi_manual)
        menu.addSeparator()
        menu.addAction(aksi_buka)
        menu.addAction(aksi_poni)
        menu.addSeparator()
        menu.addAction(aksi_keluar)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def buka_pengaturan_api_key(self):
        self.dialog_terbuka = True
        self.collapse_timer.stop()
        try:
            dialog = ApiKeyDialog(self, self.ikon_app)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if self.menampilkan_hasil and self.hasil_terakhir.get("butuh_api_key"):
                    self.tutup_hasil_ke_poni()
                self.tray_icon.showMessage(
                    "HoaxIsland",
                    "Groq API Key berhasil diperbarui. Aplikasi siap digunakan.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500
                )
        finally:
            self.dialog_terbuka = False
            self._cek_lipat_otomatis()

    def buka_manual_book(self):
        path_manual = dapatkan_resource_path("Manual_Book_HoaxIsland.txt")
        if path_manual:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path_manual))
        else:
            QMessageBox.information(
                self,
                "Manual Book",
                "File Manual_Book_HoaxIsland.txt tidak ditemukan di folder instalasi."
            )

    # --- Aksi Tombol Hasil ---
    def salin_hasil(self):
        if not self.hasil_terakhir:
            return
        status = self.hasil_terakhir.get("status", "-")
        ringkasan = self.hasil_terakhir.get("ringkasan", "-")
        sumber = self.hasil_terakhir.get("sumber", "-")
        url = self.hasil_terakhir.get("url", "")

        teks_salinan = f"[{status}]\n{ringkasan}\nSumber: {sumber}"
        if url:
            teks_salinan += f"\nReferensi: {url}"

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(teks_salinan)

        self.copy_btn.setText("✓ Tersalin")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Salin Hasil"))

    def kunjungi_sumber(self):
        url = self.hasil_terakhir.get("url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    # --- Pemantau Pintasan Keyboard (Ctrl + Shift + H) ---
    def init_hotkey_listener(self):
        if sys.platform == "win32":
            self.hotkey_timer = QTimer(self)
            self.hotkey_timer.timeout.connect(self._pantau_tombol_hotkey)
            self.hotkey_timer.start(45)

    def _pantau_tombol_hotkey(self):
        user32 = ctypes.windll.user32
        ctrl = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        shift = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
        tombol_h = (user32.GetAsyncKeyState(VK_H) & 0x8000) != 0

        if ctrl and shift and tombol_h:
            if not self.hotkey_ditahan:
                self.hotkey_ditahan = True
                self.picu_dari_hotkey()
        else:
            self.hotkey_ditahan = False

    def picu_dari_hotkey(self):
        if self.sedang_memproses:
            return

        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_C, 0, 0, 0)
            user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        QTimer.singleShot(110, self._baca_clipboard_dan_proses)

    def _baca_clipboard_dan_proses(self):
        if self.sedang_memproses:
            return
        clipboard = QApplication.clipboard()
        teks = clipboard.text().strip() if clipboard else ""
        self.mulai_analisis(teks, dari_hotkey=True)

    # --- Tata Letak & Animasi Kapsul ---
    def _animasikan_kapsul(self, target_w: int, target_h: int, target_opacity: float, animasi: bool = True):
        target_rect = QRect(12, 0, target_w, target_h)
        self.anim_group.stop()

        if not animasi:
            self.container.setGeometry(target_rect)
            self.opacity_effect.setOpacity(target_opacity)
            self._on_animasi_selesai()
            return

        self.geo_anim.setStartValue(self.container.geometry())
        self.geo_anim.setEndValue(target_rect)

        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(target_opacity)

        self.fade_anim.setDuration(110 if target_opacity == 0.0 else 220)
        self.geo_anim.setDuration(240 if target_opacity == 0.0 else 280)

        self.anim_group.start()

    def _hitung_tinggi_target(self, target_w: int) -> int:
        lebar_dalam = target_w - 32
        self.content_widget.setFixedWidth(lebar_dalam)
        self.content_widget.layout().activate()
        tinggi_konten = self.content_widget.sizeHint().height()
        return max(44, tinggi_konten + 22)

    def _sembunyikan_tombol_aksi(self):
        self.api_btn.hide()
        self.copy_btn.hide()
        self.source_btn.hide()
        self.reset_btn.hide()

    def tutup_hasil_ke_poni(self):
        self.menampilkan_hasil = False
        self.set_notch_state(animasi=True)

    def set_notch_state(self, animasi: bool = True):
        if self.sedang_memproses or self.menampilkan_hasil or self.dialog_terbuka:
            return
        self.mode_poni = True
        self.loading_timer.stop()

        self.container.setStyleSheet("""
            #capsule {
                background-color: #18181B;
                border-left: 1px solid #3F3F46;
                border-right: 1px solid #3F3F46;
                border-bottom: 1px solid #3F3F46;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
        """)
        self.notch_bar.move((100 - self.notch_bar.width()) // 2, 4)
        if not animasi:
            self.notch_bar.show()
            self.content_widget.hide()

        self._animasikan_kapsul(100, 10, 0.0, animasi=animasi)

    def set_standby_state(self):
        if self.sedang_memproses or self.menampilkan_hasil:
            return
        self.mode_poni = False
        self.collapse_timer.stop()

        self.container.setStyleSheet("""
            #capsule {
                background-color: #18181B;
                border-left: 1.5px solid #3F3F46;
                border-right: 1.5px solid #3F3F46;
                border-bottom: 1.5px solid #3F3F46;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }
        """)
        self.notch_bar.hide()
        self.content_widget.show()
        self.status_label.setText("● Seret teks / tekan Ctrl+Shift+H")
        self.status_label.setStyleSheet(
            "color: #F4F4F5; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;"
        )
        self.header_api_btn.show()
        self.summary_label.hide()
        self.source_label.hide()
        self.quota_label.hide()
        self._sembunyikan_tombol_aksi()

        target_w = 345
        target_h = self._hitung_tinggi_target(target_w)
        self._animasikan_kapsul(target_w, target_h, 1.0, animasi=True)

    def set_hover_state(self):
        self.mode_poni = False
        self.collapse_timer.stop()

        self.container.setStyleSheet("""
            #capsule {
                background-color: #1E293B;
                border-left: 2px solid #3B82F6;
                border-right: 2px solid #3B82F6;
                border-bottom: 2px solid #3B82F6;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }
        """)
        self.notch_bar.hide()
        self.content_widget.show()
        self.status_label.setText("↓ Lepaskan teks untuk memverifikasi...")
        self.status_label.setStyleSheet(
            "color: #60A5FA; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;"
        )
        self.header_api_btn.hide()
        self.summary_label.hide()
        self.source_label.hide()
        self.quota_label.hide()
        self._sembunyikan_tombol_aksi()

        target_w = 340
        target_h = self._hitung_tinggi_target(target_w)
        self._animasikan_kapsul(target_w, target_h, 1.0, animasi=True)

    def set_loading_state(self, teks_masuk: str):
        self.sedang_memproses = True
        self.menampilkan_hasil = False
        self.mode_poni = False
        self.collapse_timer.stop()
        self.titik_loading = 0
        cuplikan = teks_masuk if len(teks_masuk) <= 95 else teks_masuk[:95] + "..."

        self.container.setStyleSheet("""
            #capsule {
                background-color: #18181B;
                border-left: 1.5px solid #3B82F6;
                border-right: 1.5px solid #3B82F6;
                border-bottom: 1.5px solid #3B82F6;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }
        """)
        self.notch_bar.hide()
        self.content_widget.show()
        self.status_label.setText("◐ Meriset berita & memverifikasi")
        self.status_label.setStyleSheet(
            "color: #60A5FA; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;"
        )
        self.header_api_btn.hide()

        target_w = 400
        self.summary_label.setFixedWidth(target_w - 32)
        self.summary_label.setText(f'"{cuplikan}"')
        self.summary_label.setStyleSheet(
            "color: #A1A1AA; font-family: 'Segoe UI'; font-size: 11px; font-style: italic;"
        )
        self.summary_label.show()
        self.source_label.hide()
        self.quota_label.hide()
        self._sembunyikan_tombol_aksi()

        target_h = self._hitung_tinggi_target(target_w)
        self._animasikan_kapsul(target_w, target_h, 1.0, animasi=True)
        self.loading_timer.start(350)

    def update_animasi_loading(self):
        ikon = ["◐", "◓", "◑", "◒"][self.titik_loading % 4]
        titik = "." * ((self.titik_loading % 3) + 1)
        self.status_label.setText(f"{ikon} Meriset berita & memverifikasi{titik}")
        self.titik_loading += 1

    def show_result_state(self, hasil: dict):
        self.sedang_memproses = False
        self.menampilkan_hasil = True
        self.mode_poni = False
        self.loading_timer.stop()
        self.hasil_terakhir = hasil

        status = hasil.get("status", "BELUM TERVERIFIKASI").upper()
        ringkasan = hasil.get("ringkasan", "-")
        sumber = hasil.get("sumber", "-")
        url = hasil.get("url", "")
        is_direct = hasil.get("is_direct_url", False)
        butuh_api_key = hasil.get("butuh_api_key", False)
        kuota = hasil.get("kuota", "")

        if "FAKTA" in status:
            warna = "#10B981"
            ikon = "✓"
        elif "HOAKS" in status or "ERROR" in status or "API KEY" in status:
            warna = "#EF4444"
            ikon = "✕"
        elif "MENYESATKAN" in status:
            warna = "#F59E0B"
            ikon = "!"
        else:
            warna = "#38BDF8"
            ikon = "?"

        self.container.setStyleSheet(f"""
            #capsule {{
                background-color: #18181B;
                border-left: 1.5px solid {warna};
                border-right: 1.5px solid {warna};
                border-bottom: 1.5px solid {warna};
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
        """)
        self.notch_bar.hide()
        self.content_widget.show()
        self.status_label.setText(f"{ikon} {status}")
        self.status_label.setStyleSheet(
            f"color: {warna}; font-family: 'Segoe UI'; font-size: 13px; font-weight: bold;"
        )
        self.header_api_btn.show()

        target_w = 440
        lebar_teks = target_w - 32
        self.summary_label.setFixedWidth(lebar_teks)
        self.summary_label.setText(ringkasan)
        self.summary_label.setStyleSheet(
            "color: #F4F4F5; font-family: 'Segoe UI'; font-size: 12px;"
        )
        self.summary_label.show()

        if sumber and sumber != "-":
            self.source_label.setFixedWidth(lebar_teks)
            self.source_label.setText(f"Sumber: {sumber}")
            self.source_label.show()
        else:
            self.source_label.hide()

        if kuota:
            self.quota_label.setFixedWidth(lebar_teks)
            self.quota_label.setText(f"⚡ {kuota}")
            self.quota_label.show()
            self.tray_icon.setToolTip(f"HoaxIsland\n{kuota}")
        else:
            self.quota_label.hide()

        self._sembunyikan_tombol_aksi()

        if butuh_api_key:
            self.api_btn.show()
        else:
            self.copy_btn.setText("Salin Hasil")
            self.copy_btn.show()
            if url:
                self.source_btn.setText("Kunjungi Sumber" if is_direct else "Cari di Google")
                self.source_btn.show()

        self.reset_btn.show()

        target_h = self._hitung_tinggi_target(target_w)
        self._animasikan_kapsul(target_w, target_h, 1.0, animasi=True)

    def mulai_analisis(self, teks: str, dari_hotkey: bool = False):
        if len(teks) < 10:
            pesan = (
                "Tidak ada teks yang diblok atau teks terlalu pendek. Blok minimal satu kalimat lalu tekan Ctrl + Shift + H."
                if dari_hotkey
                else "Teks terlalu pendek. Seret minimal satu kalimat klaim untuk diperiksa."
            )
            self.show_result_state({
                "status": "BELUM TERVERIFIKASI",
                "ringkasan": pesan,
                "sumber": "-",
                "url": "",
                "is_direct_url": False,
                "butuh_api_key": False,
                "kuota": ""
            })
            return

        self.set_loading_state(teks)
        self.worker = FactCheckWorker(teks)
        self.worker.selesai.connect(self.show_result_state)
        self.worker.start()

    # --- Deteksi Kursor Kosong langsung pada Kapsul ---
    def eventFilter(self, obj, event):
        if obj is self.container:
            if event.type() == QEvent.Type.Enter:
                self.collapse_timer.stop()
                if not self.sedang_memproses and not self.menampilkan_hasil and self.mode_poni:
                    self.set_standby_state()
            elif event.type() == QEvent.Type.Leave:
                if not self.sedang_memproses and not self.menampilkan_hasil and not self.mode_poni and not self.dialog_terbuka:
                    self.collapse_timer.start(260)
        return super().eventFilter(obj, event)

    def _cek_lipat_otomatis(self):
        if not self.container.underMouse() and not self.sedang_memproses and not self.menampilkan_hasil and not self.dialog_terbuka:
            self.set_notch_state(animasi=True)

    # --- Event Drag-and-Drop ---
    def dragEnterEvent(self, event):
        self.collapse_timer.stop()
        if not self.sedang_memproses and event.mimeData().hasText():
            event.acceptProposedAction()
            self.set_hover_state()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if not self.sedang_memproses and not self.menampilkan_hasil:
            self.set_notch_state(animasi=True)

    def dropEvent(self, event):
        if self.sedang_memproses:
            event.ignore()
            return

        teks = event.mimeData().text().strip()
        event.acceptProposedAction()
        self.mulai_analisis(teks, dari_hotkey=False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    island = DynamicIslandWidget()
    island.show()
    print("HoaxIsland aktif. Seret teks ke poni kiri atas atau blok teks lalu tekan Ctrl+Shift+H.")
    sys.exit(app.exec())
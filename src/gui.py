"""
gui.py
Interface graphique PySide6 : fenêtre principale (statut, hashrate,
stats pour le profil CPU et/ou GPU selon le mode choisi, boutons
Démarrer/Arrêter/Paramètres, journal d'événements) et dialogue de
paramètres (mode de minage, pool/wallet/worker CPU et GPU, chemins des
exécutables).
"""

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QDialog,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QGroupBox,
    QFrame,
)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from config_manager import (
    MinerConfig,
    load_config,
    save_config,
    validate_config,
    ConfigError,
)
from miner_controller import MinerController
from gpu_miner_controller import GpuMinerController
from market_data_worker import MarketDataWorker
from market_data import estimate_earnings, format_time_estimate, format_btc
from utils import format_hashrate, get_default_miner_dir, get_default_gpu_miner_dir


STATUS_LABELS = {
    "arrete": "Arrêté",
    "en_cours": "En cours",
    "erreur": "Erreur",
}

STATUS_COLORS = {
    "arrete": "#888888",
    "en_cours": "#2e7d32",
    "erreur": "#c62828",
}

MODE_LABELS = {
    "cpu": "CPU uniquement",
    "gpu": "GPU uniquement",
    "both": "CPU + GPU simultanément",
}
MODE_BY_LABEL = {v: k for k, v in MODE_LABELS.items()}

GPU_ALGO_LABELS = {
    "AUTOLYKOS2": "Autolykos2 (Ergo) — nécessite ~7 Go VRAM",
    "ETHASH": "Ethash (OctaSpace) — fonctionne dès ~3 Go VRAM",
}

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
LOGO_PNG = os.path.join(ASSETS_DIR, "icon.png")
LOGO_ICO = os.path.join(ASSETS_DIR, "icon.ico")

STYLESHEET = """
QMainWindow, QDialog {
    background-color: #121214;
}
QWidget {
    color: #e8e6e1;
    font-family: "Segoe UI";
}
QGroupBox#Card {
    background-color: #1b1b1e;
    border: 1px solid #2b2b2f;
    border-radius: 12px;
    margin-top: 14px;
    padding: 12px 8px 8px 8px;
    font-weight: 600;
}
QGroupBox#Card::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #f0a838;
}
QLabel {
    background: transparent;
}
QPushButton {
    background-color: #26262b;
    border: 1px solid #34343a;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    color: #e8e6e1;
}
QPushButton:hover {
    background-color: #313136;
    border-color: #f0a838;
}
QPushButton:disabled {
    color: #6a6a6f;
    background-color: #1e1e21;
    border-color: #26262b;
}
QPushButton#PrimaryButton {
    background-color: #f0a838;
    border: none;
    color: #171308;
}
QPushButton#PrimaryButton:hover {
    background-color: #ffb84d;
}
QPushButton#PrimaryButton:disabled {
    background-color: #4a3d22;
    color: #8a7a55;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #1e1e22;
    border: 1px solid #34343a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #e8e6e1;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #f0a838;
}
QTextEdit {
    background-color: #17171a;
    border: 1px solid #2b2b2f;
    border-radius: 8px;
    color: #cfcfcf;
}
QComboBox QAbstractItemView {
    background-color: #1e1e22;
    color: #e8e6e1;
    selection-background-color: #f0a838;
    selection-color: #171308;
}
QScrollBar:vertical {
    background: #17171a;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #34343a;
    border-radius: 5px;
}
"""


class SettingsDialog(QDialog):
    def __init__(self, config: MinerConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres")
        self.setMinimumWidth(520)
        self._config = config

        layout = QVBoxLayout(self)

        mode_group = QGroupBox("Mode de minage")
        mode_form = QFormLayout(mode_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(list(MODE_LABELS.values()))
        self.mode_combo.setCurrentText(MODE_LABELS.get(config.mining_mode, MODE_LABELS["cpu"]))
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_form.addRow("Utiliser :", self.mode_combo)
        layout.addWidget(mode_group)

        mode_note = QLabel(
            "CPU mine du Bitcoin (SHA-256d). Il n'existe pas de mineur GPU "
            "Bitcoin légitime maintenu aujourd'hui (ASIC uniquement) : le mode "
            "GPU mine donc une autre crypto GPU-friendly, avec son propre "
            "wallet. Autolykos2 (Ergo) demande beaucoup de VRAM (~7 Go) ; "
            "Ethash (OctaSpace) convient aux cartes plus modestes (~3 Go). "
            "En mode \"CPU + GPU\", les deux tournent en parallèle, "
            "indépendamment, vers deux pools distincts."
        )
        mode_note.setWordWrap(True)
        mode_note.setStyleSheet("color:#666666; font-size:10px;")
        layout.addWidget(mode_note)

        # --- Profil CPU ---
        self.cpu_group = QGroupBox("Pool CPU (Bitcoin)")
        cpu_form = QFormLayout(self.cpu_group)

        self.pool_host_edit = QLineEdit(config.pool_host)
        self.pool_host_edit.setPlaceholderText("stratum.pool-exemple.com")
        cpu_form.addRow("Adresse du pool :", self.pool_host_edit)

        self.pool_port_spin = QSpinBox()
        self.pool_port_spin.setRange(1, 65535)
        self.pool_port_spin.setValue(config.pool_port)
        cpu_form.addRow("Port :", self.pool_port_spin)

        self.wallet_edit = QLineEdit(config.wallet_address)
        self.wallet_edit.setPlaceholderText("Adresse wallet Bitcoin")
        cpu_form.addRow("Adresse wallet :", self.wallet_edit)

        self.worker_edit = QLineEdit(config.worker_name)
        cpu_form.addRow("Nom du worker :", self.worker_edit)

        exe_row = QHBoxLayout()
        self.exe_edit = QLineEdit(config.miner_executable)
        self.exe_edit.setPlaceholderText(
            os.path.join(get_default_miner_dir(), "cpuminer-multi.exe")
        )
        browse_btn = QPushButton("Parcourir...")
        browse_btn.clicked.connect(self._browse_cpu_executable)
        exe_row.addWidget(self.exe_edit)
        exe_row.addWidget(browse_btn)
        cpu_form.addRow("Exécutable mineur CPU :", exe_row)

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(0, 128)
        self.threads_spin.setValue(config.threads)
        self.threads_spin.setSpecialValueText("Auto (toutes les threads)")
        cpu_form.addRow("Threads CPU :", self.threads_spin)

        layout.addWidget(self.cpu_group)

        # --- Profil GPU ---
        self.gpu_group = QGroupBox("Pool GPU")
        gpu_form = QFormLayout(self.gpu_group)

        self.gpu_algo_combo = QComboBox()
        self.gpu_algo_combo.addItems(list(GPU_ALGO_LABELS.values()))
        self.gpu_algo_combo.setCurrentText(
            GPU_ALGO_LABELS.get(config.gpu_algo, GPU_ALGO_LABELS["AUTOLYKOS2"])
        )
        gpu_form.addRow("Algorithme :", self.gpu_algo_combo)

        self.gpu_pool_host_edit = QLineEdit(config.gpu_pool_host)
        self.gpu_pool_host_edit.setPlaceholderText(
            "ergo-eu1.nanopool.org (Ergo) ou octa.kryptex.network (OctaSpace)"
        )
        gpu_form.addRow("Adresse du pool :", self.gpu_pool_host_edit)

        self.gpu_pool_port_spin = QSpinBox()
        self.gpu_pool_port_spin.setRange(1, 65535)
        self.gpu_pool_port_spin.setValue(config.gpu_pool_port)
        gpu_form.addRow("Port :", self.gpu_pool_port_spin)

        self.gpu_wallet_edit = QLineEdit(config.gpu_wallet_address)
        self.gpu_wallet_edit.setPlaceholderText("Adresse wallet Ergo")
        gpu_form.addRow("Adresse wallet :", self.gpu_wallet_edit)

        self.gpu_worker_edit = QLineEdit(config.gpu_worker_name)
        gpu_form.addRow("Nom du worker :", self.gpu_worker_edit)

        gpu_exe_row = QHBoxLayout()
        self.gpu_exe_edit = QLineEdit(config.gpu_miner_executable)
        self.gpu_exe_edit.setPlaceholderText(
            os.path.join(get_default_gpu_miner_dir(), "lolMiner.exe")
        )
        gpu_browse_btn = QPushButton("Parcourir...")
        gpu_browse_btn.clicked.connect(self._browse_gpu_executable)
        gpu_exe_row.addWidget(self.gpu_exe_edit)
        gpu_exe_row.addWidget(gpu_browse_btn)
        gpu_form.addRow("Exécutable mineur GPU :", gpu_exe_row)

        layout.addWidget(self.gpu_group)

        warning = QLabel(
            "⚠️ Le minage CPU n'est pas rentable (matériel ASIC requis pour "
            "Bitcoin). Le minage GPU peut l'être marginalement selon le "
            "matériel et le prix de l'électricité, mais reste variable. "
            "Cette application est un outil réel de connexion à un pool, "
            "fourni à but éducatif/démonstratif."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #b45309; font-size: 11px;")
        layout.addWidget(warning)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_mode_changed(self.mode_combo.currentText())

    def _on_mode_changed(self, label: str) -> None:
        mode = MODE_BY_LABEL.get(label, "cpu")
        self.cpu_group.setVisible(mode in ("cpu", "both"))
        self.gpu_group.setVisible(mode in ("gpu", "both"))

    def _browse_cpu_executable(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner l'exécutable du mineur CPU", get_default_miner_dir(),
            "Exécutables (*.exe);;Tous les fichiers (*)"
        )
        if path:
            self.exe_edit.setText(path)

    def _browse_gpu_executable(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner l'exécutable du mineur GPU", get_default_gpu_miner_dir(),
            "Exécutables (*.exe);;Tous les fichiers (*)"
        )
        if path:
            self.gpu_exe_edit.setText(path)

    def _on_save(self) -> None:
        gpu_algo_key = next(
            (k for k, v in GPU_ALGO_LABELS.items() if v == self.gpu_algo_combo.currentText()),
            "AUTOLYKOS2",
        )
        new_config = MinerConfig(
            mining_mode=MODE_BY_LABEL.get(self.mode_combo.currentText(), "cpu"),
            pool_host=self.pool_host_edit.text().strip(),
            pool_port=self.pool_port_spin.value(),
            wallet_address=self.wallet_edit.text().strip(),
            worker_name=self.worker_edit.text().strip(),
            miner_executable=self.exe_edit.text().strip(),
            threads=self.threads_spin.value(),
            gpu_pool_host=self.gpu_pool_host_edit.text().strip(),
            gpu_pool_port=self.gpu_pool_port_spin.value(),
            gpu_wallet_address=self.gpu_wallet_edit.text().strip(),
            gpu_worker_name=self.gpu_worker_edit.text().strip(),
            gpu_miner_executable=self.gpu_exe_edit.text().strip(),
            gpu_algo=gpu_algo_key,
        )
        try:
            validate_config(new_config)
        except ConfigError as exc:
            QMessageBox.warning(self, "Configuration invalide", str(exc))
            return

        save_config(new_config)
        self._config = new_config
        self.accept()

    def get_config(self) -> MinerConfig:
        return self._config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MultiMiner - Interface de minage")
        self.setMinimumSize(600, 640)
        icon_path = LOGO_ICO if os.path.isfile(LOGO_ICO) else LOGO_PNG
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._cpu_status = "arrete"
        self._gpu_status = "arrete"

        try:
            self.config = load_config()
        except ConfigError as exc:
            QMessageBox.warning(self, "Configuration", str(exc))
            self.config = load_config()

        self.cpu_controller = MinerController()
        self.cpu_controller.status_changed.connect(self._on_cpu_status_changed)
        self.cpu_controller.hashrate_updated.connect(self._on_cpu_hashrate_updated)
        self.cpu_controller.shares_updated.connect(self._on_cpu_shares_updated)
        self.cpu_controller.log_line.connect(lambda t: self._append_log(f"[CPU] {t}"))
        self.cpu_controller.error_occurred.connect(self._on_cpu_error)

        self.gpu_controller = GpuMinerController()
        self.gpu_controller.status_changed.connect(self._on_gpu_status_changed)
        self.gpu_controller.hashrate_updated.connect(self._on_gpu_hashrate_updated)
        self.gpu_controller.shares_updated.connect(self._on_gpu_shares_updated)
        self.gpu_controller.log_line.connect(lambda t: self._append_log(f"[GPU] {t}"))
        self.gpu_controller.error_occurred.connect(self._on_gpu_error)

        self._current_hashrate_hs = 0.0
        self._network_hashrate_hs = 0.0
        self._btc_price_usd = 0.0

        self._build_ui()
        self._apply_mode_visibility()

        self.market_worker = MarketDataWorker(interval_seconds=60)
        self.market_worker.data_updated.connect(self._on_market_data_updated)
        self.market_worker.error_occurred.connect(self._on_market_error)
        self.market_worker.start()

        self._cpu_timer = QTimer(self)
        self._cpu_timer.setInterval(2000)
        self._cpu_timer.timeout.connect(self._update_cpu_usage)
        self._cpu_timer.start()

    # ---------- Construction UI ----------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())

        disclaimer = QLabel(
            "⚠️ Le minage CPU n'est pas rentable (Bitcoin nécessite du matériel "
            "ASIC). Le minage GPU cible une autre crypto et sa rentabilité "
            "dépend de votre matériel et du prix de l'électricité. Les "
            "statistiques ci-dessous sont réelles, pas des estimations "
            "garanties."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet(
            "background-color:#2a2110; color:#f0c674; padding:10px; "
            "border-radius:8px; border: 1px solid #4a3d22;"
        )
        layout.addWidget(disclaimer)

        # --- Panneau CPU ---
        self.cpu_stats_group = QGroupBox("₿  CPU — Bitcoin")
        self.cpu_stats_group.setObjectName("Card")
        cpu_stats_form = QFormLayout(self.cpu_stats_group)

        self.cpu_status_label = QLabel(STATUS_LABELS["arrete"])
        self.cpu_status_label.setStyleSheet(f"color:{STATUS_COLORS['arrete']}; font-weight:bold;")
        cpu_stats_form.addRow("Statut :", self.cpu_status_label)

        self.hashrate_label = QLabel("0 H/s")
        cpu_stats_form.addRow("Hashrate :", self.hashrate_label)

        self.shares_label = QLabel("0 / 0 (—)")
        cpu_stats_form.addRow("Shares acceptées :", self.shares_label)

        self.cpu_usage_label = QLabel("N/A")
        cpu_stats_form.addRow("Utilisation CPU :", self.cpu_usage_label)

        self.pool_label = QLabel(self._pool_display())
        cpu_stats_form.addRow("Pool :", self.pool_label)

        self.wallet_label = QLabel(self._wallet_display())
        self.wallet_label.setWordWrap(True)
        cpu_stats_form.addRow("Wallet :", self.wallet_label)

        layout.addWidget(self.cpu_stats_group)

        # --- Panneau GPU ---
        self.gpu_stats_group = QGroupBox("⛏  GPU")
        self.gpu_stats_group.setObjectName("Card")
        gpu_stats_form = QFormLayout(self.gpu_stats_group)

        self.gpu_status_label = QLabel(STATUS_LABELS["arrete"])
        self.gpu_status_label.setStyleSheet(f"color:{STATUS_COLORS['arrete']}; font-weight:bold;")
        gpu_stats_form.addRow("Statut :", self.gpu_status_label)

        self.gpu_hashrate_label = QLabel("0 MH/s")
        gpu_stats_form.addRow("Hashrate :", self.gpu_hashrate_label)

        self.gpu_shares_label = QLabel("0 / 0 (—)")
        gpu_stats_form.addRow("Shares acceptées :", self.gpu_shares_label)

        self.gpu_pool_label = QLabel(self._gpu_pool_display())
        gpu_stats_form.addRow("Pool :", self.gpu_pool_label)

        self.gpu_wallet_label = QLabel(self._gpu_wallet_display())
        self.gpu_wallet_label.setWordWrap(True)
        gpu_stats_form.addRow("Wallet :", self.gpu_wallet_label)

        gpu_note = QLabel(
            "Autre crypto que le CPU : pas de mineur GPU Bitcoin légitime "
            "maintenu aujourd'hui. Vérifiez que le DAG de l'algo choisi tient "
            "dans la VRAM de votre carte (voir Paramètres)."
        )
        gpu_note.setWordWrap(True)
        gpu_note.setStyleSheet("color:#888888; font-size:10px;")
        gpu_stats_form.addRow(gpu_note)

        layout.addWidget(self.gpu_stats_group)

        # --- Estimation temps réel (CPU / Bitcoin uniquement) ---
        self.market_group = QGroupBox("📈  Estimation temps réel Bitcoin (marché)")
        self.market_group.setObjectName("Card")
        market_form = QFormLayout(self.market_group)

        self.price_label = QLabel("—")
        market_form.addRow("Prix BTC (USD) :", self.price_label)

        self.network_hashrate_label = QLabel("—")
        market_form.addRow("Hashrate réseau :", self.network_hashrate_label)

        self.btc_per_day_label = QLabel("0 BTC")
        market_form.addRow("BTC estimé / jour :", self.btc_per_day_label)

        self.usd_per_day_label = QLabel("0 $")
        market_form.addRow("Valeur estimée / jour :", self.usd_per_day_label)

        self.time_to_block_label = QLabel("—")
        market_form.addRow("Temps moyen pour trouver un bloc :", self.time_to_block_label)

        market_note = QLabel(
            "Ces chiffres concernent uniquement le profil CPU/Bitcoin. Ce sont "
            "une espérance statistique, pas une garantie : en CPU, ils sont "
            "mathématiquement proches de zéro."
        )
        market_note.setWordWrap(True)
        market_note.setStyleSheet("color:#888888; font-size:10px;")
        market_form.addRow(market_note)

        layout.addWidget(self.market_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶  Démarrer")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn = QPushButton("■  Arrêter")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        self.settings_btn = QPushButton("⚙  Paramètres")
        self.settings_btn.clicked.connect(self._on_settings_clicked)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.settings_btn)
        layout.addLayout(btn_row)

        log_group = QGroupBox("📜  Événements et erreurs")
        log_group.setObjectName("Card")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, stretch=1)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Card")
        header.setStyleSheet(
            "QFrame#Card { background-color: #1b1b1e; border: 1px solid #2b2b2f; "
            "border-radius: 14px; }"
        )
        row = QHBoxLayout(header)
        row.setContentsMargins(18, 14, 18, 14)

        logo_label = QLabel()
        logo_path = LOGO_PNG if os.path.isfile(LOGO_PNG) else LOGO_ICO
        if os.path.isfile(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
        logo_label.setFixedSize(48, 48)
        row.addWidget(logo_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("MultiMiner")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #f5f5f5;")
        subtitle = QLabel("Minage multi-crypto — CPU + GPU")
        subtitle.setStyleSheet("font-size: 11px; color: #9a9a9f;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        row.addLayout(title_col)

        row.addStretch(1)

        self.hero_status_pill = QLabel(STATUS_LABELS["arrete"])
        self.hero_status_pill.setAlignment(Qt.AlignCenter)
        self._style_status_pill(self.hero_status_pill, "arrete")
        row.addWidget(self.hero_status_pill)

        return header

    def _style_status_pill(self, label: QLabel, status: str) -> None:
        colors = {
            "arrete": ("#2b2b2f", "#b5b5ba"),
            "en_cours": ("#1d3a22", "#5fd36e"),
            "erreur": ("#3a1d1d", "#e06565"),
        }
        bg, fg = colors.get(status, colors["arrete"])
        label.setText(STATUS_LABELS.get(status, status))
        label.setStyleSheet(
            f"background-color:{bg}; color:{fg}; font-weight:700; "
            "border-radius: 12px; padding: 6px 16px;"
        )

    def _refresh_hero_status(self) -> None:
        statuses = []
        if self.config.cpu_enabled:
            statuses.append(self._cpu_status)
        if self.config.gpu_enabled:
            statuses.append(self._gpu_status)

        if "en_cours" in statuses:
            overall = "en_cours"
        elif "erreur" in statuses:
            overall = "erreur"
        else:
            overall = "arrete"

        self._style_status_pill(self.hero_status_pill, overall)

    def _apply_mode_visibility(self) -> None:
        mode = self.config.mining_mode
        self.cpu_stats_group.setVisible(mode in ("cpu", "both"))
        self.gpu_stats_group.setVisible(mode in ("gpu", "both"))
        self.market_group.setVisible(mode in ("cpu", "both"))
        self._refresh_hero_status()

    def _pool_display(self) -> str:
        if self.config.pool_host:
            return f"{self.config.pool_host}:{self.config.pool_port}"
        return "Non configuré"

    def _wallet_display(self) -> str:
        return self.config.wallet_address or "Non configuré"

    def _gpu_pool_display(self) -> str:
        if self.config.gpu_pool_host:
            return f"{self.config.gpu_pool_host}:{self.config.gpu_pool_port}"
        return "Non configuré"

    def _gpu_wallet_display(self) -> str:
        return self.config.gpu_wallet_address or "Non configuré"

    # ---------- Actions utilisateur ----------

    def _on_start_clicked(self) -> None:
        try:
            validate_config(self.config)
        except ConfigError as exc:
            QMessageBox.warning(self, "Configuration invalide", str(exc))
            return

        details = []
        if self.config.cpu_enabled:
            details.append(f"CPU → {self._pool_display()} (worker {self.config.worker_name})")
        if self.config.gpu_enabled:
            details.append(f"GPU → {self._gpu_pool_display()} (worker {self.config.gpu_worker_name})")

        confirm = QMessageBox.question(
            self,
            "Confirmer le démarrage",
            "Démarrer le minage réel avec cette configuration ?\n\n"
            + "\n".join(details)
            + "\n\nRappel : le minage CPU n'est pas rentable économiquement ; "
              "le GPU l'est marginalement selon le matériel.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if self.config.cpu_enabled:
            self._append_log("Démarrage du mineur CPU...")
            self.cpu_controller.start(self.config)
        if self.config.gpu_enabled:
            self._append_log("Démarrage du mineur GPU...")
            self.gpu_controller.start(self.config)

    def _on_stop_clicked(self) -> None:
        self._append_log("Arrêt du minage demandé par l'utilisateur...")
        if self.cpu_controller.is_running():
            self.cpu_controller.stop()
        if self.gpu_controller.is_running():
            self.gpu_controller.stop()

    def _on_settings_clicked(self) -> None:
        was_running = self.cpu_controller.is_running() or self.gpu_controller.is_running()
        if was_running:
            QMessageBox.information(
                self, "Minage en cours",
                "Arrêtez le minage avant de modifier les paramètres."
            )
            return

        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            self.config = dialog.get_config()
            self.pool_label.setText(self._pool_display())
            self.wallet_label.setText(self._wallet_display())
            self.gpu_pool_label.setText(self._gpu_pool_display())
            self.gpu_wallet_label.setText(self._gpu_wallet_display())
            self._apply_mode_visibility()
            self._append_log("Configuration mise à jour.")

    # ---------- Réactions : profil CPU ----------

    def _on_cpu_status_changed(self, status: str) -> None:
        self._cpu_status = status
        self.cpu_status_label.setText(STATUS_LABELS.get(status, status))
        self.cpu_status_label.setStyleSheet(
            f"color:{STATUS_COLORS.get(status, '#000000')}; font-weight:bold;"
        )
        if status != "en_cours":
            self.hashrate_label.setText("0 H/s")
            self._current_hashrate_hs = 0.0
            self._refresh_earnings_estimate()
        self._refresh_global_buttons()
        self._refresh_hero_status()

    def _on_cpu_hashrate_updated(self, khash: float) -> None:
        self.hashrate_label.setText(format_hashrate(khash))
        self._current_hashrate_hs = khash * 1000.0
        self._refresh_earnings_estimate()

    def _on_cpu_shares_updated(self, accepted: int, total: int) -> None:
        pct = (accepted / total * 100.0) if total else 0.0
        self.shares_label.setText(f"{accepted} / {total} ({pct:.1f}%)")

    def _on_cpu_error(self, message: str) -> None:
        self._append_log(f"[CPU][ERREUR] {message}")
        QMessageBox.critical(self, "Erreur mineur CPU", message)

    # ---------- Réactions : profil GPU ----------

    def _on_gpu_status_changed(self, status: str) -> None:
        self._gpu_status = status
        self.gpu_status_label.setText(STATUS_LABELS.get(status, status))
        self.gpu_status_label.setStyleSheet(
            f"color:{STATUS_COLORS.get(status, '#000000')}; font-weight:bold;"
        )
        if status != "en_cours":
            self.gpu_hashrate_label.setText("0 MH/s")
        self._refresh_global_buttons()
        self._refresh_hero_status()

    def _on_gpu_hashrate_updated(self, value: float, unit: str) -> None:
        self.gpu_hashrate_label.setText(f"{value:.2f} {unit}")

    def _on_gpu_shares_updated(self, accepted: int, total: int) -> None:
        pct = (accepted / total * 100.0) if total else 0.0
        self.gpu_shares_label.setText(f"{accepted} / {total} ({pct:.1f}%)")

    def _on_gpu_error(self, message: str) -> None:
        self._append_log(f"[GPU][ERREUR] {message}")
        QMessageBox.critical(self, "Erreur mineur GPU", message)

    # ---------- Boutons globaux ----------

    def _refresh_global_buttons(self) -> None:
        any_running = self.cpu_controller.is_running() or self.gpu_controller.is_running()
        self.start_btn.setEnabled(not any_running)
        self.stop_btn.setEnabled(any_running)
        self.settings_btn.setEnabled(not any_running)

    # ---------- Marché / estimation (profil CPU uniquement) ----------

    def _on_market_data_updated(self, data: dict) -> None:
        self._btc_price_usd = data["price_usd"]
        self._network_hashrate_hs = data["network_hashrate_hs"]
        self.price_label.setText(f"${self._btc_price_usd:,.2f}".replace(",", " "))
        self.network_hashrate_label.setText(format_hashrate(self._network_hashrate_hs / 1000.0))
        self._refresh_earnings_estimate()

    def _on_market_error(self, message: str) -> None:
        self.price_label.setText("Indisponible")
        self.network_hashrate_label.setText("Indisponible")
        self._append_log(f"[MARCHÉ] {message} (nouvelle tentative dans 60s)")

    def _refresh_earnings_estimate(self) -> None:
        if self._network_hashrate_hs <= 0:
            return

        estimate = estimate_earnings(self._current_hashrate_hs, self._network_hashrate_hs)
        btc_per_day = estimate["btc_per_day"]

        self.btc_per_day_label.setText(format_btc(btc_per_day))
        if self._btc_price_usd > 0:
            usd_per_day = btc_per_day * self._btc_price_usd
            self.usd_per_day_label.setText(f"${usd_per_day:.2e}")
        else:
            self.usd_per_day_label.setText("—")

        self.time_to_block_label.setText(
            format_time_estimate(estimate["seconds_per_block_found"])
        )

    # ---------- Divers ----------

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)

    def _update_cpu_usage(self) -> None:
        if HAS_PSUTIL:
            self.cpu_usage_label.setText(f"{psutil.cpu_percent(interval=None):.0f} %")
        else:
            self.cpu_usage_label.setText("psutil non installé")

    def closeEvent(self, event) -> None:
        if self.cpu_controller.is_running():
            self._append_log("Fermeture de l'application : arrêt du mineur CPU...")
            self.cpu_controller.stop()
        if self.gpu_controller.is_running():
            self._append_log("Fermeture de l'application : arrêt du mineur GPU...")
            self.gpu_controller.stop()

        self.market_worker.stop()
        # Le thread peut être bloqué jusqu'à ~10s dans un appel réseau
        # (2 requêtes x 5s de timeout) : on attend large avant de forcer.
        if not self.market_worker.wait(12000):
            self.market_worker.terminate()
            self.market_worker.wait(2000)

        event.accept()


def run_app() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()

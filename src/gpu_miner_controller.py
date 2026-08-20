"""
gpu_miner_controller.py
Encapsule le lancement/arrêt de lolMiner (mineur GPU open source réel,
maintenu, protocole stratum) via QProcess, et parse sa sortie pour
extraire hashrate et statistiques de shares.

Syntaxe et format de sortie vérifiés contre lolMiner v1.98a (dépôt
officiel https://github.com/Lolliedieb/lolMiner-releases).
"""

import os
import re

from PySide6.QtCore import QObject, Signal, QProcess

from config_manager import MinerConfig


# Exemple de bloc de statistiques lolMiner :
#   Total Speed (MH/s):  12.3  12.1
#   Shares (A/R): 4/0  3/0
HASHRATE_RE = re.compile(r"Total Speed\s*\(([a-zA-Z/]+)\):\s*([\d.\s]+)")
SHARES_RE = re.compile(r"Shares\s*\(A/R\):\s*([\d/\s]+)")
PAIR_RE = re.compile(r"(\d+)/(\d+)")
FATAL_ERROR_RE = re.compile(
    r"(no compatible.*(device|gpu)|unable to find any.*(device|gpu)|"
    r"cuda error|opencl error|invalid algorithm|unknown algorithm|"
    r"invalid pool address|could not resolve)",
    re.IGNORECASE,
)


class GpuMinerController(QObject):
    """
    Pilote le sous-processus lolMiner et émet des signaux Qt pour
    informer la GUI de l'état, du hashrate (brut, avec son unité —
    différente de Bitcoin car autre algorithme), des shares et erreurs.
    """

    status_changed = Signal(str)         # "arrete" | "en_cours" | "erreur"
    hashrate_updated = Signal(float, str)  # (valeur, unité ex. "MH/s")
    shares_updated = Signal(int, int)
    log_line = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def start(self, config: MinerConfig) -> None:
        if self.is_running():
            self.error_occurred.emit("Le mineur GPU est déjà en cours d'exécution.")
            return

        if not config.gpu_miner_executable or not os.path.isfile(
            config.gpu_miner_executable
        ):
            self.error_occurred.emit(
                f"Exécutable mineur GPU introuvable : {config.gpu_miner_executable}"
            )
            self.status_changed.emit("erreur")
            return

        args = [
            "--algo", config.gpu_algo,
            "--pool", f"{config.gpu_pool_host}:{config.gpu_pool_port}",
            "--user", f"{config.gpu_wallet_address}.{config.gpu_worker_name}",
            "--watchdog", "exit",
            "--nocolor",
        ]

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_finished)

        try:
            self._process.start(config.gpu_miner_executable, args)
        except OSError as exc:
            self.error_occurred.emit(f"Impossible de lancer le mineur GPU : {exc}")
            self.status_changed.emit("erreur")
            return

        if not self._process.waitForStarted(5000):
            self.error_occurred.emit(
                "Le mineur GPU n'a pas démarré dans le délai imparti "
                "(pilote GPU manquant, permissions insuffisantes, ou exécutable corrompu ?)."
            )
            self.status_changed.emit("erreur")
            return

        self.status_changed.emit("en_cours")

    def stop(self) -> None:
        if not self.is_running():
            self.status_changed.emit("arrete")
            return

        self._process.terminate()
        if not self._process.waitForFinished(4000):
            self._process.kill()
            self._process.waitForFinished(2000)

        self.status_changed.emit("arrete")

    def _on_output(self) -> None:
        if self._process is None:
            return
        raw = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            self.log_line.emit(line)
            self._parse_line(line)

    def _parse_line(self, line: str) -> None:
        hashrate_match = HASHRATE_RE.search(line)
        if hashrate_match:
            unit = hashrate_match.group(1)
            values = [float(v) for v in hashrate_match.group(2).split()]
            if values:
                self.hashrate_updated.emit(sum(values), unit)

        shares_match = SHARES_RE.search(line)
        if shares_match:
            pairs = PAIR_RE.findall(shares_match.group(1))
            if pairs:
                accepted = sum(int(a) for a, _ in pairs)
                rejected = sum(int(r) for _, r in pairs)
                self.shares_updated.emit(accepted, accepted + rejected)

        if FATAL_ERROR_RE.search(line):
            self.error_occurred.emit(
                f"Erreur du mineur GPU : {line}"
            )
            self.status_changed.emit("erreur")

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        messages = {
            QProcess.FailedToStart: (
                "Le mineur GPU n'a pas pu démarrer (fichier introuvable ou "
                "permissions insuffisantes)."
            ),
            QProcess.Crashed: "Le processus de minage GPU s'est arrêté brutalement.",
            QProcess.Timedout: "Le mineur GPU ne répond plus.",
            QProcess.WriteError: "Erreur de communication avec le mineur GPU.",
            QProcess.ReadError: "Erreur de lecture de la sortie du mineur GPU.",
        }
        self.error_occurred.emit(
            messages.get(error, "Erreur inconnue du processus de minage GPU.")
        )
        self.status_changed.emit("erreur")

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if exit_status == QProcess.CrashExit:
            self.error_occurred.emit(
                "Le processus de minage GPU s'est terminé de manière inattendue "
                f"(code {exit_code})."
            )
            self.status_changed.emit("erreur")
        else:
            self.status_changed.emit("arrete")

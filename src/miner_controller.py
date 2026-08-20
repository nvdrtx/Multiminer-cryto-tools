"""
miner_controller.py
Encapsule le lancement/arrêt du binaire mineur externe (cpuminer-multi,
ou tout mineur compatible protocole stratum) via QProcess, et parse sa
sortie standard pour extraire hashrate et statistiques de shares.

Ce module ne réimplémente PAS le protocole de minage : il pilote un
binaire open source existant, fourni séparément par l'utilisateur
(voir miner/README.txt), en sous-processus visible et arrêtable à tout
moment.
"""

import re
import shutil

from PySide6.QtCore import QObject, Signal, QProcess

from config_manager import MinerConfig


# Exemples de lignes typiques produites par cpuminer-multi :
#   [2024-01-01 12:00:05] thread 0: 123456 hashes, 12.35 khash/s
#   [2024-01-01 12:00:05] accepted: 1/1 (100.00%), 12.35 khash/s (yay!!!)
#   [2024-01-01 12:00:00] Stratum authentication succeeded
#   [2024-01-01 12:00:00] Stratum connection failed
HASHRATE_RE = re.compile(r"([\d.]+)\s*khash/s", re.IGNORECASE)
ACCEPTED_RE = re.compile(r"accepted:\s*(\d+)/(\d+)", re.IGNORECASE)
AUTH_OK_RE = re.compile(r"authentication succeeded", re.IGNORECASE)
CONN_FAIL_RE = re.compile(r"(connection failed|connect failed|couldn't connect)", re.IGNORECASE)
INVALID_ADDR_RE = re.compile(r"(invalid address|invalid username)", re.IGNORECASE)


class MinerController(QObject):
    """
    Pilote le sous-processus mineur et émet des signaux Qt pour informer
    la GUI de l'état, du hashrate, des shares et des erreurs.
    """

    status_changed = Signal(str)        # "arrete" | "en_cours" | "erreur"
    hashrate_updated = Signal(float)    # en kH/s
    shares_updated = Signal(int, int)   # (acceptees, total)
    log_line = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._accepted = 0
        self._submitted = 0

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def start(self, config: MinerConfig) -> None:
        if self.is_running():
            self.error_occurred.emit("Le mineur est déjà en cours d'exécution.")
            return

        if not shutil.os.path.isfile(config.miner_executable):
            self.error_occurred.emit(
                f"Exécutable mineur introuvable : {config.miner_executable}"
            )
            self.status_changed.emit("erreur")
            return

        args = [
            "-a", "sha256d",
            "-o", f"stratum+tcp://{config.pool_host}:{config.pool_port}",
            "-u", f"{config.wallet_address}.{config.worker_name}",
            "-p", "x",
        ]
        if config.threads > 0:
            args += ["-t", str(config.threads)]

        self._accepted = 0
        self._submitted = 0

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_finished)

        try:
            self._process.start(config.miner_executable, args)
        except OSError as exc:
            self.error_occurred.emit(f"Impossible de lancer le mineur : {exc}")
            self.status_changed.emit("erreur")
            return

        if not self._process.waitForStarted(5000):
            self.error_occurred.emit(
                "Le mineur n'a pas démarré dans le délai imparti "
                "(permissions Windows insuffisantes ou exécutable corrompu ?)."
            )
            self.status_changed.emit("erreur")
            return

        self.status_changed.emit("en_cours")

    def stop(self) -> None:
        if not self.is_running():
            self.status_changed.emit("arrete")
            return

        self._process.terminate()
        if not self._process.waitForFinished(3000):
            # Arrêt propre impossible dans le délai : on force
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
            self.hashrate_updated.emit(float(hashrate_match.group(1)))

        accepted_match = ACCEPTED_RE.search(line)
        if accepted_match:
            self._accepted = int(accepted_match.group(1))
            self._submitted = int(accepted_match.group(2))
            self.shares_updated.emit(self._accepted, self._submitted)

        if CONN_FAIL_RE.search(line):
            self.error_occurred.emit(
                "Connexion au pool de minage impossible. "
                "Vérifiez votre connexion Internet et l'adresse du pool."
            )
            self.status_changed.emit("erreur")

        if INVALID_ADDR_RE.search(line):
            self.error_occurred.emit(
                "Le pool a rejeté l'adresse wallet ou le nom de worker. "
                "Vérifiez ces valeurs dans Paramètres."
            )
            self.status_changed.emit("erreur")

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        messages = {
            QProcess.FailedToStart: (
                "Le mineur n'a pas pu démarrer (fichier introuvable ou "
                "permissions insuffisantes)."
            ),
            QProcess.Crashed: "Le processus de minage s'est arrêté brutalement.",
            QProcess.Timedout: "Le mineur ne répond plus.",
            QProcess.WriteError: "Erreur de communication avec le mineur.",
            QProcess.ReadError: "Erreur de lecture de la sortie du mineur.",
        }
        self.error_occurred.emit(
            messages.get(error, "Erreur inconnue du processus de minage.")
        )
        self.status_changed.emit("erreur")

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if exit_status == QProcess.CrashExit:
            self.error_occurred.emit(
                "Le processus de minage s'est terminé de manière inattendue "
                f"(code {exit_code})."
            )
            self.status_changed.emit("erreur")
        else:
            self.status_changed.emit("arrete")

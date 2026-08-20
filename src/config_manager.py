"""
config_manager.py
Chargement, sauvegarde et validation de la configuration utilisateur.

Deux profils indépendants coexistent, car CPU et GPU minent des
cryptomonnaies différentes (Bitcoin en CPU ; une crypto GPU-friendly
comme Ergo en GPU — il n'existe pas de mineur GPU Bitcoin légitime
maintenu aujourd'hui, voir README) :
- profil CPU : pool_host / pool_port / wallet_address / worker_name /
  miner_executable / threads (cpuminer-multi, SHA-256d, Bitcoin) ;
- profil GPU : gpu_pool_host / gpu_pool_port / gpu_wallet_address /
  gpu_worker_name / gpu_miner_executable / gpu_algo (lolMiner, Ergo
  par défaut).

`mining_mode` détermine quels profils sont actifs : "cpu", "gpu", ou
"both" (les deux simultanément, deux process indépendants).

Aucune information sensible (clé privée, seed phrase) n'est jamais
stockée ou demandée ici : uniquement des paramètres publics de pool.
"""

import json
import os
import re
from dataclasses import dataclass, asdict

from utils import get_config_path, get_default_miner_dir, get_default_gpu_miner_dir


MINING_MODES = ("cpu", "gpu", "both")

PREFERRED_CPU_MINER_BINARIES = [
    "cpuminer-gw64-corei7.exe",
    "cpuminer-gw64-core2.exe",
    "cpuminer-gw64-avx2.exe",
    "cpuminer-multi.exe",
    "minerd.exe",
]

PREFERRED_GPU_MINER_BINARIES = [
    "lolMiner.exe",
]


def _autodetect_executable(directory: str, names: list) -> str:
    for name in names:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    return ""


def _autodetect_cpu_miner_executable() -> str:
    return _autodetect_executable(get_default_miner_dir(), PREFERRED_CPU_MINER_BINARIES)


def _autodetect_gpu_miner_executable() -> str:
    return _autodetect_executable(get_default_gpu_miner_dir(), PREFERRED_GPU_MINER_BINARIES)


DEFAULT_CONFIG = {
    "mining_mode": "cpu",  # "cpu" | "gpu" | "both"
    # --- Profil CPU (Bitcoin, SHA-256d) ---
    "pool_host": "",
    "pool_port": 3333,
    "wallet_address": "",
    "worker_name": "worker1",
    "miner_executable": "",
    "threads": 0,  # 0 = auto (toutes les threads CPU disponibles)
    # --- Profil GPU (Ergo, Autolykos2, via lolMiner) ---
    "gpu_pool_host": "",
    "gpu_pool_port": 11111,
    "gpu_wallet_address": "",
    "gpu_worker_name": "worker1",
    "gpu_miner_executable": "",
    "gpu_algo": "AUTOLYKOS2",
}


@dataclass
class MinerConfig:
    mining_mode: str
    pool_host: str
    pool_port: int
    wallet_address: str
    worker_name: str
    miner_executable: str
    threads: int
    gpu_pool_host: str
    gpu_pool_port: int
    gpu_wallet_address: str
    gpu_worker_name: str
    gpu_miner_executable: str
    gpu_algo: str

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def cpu_enabled(self) -> bool:
        return self.mining_mode in ("cpu", "both")

    @property
    def gpu_enabled(self) -> bool:
        return self.mining_mode in ("gpu", "both")


class ConfigError(Exception):
    """Erreur de configuration invalide, avec message compréhensible pour l'utilisateur."""


def load_config() -> MinerConfig:
    path = get_config_path()
    data = dict(DEFAULT_CONFIG)

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            data.update(loaded)
        except (json.JSONDecodeError, OSError) as exc:
            raise ConfigError(
                f"Le fichier de configuration est illisible ou corrompu ({exc}). "
                "Il sera réinitialisé aux valeurs par défaut."
            )
    else:
        data["miner_executable"] = _autodetect_cpu_miner_executable()
        data["gpu_miner_executable"] = _autodetect_gpu_miner_executable()
        save_config(MinerConfig(**data))

    # Auto-détection différée : un mineur téléchargé après coup (ex.
    # après un premier lancement sans connexion Internet) est repéré
    # automatiquement au chargement suivant.
    if not data.get("miner_executable") or not os.path.isfile(data["miner_executable"]):
        detected = _autodetect_cpu_miner_executable()
        if detected:
            data["miner_executable"] = detected

    if not data.get("gpu_miner_executable") or not os.path.isfile(data["gpu_miner_executable"]):
        detected_gpu = _autodetect_gpu_miner_executable()
        if detected_gpu:
            data["gpu_miner_executable"] = detected_gpu

    if data.get("mining_mode") not in MINING_MODES:
        data["mining_mode"] = "cpu"

    return MinerConfig(**data)


def save_config(config: MinerConfig) -> None:
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


def _validate_wallet(address: str, label: str) -> None:
    if not address or len(address.strip()) < 20:
        raise ConfigError(
            f"L'adresse wallet {label} semble invalide (trop courte). "
            "Vérifiez que vous avez copié l'adresse complète."
        )


def _validate_worker(name: str, label: str) -> None:
    if not name or not re.match(r"^[a-zA-Z0-9_\-]+$", name):
        raise ConfigError(
            f"Le nom du worker {label} ne doit contenir que des lettres, "
            "chiffres, tirets et underscores."
        )


def _validate_pool(host: str, port: int, label: str) -> None:
    if not host or not re.match(r"^[a-zA-Z0-9\.\-]+$", host):
        raise ConfigError(
            f"L'adresse du pool {label} est vide ou invalide. "
            "Exemple attendu : stratum.pool-exemple.com"
        )
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ConfigError(f"Le port du pool {label} doit être un nombre entier entre 1 et 65535.")


def _validate_executable(path: str, label: str, hint: str) -> None:
    if not path:
        raise ConfigError(
            f"Aucun exécutable {label} n'est configuré. "
            f"Allez dans Paramètres et indiquez le chemin vers {hint}."
        )
    if not os.path.isfile(path):
        raise ConfigError(
            f"L'exécutable {label} est introuvable à l'emplacement :\n{path}\n"
            "Vérifiez le chemin dans Paramètres."
        )


def validate_config(config: MinerConfig) -> None:
    """
    Valide uniquement les profils actifs selon `mining_mode`. Un profil
    CPU ou GPU non utilisé n'a pas besoin d'être renseigné.
    """
    if config.mining_mode not in MINING_MODES:
        raise ConfigError("Mode de minage invalide.")

    if not config.cpu_enabled and not config.gpu_enabled:
        raise ConfigError("Aucun mode de minage n'est activé.")

    if config.cpu_enabled:
        _validate_pool(config.pool_host, config.pool_port, "CPU")
        _validate_wallet(config.wallet_address, "CPU")
        _validate_worker(config.worker_name, "CPU")
        _validate_executable(
            config.miner_executable, "mineur CPU", "cpuminer-multi.exe"
        )
        if config.threads < 0:
            raise ConfigError("Le nombre de threads CPU ne peut pas être négatif.")

    if config.gpu_enabled:
        _validate_pool(config.gpu_pool_host, config.gpu_pool_port, "GPU")
        _validate_wallet(config.gpu_wallet_address, "GPU")
        _validate_worker(config.gpu_worker_name, "GPU")
        _validate_executable(
            config.gpu_miner_executable, "mineur GPU", "lolMiner.exe"
        )
        if not config.gpu_algo:
            raise ConfigError("Aucun algorithme GPU sélectionné.")

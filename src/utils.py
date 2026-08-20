"""
utils.py
Fonctions utilitaires partagées : résolution de chemins (dev vs .exe compilé),
formatage d'unités.
"""

import sys
import os


def get_base_path() -> str:
    """
    Retourne le dossier racine de l'application, que celle-ci tourne
    depuis les sources Python ou depuis un .exe compilé par PyInstaller.
    """
    if getattr(sys, "frozen", False):
        # Exécution depuis un .exe PyInstaller : les données sont à côté de l'exe
        return os.path.dirname(sys.executable)
    # Exécution depuis les sources : remonte d'un niveau depuis src/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path() -> str:
    return os.path.join(get_base_path(), "config", "config.json")


def get_default_miner_dir() -> str:
    return os.path.join(get_base_path(), "miner")


def get_default_gpu_miner_dir() -> str:
    return os.path.join(get_base_path(), "miner", "gpu")


def format_hashrate(khash_per_sec: float) -> str:
    """
    Convertit un hashrate exprimé en kH/s vers l'unité la plus lisible.
    """
    hash_per_sec = khash_per_sec * 1000.0
    units = [
        ("TH/s", 1e12),
        ("GH/s", 1e9),
        ("MH/s", 1e6),
        ("kH/s", 1e3),
        ("H/s", 1),
    ]
    for name, factor in units:
        if hash_per_sec >= factor:
            return f"{hash_per_sec / factor:.2f} {name}"
    return "0 H/s"

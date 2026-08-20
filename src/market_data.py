"""
market_data.py
Récupère en temps réel le prix du Bitcoin et le hashrate du réseau via
des API publiques, pour calculer une estimation statistique honnête
des gains de minage. Ceci est purement informatif : à l'échelle d'un
CPU, le résultat attendu est mathématiquement nul (voir
format_time_estimate ci-dessous, qui l'exprime clairement).
"""

import json
import urllib.request
import urllib.error

PRICE_URL = "https://blockchain.info/ticker"
NETWORK_HASHRATE_URL = "https://mempool.space/api/v1/mining/hashrate/3d"

BLOCK_REWARD_BTC = 3.125  # récompense de bloc courante (post-halving 2024)
SECONDS_PER_BLOCK = 600
SECONDS_PER_DAY = 86400
UNIVERSE_AGE_YEARS = 13.8e9


class MarketDataError(Exception):
    """Erreur réseau ou de parsing lors de la récupération des données marché."""


def fetch_btc_price_usd(timeout: int = 5) -> float:
    try:
        with urllib.request.urlopen(PRICE_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return float(data["USD"]["last"])
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError) as exc:
        raise MarketDataError(f"Impossible de récupérer le prix BTC : {exc}")


def fetch_network_hashrate_hs(timeout: int = 5) -> float:
    """Retourne le hashrate réseau Bitcoin en H/s, via mempool.space."""
    try:
        with urllib.request.urlopen(NETWORK_HASHRATE_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return float(data["currentHashrate"])
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError, OSError) as exc:
        raise MarketDataError(f"Impossible de récupérer le hashrate réseau : {exc}")


def estimate_earnings(user_hashrate_hs: float, network_hashrate_hs: float) -> dict:
    """
    Estimation statistique (espérance mathématique) des gains, purement
    informative. share = part du hashrate total détenue par l'utilisateur.
    """
    if network_hashrate_hs <= 0 or user_hashrate_hs <= 0:
        return {"btc_per_day": 0.0, "seconds_per_block_found": float("inf"), "share": 0.0}

    share = user_hashrate_hs / network_hashrate_hs
    blocks_per_day = SECONDS_PER_DAY / SECONDS_PER_BLOCK
    btc_per_day = share * blocks_per_day * BLOCK_REWARD_BTC
    seconds_per_block_found = SECONDS_PER_BLOCK / share

    return {
        "btc_per_day": btc_per_day,
        "seconds_per_block_found": seconds_per_block_found,
        "share": share,
    }


def format_time_estimate(seconds: float) -> str:
    """
    Formate un temps attendu en une chaîne lisible, en gardant une
    honnêteté totale sur les ordres de grandeur absurdes typiques du
    minage CPU (bien au-delà de l'âge de l'univers).
    """
    if seconds == float("inf") or seconds <= 0:
        return "indéterminé"

    years = seconds / (365.25 * 24 * 3600)

    if years > UNIVERSE_AGE_YEARS * 1000:
        magnitude = years / UNIVERSE_AGE_YEARS
        return f"≈ {magnitude:.1e} fois l'âge de l'univers"
    if years >= 1:
        return f"≈ {years:,.0f} ans".replace(",", " ")

    days = seconds / SECONDS_PER_DAY
    if days >= 1:
        return f"≈ {days:.1f} jours"

    hours = seconds / 3600
    return f"≈ {hours:.1f} heures"


def format_btc(value: float) -> str:
    if value == 0:
        return "0 BTC"
    return f"{value:.2e} BTC"

"""
market_data_worker.py
QThread qui interroge périodiquement market_data.py en arrière-plan
(sans bloquer l'interface) et notifie la GUI via signaux Qt.
"""

from PySide6.QtCore import QThread, Signal

from market_data import fetch_btc_price_usd, fetch_network_hashrate_hs, MarketDataError


class MarketDataWorker(QThread):
    data_updated = Signal(dict)   # {"price_usd": float, "network_hashrate_hs": float}
    error_occurred = Signal(str)

    def __init__(self, interval_seconds: int = 60, parent=None):
        super().__init__(parent)
        self._interval = interval_seconds
        self._running = True

    def run(self) -> None:
        while self._running:
            try:
                price = fetch_btc_price_usd()
                network_hr = fetch_network_hashrate_hs()
                if self._running:
                    self.data_updated.emit(
                        {"price_usd": price, "network_hashrate_hs": network_hr}
                    )
            except MarketDataError as exc:
                if self._running:
                    self.error_occurred.emit(str(exc))

            for _ in range(self._interval):
                if not self._running:
                    break
                self.msleep(1000)

    def stop(self) -> None:
        self._running = False

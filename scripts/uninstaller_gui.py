"""
uninstaller_gui.py
Petite interface graphique de désinstallation pour MultiMiner,
utilisée à la place d'un script batch brut.

Supprime : le processus MultiMiner.exe s'il tourne encore, le
raccourci Bureau, puis l'intégralité du dossier du projet (le dossier
MultiMiner tout entier : venv, dist, src, scripts, config, miner,
assets...), pas seulement le sous-dossier dist.

Comme ce script se trouve lui-même dans le dossier à supprimer, la
suppression finale est déléguée à un script auxiliaire temporaire
(copié dans %TEMP%) qui attend la fermeture de cette fenêtre avant
d'agir — sinon le dossier ne pourrait pas être entièrement supprimé
pendant que ce processus l'utilise encore.
"""

import os
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW_FLAGS = 0x08000000 if _IS_WINDOWS else 0  # CREATE_NO_WINDOW

STEPS = [
    "Arrêt de MultiMiner si en cours",
    "Suppression du raccourci Bureau",
    "Préparation de la suppression du dossier",
    "Suppression complète du dossier MultiMiner",
]


class UninstallerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Désinstallation de MultiMiner")
        root.geometry("560x420")
        root.resizable(False, False)

        icon_png = os.path.join(PROJECT_ROOT, "assets", "icon.png")
        icon_ico = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
        try:
            if os.path.isfile(icon_png):
                self._icon_image = tk.PhotoImage(file=icon_png)
                root.iconphoto(True, self._icon_image)
            elif os.path.isfile(icon_ico):
                root.iconbitmap(icon_ico)
        except tk.TclError:
            pass

        tk.Label(
            root, text="Désinstallation de MultiMiner",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(16, 4))

        tk.Label(
            root,
            text="Ceci supprimera définitivement tout le dossier MultiMiner\n"
                 "(application, mineur, configuration, environnement Python).",
            font=("Segoe UI", 9), fg="#666666", justify="center",
        ).pack(pady=(0, 12))

        self.progress = ttk.Progressbar(
            root, orient="horizontal", length=500, mode="determinate",
            maximum=len(STEPS),
        )
        self.progress.pack(pady=(0, 8))

        self.status_label = tk.Label(root, text="Prêt à désinstaller.", font=("Segoe UI", 9))
        self.status_label.pack(pady=(0, 8))

        self.log = scrolledtext.ScrolledText(
            root, width=68, height=12, font=("Consolas", 8), state="disabled"
        )
        self.log.pack(padx=16, pady=(0, 12))

        self.uninstall_btn = tk.Button(
            root, text="Désinstaller", width=20, command=self.confirm_and_start
        )
        self.uninstall_btn.pack(pady=(0, 16))

    # ---------- Helpers UI ----------

    def log_line(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def set_step(self, index: int) -> None:
        self.progress["value"] = index
        if index < len(STEPS):
            self.status_label.config(text=f"Étape {index + 1}/{len(STEPS)} : {STEPS[index]}")
        self.root.update_idletasks()

    def _run_cmd(self, args) -> None:
        try:
            subprocess.run(
                args, cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW_FLAGS,
                check=False,
            )
        except OSError:
            pass

    # ---------- Désinstallation ----------

    def confirm_and_start(self) -> None:
        confirmed = messagebox.askyesno(
            "Confirmer la désinstallation",
            "Voulez-vous vraiment supprimer MultiMiner ?\n\n"
            f"Tout le dossier sera supprimé définitivement :\n{PROJECT_ROOT}\n\n"
            "Cette action est irréversible.",
            icon="warning",
        )
        if not confirmed:
            return

        self.uninstall_btn.config(state="disabled")
        threading.Thread(target=self._run_uninstall, daemon=True).start()

    def _run_uninstall(self) -> None:
        self.set_step(0)
        self.log_line("Arrêt de MultiMiner.exe s'il est en cours d'exécution...")
        self._run_cmd(["taskkill", "/f", "/im", "MultiMiner.exe"])

        self.set_step(1)
        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        shortcut = os.path.join(desktop, "MultiMiner.lnk")
        if os.path.isfile(shortcut):
            try:
                os.remove(shortcut)
                self.log_line("Raccourci Bureau supprimé.")
            except OSError as exc:
                self.log_line(f"[ATTENTION] Impossible de supprimer le raccourci : {exc}")
        else:
            self.log_line("Aucun raccourci Bureau trouvé.")

        self.set_step(2)
        temp_dir = os.environ.get("TEMP") or os.environ.get("TMP") or "."
        helper_path = os.path.join(temp_dir, "MultiMiner_uninstall_helper.bat")
        self.log_line("Préparation de la suppression complète du dossier...")

        helper_content = (
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'rmdir /s /q "{PROJECT_ROOT}"\r\n'
            'del /f /q "%~f0"\r\n'
        )
        try:
            with open(helper_path, "w", encoding="utf-8") as f:
                f.write(helper_content)
        except OSError as exc:
            self._fail(f"Impossible de préparer la suppression : {exc}")
            return

        self.set_step(3)
        self.log_line(f"Suppression de {PROJECT_ROOT} ...")
        self.log_line("Cette fenêtre va se fermer pour libérer les fichiers, "
                       "la suppression continue ensuite en arrière-plan.")

        # Lance le nettoyeur en arriere-plan, detache du processus courant,
        # puis ferme la fenetre pour liberer les verrous de fichiers avant
        # que le nettoyeur ne tente de supprimer le dossier.
        subprocess.Popen(
            ["cmd", "/c", helper_path],
            cwd=temp_dir,
            creationflags=_NO_WINDOW_FLAGS | 0x00000008,  # + DETACHED_PROCESS
            close_fds=True,
        )

        self.root.after(1200, self.root.destroy)

    def _fail(self, message: str) -> None:
        self.log_line(f"[ERREUR] {message}")
        self.status_label.config(text="Échec de la désinstallation.")
        self.uninstall_btn.config(state="normal")
        messagebox.showerror("Désinstallation échouée", message)


def main() -> None:
    root = tk.Tk()
    UninstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

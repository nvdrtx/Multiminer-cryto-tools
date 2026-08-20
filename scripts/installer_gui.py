"""
installer_gui.py
Petite interface graphique d'installation pour MultiMiner, utilisée
à la place d'un script batch brut affichant du texte qui défile.

Utilise uniquement Tkinter (fourni avec Python) : au moment où cet
installateur démarre, PySide6 n'est pas encore installé, donc
l'interface d'installation elle-même ne peut pas en dépendre.

Orchestre les mêmes étapes que build.bat : téléchargement du mineur,
création de l'environnement virtuel, installation des dépendances,
compilation avec PyInstaller, préparation du dossier de distribution,
création du raccourci Bureau.
"""

import os
import platform
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Sur Windows, empêche chaque sous-processus (pip, powershell, pyinstaller...)
# d'ouvrir sa propre fenêtre console visible pendant l'installation.
_IS_WINDOWS = platform.system() == "Windows"
_NO_WINDOW_FLAGS = 0x08000000 if _IS_WINDOWS else 0  # CREATE_NO_WINDOW

STEPS = [
    "Vérification de Python",
    "Téléchargement du mineur CPU",
    "Téléchargement du mineur GPU",
    "Création de l'environnement virtuel",
    "Installation des dépendances",
    "Nettoyage des anciens builds",
    "Compilation de MultiMiner.exe",
    "Préparation du dossier de distribution",
    "Création du raccourci Bureau",
]


class InstallerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Installation de MultiMiner")
        root.geometry("580x460")
        root.resizable(False, False)

        icon_png = os.path.join(PROJECT_ROOT, "assets", "icon.png")
        icon_ico = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
        try:
            if os.path.isfile(icon_png):
                # PhotoImage doit rester référencée sinon elle est
                # garbage-collectée et l'icône redevient la plume Tk par
                # défaut.
                self._icon_image = tk.PhotoImage(file=icon_png)
                root.iconphoto(True, self._icon_image)
            elif os.path.isfile(icon_ico):
                root.iconbitmap(icon_ico)
        except tk.TclError:
            pass

        tk.Label(
            root, text="Installation de MultiMiner",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(16, 4))

        tk.Label(
            root,
            text="Interface de minage Bitcoin — installation automatique",
            font=("Segoe UI", 9), fg="#666666",
        ).pack(pady=(0, 6))

        tk.Label(
            root,
            text="⚠ Le minage CPU n'est pas rentable : outil réel, à but "
                 "éducatif/démonstratif.",
            font=("Segoe UI", 8), fg="#a06000", wraplength=520, justify="center",
        ).pack(pady=(0, 12))

        self.progress = ttk.Progressbar(
            root, orient="horizontal", length=520, mode="determinate",
            maximum=len(STEPS),
        )
        self.progress.pack(pady=(0, 8))

        self.status_label = tk.Label(root, text="Prêt à installer.", font=("Segoe UI", 9))
        self.status_label.pack(pady=(0, 8))

        self.log = scrolledtext.ScrolledText(
            root, width=72, height=14, font=("Consolas", 8), state="disabled"
        )
        self.log.pack(padx=16, pady=(0, 12))

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=(0, 12))

        self.install_btn = tk.Button(
            btn_frame, text="Installer", width=16, command=self.start_install
        )
        self.install_btn.grid(row=0, column=0, padx=6)

        self.launch_btn = tk.Button(
            btn_frame, text="Lancer MultiMiner", width=18,
            command=self.launch_app, state="disabled",
        )
        self.launch_btn.grid(row=0, column=1, padx=6)

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

    # ---------- Installation ----------

    def start_install(self) -> None:
        self.install_btn.config(state="disabled")
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_cmd(self, args, cwd=None) -> bool:
        try:
            process = subprocess.Popen(
                args, cwd=cwd or PROJECT_ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                creationflags=_NO_WINDOW_FLAGS,
            )
        except OSError as exc:
            self.log_line(f"[ERREUR] {exc}")
            return False

        for line in process.stdout:
            self.log_line(line.rstrip())
        process.wait()
        return process.returncode == 0

    def _run_install(self) -> None:
        try:
            self.set_step(0)
            self.log_line("Vérification de Python...")
            if not self._run_cmd(["python", "--version"]):
                self._fail(
                    "Python est introuvable. Installez-le depuis python.org "
                    "et cochez 'Add Python to PATH'."
                )
                return

            self.set_step(1)
            miner_dir = os.path.join(PROJECT_ROOT, "miner")
            os.makedirs(miner_dir, exist_ok=True)
            if not os.path.isfile(os.path.join(miner_dir, "cpuminer-gw64-corei7.exe")):
                self.log_line("Téléchargement du mineur CPU depuis GitHub...")
                if not self._run_cmd([
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(SCRIPT_DIR, "fetch_miner.ps1"),
                ]):
                    self.log_line(
                        "[ATTENTION] Téléchargement du mineur CPU échoué. "
                        "Vous pourrez le faire manuellement (voir miner/README.txt)."
                    )
            else:
                self.log_line("Mineur CPU déjà présent, téléchargement ignoré.")

            self.set_step(2)
            gpu_miner_dir = os.path.join(PROJECT_ROOT, "miner", "gpu")
            os.makedirs(gpu_miner_dir, exist_ok=True)
            if not os.path.isfile(os.path.join(gpu_miner_dir, "lolMiner.exe")):
                self.log_line("Téléchargement du mineur GPU (lolMiner) depuis GitHub...")
                if not self._run_cmd([
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", os.path.join(SCRIPT_DIR, "fetch_gpu_miner.ps1"),
                ]):
                    self.log_line(
                        "[ATTENTION] Téléchargement du mineur GPU échoué. "
                        "Le mode GPU pourra être configuré manuellement plus tard "
                        "si vous en avez besoin."
                    )
            else:
                self.log_line("Mineur GPU déjà présent, téléchargement ignoré.")

            self.set_step(3)
            venv_dir = os.path.join(PROJECT_ROOT, "venv")
            if not os.path.isdir(venv_dir):
                self.log_line("Création de l'environnement virtuel...")
                if not self._run_cmd(["python", "-m", "venv", "venv"]):
                    self._fail("Impossible de créer l'environnement virtuel.")
                    return
            else:
                self.log_line("Environnement virtuel déjà présent.")

            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")

            self.set_step(4)
            self.log_line("Installation des dépendances (1-2 minutes)...")
            if not self._run_cmd([venv_python, "-m", "pip", "install", "--upgrade", "pip"]):
                self._fail("Échec de la mise à jour de pip.")
                return
            if not self._run_cmd([venv_python, "-m", "pip", "install", "-r", "requirements.txt"]):
                self._fail("Échec de l'installation des dépendances.")
                return

            self.set_step(5)
            for folder in ("build", "dist"):
                path = os.path.join(PROJECT_ROOT, folder)
                if os.path.isdir(path):
                    shutil.rmtree(path)
            self.log_line("Anciens builds nettoyés.")

            self.set_step(6)
            self.log_line("Compilation de MultiMiner.exe (PyInstaller)...")
            if not self._run_cmd([venv_python, "-m", "PyInstaller", "MultiMiner.spec"]):
                self._fail("La compilation a échoué. Voir le journal ci-dessus.")
                return

            exe_path = os.path.join(PROJECT_ROOT, "dist", "MultiMiner.exe")
            if not os.path.isfile(exe_path):
                self._fail("MultiMiner.exe introuvable après compilation.")
                return

            self.set_step(7)
            self.log_line("Préparation du dossier de distribution...")
            dist_dir = os.path.join(PROJECT_ROOT, "dist")
            icon_src = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
            if os.path.isfile(icon_src):
                shutil.copy2(icon_src, os.path.join(dist_dir, "icon.ico"))
            shutil.copy2(
                os.path.join(SCRIPT_DIR, "uninstall_template.bat"),
                os.path.join(dist_dir, "Uninstall.bat"),
            )
            if not os.path.isdir(os.path.join(dist_dir, "miner")):
                shutil.copytree(miner_dir, os.path.join(dist_dir, "miner"))
            elif not os.path.isdir(os.path.join(dist_dir, "miner", "gpu")) and os.path.isdir(gpu_miner_dir):
                shutil.copytree(gpu_miner_dir, os.path.join(dist_dir, "miner", "gpu"))
            config_src = os.path.join(PROJECT_ROOT, "config")
            if not os.path.isdir(os.path.join(dist_dir, "config")):
                shutil.copytree(config_src, os.path.join(dist_dir, "config"))

            self.set_step(8)
            self.log_line("Création du raccourci sur le Bureau...")
            icon_for_shortcut = os.path.join(dist_dir, "icon.ico")
            if not os.path.isfile(icon_for_shortcut):
                icon_for_shortcut = exe_path
            self._run_cmd([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", os.path.join(SCRIPT_DIR, "create_shortcut.ps1"),
                "-ExePath", exe_path, "-IconPath", icon_for_shortcut,
            ])

            self.set_step(len(STEPS))
            self.status_label.config(text="Installation terminée !")
            self.log_line(
                "\nMultiMiner est installé. Un raccourci a été créé sur le Bureau."
            )
            self.launch_btn.config(state="normal")
            self.install_btn.config(state="normal", text="Réinstaller")

        except Exception as exc:  # ne jamais planter silencieusement
            self._fail(f"Erreur inattendue : {exc}")

    def _fail(self, message: str) -> None:
        self.log_line(f"[ERREUR] {message}")
        self.status_label.config(text="Échec de l'installation.")
        self.install_btn.config(state="normal", text="Réessayer")
        messagebox.showerror("Installation échouée", message)

    def launch_app(self) -> None:
        exe_path = os.path.join(PROJECT_ROOT, "dist", "MultiMiner.exe")
        if os.path.isfile(exe_path):
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        else:
            messagebox.showerror("Erreur", "MultiMiner.exe introuvable.")


def main() -> None:
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

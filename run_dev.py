import subprocess
import sys
import time
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

processus = None
_derniere_relance = 0


def lancer_app():
    global processus
    if processus and processus.poll() is None:
        processus.terminate()
        try:
            processus.wait(timeout=3)
        except subprocess.TimeoutExpired:
            processus.kill()

    # --dev : garde la session active (ne repasse pas par le login)
    processus = subprocess.Popen([sys.executable, "main.py", "--dev"])


class SurModification(FileSystemEventHandler):
    def on_modified(self, event):
        global _derniere_relance
        if not event.src_path.endswith((".py", ".qss")):
            return
        if event.src_path.endswith(".session.json"):
            return

        # Débounce : ignorer les événements multiples du même fichier
        maintenant = time.time()
        if maintenant - _derniere_relance < 0.5:
            return
        _derniere_relance = maintenant

        print(f"Modification détectée : {event.src_path} → relancement...")
        lancer_app()


if __name__ == "__main__":
    lancer_app()
    observateur = Observer()
    observateur.schedule(SurModification(), path=".", recursive=True)
    observateur.start()
    print("Mode développement actif — l'app se relance automatiquement (session conservée).")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observateur.stop()
        if processus and processus.poll() is None:
            processus.terminate()
    observateur.join()

import os
import threading
import urllib.request


def _count_hits(category):
    # Ignore counting in development environment by checking if cli.py exists
    # (cli.py is excluded from the production bundle)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(current_dir, "..", "cli.py")):
        return

    def _count():
        try:
            url = f"https://hits.sh/github.com/silentsoft/whiscribe/{category}.svg"
            with urllib.request.urlopen(url) as response:
                response.read()
        except:
            pass

    threading.Thread(target=_count, daemon=True).start()


def count_launch():
    _count_hits("launch")


def count_transcribe():
    _count_hits("transcribe")

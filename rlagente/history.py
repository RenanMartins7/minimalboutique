import json
import os
import time

HISTORY_FILE = "policies_history.json"

def save_history(config_hash, policies):
    """Salva histórico de execuções em um arquivo JSON local"""
    record = {
        "hash": config_hash,
        "policies": policies,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    }

    if not os.path.exists(HISTORY_FILE):
        history = []
    else:
        with open(HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

    history.append(record)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    print(f"Histórico atualizado em {HISTORY_FILE}")

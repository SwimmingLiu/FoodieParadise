import json
import os
from datetime import datetime
from typing import List, Dict

HISTORY_FILE = "history.json"

def load_history() -> List[Dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_history(record: Dict):
    history = load_history()
    record["timestamp"] = datetime.now().isoformat()
    history.insert(0, record) # Prepend
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_user_history(user_id: str = "default") -> List[Dict]:
    # For now, we ignore user_id as we don't have auth
    return load_history()

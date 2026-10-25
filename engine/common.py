import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.private'

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()

def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(obj))

def read_json(path):
    return json.loads(Path(path).read_text())

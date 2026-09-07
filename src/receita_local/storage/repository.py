from __future__ import annotations

import hashlib, json, os, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return root / "ReceitasProcesso"


class Repository:
    def __init__(self, root: Path | None = None):
        self.root = root or data_dir(); self.files = self.root / "files"; self.logs = self.root / "logs"
        self.files.mkdir(parents=True, exist_ok=True); self.logs.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "receitas.db", check_same_thread=False)
        self.db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, name TEXT, sha256 TEXT UNIQUE, imported_at TEXT, stored_path TEXT);
        CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY, product TEXT, created_at TEXT, algorithm TEXT, config_json TEXT, result_json TEXT);
        CREATE TABLE IF NOT EXISTS analysis_documents(analysis_id TEXT, document_id TEXT, PRIMARY KEY(analysis_id,document_id), FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE, FOREIGN KEY(document_id) REFERENCES documents(id));
        CREATE TABLE IF NOT EXISTS recipe_versions(id TEXT PRIMARY KEY, analysis_id TEXT, version INTEGER, created_at TEXT, result_json TEXT, justification TEXT, reviewed INTEGER, UNIQUE(analysis_id,version), FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS aliases(product TEXT, alias TEXT, confirmed INTEGER, PRIMARY KEY(product,alias));
        """); self.db.commit()

    def import_file(self, path: Path) -> dict:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        row = self.db.execute("SELECT id,name,sha256,stored_path FROM documents WHERE sha256=?", (digest,)).fetchone()
        if row: return {"id": row[0], "name": row[1], "sha256": row[2], "stored_path": row[3], "duplicate": True}
        doc_id, destination = uuid4().hex, self.files / f"{digest}{path.suffix.lower()}"
        shutil.copy2(path, destination)
        self.db.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (doc_id, path.name, digest, datetime.now(timezone.utc).isoformat(), str(destination)))
        self.db.commit(); return {"id": doc_id, "name": path.name, "sha256": digest, "stored_path": str(destination), "duplicate": False}

    def save_analysis(self, product: str, config: dict, result: dict, document_ids: list[str]) -> str:
        aid, now = uuid4().hex, datetime.now(timezone.utc).isoformat()
        payload = json.dumps(result, ensure_ascii=False, default=str)
        self.db.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?)", (aid, product, now, "exploratory-medoid-v1", json.dumps(config, ensure_ascii=False), payload))
        self.db.execute("INSERT INTO recipe_versions VALUES(?,?,?,?,?,?,?)", (uuid4().hex, aid, 1, now, payload, "versão calculada", 0))
        self.db.executemany("INSERT INTO analysis_documents VALUES(?,?)", [(aid, d) for d in document_ids]); self.db.commit(); return aid

    def save_alias(self, product: str, alias: str, confirmed: bool = True) -> None:
        self.db.execute("INSERT OR REPLACE INTO aliases VALUES(?,?,?)", (product, alias, int(confirmed)))
        self.db.commit()

    def list_aliases(self, product: str) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT alias FROM aliases WHERE product=? AND confirmed=1", (product,))]

    def list_versions(self, aid: str) -> list[dict]:
        return [dict(zip(("version", "created_at", "justification", "reviewed"), r)) for r in self.db.execute(
            "SELECT version,created_at,justification,reviewed FROM recipe_versions WHERE analysis_id=? ORDER BY version", (aid,))]

    def get_version(self, aid: str, version: int) -> dict:
        row = self.db.execute("SELECT result_json FROM recipe_versions WHERE analysis_id=? AND version=?", (aid, version)).fetchone()
        if not row: raise KeyError(f"{aid}:{version}")
        return json.loads(row[0])

    def get_config(self, aid: str) -> dict:
        row = self.db.execute("SELECT config_json FROM analyses WHERE id=?", (aid,)).fetchone()
        return json.loads(row[0]) if row else {}

    def list_analyses(self) -> list[dict]:
        return [dict(zip(("id","product","created_at","algorithm"), r)) for r in self.db.execute("SELECT id,product,created_at,algorithm FROM analyses ORDER BY created_at DESC")]

    def get_analysis(self, aid: str) -> dict:
        row = self.db.execute("SELECT result_json FROM analyses WHERE id=?", (aid,)).fetchone()
        if not row: raise KeyError(aid)
        return json.loads(row[0])

    def save_revision(self, aid: str, result: dict, justification: str) -> int:
        version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM recipe_versions WHERE analysis_id=?", (aid,)).fetchone()[0]
        self.db.execute("INSERT INTO recipe_versions VALUES(?,?,?,?,?,?,?)", (uuid4().hex, aid, version, datetime.now(timezone.utc).isoformat(), json.dumps(result, ensure_ascii=False), justification, 1)); self.db.commit(); return version

    def delete_analysis(self, aid: str) -> None:
        self.db.execute("DELETE FROM analyses WHERE id=?", (aid,)); self.db.commit()
        referenced = {r[0] for r in self.db.execute("SELECT document_id FROM analysis_documents")}
        for did, path in self.db.execute("SELECT id,stored_path FROM documents").fetchall():
            if did not in referenced:
                Path(path).unlink(missing_ok=True); self.db.execute("DELETE FROM documents WHERE id=?", (did,))
        self.db.commit()

"""Backup and restore. Secrets are included only when explicitly requested."""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from mailgate.config import load_config
from mailgate.paths import BACKUP_DIR, CONFIG_FILE, DATA_DIR, DKIM_DIR, ETC_DIR, POSTFIX_DIR, SECRETS_DIR


MANIFEST_NAME = "manifest.json"


def create_backup(include_secrets: bool = False) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = BACKUP_DIR / f"mailgate-{stamp}.tar.gz"
    cfg = load_config()
    manifest = {
        "created_at": stamp,
        "hostname": cfg.server.hostname,
        "include_secrets": include_secrets,
        "contents": ["config.yml", "postfix/", "database (if sqlite file present)"],
    }
    fd, tmp = tempfile.mkstemp(suffix=".tar.gz", dir=str(BACKUP_DIR))
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        with tarfile.open(tmp_path, "w:gz") as tar:
            _add_if_exists(tar, CONFIG_FILE, "config.yml")
            if POSTFIX_DIR.exists():
                tar.add(POSTFIX_DIR, arcname="postfix")
            sqlite = DATA_DIR / "mailgate.db"
            if sqlite.exists():
                tar.add(sqlite, arcname="mailgate.db")
            if include_secrets and SECRETS_DIR.exists():
                tar.add(SECRETS_DIR, arcname="secrets")
                manifest["contents"].append("secrets/")
            else:
                # DKIM public keys only
                if DKIM_DIR.exists():
                    for pub in DKIM_DIR.rglob("*.public.pem"):
                        tar.add(pub, arcname=f"dkim-public/{pub.parent.name}/{pub.name}")
            manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
            info = tarfile.TarInfo(MANIFEST_NAME)
            info.size = len(manifest_bytes)
            import io

            tar.addfile(info, io.BytesIO(manifest_bytes))
        os.replace(tmp_path, dest)
        dest.chmod(0o600)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return dest


def restore_backup(archive: Path, include_secrets: bool = False) -> dict:
    if not archive.exists():
        raise FileNotFoundError(str(archive))
    ETC_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        _safe_extract(tar, DATA_DIR / "restore-staging")
    staging = DATA_DIR / "restore-staging"
    report = {"restored": []}
    cfg = staging / "config.yml"
    if cfg.exists():
        CONFIG_FILE.write_bytes(cfg.read_bytes())
        report["restored"].append("config.yml")
    postfix_src = staging / "postfix"
    if postfix_src.exists():
        POSTFIX_DIR.mkdir(parents=True, exist_ok=True)
        for item in postfix_src.iterdir():
            target = POSTFIX_DIR / item.name
            if item.is_file():
                target.write_bytes(item.read_bytes())
        report["restored"].append("postfix maps")
    db = staging / "mailgate.db"
    if db.exists():
        (DATA_DIR / "mailgate.db").write_bytes(db.read_bytes())
        report["restored"].append("sqlite database")
    if include_secrets:
        secrets_src = staging / "secrets"
        if secrets_src.exists():
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            for item in secrets_src.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(secrets_src)
                    dest = SECRETS_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(item.read_bytes())
                    dest.chmod(0o600)
            report["restored"].append("secrets")
    return report


def _add_if_exists(tar: tarfile.TarFile, path: Path, arcname: str) -> None:
    if path.exists():
        tar.add(path, arcname=arcname)


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        member_path = (dest / member.name).resolve()
        if not str(member_path).startswith(str(dest_resolved)):
            raise RuntimeError("Backup archive contains an unsafe path")
    tar.extractall(dest)

"""Background worker: ingest Postfix logs, expire old events, watch public IP."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from mailgate.config import load_config
from mailgate.db import get_session_factory, init_db
from mailgate.models import MailEvent, SystemSetting
from mailgate.services.logs import classify_line, read_journal
from mailgate.services.network import detect_network

log = logging.getLogger("mailgate.worker")


def ingest_logs(session) -> int:
    lines = read_journal("postfix", lines=300)
    inserted = 0
    seen_ids = set(
        session.scalars(
            select(MailEvent.queue_id).where(MailEvent.queue_id.is_not(None)).limit(2000)
        ).all()
    )
    for line in lines:
        parsed = classify_line(line)
        if not parsed:
            continue
        # Deduplicate loosely by queue + type + recipient
        exists = session.scalar(
            select(MailEvent.id).where(
                MailEvent.queue_id == parsed["queue_id"],
                MailEvent.event_type == parsed["event_type"],
                MailEvent.recipient == parsed["recipient"],
                MailEvent.response == parsed["response"],
            )
        )
        if exists:
            continue
        session.add(MailEvent(**parsed))
        inserted += 1
    return inserted


def expire_events(session) -> int:
    cfg = load_config()
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.logging.retain_events_days)
    result = session.execute(delete(MailEvent).where(MailEvent.timestamp < cutoff))
    return result.rowcount or 0


def watch_public_ip(session) -> None:
    net = detect_network()
    if not net.public_ipv4:
        return
    row = session.get(SystemSetting, "public_ipv4")
    if row is None:
        session.add(SystemSetting(key="public_ipv4", value=net.public_ipv4))
        return
    if row.value != net.public_ipv4:
        log.warning("Public IP changed: %s -> %s", row.value, net.public_ipv4)
        session.add(
            MailEvent(
                event_type="system",
                status="warning",
                response=f"Public IP changed from {row.value} to {net.public_ipv4}. Update DNS A records.",
            )
        )
        row.value = net.public_ipv4


def run_forever(interval: int = 15) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db()
    factory = get_session_factory()
    log.info("MailGate worker started")
    while True:
        session = factory()
        try:
            n = ingest_logs(session)
            expired = expire_events(session)
            watch_public_ip(session)
            session.commit()
            if n or expired:
                log.info("ingested=%s expired=%s", n, expired)
        except Exception:
            session.rollback()
            log.exception("worker loop failed")
        finally:
            session.close()
        time.sleep(interval)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()

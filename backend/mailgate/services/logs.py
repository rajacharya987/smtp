"""Parse Postfix logs into structured MailGate events. Bodies are never stored."""

from __future__ import annotations

import re
from datetime import datetime, timezone

QUEUE_RE = re.compile(r"\b([A-F0-9]{8,12}):\s+(.*)")
FROM_RE = re.compile(r"from=<([^>]*)>")
TO_RE = re.compile(r"to=<([^>]*)>")
STATUS_RE = re.compile(r"status=(\w+)(?:\s+\((.*)\))?")
SIZE_RE = re.compile(r"size=(\d+)")
CLIENT_RE = re.compile(r"client=([^\s]+)")
REJECT_RE = re.compile(r"reject:\s+(.*)")
MSGID_RE = re.compile(r"message-id=<([^>]+)>")


EVENT_MAP = {
    "sent": ("delivered", "Delivered"),
    "deferred": ("deferred", "Deferred"),
    "bounced": ("failed", "Failed"),
    "reject": ("rejected", "Rejected"),
    "hold": ("spam", "Held"),
}


def classify_line(line: str) -> dict | None:
    if "postfix" not in line and "postfix/" not in line:
        # still try — journalctl lines include the unit
        if "smtpd" not in line and "qmgr" not in line and "smtp[" not in line and "pipe" not in line:
            if "postfix/" not in line:
                pass
    match = QUEUE_RE.search(line)
    queue_id = match.group(1) if match else None
    rest = match.group(2) if match else line

    event_type = None
    status = None
    response = None

    if "reject:" in line or "NOQUEUE: reject" in line:
        event_type = "rejected"
        status = "rejected"
        rej = REJECT_RE.search(line)
        response = rej.group(1) if rej else line[-300:]
    elif "spam" in line.lower() and "reject" in line.lower():
        event_type = "spam"
        status = "spam"
    elif "status=" in rest:
        st = STATUS_RE.search(rest)
        if st:
            raw = st.group(1)
            response = st.group(2)
            event_type, status = EVENT_MAP.get(raw, (raw, raw))
            if raw == "sent":
                event_type = "delivered"
            elif raw == "deferred":
                event_type = "deferred"
    elif "from=<" in rest and queue_id and "client=" in line:
        event_type = "accepted"
        status = "accepted"
    elif "message-id=" in rest:
        event_type = "accepted"
        status = "accepted"
    else:
        return None

    sender = None
    recipient = None
    frm = FROM_RE.search(line)
    to = TO_RE.search(line)
    if frm:
        sender = frm.group(1)
    if to:
        recipient = to.group(1)
    size = None
    sm = SIZE_RE.search(line)
    if sm:
        size = int(sm.group(1))
    msgid = None
    mm = MSGID_RE.search(line)
    if mm:
        msgid = mm.group(1)

    destination = recipient if event_type in {"forwarded", "delivered", "deferred", "failed"} else None

    return {
        "timestamp": datetime.now(timezone.utc),
        "event_type": event_type,
        "queue_id": queue_id,
        "message_id": msgid,
        "sender": sender,
        "recipient": recipient,
        "destination": destination,
        "size": size,
        "status": status,
        "response": (response or "")[:500] or None,
        "extra": None,
    }


def read_journal(unit: str = "postfix", lines: int = 200) -> list[str]:
    import shutil
    import subprocess

    if not shutil.which("journalctl"):
        return []
    result = subprocess.run(
        ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "-o", "cat"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()

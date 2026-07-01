import logging
import socket

from fastapi import APIRouter

router = APIRouter(tags=["Saude"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/smtp-test")
def smtp_tcp_test() -> dict[str, list[dict[str, str | int | bool]]]:
    targets = [
        ("smtp.gmail.com", 587),
        ("smtp-relay.gmail.com", 587),
        ("smtp.gmail.com", 465),
    ]
    results = []
    for host, port in targets:
        logger.info("SMTP TCP test starting. host=%s port=%s timeout=10", host, port)
        try:
            with socket.create_connection((host, port), timeout=10):
                logger.info("SMTP TCP test succeeded. host=%s port=%s", host, port)
            results.append({"host": host, "port": port, "ok": True, "error": ""})
        except OSError as exc:
            logger.exception("SMTP TCP test failed. host=%s port=%s", host, port)
            results.append({"host": host, "port": port, "ok": False, "error": str(exc)})
    return {"results": results}

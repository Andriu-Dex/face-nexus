"""Envía CHECK al firmware LATCH. No reenvía si falta el acuse."""

from time import monotonic

from scripts.hog_knn import PEOPLE


LATCH_PONG = "PONG FACENEXUS LATCH 1"
BENCH_PONG = "PONG FACENEXUS BENCH 1"


def ping_firmware(connection, timeout=2):
    connection.write(b"PING\n")
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = connection.readline().decode("ascii", errors="replace").strip()
        if response.startswith("READY") or not response:
            continue
        return response
    raise TimeoutError("Sin respuesta a PING.")


def latch_ready(pong):
    return pong == LATCH_PONG


def format_check(event_id, identity, decision):
    if identity not in PEOPLE and identity != "UNKNOWN":
        raise ValueError("Identidad no permitida.")
    if decision not in {"GRANTED", "DENIED"}:
        raise ValueError("Decisión no permitida.")
    if decision == "GRANTED" and identity == "UNKNOWN":
        raise ValueError("UNKNOWN no puede ir con GRANTED.")
    text_id = str(event_id)
    if not text_id.isdigit() or len(text_id) > 16:
        raise ValueError("Identificador de evento inválido.")
    return f"CHECK {text_id} {identity} {decision}"


def read_ack(connection, expected, timeout=4):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = connection.readline().decode("ascii", errors="replace").strip()
        if response.startswith("READY") or not response:
            continue
        if response == expected:
            return response
        raise RuntimeError(f"Respuesta inesperada: {response}")
    raise TimeoutError("Sin acuse del pestillo.")


def send_decision(connection, event_id, identity, decision):
    command = format_check(event_id, identity, decision)
    connection.write((command + "\n").encode("ascii"))
    suffix = "ACTUATED" if decision == "GRANTED" else "CLOSED"
    expected = f"ACK {event_id} {identity} {decision} {suffix}"
    ack = read_ack(connection, expected, timeout=4 if decision == "DENIED" else 8)
    return {
        "command": command,
        "ack": ack,
        "pulse_confirmed": ack == expected and suffix == "ACTUATED",
        "state": "ACTUATED" if suffix == "ACTUATED" else "CLOSED",
    }

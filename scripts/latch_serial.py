"""Envía CHECK al firmware LATCH. No reenvía si falta el acuse."""

from time import monotonic, sleep

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


SERVO_CLOSED = 20
SERVO_OPEN = 90


def send_servo_test(port, action="cycle", degrees=None):
    """Una operación manual por conexión, sin decisiones de reconocimiento."""
    import serial

    if action not in ("check", "cycle", "move"):
        raise ValueError("Operación de servo desconocida.")
    if action == "move" and (type(degrees) is not int or not SERVO_CLOSED <= degrees <= SERVO_OPEN):
        raise ValueError(f"El ángulo debe estar entre {SERVO_CLOSED}° y {SERVO_OPEN}°.")
    connection = serial.Serial(baudrate=115200, timeout=.2, write_timeout=2)
    connection.port = port
    connection.dtr = False
    connection.rts = False
    with connection:
        sleep(2)
        connection.reset_input_buffer()
        pong = ping_firmware(connection)
        if not latch_ready(pong):
            raise RuntimeError("El ESP32 no respondió como firmware LATCH.")
        if action == "check":
            return pong
        if action == "move":
            connection.write(b"SERVO RANGE\n")
            read_ack(connection, f"SERVO RANGE {SERVO_CLOSED} {SERVO_OPEN}")
            connection.write(f"SERVO MOVE {degrees}\n".encode("ascii"))
            return read_ack(connection, f"SERVO ACK {degrees}")
        event = str(int(monotonic() * 1000))[-16:]
        return send_decision(connection, event, PEOPLE[0], "GRANTED")["ack"]

"""Envía CHECK al firmware LATCH. No reenvía si falta el acuse."""

from time import monotonic, sleep

from scripts.hog_knn import PEOPLE


LATCH_PONG = "PONG FACENEXUS LATCH 1"
BENCH_PONG = "PONG FACENEXUS BENCH 1"
PROTOCOL_PREFIXES = ("ACK", "ERROR", "SERVO")


def read_line(connection):
    """Una línea del ESP32 sin el ruido 0xFF que a veces deja la apertura del puerto."""
    raw = connection.readline().lstrip(bytes((0xFF, 0x00)))
    return raw.decode("ascii", errors="replace").strip()


def open_latch_port(port):
    """Abre sin activar DTR/RTS, igual que el banco de pruebas, para no alterar al ESP32."""
    import serial

    connection = serial.Serial(baudrate=115200, timeout=.2, write_timeout=2)
    connection.port = port
    connection.dtr = False
    connection.rts = False
    connection.open()
    # La primera escritura tras abrir puede ir precedida de ruido 0xFF; una línea vacía
    # lo absorbe y luego se descarta todo lo recibido antes del PING real.
    sleep(2)
    connection.write(b"\n")
    sleep(.3)
    connection.reset_input_buffer()
    return connection


def ping_firmware(connection, timeout=2):
    connection.write(b"PING\n")
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = read_line(connection)
        if response.startswith("PONG"):
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
        response = read_line(connection)
        if response == expected:
            return response
        # Solo un mensaje del protocolo distinto al esperado es una falla; un fragmento
        # de ruido serie se ignora y se sigue esperando hasta el límite de tiempo.
        if response.startswith(PROTOCOL_PREFIXES):
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


SERVO_CLOSED = 100
SERVO_OPEN = 0
# Recorrido físico del SG90; cierre y apertura son posiciones dentro de él.
SERVO_MIN = 0
SERVO_MAX = 180


def run_servo_test(connection, action="cycle", degrees=None):
    """Una operación manual sobre una conexión ya abierta y verificada."""
    if action not in ("check", "cycle", "move"):
        raise ValueError("Operación de servo desconocida.")
    if action == "move" and (type(degrees) is not int or not SERVO_MIN <= degrees <= SERVO_MAX):
        raise ValueError(f"El ángulo debe estar entre {SERVO_MIN}° y {SERVO_MAX}°.")
    pong = ping_firmware(connection)
    if not latch_ready(pong):
        raise RuntimeError("El ESP32 no respondió como firmware LATCH.")
    if action == "check":
        return pong
    if action == "move":
        connection.write(b"SERVO RANGE\n")
        read_ack(connection, f"SERVO RANGE {SERVO_MIN} {SERVO_MAX}")
        connection.write(f"SERVO MOVE {degrees}\n".encode("ascii"))
        return read_ack(connection, f"SERVO ACK {degrees}")
    event = str(int(monotonic() * 1000))[-16:]
    return send_decision(connection, event, PEOPLE[0], "GRANTED")["ack"]


def send_servo_test(port, action="cycle", degrees=None):
    """Abre el puerto solo para esta operación (cuando el reconocimiento no lo tiene abierto)."""
    if action not in ("check", "cycle", "move"):
        raise ValueError("Operación de servo desconocida.")
    if action == "move" and (type(degrees) is not int or not SERVO_MIN <= degrees <= SERVO_MAX):
        raise ValueError(f"El ángulo debe estar entre {SERVO_MIN}° y {SERVO_MAX}°.")
    with open_latch_port(port) as connection:
        return run_servo_test(connection, action, degrees)

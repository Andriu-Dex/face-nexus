"""Comprueba el protocolo de banco FaceNexus con el actuador desconectado."""

import argparse
import time


CASES = (
    ("CHECK 1 K01 GRANTED", "ACK 1 K01 GRANTED SIMULATED"),
    ("CHECK 2 K01 DENIED", "ACK 2 K01 DENIED SIMULATED"),
    ("CHECK 3 UNKNOWN DENIED", "ACK 3 UNKNOWN DENIED SIMULATED"),
    ("CHECK 4 UNKNOWN GRANTED", "ERROR BAD_DECISION"),
    ("CHECK xyz K01 GRANTED", "ERROR BAD_COMMAND"),
    ("CHECK1 K01 GRANTED", "ERROR BAD_COMMAND"),
    ("CHECK 1234567890123456K01 GRANTED", "ERROR BAD_COMMAND"),
    ("CHECK 1234567890123456 K04 GRANTED", "ACK 1234567890123456 K04 GRANTED SIMULATED"),
    ("X" * 100, "ERROR LINE_TOO_LONG"),
    ("PING", "PONG FACENEXUS BENCH 1"),
)


def check_reply(connection, command, expected, timeout=2):
    connection.write((command + "\n").encode("ascii"))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = connection.readline().decode("ascii", errors="replace").strip()
        if response == expected:
            return response
        if response and not response.startswith("READY"):
            raise RuntimeError(f"Respuesta inesperada: {response}")
    raise TimeoutError(f"Sin respuesta esperada para {command[:30]}.")


def main():
    import serial

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    args = parser.parse_args()
    try:
        with serial.Serial(args.port, 115200, timeout=.2, write_timeout=2) as connection:
            time.sleep(2)
            connection.reset_input_buffer()
            print(check_reply(connection, "PING", "PONG FACENEXUS BENCH 1"))
            for command, expected in CASES:
                print(check_reply(connection, command, expected))
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"Prueba detenida: {error}\n")


if __name__ == "__main__":
    main()

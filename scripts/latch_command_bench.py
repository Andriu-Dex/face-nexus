"""Órdenes de banco al firmware LATCH. No usa reconocimiento ni flashea."""

import argparse
import time

from scripts.latch_serial import LATCH_PONG, format_check, latch_ready, ping_firmware, read_ack
from scripts.serial_bench import check_reply


def latch_cases():
    """GRANTED mueve el pin; DENIED no. UNKNOWN no puede ir con GRANTED."""
    return (
        ("PING", LATCH_PONG),
        (format_check(1, "K01", "DENIED"), "ACK 1 K01 DENIED CLOSED"),
        (format_check(2, "UNKNOWN", "DENIED"), "ACK 2 UNKNOWN DENIED CLOSED"),
        ("CHECK 3 UNKNOWN GRANTED", "ERROR BAD_DECISION"),
        (format_check(4, "K01", "GRANTED"), "ACK 4 K01 GRANTED ACTUATED"),
    )


def require_disconnected_servo(confirmed):
    if confirmed is not True:
        raise ValueError("Confirmar --servo-disconnected. El SG90 no debe estar engranado.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--servo-disconnected", action="store_true",
                        help="Obligatorio: mecanismo libre o servo desconectado.")
    args = parser.parse_args()
    try:
        require_disconnected_servo(args.servo_disconnected)
        import serial
        with serial.Serial(args.port, 115200, timeout=.2, write_timeout=2) as connection:
            time.sleep(2)
            connection.reset_input_buffer()
            pong = ping_firmware(connection)
            if not latch_ready(pong):
                raise RuntimeError(f"Firmware {pong}. Se espera {LATCH_PONG}.")
            print(pong)
            for command, expected in latch_cases():
                if command == "PING":
                    print(check_reply(connection, command, expected))
                    continue
                connection.write((command + "\n").encode("ascii"))
                print(read_ack(connection, expected, timeout=8))
    except (OSError, RuntimeError, ValueError, TimeoutError) as error:
        parser.exit(1, f"Prueba detenida: {error}\n")


if __name__ == "__main__":
    main()

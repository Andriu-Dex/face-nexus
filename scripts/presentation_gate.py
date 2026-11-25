"""Latido de apertura: mientras haya un autorizado se renueva la orden cada medio segundo.

El ESP32 cierra solo si deja de recibir GRANTED durante HOLD_MS (3 s). Así, si la PC,
la cámara o el cable fallan con la puerta abierta, la puerta se cierra igualmente.
"""

from time import monotonic

AUTHORIZED = "authorized"
EMPTY = "empty"
UNCERTAIN = "uncertain"
HEARTBEAT_SECONDS = 0.5
# Fotogramas autorizados seguidos antes de abrir (~0,6 s a 13 fps). Un desconocido parecido
# a un integrante suele parpadear entre Autorizado y Desconocido; un integrante real no.
CONSENSUS_FRAMES = 8


def scene_kind(scene):
    """Autorizado, ausencia de detección, o incertidumbre."""
    if scene.get("outcome") == "GRANTED":
        return AUTHORIZED
    if scene.get("reason") == "no_face":
        return EMPTY
    return UNCERTAIN


class PresentationGate:
    def __init__(self):
        self.can_send = True
        self.last_sent = None
        self.streak = 0

    def rearm(self):
        """El operador confirma que la falla del pestillo quedó resuelta."""
        self.can_send = True
        self.last_sent = None

    def interrupt(self):
        """La autorización se perdió (sin rostro, señal perdida, caducidad): exige una racha nueva.

        No bloquea: al dejar de renovar, el ESP32 cierra solo tras 3 s.
        """
        self.streak = 0

    def note_fault(self):
        self.can_send = False

    def note_disconnect(self):
        self.interrupt()

    def on_frame(self, kind, now=None):
        """True si este fotograma debe renovar la orden de apertura.

        Un fotograma sin autorizado no envía nada: el silencio basta para que el ESP32 cierre.
        """
        self.streak = self.streak + 1 if kind == AUTHORIZED else 0
        if self.streak < CONSENSUS_FRAMES or not self.can_send:
            return False
        now = monotonic() if now is None else now
        if self.last_sent is not None and now - self.last_sent < HEARTBEAT_SECONDS:
            return False
        self.last_sent = now
        return True

"""Una orden física por presentación. YuNet no_face no cuenta como salida."""

AUTHORIZED = "authorized"
EMPTY = "empty"
UNCERTAIN = "uncertain"


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

    def rearm(self):
        """El operador confirma que la presentación terminó."""
        self.can_send = True

    def note_fault(self):
        self.can_send = False

    def note_disconnect(self):
        self.note_fault()

    def on_frame(self, kind):
        """True solo si este fotograma puede emitir la orden física."""
        if kind != AUTHORIZED:
            if kind != EMPTY:
                self.note_fault()
            return False
        if not self.can_send:
            return False
        self.can_send = False
        return True

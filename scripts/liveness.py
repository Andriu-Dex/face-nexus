"""Prueba de vida por giro de cabeza con los cinco puntos de YuNet. Sin modelos adicionales.

Idea geométrica: una foto o una pantalla es plana. Si se inclina, la nariz conserva su
posición proporcional entre los ojos. Una cabeza real es tridimensional: al girar, la nariz
se desplaza respecto del punto medio de los ojos (paralaje).

Razón de giro = (x_nariz − x_punto_medio_ojos) / distancia_entre_ojos.
  De frente ≈ 0; al girar crece hacia un lado u otro.
Se acepta la prueba cuando, para la misma identidad autorizada y dentro de WINDOW_SECONDS,
la razón recorre al menos MIN_SPAN (máximo − mínimo).

Medición con los videos 05 (26-11-2026): una foto plana simulada girada de −45° a +45°
recorrió como máximo 0,15; la cabeza real de cada integrante recorrió de 0,72 a 3,3
(percentiles 5 a 95). MIN_SPAN = 0,35 queda por encima del doble de la foto.

No detiene un video del integrante girando la cabeza: eso exige un modelo antisuplantación.
"""

from collections import deque

MIN_SPAN = 0.35
WINDOW_SECONDS = 5.0
# Con el perfil completo los ojos casi coinciden y la razón se dispara; esas muestras se ignoran.
MAX_VALID_RATIO = 1.5
# Si no hay rostro durante este lapso, la siguiente persona debe repetir la prueba.
RESET_SECONDS = 1.0


def turn_ratio(landmarks):
    """Razón de giro con los puntos de YuNet: ojo derecho, ojo izquierdo, nariz, ..."""
    (right_x, right_y), (left_x, left_y), (nose_x, _nose_y) = landmarks[:3]
    eye_distance = ((left_x - right_x) ** 2 + (left_y - right_y) ** 2) ** 0.5
    if eye_distance < 1:
        return None
    ratio = (nose_x - (right_x + left_x) / 2) / eye_distance
    return ratio if abs(ratio) <= MAX_VALID_RATIO else None


class LivenessCheck:
    """Sigue a la identidad autorizada y decide si giró la cabeza."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.identity = None
        self.samples = deque()
        self.passed = False
        self.last_face_at = None

    def update(self, scene, now):
        """Registra un fotograma. Devuelve True si la identidad actual ya pasó la prueba."""
        regions = scene.get("regions") or []
        if not regions:
            if self.last_face_at is not None and now - self.last_face_at > RESET_SECONDS:
                self.reset()
            return self.passed
        self.last_face_at = now
        granted = next((row for row in regions
                        if row.get("outcome") == "GRANTED" and row.get("landmarks")), None)
        if granted is None:
            return self.passed
        # Solo cuentan muestras de la misma identidad autorizada: un tercero girando la cabeza
        # no puede «prestar» su movimiento a la foto de un integrante.
        if granted["identity"] != self.identity:
            self.reset()
            self.identity = granted["identity"]
            self.last_face_at = now
        ratio = turn_ratio(granted["landmarks"])
        if ratio is not None:
            self.samples.append((now, ratio))
        while self.samples and now - self.samples[0][0] > WINDOW_SECONDS:
            self.samples.popleft()
        if self.samples:
            values = [value for _, value in self.samples]
            self.passed = self.passed or max(values) - min(values) >= MIN_SPAN
        return self.passed

    def progress(self):
        """Fracción del recorrido exigido (0 a 1), para mostrarla en la interfaz."""
        if self.passed:
            return 1.0
        if not self.samples:
            return 0.0
        values = [value for _, value in self.samples]
        return min(1.0, (max(values) - min(values)) / MIN_SPAN)

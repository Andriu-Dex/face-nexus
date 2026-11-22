# Cuatro identidades con encuentros de Downloads y pestillo

22-11-2026. Se usan las carpetas privadas de `C:\Downloads\FaceNexus\data` **sin copiar las fotos a Git**. TRAIN y VALIDATION son encuentros distintos. No es TEST ni el celular de la defensa.

## Partición (no por ráfaga)

| ID | TRAIN | VALIDATION |
| --- | --- | --- |
| K01 | Encuentro propio A + 15 HOG del celular `k01_phone_v3` | Encuentro propio B |
| K02 | Dos encuentros anteriores | Lote posterior (sesión 03) |
| K03 | Dos encuentros anteriores | Lote posterior (sesión 03) |
| K04 | Dos encuentros anteriores | Lote posterior (sesión 03) |

La correspondencia carpeta → ID está en el manifiesto privado del volumen, no en Git.

YuNet, un solo recorte, HOG 1764-D, k=3. Ensayo `identity_four_v2`. Galería 120 vectores, SHA-256 `139a8e839928f3a7fab211373dd96cc92b52a7e79f148faf9cea31fde8eed339`. T = 0,770 (máximo d de aciertos en VALIDATION × 1,1).

## Validación (39 recortes usables)

Filas = verdadero; columnas = K01, K02, K03, K04, otro.

| | K01 | K02 | K03 | K04 | ? | Aciertos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K01 | 9 | 0 | 0 | 3 | 0 | 9/12 |
| K02 | 0 | 5 | 4 | 0 | 0 | **5/9** |
| K03 | 0 | 0 | 9 | 0 | 0 | 9/9 |
| K04 | 1 | 0 | 0 | 8 | 0 | 8/9 |

Exactitud **31/39 = 0,79**. T no cambió esas cifras: los errores están cerca, no lejos. K02 se confunde con K03. Eso **no** está listo para la defensa: hace falta el mismo celular de demostración para K02–K04.

El vivo y la interfaz cargan esta galería. Cualquier K01–K04 con permiso activo autoriza la escena (varios rostros). Un extraño debe quedar `DENIED` si no gana el voto o supera T.

## Interfaz y pestillo

`scripts/operator_ui.py`: cámara o **Abrir imagen / Probar carpeta**, permisos por casilla, historial sin fotos, cajas verde/rojo.

Firmware `firmware/latch/latch.ino`: GPIO **18**, pulso 90° / 1,5 s / cierra 20°. Alimentar el SG90 a **5 V externos**, GND común, no desde el 3,3 V del ESP32. Acuse `ACTUATED` o `CLOSED`. El firmware de banco (`SIMULATED`) **no** mueve el servo; hay que grabar este.

El 22-11-2026 el ESP32 en COM5 respondió `PONG FACENEXUS BENCH 1`. No se flasheó `latch` ni se observó el servo.

```powershell
.\.venv\Scripts\python.exe -m scripts.operator_ui --vault V:\FaceNexus --url http://192.168.1.20:8080/video --port COM5
```

Probar carpeta: PNG de VALIDATION en el volumen privado. No promete el mismo resultado que el celular del aula. Las imágenes no envían orden serie.

## Escenarios del profesor

| Caso | Estado |
| --- | --- |
| Un integrante autorizado | Cubierto en código; K02 débil en estas fotos |
| Cuatro a la vez | Una caja autorizada basta; falta dominio celular |
| Extraño solo | T + voto; no medido con un desconocido de Downloads |
| Permiso revocado | Casillas de la interfaz, sin reentrenar |
| Foto impresa | No hay liveness; dirá autorizado si el HOG coincide |
| Pestillo | Código listo; hay que grabar firmware y observar el SG90 |

## Limitaciones

WhatsApp/WIN y TMCAM no son la IP Webcam. 16 fotogramas por carpeta no equivalen a miles de identidades independientes. K02 frente a K03 es el fallo a corregir el lunes.

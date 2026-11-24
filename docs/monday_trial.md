# Guion del ensayo (celular, simulación)

Montar VeraCrypt en `V:\FaceNexus`. Sin lentes en las tomas nuevas. Conservar las fotos históricas con lentes. No cambiar T, G ni el preprocesamiento después de congelar.

Un `encounter-id` distinto **no** basta: tune y eval deben ser sesiones distintas (otro momento, otra toma). No reutilizar la ráfaga de tune como eval.

`FaceNexus.cmd` carga `identity_four/identity_four_v2`. El candidato `--phone-tune` vive en `experiments/identity_four_other/<run>` y **no** pisa v2. Para evaluarlo en la UI hay que pasar `--trial` explícito.

## URL y giro (antes de capturar)

Sustituir IP y puerto por los que muestre IP Webcam. Anotar el giro que deje el rostro derecho.

```powershell
$PhoneUrl = 'http://192.168.1.20:8080/video'
$Rotation = 0
Set-Location -LiteralPath 'C:\Documentos\D-Proyectos\Git\FaceNexus'
.\.venv\Scripts\python.exe -m scripts.calibrate_hog probe --url $PhoneUrl
```

Usar el mismo `$PhoneUrl` y `--rotation $Rotation` en captura, eval y, si hace falta, en la UI.

## Arranque (galería vigente, simulación)

```powershell
.\FaceNexus.cmd
```

En Cámara: IP y puerto 8080, o `IP:8080`. Sin `--port`. Giro el que salió del probe.

## Captura tune (encuentro A)

Un encuentro por persona, **sin lentes**, en este momento. `encounter-id` y `run-name` propios.

```powershell
.\.venv\Scripts\python.exe -m scripts.capture_phone_train --vault V:\FaceNexus --url $PhoneUrl --rotation $Rotation --person K01 --run-name k01_phone_tune_lunes --encounter-id E_TUNE_LUNES_K01 --role tune
```

Repetir K02–K04 con su `person`, `run-name` y `encounter-id`.

## Ajuste (congela el modelo; no pisa v2)

Nombre de ensayo **nuevo**. Si `identity_four_other_v1` ya existe, el comando falla.

```powershell
$Trial = 'identity_four_other_phone_lunes'
.\.venv\Scripts\python.exe -m scripts.identity_four_other --vault V:\FaceNexus --run-name $Trial --phone-tune
```

Anotar de `summary.json`: `gallery_sha256`, T y G (si el ensayo los escribe) o las métricas de k-NN. A partir de aquí no se retocan umbrales ni HOG.

## Captura eval (encuentro B)

Otra sesión, otro `encounter-id`, `--role eval`. No mezclar con tune.

```powershell
.\.venv\Scripts\python.exe -m scripts.capture_phone_train --vault V:\FaceNexus --url $PhoneUrl --rotation $Rotation --person K01 --run-name k01_phone_eval_lunes --encounter-id E_EVAL_LUNES_K01 --role eval
```

Repetir K02–K04.

## Evaluación del candidato (no consume TEST)

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_demo_domain --vault V:\FaceNexus --gallery-run $Trial --report-name phone_eval_lunes --use-phone-eval
```

La UI del candidato (simulación; no sustituye `FaceNexus.cmd`):

```powershell
.\.venv\Scripts\python.exe -m scripts.operator_ui --vault V:\FaceNexus --url $PhoneUrl --rotation $Rotation --trial identity_four_other/$Trial
```

Comprobar en el panel: ensayo `identity_four_other/...`, hash de galería, T y G. Si no coinciden con el `summary.json` anotado, no empezar el conteo.

`--phone-tune` no pisa v2. La UI k-NN solo acepta el candidato si esa carpeta tiene galería y `knn_max_distance.json` verificados (`load_verified_knn`). Si falta el umbral ligado, todo queda Denegado y la evaluación numérica es `compare_demo_domain`, no copiar T/G de v2.

## Conteo por presentación

Una fila por presentación, no por ráfaga. Modelo congelado.

| # | Quién (código) | Encuentro | Luz / giro / dist. | Esperado | Visto | Autorizado / Denegado | Motivo en pantalla | Notas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |

Casos mínimos: cada K01–K04; permiso inactivo; desconocido; fondo; dos autorizados; autorizado + extraño. Foto en pantalla = exploratorio.

### Ensayo presencial sin hardware

En **Reconocimiento**, seleccionar un candidato verificado y registrar el ensayo y la huella que muestra **Detalle técnico**. Mantener el mismo modelo, lente y umbrales durante una ronda. SFace sirve para la comparación experimental. Si se repite con otro modelo, usar el mismo orden y condiciones.

Empezar con el cuadro vacío. Para cada integrante, hacer tres presentaciones de tres segundos: de frente, con un giro suave a la izquierda y con un giro suave a la derecha. Entre presentaciones, dejar el cuadro vacío dos segundos. Anotar una fila por presentación, con la identidad observada, la decisión y cualquier identidad incorrecta que haya aparecido durante el intento. Conservar como observaciones los cambios intermitentes de estado. El contador de la interfaz agrupa fotogramas y no sustituye el conteo por presentación.

Después, probar un integrante reconocido con su permiso desactivado, dos integrantes con permiso y, si hay un voluntario que acepte participar, un desconocido solo y junto a un integrante autorizado. En una escena mixta registrar por separado la identidad de cada rostro y la autorización de la escena. La autorización esperada depende de que haya al menos un inscrito correctamente reconocido con permiso activo.

## Banco físico (aparte del reconocimiento)

El reconocimiento **sigue en simulación** hasta cerrar estos bancos. No grabar `firmware/latch` en esta sesión si no está acordado. No pasar `--port` a la UI.

### 1. Serie con SG90 fuera

Los tres cables del servo (PWM, GND y V5) **desconectados**. Firmware de banco: `PONG FACENEXUS BENCH 1`.

```powershell
.\.venv\Scripts\python.exe -m scripts.latch_command_bench --port COM5 --servo-disconnected --v5-unplugged
```

### 2. Servo sin carga y fuente externa (después)

Mecanismo libre. Rojo (V+) a la fuente externa; tierra común con el ESP32; PWM al GPIO. **V5 del ESP32 queda libre** (no alimentar el SG90 desde V5). Firmware de pestillo: `PONG FACENEXUS LATCH 1`. Distinguir orden, acuse y movimiento **visto**. `pulse_confirmed` no es posición.

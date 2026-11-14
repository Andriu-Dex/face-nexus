# Verificación de la herramienta de diagnóstico

Fecha local: 13-11-2026. Alcance: incorporación de la cámara elegida y primer código de diagnóstico, sin reconocimiento ni entrenamiento.

## Implementado y comprobado

- TMCAM 8305 registrada como cámara oficial, objetivo 1920×1080/30 FPS y 60 Hz previsto pendiente de comprobación.
- Script con selección explícita de índice/backend, confirmación del operador, vista transitoria opcional, calentamiento y ensayo de 600 segundos por defecto.
- Medición de entregas mediante reloj monotónico, dimensiones de matrices, intervalos y pausas. JSON técnico en outputs, sin imágenes, vídeos ni vectores.
- Fallo de lectura termina el ensayo; no cambia de cámara ni reconecta automáticamente. Q/Esc cancela con vista activa; sin vista se usa Ctrl+C. Las llamadas nativas bloqueadas son una limitación documentada.
- Entorno local .venv creado. Python 3.14.7, paquete opencv-python 4.14.0.94 (cv2 4.14.0), NumPy 2.5.4 y pytest 9.2.0 instalados. OpenCV y pytest fijados en requirements; no se descargaron pesos ni datasets.

Comandos ejecutados: `.venv/Scripts/python.exe -m pytest -q` → **11 passed**; ayuda CLI ejecutada correctamente; `git diff --check` sin errores. Los tests usan reloj, matrices y dispositivo ficticios. Cubren frecuencia efectiva, calentamiento, pausas, fallo de lectura, interrupción, parámetros inválidos, apertura fallida con liberación y JSON, y cancelación antes de importar OpenCV. No acreditan funcionamiento físico.

## Hardware: evidencia y pendientes

La consulta PnP de Windows detectó Integrated Camera y USB CAMERA con estado OK; también un dispositivo de imagen de impresora. No se guardaron identificadores de serie. PnP no acredita que USB CAMERA sea una TMCAM 8305 ni que su índice OpenCV sea 1.

Estado inicial de la entrega de herramienta: no se abrió la webcam hasta recibir la confirmación del responsable. Tras su respuesta se ejecutó el ensayo continuo registrado abajo; 60 Hz y desconexión/reconexión se verifican por separado.

Ejecutar el procedimiento de [camera_diagnostic.md](../camera_diagnostic.md) una vez identificado el dispositivo. Conservar reportes técnicos de cada intento y añadir resultados observados. No iniciar captura masiva todavía.

## Archivos y trazabilidad

Código: scripts/camera_diagnostic.py y scripts/__init__.py; pruebas: tests/test_camera_diagnostic.py; dependencias: requirements.txt y requirements-dev.txt. Documentación ajustada: requisitos, arquitectura, protocolo de datos, plan, decisiones y README; se corrigieron enlaces que aún apuntaban al nombre anterior de 02_dataset_research.md.

Los cambios previos del usuario se conservaron. No se modificó instruction.md, no se creó commit ni se alteró el índice de Git. Mensaje de commit propuesto tras revisar la entrega: `feat: add camera diagnostics without frame persistence`.

Limitación de evidencia: los reportes técnicos no detectan por sí solos fotogramas repetidos del sensor ni congelamientos visuales y no miden latencia óptica. La visualización puede reducir FPS de entrega; se registra si estaba activa. La prueba inicial no demuestra estabilidad indefinida.


## Ensayo continuo real — 13-11-2026

El responsable confirmó USB CAMERA como TMCAM 8305 y escena sin personas. Se instaló cv2-enumerate-cameras 1.4.0 (MIT, herramienta de desarrollo) para mapear nombres a índices DirectShow sin abrir cámaras por tanteo: 0=Integrated Camera y 1=USB CAMERA. Se abrió únicamente el índice 1.

Inicio del proceso 16:43:02, zona America/Guayaquil (21:43:02 UTC). Comando: `.venv/Scripts/python.exe scripts/camera_diagnostic.py --camera 1 --backend dshow --duration 600`; confirmación TMCAM aportada tras autorización explícita del responsable. Vista activa. Calentamiento de 5 segundos; configuración solicitada 1920×1080/30 FPS. El controlador negoció MJPG.

| Medida observada | Resultado |
| --- | --- |
| Estado | completed |
| Duración medida después del calentamiento | 600,046 s |
| Lecturas válidas | 17.547 |
| Resolución en todas las matrices recibidas | 1920×1080 |
| Frecuencia media de entrega | 29,241 FPS |
| Intervalo mediano / p95 / máximo | 32,191 / 51,235 / 96,062 ms |
| p95 de duración de read | 47,161 ms |
| Fallos de lectura, incluido calentamiento | 0 |
| Intervalos mayores de 250 ms | 0 |

El responsable informó vista fluida y sin bandas visibles; no confirmó que el ajuste 60 Hz estuviera aplicado. Es observación humana bajo esa luz, no detección automática ni certificación de antiparpadeo.

Conclusión: 1080p fue recibido durante diez minutos sin fallos reportados, con entrega media cercana a 30 FPS (29,24); no se demuestra 30 FPS constantes ni FPS de reconocimiento. Los contadores de progreso descendieron de aproximadamente 30 a 28–29 lecturas/s hacia la segunda parte; el reporte solo resume intervalos y no permite atribuir la causa a sensor, carga, ventana o driver. No se modificó configuración durante el ensayo ni se adoptó resolución inferior. La prueba no mide latencia óptica ni descarta duplicados del sensor.

Fuente local excluida de Git: `outputs/camera/20261113T215309172677Z.json`. No contiene fotogramas; no se guardaron fotos ni vídeo. Se conservan aquí solo resultados agregados.


## Segundo ensayo y apertura sin dispositivo

Se abrió un segundo intento de hasta 180 s solicitando al operador desconectar. Terminó como completed: 5.402 lecturas 1920×1080, 30,003 FPS medios, cero fallos y cero intervalos mayores de 250 ms. El nombre local `disconnection_20261113.json` refleja el propósito, no acredita la desconexión. La confirmación del operador llegó después de que el ensayo terminara. No hay evidencia de fallo de lectura en caliente.

Tras la confirmación de que la cámara estaba desconectada se ejecutó un tercer intento, índice 1 / DirectShow: open_failed, código de salida 1. No se abrió la cámara integrada ni se cambió automáticamente de índice. Fuente: `outputs/camera/disconnected_open_20261113.json`. Esto acredita manejo de apertura fallida en ese contexto; no equivale a desconexión durante read. Se solicitó reconexión para comprobar nueva apertura independiente.


## Apertura después de reconectar

El responsable confirmó reconexión y escena lista. Se volvió a enumerar DirectShow: USB CAMERA continuó en índice 1. Un nuevo proceso de captura, tras 5 s de calentamiento, completó 30,009 s y 901 lecturas 1920×1080; frecuencia media 30,001 FPS, p95 de intervalo 48,121 ms y máximo 52,143 ms. Cero fallos y cero intervalos mayores de 250 ms. La cámara fue liberada al finalizar. Fuente: `outputs/camera/reconnected_20261113.json`.

Queda comprobada la recuperación mediante nueva apertura después de reconectar, no la reconexión automática (que no existe). Sigue pendiente ensayar desconexión mientras read está activo y confirmar ajuste de 60 Hz. No hay obstáculo observado para continuar el piloto de desarrollo con esta cámara después de resolver consentimiento/custodia, pero no se declara cerrada toda la validación técnica ni aprobado un 30 FPS constante.

### Integridad de evidencia técnica local

Los JSON originales conservan campos manuales pendientes por diseño; las observaciones posteriores del operador se registran en este informe sin alterar los originales. SHA-256 calculados al cierre:

- `20261113T215309172677Z.json`: `21f280682a231750dca0a8beea57c3649b24464040f6300ff645c2a518757b48`.
- `disconnection_20261113.json`: `173ad1528ffaa70802f4a681d6a45eb42f4f7da3e1d99a8b682861566ace6a60`.
- `disconnected_open_20261113.json`: `6627f4afce6bcb969d300136aa0635c6e609ae11f452e0d780c1823e861d9967`.
- `reconnected_20261113.json`: `20f12b4e049205c9ce7c56ee16fcecb939ee45318a5f0973b0fb3a912707959c`.


## Cierre para preparación del piloto — 14-11-2026

Se considera la TMCAM **apta para preparar y, tras aprobación/consentimiento, ejecutar el piloto** con 1920×1080, objetivo 30 FPS, DirectShow y MJPG. Evidencia medida: 29,241 FPS medios en diez minutos sin fallos; no se promete 30 FPS constantes. El promedio de otra ejecución no reemplaza el del ensayo principal. La cámara sigue siendo la única fuente oficial.

Se recalcularon hoy los SHA-256 de los cuatro JSON y coinciden con los registrados arriba. No se sobrescribió ninguno. La observación de vista fluida/sin bandas es la ya aportada por el operador, no una nueva prueba del 14-11.

Pendientes acotados: (1) comprobar en el controlador el ajuste de 60 Hz y observarlo con la iluminación de uso; (2) evaluar desconexión durante captura activa. No bloquean la preparación del piloto, pero no se declaran cerrados.

Procedimiento propuesto para (2), aún no ejecutado: lanzar un único ensayo de 30 s y 5 s de calentamiento en un proceso hijo supervisado por otro proceso, con límite externo de 45 s. Confirmar dispositivo/escena, avisar al operador cuando haya lectura activa y desconectar entonces. Si read falla, registrar fallo y liberación; si la llamada nativa no vuelve, el supervisor termina exclusivamente el proceso hijo y registra timeout/incompleto. Confirmar que terminó antes de reconectar y abrir un intento independiente. No esperar indefinidamente, no matar todos los procesos Python, no cambiar a la integrada y no reintentar automáticamente. Las métricas pueden no guardarse si se fuerza terminación; el supervisor debe registrar ese hecho. No se modificó el diagnóstico para implementar este procedimiento hoy.

Si aparece un comportamiento que impide cerrar el proceso de prueba de forma controlada, detener el ensayo y documentarlo en lugar de insistir. La limitación de una llamada bloqueante no implica por sí sola inestabilidad de Windows. Antes de integración de acceso, garantizar que captura fallida/bloqueada no conserva decisiones antiguas ni habilita apertura; esto no se ha implementado todavía.

# Diagnóstico técnico de la TMCAM 8305

Objetivo: verificar captura antes del dataset. No identifica personas, no extrae biometría y no guarda imágenes ni vídeo. La ventana muestra fotogramas transitorios; el JSON solo contiene configuración, tiempos, dimensiones y estado. El dispositivo de acceso no interviene.

## Instalación

Desde la raíz del proyecto en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/camera_diagnostic.py --help
```

El entorno .venv y los reportes outputs están excluidos de Git. Las dependencias corresponden a bibliotecas, no a pesos o datasets. Las pruebas automáticas usan tiempos y fotogramas ficticios; no abren webcams.

## Identificar la cámara

Cerrar aplicaciones que puedan ocuparla. Apuntar la TMCAM a una escena sin personas. Windows puede mostrar el dispositivo como USB CAMERA; ese nombre no certifica el modelo y el orden PnP no determina el índice OpenCV. Confirmar físicamente cuál es la USB; si existe duda, deshabilitar temporalmente la cámara integrada desde Windows antes de seleccionar índice. El script no enumera ni abre cámaras en busca de una disponible.

Para obtener nombres e índices DirectShow sin probar índices a ciegas, usar la utilidad de enumeración instalada como dependencia de desarrollo:

```powershell
.\.venv\Scripts\python.exe -c "import cv2; from cv2_enumerate_cameras import enumerate_cameras; print([(c.index, c.name) for c in enumerate_cameras(cv2.CAP_DSHOW)])"
```

La [utilidad de enumeración](https://pypi.org/project/cv2-enumerate-cameras/) permite mapear nombre e índice del backend; no confirma por sí sola el modelo comercial. En la sesión del 13-11-2026 devolvió 0=Integrated Camera y 1=USB CAMERA. El responsable confirmó que USB CAMERA es la TMCAM y que la escena estaba lista; los índices pueden cambiar al reconectar.

Elegir explícitamente el índice confirmado (en el ejemplo se usa 1 solo como ejemplo, no como asignación comprobada):

```powershell
.\.venv\Scripts\python.exe scripts/camera_diagnostic.py --camera 1 --duration 10
```

El programa solicita escribir TMCAM antes de abrir. Comprobar que la vista pertenece al dispositivo correcto; Q/Esc cancela. La prueba de 10 segundos identifica configuración; no reemplaza el ensayo continuo. Si es incorrecta, salir, confirmar el índice en Windows y repetir. No etiquetar un reporte como TMCAM solo porque el programa usa ese nombre.

## Ensayo continuo y fallos

Una vez confirmado el índice, ejecutar el mismo comando con `--duration 600` (valor predeterminado). Hay 5 segundos previos de calentamiento. Mantener visible una escena sin personas, iluminación real y algún movimiento no personal para detectar congelamientos. No manipular la conexión durante los diez minutos: el ensayo de desconexión es otro intento.

La configuración se solicita como 1920×1080/30 FPS. Si falla no se adopta silenciosamente una inferior. Puede compararse `--backend msmf` con el predeterminado `dshow`, en ensayos identificados por separado. `--no-preview` mide entrega sin coste de ventana; no mezclarla con medidas con vista. No se solicita FOURCC concreto inicialmente; se registra el negociado. Si 1080p/30 no funciona, estudiar después el formato soportado antes de cambiar objetivos.

Tras la prueba continua, ejecutar otro intento y desconectar físicamente la USB. Registrar cuándo se hizo y si finaliza como read_failed o si el controlador queda bloqueado. Reconectar y ejecutar un tercer intento nuevo, volviendo a confirmar el índice; no hay reapertura automática ni apertura de otro dispositivo. Registrar recuperación real. No marcar reconexión comprobada por haber ejecutado solamente el ensayo continuo.

Configurar 60 Hz en el controlador si lo permite; este script no impone un ID de propiedad no portable. Registrar dónde se aplicó, soporte observado y presencia de bandas/parpadeo a la luz usada. El campo manual_pending_verification del JSON es deliberado: se completa en el informe de observación, no se deduce de FPS ni de un set aceptado.

## Interpretación

- delivery_fps = (N−1)/(t_última−t_primera), con tiempos de finalización de read tras calentamiento. Es frecuencia de entrega al programa, no FPS de reconocimiento ni prueba de que cada imagen sea nueva en el sensor.
- observed_dimensions procede de las matrices recibidas; driver_reported procede del controlador y puede diferir.
- Mediana, p95 (rango más cercano) y máximo de intervalos describen irregularidad. gaps_over_threshold cuenta intervalos mayores de 250 ms por defecto: es una alerta técnica inicial, no frames perdidos contabilizados.
- read_ms_p95 incluye espera y decodificación de read; no equivale a latencia óptica extremo a extremo.
- completed significa que terminó el período solicitado, no que aprobó 1080p/30 ni que no hubo imágenes duplicadas. Interrupciones/fallos no acreditan estabilidad.

Revisar duración real, dimensiones constantes, frecuencia sostenida cercana al objetivo, pausas, errores, calentamiento, luz, backend y formato. No hay aprobación automática ni umbral docente inventado. Si no cumple el objetivo, conservar las cifras y decidir una configuración alternativa antes de capturar.

Limitación: algunos controladores pueden bloquear open/read; el temporizador no puede interrumpir una llamada nativa bloqueada. Si deja de responder, finalizar el proceso desde el Administrador de tareas y registrar ensayo incompleto, nunca aprobado. Q y Ctrl+C requieren que el controlador devuelva el control. El informe JSON se escribe al finalizar; una terminación forzada puede impedirlo.

## Evidencia

Los JSON se crean en outputs/camera con nombres temporales UTC, sin sobrescribir archivos existentes. No contienen imágenes. Registrar en un informe agregado fecha local, cámara confirmada por operador, Python/OpenCV, backend, alimentación/conexión USB, iluminación, observación de parpadeo, estado de 60 Hz y desconexión/reconexión. No compartir vistas que incluyan personas.

Estado de implementación y comprobaciones: [03_camera_diagnostic.md](reports/03_camera_diagnostic.md).

Referencia: [VideoCapture oficial de OpenCV](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html). Los valores solicitados, los reportados por el controlador y los observados son evidencias diferentes.

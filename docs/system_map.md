# Mapa del sistema final

Este documento indica qué archivos forman el sistema que se entrega y cuáles son historial de experimentos. Para defender el proyecto basta con dominar las 12 piezas de la tabla siguiente.

## Recorrido de un fotograma

```
Celular (IP Webcam) ──MJPEG──► Windows
  1. YuNet localiza cada rostro                      hog_knn.detect_faces
  2. CNN propia: gris 64×64 → vector de 128          hog_knn.describe_face_cnn
     SFace (apoyo): rostro alineado → vector de 128  hog_knn.describe_sface
     Fusión: [√0,75·CNN, √0,25·SFace]                hog_knn.fuse_vectors
  3. k-NN (k = 3) + rechazo: d₁ ≤ T y d₂ − d₁ ≥ G    open_set_knn.open_set_row
  4. Permiso de la identidad → Autorizado/Denegado   access.decide / decide_scene
  5. 8 fotogramas autorizados seguidos → orden       presentation_gate
  6. CHECK <evento> K0x GRANTED por USB serie        latch_serial.send_decision
ESP32: abre a 0°, cierra a 100° si pasan 3 s sin orden   firmware/latch/latch.ino
```

## Las 12 piezas del sistema final

| # | Archivo | Qué hace | Cómo explicarlo |
| --- | --- | --- | --- |
| 1 | `scripts/prepare_hyperface.py` | Lee HyperFace, recorta con YuNet y guarda 1 068 878 rostros grises de 64×64 | Preparación de los datos de entrenamiento |
| 2 | `scripts/train_face_cnn.py` | Clase `FaceNet` (4 bloques convolucionales → vector de 128) y pérdida CosFace | **Nuestra red, entrenada desde cero** |
| 3 | `scripts/export_face_cnn.py` | Exporta la red entrenada a ONNX para usarla con OpenCV | Paso técnico: de PyTorch a la aplicación |
| 4 | `scripts/hog_knn.py` | Detección (`detect_faces`), atributos (`describe_face_cnn`, `describe_sface`), fusión (`fuse_vectors`), regla de aceptación (`accepts_open_set`) | Convierte una cara en números |
| 5 | `scripts/open_set_knn.py` | `open_set_row`: vecino ganador, distancia d₁ y holgura d₂ − d₁; `pick_operating_point`: búsqueda de T y G | **Clasificador k-NN con rechazo de desconocidos** |
| 6 | `scripts/recalibrate_real_unknowns.py` | Construye la galería (videos 04 + 06), calibra T y G con LFW y desconocidos reales, y publica el modelo final | De dónde salen T = 1,011 y G = 0,114 |
| 7 | `scripts/access.py` | `decide` y `decide_scene`: rostro + identidad + permiso → GRANTED o DENIED con su motivo | Regla de autorización; ante cualquier duda, DENIED |
| 8 | `scripts/live_k01.py` | `recognize_frame`: aplica los pasos 1–4 a cada rostro del fotograma | Une las piezas 4, 5 y 7 |
| 9 | `scripts/presentation_gate.py` | Exige 8 fotogramas autorizados seguidos y renueva la orden cada 0,5 s | Evita abrir por un parpadeo del modelo |
| 10 | `scripts/latch_serial.py` | Formato del mensaje serie y lectura del acuse del ESP32 | Comunicación con el nodo IoT |
| 11 | `firmware/latch/latch.ino` | Recibe `CHECK`, mueve el SG90 en GPIO25 y cierra solo tras 3 s | El nodo de actuación |
| 12 | `scripts/operator_ui.py` | Interfaz Tkinter: video, recuadros, decisión, permisos, historial y pestaña Servo | Lo que ve el operador |

Pieza auxiliar: `scripts/identity_artifacts.py` comprueba con huellas SHA-256 que la galería, los umbrales y la red correspondan entre sí. Si algo no coincide, el sistema deniega todo.

## Humano / no humano (PROF-05)

- `scripts/human_cnn.py` entrena en Keras la CNN binaria humano/no humano con LFW y CIFAR-10. Obtuvo 0,99960 de exactitud en validación.
- En vivo, quien decide si hay una persona es YuNet: sin rostro detectado no hay reconocimiento y la escena queda **Denegado · sin rostro**.
- La CNN binaria se ejecuta como diagnóstico y su marca aparece en el detalle técnico.
- Ninguna de las dos distingue a una persona real de su foto.

## Scripts que generan las tablas del informe

| Script | Tabla del informe |
| --- | --- |
| `scripts/compare_aligned_phone.py` | HOG frente a la CNN propia |
| `scripts/compare_cnn_classifiers.py` | SVM, Random Forest, k-NN y MLP sobre la CNN |
| `scripts/compare_fusion.py` | Ablación del peso de SFace |
| `scripts/recalibrate_real_unknowns.py` | Recalibración con desconocidos reales |

## El resto

Los demás scripts de `scripts/` son historial de fases anteriores: HOG, alineación, SFace solo, calibraciones previas, bancos serie, captura y manifiestos. Respaldan decisiones registradas en `docs/decisions.md` y los informes de `docs/reports/`, pero **no hace falta explicarlos** para defender el sistema final. Algunos siguen importándose desde la aplicación por funciones auxiliares; separarlos queda como limpieza posterior a la entrega.

## Cómo ejecutar

```
.\FaceNexus.cmd                           # simulación: reconoce pero no mueve el pestillo
.\FaceNexus.cmd --port COM5 --actuate     # demostración real con el ESP32
```

`FaceNexus.cmd` equivale a `.venv\Scripts\python.exe -m scripts.operator_ui --vault V:\FaceNexus`, y antes de arrancar comprueba que exista `.venv` y que el volumen `V:` esté montado.

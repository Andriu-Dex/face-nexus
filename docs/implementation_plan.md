# Plan de implementación

## Entrenamiento externo a escala

Para CONF-05, entrenar una CNN de reconocimiento facial con pesos inicializados desde cero e identidades externas etiquetadas. Usar YuNet para el recorte y SFace como referencia. Integrar el extractor entrenado con los cuatro participantes y comparar su rendimiento en sesiones reservadas. Reservar datos externos y voluntarios para medir el rechazo, comprobando su separación respecto a los datos usados para entrenar y calibrar.

El objetivo operativo es usar al menos dos millones de imágenes externas únicas en TRAIN. La fuente principal propuesta es HyperFace-50k-StyleGAN, con 3,2 millones de imágenes sintéticas de 50 000 identidades antes de dividir y filtrar. El archivo oficial ocupa 87,3 GB y su documentación incluye la licencia CC BY-SA 4.0. DigiFace-1M queda disponible para comparar el efecto de la fuente de entrenamiento. Registrar por fuente las imágenes utilizadas y guardar los pesos y resultados de cada ejecución. [HyperFace en Idiap](https://www.idiap.ch/en/dataset/hyperface) · [Archivos y documentación en Zenodo](https://zenodo.org/records/15087238) · [DigiFace-1M](https://github.com/microsoft/DigiFace1M)

Primero medir el costo de un paso completo de entrenamiento en la RTX 5090 con `scripts/benchmark_face_training.py`. El script informa imágenes por segundo y memoria de GPU con lotes simulados residentes en el dispositivo. Después medir lectura del SSD, decodificación, recorte y carga de lotes con imágenes del dataset. La estimación de tiempo para la corrida completa sale de esta segunda medición.

La verificación local del script en la RTX 4060 Laptop registró 12 549 imágenes/s y 174 MiB de memoria pico asignada por PyTorch, con lote 64, 50 000 clases y 60 pasos medidos. El resultado corresponde al cálculo de una CNN inicial con lotes simulados residentes en GPU. La RTX 5090 y el rendimiento con archivos en SSD se miden por separado.

La comprobación del origen leyó los primeros 12 MiB del archivo publicado. OpenCV decodificó 463 imágenes de ocho carpetas de identidad, todas de 112 × 112 y con huellas SHA-256 distintas dentro de la muestra. Al descargar el archivo completo, verificar el MD5 publicado (`5b2e291986a453e8270e69738f85cf38`) antes de preparar el corpus. Medir la preparación en disco con una muestra y reservar espacio para el archivo, los datos preparados y los checkpoints. Mantener las fotos de los participantes en el almacenamiento privado y fuera de la corrida con datos externos.

Separar las identidades sintéticas que se usen para validar la representación. Durante el entrenamiento, la capa final predice las identidades externas de TRAIN. Para validar sobre identidades reservadas, usar el vector anterior a esa capa y comparar pares de la misma identidad y de identidades diferentes. En FaceNexus, inscribir a los cuatro integrantes con sus sesiones de entrenamiento y congelar el modelo y los umbrales antes de medir las sesiones de prueba y los desconocidos reservados.

En Windows con Python 3.14 y un controlador compatible, ejecutar desde la raíz del repositorio. El entorno de la prueba queda fuera del repositorio. [Instalación oficial de PyTorch](https://docs.pytorch.org/get-started/)

```powershell
$bench = Join-Path $env:LOCALAPPDATA 'FaceNexus\training-venv'
python -m venv $bench
$benchPython = Join-Path $bench 'Scripts\python.exe'
& $benchPython -m pip install torch==2.11.0+cu128 --index-url https://download.pytorch.org/whl/cu128
& $benchPython scripts/benchmark_face_training.py
```

Configuración de entrega confirmada: celular como fuente de video, Windows para procesar, ESP-WROOM-32 por USB serie y SG90 para el pestillo. El volumen cifrado y la TMCAM de desarrollo se verificaron. Están auditados S01 y R01 y el código de comparación de referencia se probó con datos sintéticos.

Cada fase requiere plan breve de archivos, trabajo acotado, comprobaciones disponibles, inspección de resultados y registro de evidencia antes de preparar un commit. No publicar ramas ni cambios remotos sin autorización. Priorizar claridad y defensa del código (CONF-02).

| Fase | Trabajo previsto | Condición de salida |
| --- | --- | --- |
| 1. Preparación y auditoría del dataset | Investigación de fuentes, consentimiento, captura piloto, manifiesto y particiones; protocolo en data_protocol.md | Datos propios autorizados, grupos de desconocidos disjuntos y auditoría ejecutada sin fugas pendientes |
| 2. Detección y procesamiento facial | Detector, recortes, alineación y calidad; comprobar piloto antes de captura definitiva | Configuración explicada, archivos/rostros utilizables y fallos registrados |
| 3. Extracción y comparación de características | Representación propia, preentrenada y combinación bajo experimento acotado; entrenamiento preliminar con referencia fija | Comparación en VALIDATION, versiones/dimensiones y procedencia verificadas |
| 4. Entrenamiento y evaluación de clasificadores | Comparar k-NN, MLP y SVM lineal multiclase con HOG y entradas comunes. Entrenar una CNN binaria pequeña para humano/no humano | Configuraciones elegidas con TRAIN/VALIDATION y evidencia separada para ambas tareas |
| 5. Reconocimiento en tiempo real y rechazo | Calibración con R01 y desconocidos del grupo A grabados con el celular, regla temporal y cámara | Modelo, preparación y rechazo congelados antes del ensayo final en vivo con el grupo B |
| 6. Sistema de autorización | Integrar identidad, permisos e interfaz con controlador simulado | Revocación sin reentrenar, denegaciones y estados de ejecución comprobados |
| 7. Integración y pruebas con dispositivo físico | Adaptador y pruebas de apertura, denegación, repetición, desconexión y reconexión; cierre de informe | Orden transmitida y acción efectiva comprobada; limitaciones y todos los resultados reales documentados |

La fase 1 empieza con protocolo y piloto; se coordina con fase 2 antes de capturar el dataset definitivo. No requiere agotar toda la adquisición antes de comprobar el detector. La comparación de características de fase 3 permite entrenamiento preliminar sin consumir TEST; la selección completa corresponde a fase 4.

La lógica sencilla de permisos y el contrato de controlador se definen y prueban desde el inicio con datos simulados, aunque su integración completa sea fase 6. Los casos de acceso físico se ensayan en fase 7 con intentos reservados; no sustituyen la evaluación del reconocimiento ni justifican retocar un TEST ya consumido. Si se necesitan cambios tras TEST, declarar la evaluación de desarrollo y obtener nuevas sesiones para una evaluación final independiente.

El contrato serie se puede implementar desde el inicio con un controlador simulado. El montaje con el SG90 se realiza en la fase 7. CONF-01 exige reconocer a los cuatro integrantes, verificar sus permisos, transmitir una orden válida y observar el movimiento del pestillo.

## Registro de evidencias

Anotar fecha, requisito, versión/configuración, comando o procedimiento, resultado observado, ubicación privada o pública del reporte y limitaciones. No convertir resultados esperados en observados. Las pruebas de lógica usan datos sintéticos y dobles de cámara/controlador; las de dispositivos se separan y las no ejecutadas quedan pendientes. Si se adopta Python, utilizar pytest y análisis estático proporcionales al cambio.

## Siguiente paso concreto

### Prioridades para la demostración

1. Implementar el contrato de salida con un controlador simulado, preparar la lectura del stream y verificar la comunicación serie sin carga. Probar en banco el recorrido celular → Windows → ESP-WROOM-32 → SG90.
2. Construir HOG + k-NN primero, después MLP y SVM lineal multiclase con la misma entrada. Entrenar aparte la CNN binaria pequeña con positivos y negativos adecuados a esa tarea. Usar YuNet para localización y recorte. Conservar SFace y el código anterior como referencias internas.
3. Usar S01 para ajustar y R01 para la validación exploratoria entre encuentros. El responsable confirmó que son dos días distintos, con grabaciones individuales en cada jornada. Fijar las asignaciones en el manifiesto del experimento antes de entrenar. Un ensayo en vivo con el modelo congelado aporta evidencia adicional sin requerir otro lote de fotografías almacenadas.
4. Ensayar una persona autorizada, varias autorizadas, una autorizada con desconocidos, solo desconocidos y la salida de la última persona autorizada. Presentar el modelo elegido y documentar en el informe la exactitud de los candidatos y la interfaz.

### Cierre del informe LaTeX

Usar la plantilla local de `docs/informe_facenexus/`. Completar el informe con la arquitectura implementada, las muestras y particiones efectivamente usadas, la exactitud y matriz de confusión de cada candidato, la elección del modelo, la interfaz y el ensayo en vivo. Registrar aciertos, rechazos correctos, aceptaciones indebidas y acciones físicas observadas. Cerrar y compilar el informe tras ejecutar las pruebas. Las tablas del informe deben llevar resultados observados y los denominadores de cada métrica.

### Preparación técnica ya realizada

La [referencia HOG + k-NN](reports/10_hog_knn_baseline.md) alcanzó 52 aciertos en 72 fotogramas usables de R01. MLP y SVM lineal lograron 57 de 72 cada uno con los mismos vectores. La SVM pasa primero a calibración por su mayor recall mínimo por persona y su menor latencia frente a MLP. La selección final requiere medir rechazo y aceptaciones indebidas. [Comparación de clasificadores](reports/11_hog_classifier_comparison.md)

El [piloto de calibración del rechazo](reports/12_hog_rejection_calibration.md) midió el solapamiento de márgenes en R01. Hay un lote TRAIN de K01 en el celular (`k01_phone_v3`, 20/20). El reentrenamiento de cuatro clases espera K02–K04 en el mismo montaje. La [CNN humano/no humano](reports/15_human_cnn.md) ya se entrenó con LFW y CIFAR-10. El [clasificador de identidad K01](reports/16_identity_k01.md) usa S01, el celular y LFW como OTHER; no declara las cuatro identidades. La [comparación k-NN / MLP / SVM](reports/17_identity_k01_comparison.md) elige k-NN y la [demo en vivo](reports/18_live_knn.md) ya lo usa. La CNN se [ajustó al celular](reports/19_human_cnn_phone.md). El [híbrido landmarks+HOG](reports/20_hybrid_landmarks_hog.md) no mejora el k-NN; la demo sigue en HOG. El [filtro de calidad](reports/21_frame_quality.md) se midió en esas fotos: Laplaciano 85 descartaría 8/20 del celular y no se usa. El [vivo](reports/22_live_scene_knn.md) decide por cara. La [galería de cuatro](reports/23_four_identities_downloads.md) usa Downloads (31/39 en VALIDATION; K02 débil). Galería y T van ligados por SHA-256. Archivos no accionan el pestillo. Los [extraños LFW](reports/24_unregistered_and_human.md) no se rechazan con T=0,770 (6004/6537). El [rechazo abierto](reports/25_open_set_rejection.md) baja eso a 60/6537 con T=0,530 y holgura 0,057. En [VALIDATION de cuatro](reports/26_four_validation_open_set.md) esos candidatos dan 13/39 (K02 0/9). El [ensayo K01–K04+OTHER](reports/27_four_other.md) elige k-NN (19/39, 2/2627 LFW) y no sustituye el vivo. El [manifiesto del celular](reports/28_phone_manifest_and_cnn_veto.md) prepara `tune`/`eval`; la CNN no veta el vivo (0/20 caras, 1/60 fondos colados). La [recuperación de lotes](reports/30_lot_recovery_and_provenance.md) no borra carpetas históricas y exige encuentro explícito y filas con huella. El [candado del índice](reports/31_lock_recovery_binding.md) cubre lectura y escritura; un pendiente corrupto se conserva. La [reserva de lote](reports/32_lot_key_and_calibration_rows.md) no pisa un pendiente ajeno; la calibración verificada sale de las filas del NPZ. La [calibración del ensayo](reports/33_calibration_trial_binding.md) exige la huella registrada en `summary.json` y vectores HOG. El [ajuste con tune del celular](reports/34_phone_tune_training.md) no mete eval en el entrenamiento. La [interfaz de operador](reports/35_operator_ui_redesign.md) agranda el visor y arranca con `FaceNexus.cmd` en simulación; un fallo de cámara no conserva Autorizado. El [rechazo visible](reports/36_operator_rejection_path.md) enseña d, T y G sin bajar umbrales. El [pipeline de vivo](reports/37_live_pipeline_decouple.md) pinta el último fotograma sin esperar cada predicción. El [recuadro](reports/38_overlay_decouple.md) vive en el Canvas con vigencia breve. El [guion del lunes](monday_trial.md) y el [informe 39](reports/39_monday_defense.md) fijan capturas sin lentes, caducidad de Autorizado y el banco del servo. La CNN independiente acertó 5 recortes del celular y 500 CIFAR; no veta YuNet. Falta capturar K02–K04 en el celular, grabar `firmware/latch` en banco y observar el SG90.

Completar la [evaluación de impacto](biometric_impact_assessment.md) para el único flujo de acceso por reconocimiento facial y verificar localmente el alcance del consentimiento verbal grabado antes de la adquisición. Confirmar los datos de contacto del responsable. Los [formularios](consent_templates.md) quedan disponibles como apoyo opcional.

La revisión local y el primer pipeline de las 80 candidatas se ejecutaron; ver [informe 07](reports/07_face_pipeline_validation.md): 73 embeddings válidos y siete sin detección, con fallos preservados y similitudes exploratorias solapadas. Se autorizaron únicamente los pesos concretos de YuNet y SFace y permanecen privados/verificados.

El volumen VeraCrypt superó el remontaje y la comprobación del SHA-256 de prueba. La TMCAM superó el diagnóstico operativo de R01. El [lote R01 preparado inicialmente para TRAIN](reports/09_classifier_preparation.md#primer-lote-de-train) produjo 72 embeddings válidos. El registro original se conserva y su uso como validación exploratoria quedará en el manifiesto del experimento.

El manifiesto privado de HOG registra 80 tomas de S01 para TRAIN y 80 de R01 para VALIDATION, con hashes verificados y sin imágenes idénticas entre los lotes. En el banco serie, el ESP32 respondió como se esperaba a 11 tramas en cada una de dos rondas por COM5, con el SG90 desconectado. [Resultado del ensayo de banco](hardware_protocol.md#ensayo-de-banco-del-protocolo-facenexus)

Se comprobó el recorrido celular → Windows → ESP32 en dos rondas con una escena sin personas. Windows procesó cinco fotogramas de 1920 × 1080 por ronda y el ESP32 confirmó ambas denegaciones de banco. [Prueba con el celular](hardware_protocol.md#video-local-y-decisión-de-banco)

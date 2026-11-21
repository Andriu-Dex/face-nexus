# Informes de FaceNexus

Estado al 21-11-2026. Los informes conservan las observaciones y decisiones de cada etapa. Para el estado vigente, consultar las actualizaciones enlazadas desde los informes históricos.

| Informe | Evidencia |
| --- | --- |
| [01 · Revisión previa](01_preimplementation_review.md) | Alcance, requisitos y material académico. |
| [02 · Fuentes de datos](02_dataset_research.md) | Revisión de datasets públicos y extractores. |
| [03 · Diagnóstico de la TMCAM](03_camera_diagnostic.md) | Captura continua, desconexión y reconexión. |
| [04 · Preparación del piloto](04_pilot_preparation.md) | Condiciones de captura y criterios iniciales. |
| [05 · Herramienta del piloto](05_pilot_capture.md) | Captura guiada y auditoría sintética. |
| [06 · Fotogramas externos](06_external_frames.md) | Inventario, procedencia y organización. |
| [07 · Procesamiento facial](07_face_pipeline_validation.md) | YuNet, alineación y SFace en 80 imágenes. |
| [08 · Adquisición y custodia](08_dataset_acquisition.md) | Sesiones, diagnóstico operativo y verificación de VeraCrypt. |
| [09 · Preparación de clasificadores](09_classifier_preparation.md) | Comparación sintética y extracción de la segunda jornada. |
| [10 · Referencia HOG + k-NN](10_hog_knn_baseline.md) | S01 para entrenamiento y R01 para validación. |
| [11 · Comparación HOG](11_hog_classifier_comparison.md) | k-NN, MLP y SVM con entradas comunes y repetición del ensayo. |
| [12 · Piloto de rechazo](12_hog_rejection_calibration.md) | Márgenes en R01 y seis presentaciones usables con el celular. |
| [13 · Integración de banco](13_esp32_phone_integration.md) | Respaldo y carga del ESP32, pruebas por COM5 y video real del celular. |

La calibración en vivo reúne tres presentaciones usables de un voluntario y tres del primer integrante. Faltan las presentaciones de los otros tres integrantes para estimar el umbral. El enlace con el ESP32 está comprobado en banco. El accionamiento del SG90 y el ensayo final de reconocimiento siguen pendientes.

# Informes de FaceNexus

Estado al 22-11-2026. Los informes conservan las observaciones y decisiones de cada etapa. Para el estado vigente, consultar las actualizaciones enlazadas desde los informes históricos.

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
| [12 · Piloto de rechazo](12_hog_rejection_calibration.md) | Márgenes en R01, seis presentaciones usables y diagnóstico por fotograma en el celular. |
| [13 · Integración de banco](13_esp32_phone_integration.md) | Respaldo y carga del ESP32, pruebas por COM5 y video real del celular. |
| [14 · Dominio celular y acceso](14_phone_domain_and_access.md) | HOG de K01 en el celular frente a S01 y contrato de autorización simulada. |
| [15 · CNN humano / no humano](15_human_cnn.md) | Entrenamiento propio con LFW y CIFAR-10; no identifica a los cuatro. |
| [16 · Identidad K01](16_identity_k01.md) | SVM Keras K01 frente a LFW; no finge K02–K04. |
| [17 · Comparación K01 / OTHER](17_identity_k01_comparison.md) | k-NN, MLP y SVM con el mismo HOG; gana k-NN. |
| [18 · Demo k-NN](18_live_knn.md) | El vivo usa el ganador de la comparación; SVM opcional. |
| [19 · CNN en el celular](19_human_cnn_phone.md) | Ajuste fino con caras YuNet y fondo del cuarto. |
| [20 · Híbrido landmarks + HOG](20_hybrid_landmarks_hog.md) | PROF-04: puntos YuNet más HOG completo; la demo no cambia. |
| [21 · Calidad del recorte](21_frame_quality.md) | Laplaciano y exposición medidos; no se copia el umbral 85. |
| [22 · Escena y umbral k-NN](22_live_scene_knn.md) | Varios rostros; T=0,456; un K01 basta para autorizar. |
| [23 · Cuatro identidades](23_four_identities_downloads.md) | Downloads TRAIN/VAL distintos; 31/39; interfaz y firmware del pestillo. |
| [24 · Extraños y humano/no humano](24_unregistered_and_human.md) | LFW OTHER 6004/6537 aceptados con T=0,770; CNN 5+500; sin pestillo. |
| [25 · Rechazo abierto](25_open_set_rejection.md) | T=0,530 y holgura 0,057: 60/6537 extraños; LOO TRAIN 78/120. |

La calibración en vivo reúne tres presentaciones usables de un voluntario y tres del primer integrante. El software ya puede sondear el giro del celular e inspeccionar intentos incompletos. Hay galería de cuatro IDs con fotos de Downloads (VALIDATION 31/39; K02 se confunde con K03). El vivo autoriza a cualquier integrante con permiso en pantalla, no el pestillo. Extraños LFW no se rechazan con el T actual. El 22-11-2026 el ESP32 volvió a aparecer en COM5 y respondió `PONG FACENEXUS BENCH 1`; el firmware `latch` no se grabó y el SG90 no se observó. El celular del lunes sigue siendo el dominio de la defensa.

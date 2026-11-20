# Preparación de la comparación de clasificadores

El flujo local en CPU compara SVM con núcleo RBF, Random Forest de 100 árboles, k-NN de tres vecinos y una MLP de una capa oculta con 32 unidades. Son configuraciones iniciales fijas, con semilla 17 para los estimadores que la requieren. Las cuatro reciben los mismos vectores SFace de 128 componentes normalizados por norma L2. La normalización de cada fila depende solo de esa fila.

La comparación tiene dos condiciones: TRAIN nuevo y el mismo TRAIN más S01. Ambas usan exactamente la misma VALIDATION. El informe registra exactitud, macro-F1, precisión y recall por persona, matriz de confusión, avisos y tiempos de ajuste y predicción. Las matrices tienen identidades reales en filas e identidades predichas en columnas. La predicción se mide por lote. Los fallos de extracción aparecen separados de las métricas condicionadas a un vector válido. La calibración del rechazo, la selección final y TEST corresponden a pasos posteriores.

## Ejecución sintética

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe -m scripts.compare_classifiers --synthetic --output 'classifiers/synthetic-baseline.json'
```

El ensayo genera 48 muestras por lote simulado. Compara 48 frente a 96 muestras en TRAIN con las mismas 48 de VALIDATION. El JSON se escribe en `outputs/`, excluido de Git. Las métricas sintéticas verifican el flujo y sus denominadores. La precisión facial y la latencia real quedan por medir con las nuevas sesiones.

Se completaron los ocho ajustes sin avisos. Cada ajuste tardó menos de 0,4 s en la laptop actual para este lote sintético. La suite completa pasó 51 pruebas y `pip check` confirmó las dependencias. La extracción con un fotograma sintético de 1080p y los pesos verificados registró `no_face` con su procedencia y rechazó una partición incorrecta.

## Preparación de las nuevas grabaciones

Para cada integrante, conservar el vídeo original de la TMCAM y exportar un conjunto de tomas variadas a su carpeta de sesión en VeraCrypt. Dar de alta las sesiones y sus particiones en el plan privado antes de generar vectores. El manifiesto privado de cada partición contiene una lista de tomas con rutas relativas al volumen. Ejemplo de una entrada:

```json
[
  {
    "session_id": "K01_S02",
    "video": "recordings/K01/S02/source.mp4",
    "image": "recordings/K01/S02/frames/frame_000120.png",
    "frame_index": 120
  }
]
```

Usar el índice que corresponda al vídeo original y registrar la convención de numeración y la configuración de exportación en la ficha privada de sesión. La extracción verifica la asignación, las dimensiones 1920×1080 y los hashes. También conserva los estados de ausencia de rostro y demás fallos. Cada salida contiene `embeddings.npz` y `records.json`. El comparador revisa el plan, los registros de extracción y si se comparten sesiones, archivos fuente, imágenes o vectores idénticos entre TRAIN y VALIDATION.

```powershell
.\.venv\Scripts\python.exe -m scripts.extract_session_features --vault 'V:\FaceNexus' --manifest 'manifests/train.json' --split TRAIN --output 'features/train'
.\.venv\Scripts\python.exe -m scripts.extract_session_features --vault 'V:\FaceNexus' --manifest 'manifests/validation.json' --split VALIDATION --output 'features/validation'
.\.venv\Scripts\python.exe -m scripts.compare_classifiers --vault 'V:\FaceNexus' --train 'features/train/embeddings.npz' --validation 'features/validation/embeddings.npz' --historical 'features/s01/embeddings.npz' --output 'results/comparison.json'
```

La ruta de S01 es un ejemplo para el archivo histórico una vez disponible dentro del volumen cifrado. Su uso para entrenar requiere verificar en privado el alcance del consentimiento. Conservar vídeos y resultados en el volumen y usar las sesiones de TEST solo para la evaluación final.

## Primer lote de TRAIN

El 19-11-2026 se copiaron al volumen cifrado los cuatro MP4 de R01 y 20 fotogramas espaciados por integrante, con SHA-256 verificado contra los archivos entregados. Tres vídeos son de 1920×1080 y uno es de 848×478. El responsable aprobó usar este último para TRAIN exploratorio a su resolución nativa. La opción `--allow-848x478` se aplicó únicamente a ese lote de TRAIN. VALIDATION conserva el requisito de 1920×1080.

Hubo 72 embeddings válidos de 80 tomas. Se conservaron los ocho casos sin detección en el registro privado. El lote queda disponible para compararlo con y sin S01 cuando lleguen las sesiones de VALIDATION. La resolución y la identidad siguen asociadas en R01 y deben considerarse al interpretar los resultados por persona.

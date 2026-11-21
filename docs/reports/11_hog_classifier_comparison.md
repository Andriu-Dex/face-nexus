# Comparación de k-NN, MLP y SVM lineal con HOG

Ensayo exploratorio del 20-11-2026. Se reutilizaron los mismos 73 vectores de TRAIN (S01) y 72 de VALIDATION (R01) del [ensayo de referencia](10_hog_knn_baseline.md). Ambos lotes proceden de 80 fotogramas de origen por jornada. Se comprobó la correspondencia de los vectores con el manifiesto congelado y se registraron las huellas de ambos archivos de entrada.

## Modelos y ajuste

- **k-NN** conserva los vectores de ajuste, mide la distancia euclidiana con NumPy y vota entre tres vecinos. Un empate deja la muestra sin candidato.
- **MLP** usa 32 unidades ReLU y cuatro puntuaciones lineales de salida en Keras. Aprende con entropía cruzada sobre esas puntuaciones.
- **SVM lineal multiclase** calcula cuatro puntuaciones lineales en Keras. La pérdida `max(0, 1 + puntuación_rival - puntuación_correcta)` penaliza que la puntuación correcta supere en menos de un punto a la mayor puntuación rival.

MLP y SVM usaron Adam a 0,01, regularización L2 de 0,001 en los pesos, 150 épocas, lotes de 16 y semilla 17. Se fijó una configuración por modelo y se entrenó solo con S01. Keras 3.15.1 ejecutó el ajuste con JAX 0.12.1 en la CPU del Intel Core i7-13700H. Se comprobó que los dos modelos guardados conservaban sus puntuaciones al recargarlos y que una repetición produjo las mismas predicciones en ambos lotes.

## Resultados

| Modelo | Ajuste S01, usables | R01, usables | R01, todos | Macro-F1 de R01 | Inferencia p50 / p95 de R01 |
| --- | ---: | ---: | ---: | ---: | ---: |
| k-NN | 68/73 (93,15 %) | 52/72 (72,22 %) | 52/80 (65,00 %) | 0,745 | 0,08 / 0,09 ms |
| MLP | 73/73 (100 %) | 57/72 (79,17 %) | 57/80 (71,25 %) | 0,794 | 0,67 / 0,82 ms |
| SVM lineal | 73/73 (100 %) | 57/72 (79,17 %) | 57/80 (71,25 %) | 0,792 | 0,34 / 0,43 ms |

R01 incluyó ocho fotogramas sin descriptor usable. Entre los usables, k-NN produjo 16 confusiones y cuatro empates. MLP y SVM produjeron 15 confusiones cada uno, con cero empates. Las mediciones de inferencia corresponden al clasificador con el vector HOG ya calculado, tras tres llamadas de calentamiento por lote. El ajuste de MLP tomó 642 ms y el de SVM 398 ms en la repetición. Las medidas de ajuste incluyen la primera compilación del entrenamiento.

| Identidad real | Aciertos k-NN | Aciertos MLP | Aciertos SVM | Fotogramas usables |
| --- | ---: | ---: | ---: | ---: |
| K01 | 12 | 10 | 15 | 19 |
| K02 | 13 | 17 | 14 | 19 |
| K03 | 13 | 15 | 15 | 15 |
| K04 | 14 | 15 | 13 | 19 |

La SVM pasa primero al ensayo de rechazo por su mayor recall mínimo entre las cuatro personas (13/19 frente a 10/19 en MLP) y menor latencia que MLP en esta prueba. MLP sigue como candidato. La selección se revisará según los rechazos y las aceptaciones indebidas en intentos separados. R01 solo mide identificación cerrada de conocidos entre jornadas. Los parámetros de rechazo no se calibraron en esta comparación.

Los archivos `.keras`, predicciones por muestra, pérdidas y matrices de confusión completas quedan bajo VeraCrypt. Estos comandos reproducen el ensayo y guardan otra ejecución.

```powershell
python -m pip install -r requirements-keras.txt
python -m scripts.compare_hog_models --vault V:\FaceNexus --run-name hog_comparison_new
```

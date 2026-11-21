# Referencia HOG + k-NN entre dos jornadas

Ensayo del 20-11-2026 en Windows, CPU Intel Core i7-13700H, OpenCV 4.14.0 con un hilo, NumPy 2.5.4 y scikit-learn 1.9.1 para las métricas.

## Método

Se verificaron las huellas de los 160 fotogramas del manifiesto privado y la ausencia de copias exactas entre lotes. S01 aportó 80 fotogramas de entrenamiento. R01 aportó 80 fotogramas de validación del segundo día, identificados internamente como `K##_S02`. Cada lote de origen aportó 20 imágenes por persona.

YuNet localizó el rostro. Para ser usable, cada imagen debía producir una sola detección y un recorte con un descriptor de norma positiva. HOG se calculó sobre el recorte en gris de 64 × 64 con ecualización de histograma. Se usaron celdas de 8 × 8, bloques de 16 × 16 con paso 8 × 8 y nueve intervalos de orientación. Cada vector de 1764 componentes se dividió por su propia norma L2.

k-NN guardó los vectores de S01. Para cada muestra calculó distancias euclidianas, ordenó los vecinos y votó entre los tres más cercanos. Si hubo empate, la muestra contó como error de identificación sin candidato. Se fijó `k = 3` como referencia y no se calibró el umbral de rechazo en este ensayo.

## Resultados

| Lote | Fotogramas usables | Identificación sobre usables | Identificación sobre todos | Macro-F1 sobre usables |
| --- | ---: | ---: | ---: | ---: |
| S01, ajuste | 73/80 | 68/73 (93,15 %) | 68/80 (85,00 %) | 0,944 |
| R01, validación | 72/80 | 52/72 (72,22 %) | 52/80 (65,00 %) | 0,745 |

La medición de S01 incluye los mismos vectores que el modelo guarda. En R01 hubo 52 aciertos, 16 identificaciones incorrectas, cuatro empates y ocho imágenes sin un descriptor usable.

Matriz de R01. Las filas indican la identidad real y las columnas la predicción. Las últimas dos columnas registran los resultados fuera de la matriz de cuatro clases.

| Real | K01 | K02 | K03 | K04 | Empate | Sin descriptor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K01 | 12 | 0 | 1 | 5 | 1 | 1 |
| K02 | 0 | 13 | 4 | 1 | 1 | 1 |
| K03 | 0 | 1 | 13 | 1 | 0 | 5 |
| K04 | 2 | 1 | 0 | 14 | 2 | 1 |

La mediana y el p95 en R01 fueron 13,83 y 29,42 ms para detección y extracción HOG, y 0,080 y 0,097 ms para el voto k-NN. Los tiempos se midieron sobre imágenes ya decodificadas. Las métricas usan fotogramas de personas conocidas en una segunda jornada. La prueba final contará intentos completos e incluirá personas desconocidas.

## Reproducción y comparación

```powershell
python -m scripts.evaluate_hog_knn --vault V:\FaceNexus
```

El ensayo guarda bajo VeraCrypt los vectores de ajuste y validación, el resultado por muestra y un resumen con huellas, versiones, medidas por identidad y tiempos. Una repetición requiere otro `--run-name`. MLP y SVM compartirán los vectores y las etiquetas de este ensayo para que cualquier diferencia observada se pueda atribuir al clasificador con esta representación fija.

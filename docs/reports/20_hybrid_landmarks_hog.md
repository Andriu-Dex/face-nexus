# Landmarks YuNet + HOG completo frente a HOG solo

22-11-2026. Experimento de características propias (PROF-04): los cinco puntos de YuNet, normalizados a la caja, concatenados al HOG de 1764 dimensiones **sin recortar**. Misma tarea K01 frente a OTHER. La demo en vivo **no** se cambió.

## Vector híbrido

YuNet ordena: ojo derecho, ojo izquierdo, nariz, comisura derecha, comisura izquierda.

- 10 coordenadas \((x,y)\) en \([0,1]\) respecto al recorte, más distancia interocular y de punto medio de ojos a nariz (12-D, L2).
- HOG 64×64, celdas 8, 9 orientaciones (1764-D, L2), igual que el resto del proyecto.
- Concatenación y L2 global: cada bloque unitario aporta la mitad de la energía. Dimensión final 1776.

No se usó el recorte a 60 bins del apunte externo.

## Datos (mismas reglas que identidad K01)

| Origen | TRAIN | VALIDATION |
| --- | ---: | ---: |
| S01 K01 (TMCAM) | 18 | — |
| Celular `k01_phone_v3` | 15 | 5 |
| LFW con un recorte YuNet usable | 6.553 OTHER | 2.302 OTHER |

LFW: 9.164 imágenes, 8.855 con un rostro YuNet (309 sin caja usable, excluidas de **ambos** descriptores). Partición por identidad. Ensayo: `experiments/hybrid_k01/hybrid_k01_v1`.

HOG de este ensayo se calcula **sobre el mismo recorte YuNet** que los landmarks, para no atribuir al híbrido una mejora que venga solo de recortar mejor.

## Validación (argmax / voto k=3)

| Modelo | K01 | LFW como K01 | Macro-F1 | Mediana ms |
| --- | ---: | ---: | ---: | ---: |
| k-NN HOG | 5/5 | **0**/2302 | 1,000 | 24,9 |
| k-NN híbrido | 5/5 | **0**/2302 | 1,000 | 25,1 |
| SVM HOG | 5/5 | 54/2302 | 0,572 | 0,32 |
| SVM híbrido | 5/5 | **225**/2302 | 0,496 | 0,32 |

Regla de elección: recall K01 > 0, luego menos LFW aceptados, luego menos rechazos, luego latencia.

**Ganador de este experimento: k-NN HOG** (empate en aciertos con el híbrido; un poco más rápido). El híbrido **no redujo** falsos K01. En SVM los landmarks **empeoraron** (54 → 225 LFW colados).

## Relación con el informe 17

Allí el k-NN usaba HOG de la imagen LFW entera y tuvo 1/2627 falsos K01. Aquí el recorte YuNet ya deja el k-NN en 0/2302 sobre el subconjunto detectable. No se mezclan las dos tablas.

## Conclusión para la demo

Se conserva k-NN + HOG en vivo. Los landmarks se documentan como experimento: cumplen la consigna de sumar geometría a la imagen tratada, y en estos datos no mejoran el rechazo de extraños.

## Limitaciones

Cinco fotos de validación de K01 son la misma ráfaga. 0/2302 no es riesgo cero ni TEST. YuNet umbral 0,9 dejó fuera 309 LFW. No hay K02–K04.

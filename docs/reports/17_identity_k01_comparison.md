# Comparación k-NN, MLP y SVM para K01 frente a OTHER

21-11-2026. Mismos vectores HOG, mismas particiones y misma semilla. No sustituye la comparación de cuatro clases en S01/R01 ([informe 11](11_hog_classifier_comparison.md)). No declara reconocimiento de K02–K04.

## Entradas comunes

| Lote | K01 | OTHER (LFW) | Total |
| --- | ---: | ---: | ---: |
| TRAIN | 18 S01 + 15 celular = 33 | 6.537 | 6.570 |
| VALIDATION | 5 celular (últimos de `k01_phone_v3`) | 2.627 (otras identidades que TRAIN) | 2.632 |

LFW se parte **por persona**. HOG 1764-D L2, k=3, MLP 32 ReLU, SVM lineal, Adam 0,01, L2 0,001, 80 épocas, lote 32, pesos de clase, semilla 17, Keras 3.15.1 / JAX 0.12.1 en CPU. Ensayo privado: `experiments/identity_k01/identity_k01_compare_v1`.

## Validación (argmax; sin umbral de margen)

| Modelo | K01 aciertos | K01 rechazos | LFW como K01 | LFW correctos | Macro-F1 | Mediana inferencia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| k-NN | 5/5 | 0 | **1**/2627 | 2626 | 0,954 | 26,0 ms |
| MLP | **0**/5 | 5 | 0 | 2627 | 0,500 | 0,65 ms |
| SVM lineal | 5/5 | 0 | 47/2627 | 2580 | 0,583 | 0,34 ms |

La exactitud global supera 0,98 en los tres porque OTHER es ~99,8 % de VALIDATION. No se usa para elegir.

## TRAIN (diagnóstico, no selección)

| Modelo | K01 aciertos | LFW como K01 | Nota |
| --- | ---: | ---: | --- |
| k-NN | 23/33 | 1 | Diez K01 de TRAIN no ganan el voto (S01 mezclado con LFW) |
| MLP | 0/33 | 0 | Colapsa a OTHER también en TRAIN (pérdida final 0,70) |
| SVM | 33/33 | 114 | Separa K01; acepta de más en LFW |

## Elección

Regla: se descarta quien no reconoce a K01 (`k01_recall = 0`). Entre el resto, menos aceptaciones de LFW, luego menos rechazos de K01, luego latencia.

**Ganador de este experimento: k-NN.** Un falso K01 en 2.627 LFW frente a 47 de la SVM. La MLP no es candidata: nunca predijo K01.

La demo en vivo pasó a k-NN (D-58, [informe 18](18_live_knn.md)). La SVM queda como contraste. k-NN usa la galería de 6.570 vectores (~26 ms por consulta frente a 0,34 ms de la SVM).

## Limitaciones

- Cinco fotos de validación de K01 son el final de la misma ráfaga del celular, no una sesión nueva.
- k-NN no está calibrado con umbral de distancia; el único LFW aceptado sería `GRANTED` con la regla actual de argmax.
- Esta tabla no elige el modelo de cuatro identidades ni sustituye TEST.
- Hashes Keras: MLP `41073be0…0181c`, SVM `adede4e5…93adff2`.

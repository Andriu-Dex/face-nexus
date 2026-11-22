# Identidad K01 frente a otros humanos

21-11-2026. El profesor pidió entrenar los modelos que se presentan (PROF-04), no limitarse a cuatro fotos de compañeros, y separar humano/no humano del reconocimiento de integrantes (PROF-05). Con un solo integrante en el celular, el entrenamiento de identidad se cierra como **K01 frente a OTHER**, no como cuatro clases.

## Qué pedía la clase

| Requisito | Cómo se cubre ahora | Qué falta |
| --- | --- | --- |
| PROF-04 construir y entrenar en Keras | CNN humano/no humano ya entrenada; SVM lineal HOG K01/OTHER | MLP y k-NN del mismo esquema binario si se quiere la comparación completa |
| PROF-05 humano vs no humano | LFW + CIFAR-10, pesos `human_cnn_full` | Recortes reales del celular y objetos a la misma escala |
| PROF-02 datos propios + auxiliares | S01 y celular de K01 + LFW como OTHER | K02–K04 en el celular |
| PROF-03 comparar clasificadores | Ya hay k-NN, MLP y SVM de cuatro clases en S01/R01 | Esa comparación de cuatro clases no se reutiliza como demo de K01 |
| PROF-01 y PROF-07 cuatro personas y escenas mixtas | Fuera de alcance hasta capturar a los demás | No se declara reconocimiento de cuatro identidades |

Entrenar solo con cuatro compañeros, sin negativos externos, es lo que la clase del 19-11 desaconsejó (sobreajuste). LFW no identifica a K01: es el conjunto de «otras personas». YuNet sigue siendo el único peso preentrenado, para recortar.

## Datos de esta corrida

| Origen | Papel |
| --- | --- |
| HOG S01 de K01 (`knn_baseline_v1` TRAIN) | positivos de la TMCAM |
| `k01_phone_v3` (20 vectores) | 15 TRAIN, últimos 5 VALIDATION del celular |
| LFW color, ≥2 fotos por persona | OTHER; partida por identidad 70/30 |

No se usan las sesiones 03 de K02 y K04 (otra cámara). No se mezclan K02–K04 como si estuvieran en el celular.

## Modelo

Entrada HOG 1764-D L2. Capa densa de 2 logits, pérdida de margen SVM, Adam 0,01, L2 0,001, 80 épocas, pesos de clase, semilla 17. Umbral: el menor valor que rechaza a todos los OTHER de validación clasificados como K01.

## Resultados observados (`identity_k01_v1`)

| Métrica | Valor |
| --- | ---: |
| Positivos TRAIN (S01 + celular) | 18 + 15 = 33 |
| OTHER TRAIN (LFW) | 6.537 |
| VALIDATION celular K01 aceptados | 4 / 5 |
| VALIDATION LFW aceptados como K01 | 0 / 2.627 |
| Umbral de margen | 1,4596 |
| Tiempo de ajuste | 3,4 s |
| SHA-256 del modelo | `36622a1bb1d00882bc28fdfcb350fd793eb398eec3d27417d85191a20136ac77` |

## Ensayo en vivo (celular)

Sobre las 20 fotos TRAIN del celular, YuNet recortó un rostro en todas. La SVM ya etiquetaba las 20 como K01; el umbral 1,46 dejaba fuera 3 (márgenes 0,58, 1,40 y 1,41). La CNN humano/no humano falló en 1/20 con argmax. En vivo se usa margen 0 (argmax) y no se veta un recorte YuNet con LFW/CIFAR. Con argmax, 47/2627 rostros LFW de validación salen como K01.

La ventana muestra `K01 m=… cnn=H|N`. `cnn=N` es diagnóstico, no cierra el acceso si YuNet ya vio una cara.

La comparación de k-NN, MLP y SVM con estas mismas entradas está en [el informe 17](17_identity_k01_comparison.md).

## Limitación

Aceptar a K01 y rechazar LFW no equivale a reconocer a los cuatro. El holdout del celular son cinco fotos de la misma ráfaga: no es una sesión nueva. El dominio TMCAM frente a IP Webcam sigue presente. K02–K04 se añadirán como clases, reentrenando con sus lotes del celular y negativos LFW. La CNN LFW/CIFAR no transfiere bien a recortes del cuarto; no se presenta como prueba de vida.

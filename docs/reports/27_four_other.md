# Ensayo exploratorio K01–K04 + OTHER

22-11-2026. Se entrenó k-NN, MLP y SVM lineal con el mismo HOG: 120 inscritos de `identity_four_v2` y 6.537 OTHER de LFW (partición por identidad). VALIDATION: 39 recortes de otro encuentro propio y 2.627 LFW de personas distintas a las de TRAIN. No es TEST. El vivo no cambió.

## VALIDATION

| Modelo | Inscritos correctos | Confusiones | Inscritos → OTHER | LFW → inscrito |
| --- | ---: | ---: | ---: | ---: |
| **k-NN** | **19/39** | **2** | 18 | **2/2627** |
| MLP | 22/39 | 10 | 7 | 2347/2627 |
| SVM | 27/39 | 12 | 0 | 1364/2627 |

Gana k-NN: menos aceptaciones indebidas de LFW y menos confusiones entre integrantes. SVM reconoce más inscritos y cuela 1364 extraños.

k-NN por persona (columna UNKNOWN = voto OTHER): K01 6/12, **K02 1/9**, K03 8/9, K04 4/9. Las 2 confusiones son K01→K04.

La política T+G de cuatro clases (referencia de simulación) sigue en el vivo: 13/39 y 31/2627 LFW en la comprobación de supervisión. Este ensayo no la sustituye.

## Comprobación de supervisión

Se verificó la huella de la galería y su correspondencia exacta con los vectores y etiquetas de ajuste. Se recalcularon las 2.666 predicciones de validación de k-NN y todas coincidieron con el registro. Las cifras de MLP y SVM se cotejaron contra sus predicciones guardadas.

El objetivo corregido de calibración de la referencia de cuatro clases eligió los mismos T y G en memoria. De sus 78 aceptaciones por exclusión individual en TRAIN, 77 fueron correctas y una fue una confusión. La corrección distingue ambos resultados aunque los umbrales elegidos coincidan. La suite con Keras sobre JAX en CPU pasó 117 pruebas.

## Limitaciones

Downloads + LFW no son el celular del aula. K02–K04 en IP Webcam siguen pendientes. MLP y SVM no sirven aquí para acceso. No se consumió TEST.

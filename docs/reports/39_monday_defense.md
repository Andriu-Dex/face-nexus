# Ensayo, defensa y comparación

22-11-2026. Simulación. T ≈ 0,530 y G ≈ 0,057 de `identity_four_v2`. Sin pestillo desde el reconocimiento.

Las tomas nuevas y la demostración van **sin lentes**. Las fotos históricas con lentes se conservan. No se ajustan umbrales con esas capturas.

## Caducidad de Autorizado

Si el video sigue y la inferencia no entrega un resultado fresco, la decisión visible pasa a Espera a los 1 s. La caja puede caducar antes (0,45 s) y eso no basta para quitar Autorizado.

## Ruta efectiva

YuNet recorta. Gris 64×64, ecualización, HOG 1764-D, k-NN k=3. Se acepta si el ganador es K01–K04, `d ≤ T` y `g ≥ G`. PROF-07: `decide_scene` autoriza si **al menos una** región está concedida.

## Casos de defensa (simulación)

En la interfaz: Abrir imagen o carpeta; permisos en el lateral. Una presentación = un resultado.

| Caso | Qué hacer | Qué debe verse |
| --- | --- | --- |
| K01–K04 por separado | Una persona, permiso activo | Autorizado solo si pasa T y G |
| Permiso inactivo | Desmarcar a esa persona | Denegado, permiso inactivo |
| Desconocido | Alguien no inscrito | Rostro detectado · identidad no confirmada |
| Fondo u objeto | Sin cara | Denegado, sin rostro |
| Dos autorizados | Dos integrantes con permiso | Autorizado (basta uno) |
| Autorizado + desconocido | Un inscrito y un extraño | Autorizado si el inscrito cumple T y G |
| Luz / giro / distancia | Variar de forma controlada | Anotar el resultado; no retocar T/G |
| Foto en pantalla | Exploratorio | Anotar lo observado. No es prueba de anti-suplantación |

## Comparación ya medida (no TEST)

| Ensayo | Partición | n | Exactitud / aciertos | Rechazos o extraños |
| --- | --- | ---: | --- | --- |
| 23 cuatro IDs, argmax | VAL Downloads, otro encuentro | 39 | 31/39 | K02 5/9 |
| 26 T=0,530 | misma VAL | 39 | 22/39 | 15 UNKNOWN |
| 26 T y G (vivo) | misma VAL | 39 | **13/39** | 26 UNKNOWN; K02 0/9 |
| 25 T y G | LFW TRAIN OTHER | 6537 | — | 60 aceptados |
| 27 k-NN + OTHER | VAL 39 + LFW 2627 | 39+2627 | 19/39 | 2/2627 LFW |
| 17 K01/OTHER k-NN | VAL celular 5 + LFW 2627 | 5+2627 | 5/5 K01 | 1/2627 |

El vivo usa la fila T y G de 26, no el ganador de 27. Downloads no es el celular del aula.

## Mismos datos, mismos cortes (informe 27)

Mismo HOG, mismo TRAIN (120 inscritos de `identity_four_v2` + 6.537 OTHER LFW) y misma VALIDATION (39 recortes de otro encuentro + 2.627 LFW). No es TEST. El vivo no cambió.

| Modelo | Inscritos correctos | Confusiones | Inscritos → OTHER | LFW → inscrito |
| --- | ---: | ---: | ---: | ---: |
| **k-NN** | **19/39** | **2** | 18 | **2/2627** |
| MLP | 22/39 | 10 | 7 | 2347/2627 |
| SVM | 27/39 | 12 | 0 | 1364/2627 |

k-NN se elige por menos extraños aceptados y menos confusiones entre integrantes, no por mayor acierto en inscritos. SVM reconoce más K01–K04 y cuela 1364 LFW. MLP cuela 2347. No sustituyen T+G del vivo (13/39 en la fila 26).

Filtro (informe 21): Laplaciano 85 habría tirado 8/20 del celular que ya sirven en TRAIN. La línea base **no** veta por nitidez. Una sola variante sobre la misma VALIDATION, si se defiende un filtro; el ensayo final queda aparte.

## Banco

Servo sin carga y fuente externa primero. Luego pestillo de maqueta. Orden ≠ acuse ≠ movimiento visto. Reconocimiento en simulación hasta completar el banco.

# VALIDATION de cuatro identidades con T y G

22-11-2026. Se volvió a extraer VALIDATION de Downloads (otro encuentro, 39 recortes) y se aplicaron los candidatos T=0,530 y G=0,057. No es TEST. No es el celular de la demostración. La galería no se reentrenó.

## Observado

Filas = verdadero; columnas = K01, K02, K03, K04, UNKNOWN.

Argmax sin umbral (informe 23): **31/39**. T=0,770 no cambiaba esas cifras.

| Criterio | Aciertos | UNKNOWN | K01 | K02 | K03 | K04 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Solo T=0,530 | 22/39 | 15 | 8/12 | 3/9 | 7/9 | 4/9 |
| T y G | **13/39** | **26** | 4/12 | **0/9** | 7/9 | 2/9 |

Con T y G, las confusiones K01→K04 y K02→K03 de esa partición pasan a UNKNOWN. K02 no obtiene ningún acierto. El reconocimiento permanece en simulación.

## Comprobación adicional de supervisión

Se reprodujo el resultado de 13/39 con la misma galería y los mismos umbrales. Al revisar la exclusión de una muestra por vez en TRAIN, 78/120 pasaron el filtro y 77/120 se asignaron a la identidad correcta. La diferencia corresponde a una confusión aceptada.

Sin cambiar T ni G, se aplicó la política a la partición de validación LFW usada como referencia en el experimento K01/OTHER. Contiene 2.627 imágenes de 504 personas, separadas por identidad de las usadas para calibrar T y G en este ensayo. Se aceptaron 31/2.627 (1,18 %). El resultado superó la meta exploratoria del 1 %. Esta comprobación mide imágenes de LFW y deja pendiente la prueba por presentación con el celular.

## Qué no es

No reserva extraños del aula. No calibra de nuevo T y G. No entrena identidad con capturas propias más rostros externos. No cambia el papel de la CNN en la decisión. No flashea el pestillo.

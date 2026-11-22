# Calidad del recorte: nitidez y exposición medidas

22-11-2026. Filtro de calidad sobre **fotos propias**, no umbrales copiados. Laplaciano y colas del histograma en el recorte YuNet. No se borró TRAIN. El vivo **no** veta por estos números.

## Definición

Sobre el recorte en gris (uint8):

- Varianza del Laplaciano (nitidez).
- Fracción de píxeles ≤ 10 (cola oscura) y ≥ 245 (cola clara).
- Lado menor de la caja, en píxeles.

Umbral de apunte externo para comparar: Laplaciano **85**. Colas 20 % / 25 % no se usaron: en estas fotos las colas están muy por debajo.

Los pisos de aviso del celular son el percentil 5 (método `lower`) de nitidez y lado, y el percentil 95 (`higher`) de las colas, calculados **solo** con las 20 caras de `k01_phone_v3`. No se cruzan con TMCAM: el lado de caja del celular (~500 px) no es comparable al de S01 (~140 px).

Ensayo: `experiments/frame_quality/frame_quality_v2`.

## Resultados

| Lote | n YuNet único | Laplaciano min / mediana / máx | Oscuros mediana | Lado menor mediana | Laplaciano < 85 |
| --- | ---: | --- | ---: | ---: | ---: |
| Celular `k01_phone_v3` | 20/20 | 8,8 / **105** / 151 | 1,0 % | 519 px | **8/20** |
| S01 K01 (TMCAM) | 18/18 | 106 / **405** / 1317 | 3,6 % | 140 px | 0/18 |

Cola clara del celular: mediana ≈ 0, máxima 0,055 %. Ninguna foto propia se acerca a un 20 % de saturación.

Pisos de aviso (solo celular, mismo montaje): Laplaciano 8,81; oscuros 2,60 %; claros 0,055 %; lado 519 px. Con esa regla, **0/20** del propio lote avisan (el piso de nitidez coincide con el mínimo). 15/18 de S01 superarían la cola oscura del celular: es **otra cámara y otra luz**, no un fallo de esas fotos.

## Qué no se hace

- No se descartan las 8 fotos del celular con Laplaciano < 85: ya entrenan y aparecen en la demo.
- No se niega acceso en vivo por nitidez. Un recorte blando de MJPEG seguiría el mismo camino HOG + k-NN.
- No se unifica un umbral de tamaño de caja entre TMCAM y el teléfono.

Las capturas nuevas del celular guardan el bloque `quality` en la ficha (`inspect_live_frame`). Un aviso tendría sentido si una toma nueva queda **por debajo del mínimo ya observado** en ese montaje (Laplaciano < 8,8), no si queda bajo 85.

## Limitaciones

Veinte fotos de una ráfaga, una persona, un cuarto. El Laplaciano depende de resolución, compresión MJPEG y distancia. S01 más nítido no implica mejor identidad: es otra óptica. K02–K04 no están.

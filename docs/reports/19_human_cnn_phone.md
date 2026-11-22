# Ajuste de la CNN humano/no humano al celular

21-11-2026. La CNN de [LFW y CIFAR-10](15_human_cnn.md) marcaba recortes YuNet del cuarto como no humano. Se partió de `human_cnn_full` y se ajustó con caras y fondo del lote `k01_phone_v3`. No identifica a K01. No es detección de vida.

## Datos añadidos

| Origen | Etiqueta | TRAIN | VALIDATION |
| --- | --- | ---: | ---: |
| Recorte YuNet de las 20 fotos del celular | humano | 15 | 5 (mismos últimos fotogramas que identidad) |
| Parches 160×160 sin solape con la cara | no humano | 45 | 15 |
| LFW + CIFAR-10 (límite 2000 por clase en TRAIN, como en `human_cnn_v1`) | se conservan | mezcla | mezcla |

Los parches son estantería, póster y pared del mismo encuadre, no gatos ni papeles nuevos. El peso de cada muestra del celular es 20 frente a 1 de LFW/CIFAR. Ocho épocas, Adam 0,0003. Ensayo: `experiments/human_cnn/human_cnn_phone_v1`. SHA-256 `d0718111920fc9d450d50b4d9273630dd15dc962259155c59331c78e331b39da`.

## Recortes del celular (lo que fallaba)

| Subconjunto | n | Resultado |
| --- | ---: | --- |
| Caras TRAIN | 15 | 15/15 humano |
| Caras VALIDATION | 5 | **5/5 humano** |
| Parches TRAIN | 45 | 45/45 no humano |
| Parches VALIDATION | 15 | 14/15 no humano |

## Validación mezclada (público + celular)

n = 1020. Exactitud 0,999. Recall humano 1,000. Recall no humano 0,998. El único error de este lote mezclado es un parche del celular etiquetado humano.

## Demo

`live_k01` carga este modelo. Sigue **sin vetar** un recorte YuNet (`not_human` no cierra si ya hay cara). En `no_face` (silla, póster) el overlay añade `cnn=H|N` sobre el fotograma completo.

## Limitación

Cinco caras de validación son la misma ráfaga. Un parche de fondo se confundió con humano. No se entrenó con foto impresa de K01, animal a escala real ni papel en la mano. Eso no autoriza a presentar la CNN como anti-spoof.

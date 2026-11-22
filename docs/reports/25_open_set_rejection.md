# Rechazo abierto de extraños (T y holgura)

22-11-2026. El T = 0,770 (máximo d genuino × 1,1) aceptaba 6.004/6.537 HOG LFW no inscritos. Se añade un segundo número: la holgura respecto a **otra** identidad de la galería.

## Fórmula

Aceptar solo si el voto k=3 es K01–K04, `d_ganador ≤ T` y `d_otra − d_ganador ≥ G`, donde `d_otra` es la distancia mínima a una muestra de una etiqueta distinta.

T y G se eligen en VALIDATION de extraños de calibración (LFW TRAIN OTHER del ensayo K01, 6.537 vectores) con FAR ≤ 1 %, maximizando el acierto leave-one-out de TRAIN y, en empate, el T más pequeño. No se usa TEST.

## Observado

| Criterio | Extraños aceptados | FAR |
| --- | ---: | ---: |
| Solo T=0,770 | 6.004 / 6.537 | 0,918 |
| T=0,530 y G=0,057 | **60 / 6.537** | **0,0092** |

De esos 60, 44 van a K03. Leave-one-out en los 120 de TRAIN: **78/120** aceptados (42 rechazados de más). Eso no es la VALIDATION de Downloads (31/39 con el T viejo); no se volvió a extraer esa partición.

La galería no cambió (`139a8e83…eed339`). `knn_max_distance.json` guarda T y G ligados a esa huella. El vivo usa ambos. El pestillo sigue sin recibir reconocimiento.

## Limitaciones

LFW no es un extraño delante del celular. K02 sigue débil. 1 % de FAR en este lote no es riesgo cero. Una foto impresa de un integrante puede seguir aceptándose.

# Manifiesto del celular, dominio y veto CNN

22-11-2026. Encargo sin hardware: preparar lotes del celular para K01–K04, repetir la comparación con extraños disjuntos y medir qué hace la CNN si veta antes de identificar. No se flasheó el pestillo.

## Manifiesto privado

`scripts/phone_demo_manifest.py` y `--role tune|eval` en la captura parametrizada. Ajuste y evaluación son encuentros distintos. Una ráfaga entera queda en una sola partición. Huellas repetidas entre ajuste y evaluación se rechazan. Si falta una clase, se avisa. La comprobación sintéticas cubre manifiesto completo, K02 ausente y hash cruzado.

Aún no hay ráfagas `tune`/`eval` de los cuatro en el volumen. K01 `k01_phone_v3` es un lote de adaptación anterior, no el manifiesto de demostración.

## Comparación de dominio

El candidato k-NN K01–K04+OTHER (`identity_four_other_v1`) se conserva para cuando existan lotes de evaluación del celular. Los extraños de esa VALIDATION (LFW por identidad, 2.627) son distintos de LFW TRAIN usado al ajustar OTHER. En esa VALIDATION: 19/39 inscritos, 2 confusiones, K02 1/9, 2/2627 extraños. La interfaz sigue en simulación.

## CNN antes de identificar

Mismo montaje: 20 recortes YuNet de `k01_phone_v3` (humano) y 60 parches de fondo (no humano). Identidad forzada a K01 para aislar el veto.

| Entrada | n | CNN bloquea | Veto indebido de un GRANTED | No humano que pasa |
| --- | ---: | ---: | ---: | ---: |
| Recortes de cara | 20 | 0 | 0 | — |
| Parches de fondo | 60 | 59 | 0 | **1** |

Sin veto (YuNet de confianza), un parche no se presenta como cara. Con veto sobre un recorte ya hecho, esas 20 caras siguen pasando y 1/60 fondos se etiquetarían humano. El vivo **sigue sin vetar** YuNet. No es liveness.

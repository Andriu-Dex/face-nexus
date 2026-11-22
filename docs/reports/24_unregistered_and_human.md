# Extraños y humano/no humano, sin pestillo

22-11-2026. La tercera revisión exige medir K01–K04 frente a rostros no inscritos y comprobar humano/no humano **aparte** de la identidad. El reconocimiento no envía el pestillo. El ESP32 sigue en firmware de banco. El SG90 no se conectó.

## Extraños (LFW OTHER vs galería de cuatro)

Ensayo `identity_four_v2`, T = 0,770, huella `139a8e83…eed339`. Los 6.537 HOG OTHER del ensayo K01/OTHER (`identity_k01_compare_v1`, LFW TRAIN por identidad) no están inscritos como K01–K04.

| Destino | n |
| --- | ---: |
| Rechazados (`UNKNOWN`) | **533** |
| Aceptados como algún K0x | **6.004** |
| como K01 | 2.334 |
| como K02 | 216 |
| como K03 | 3.025 |
| como K04 | 429 |

T calibrado con aciertos de los cuatro **no** rechaza extraños de LFW. No es TEST. No se cambió la galería ni se flasheó el pestillo. La interfaz no acciona por reconocimiento.

## Humano / no humano (independiente)

Modelo `human_cnn_phone_v1`. Recortes YuNet de las 5 fotos reservadas del celular + 500 imágenes del test oficial CIFAR-10. No veta YuNet. No es liveness. No identifica integrantes.

| Lote | n | Resultado |
| --- | ---: | --- |
| Recortes del celular (humano) | 5 | 5/5 humano |
| CIFAR-10 test (no humano) | 500 | 500/500 no humano |

Un fotograma completo sin recorte no es la entrada de esta red: por eso el vivo sigue confiando en YuNet para localizar y usa la CNN solo como comprobación aparte.

## Banco LATCH

`scripts/latch_command_bench.py` envía `PING` y `CHECK` al firmware de pestillo, con `--servo-disconnected`. No se ejecutó en COM5: la placa responde `PONG FACENEXUS BENCH 1`. No grabar el pestillo ni engranar el SG90 hasta ese banco.

## Limitaciones

Downloads + LFW no sustituyen el celular del aula para K02–K04. 6.004/6.537 extraños aceptados impiden habilitar la autorización física con este T.

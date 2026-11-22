# CNN humano / no humano entrenada por el grupo

21-11-2026. Se construyó y entrenó en Keras una CNN de dos clases. No sustituye el reconocimiento de K01–K04. YuNet sigue siendo el recorte preentrenado.

## Datos

| Fuente | Papel | Partición | Recorte de esta corrida |
| --- | --- | --- | --- |
| LFW (UMass, vía scikit-learn) | humano | por identidad, 70/30 de personas | 2000 TRAIN, 500 VALIDATION |
| CIFAR-10 (Keras) | no humano (objetos y animales; sin clase persona) | train/test oficiales | 2000 TRAIN, 500 VALIDATION |

LFW aportó 9164 imágenes de 1680 identidades (6.537 TRAIN / 2.627 VALIDATION, partida por persona). CIFAR-10 aportó las 50.000 de train y 10.000 de test oficiales. Las identidades de LFW no se etiquetan como integrantes. Las imágenes no van a Git. Uso académico; no se republican. El desbalance (más objetos que caras) se compensó con `class_weight`.

## Modelo

Entrada 64×64×3. Conv 16, MaxPool, Conv 32, MaxPool, Dense 32, 2 logits. Entropía cruzada, Adam 0,001, 8 épocas, semilla 17, CPU. Arquitectura definida en Keras, no un estimador cerrado de scikit-learn.

## Resultados observados

Primera corrida recortada (`human_cnn_v1`, 2000 por clase en TRAIN):

| Lote | n | Exactitud | Recall humano | Recall no humano |
| --- | ---: | ---: | ---: | ---: |
| TRAIN | 4000 | 0,99975 | 0,9995 | 1,000 |
| VALIDATION | 1000 | 0,999 | 1,000 | 0,998 |

Corrida completa (`human_cnn_full`, sin recorte, pesos de clase para el desbalance):

| Lote | Humanos | No humanos | n | Exactitud | Recall humano | Recall no humano |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAIN | 6.537 | 50.000 | 56.537 | 0,99996 | 0,99985 | 0,99998 |
| VALIDATION | 2.627 | 10.000 | 12.627 | 0,99960 | 0,99810 | 1,000 |

En VALIDATION completa, 5 rostros LFW se etiquetaron no humano y 0 objetos CIFAR se etiquetaron humano. Modelo de referencia para el informe: `experiments/human_cnn/human_cnn_full`.

## Limitación

La exactitud alta **no** demuestra detección de vida ni muñecos. LFW son retratos; CIFAR-10 son objetos pequeños. La red puede estar separando «retrato de cara» frente a «miniatura de objeto», no «humano frente a gato a la misma escala y cámara». El ajuste con recortes del celular está en [el informe 19](19_human_cnn_phone.md).

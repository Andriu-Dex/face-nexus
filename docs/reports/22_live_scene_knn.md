# Escena con varios rostros y umbral de distancia k-NN

22-11-2026. Adelanto con un solo integrante (K01). No se etiquetan K02–K04. El pestillo físico sigue sin accionarse.

## Qué cambió en vivo

Cada caja YuNet se clasifica aparte (HOG + k-NN). `decide_scene` autoriza si **al menos una** región es K01 con permiso. Las demás pueden ser `unknown_identity`. Caja verde = autorizada, roja = denegada.

Antes, dos caras en el fotograma eran `DENIED / multiple_faces` sin mirar quién era. Eso fallaría el día de la defensa con cuatro personas delante de la cámara, aunque K01 estuviera en el cuadro.

## Umbral T

Misma galería que el informe 17 (`identity_k01_compare_v1`). T se fija con VALIDATION: máximo de distancias de las 5 fotos K01 del celular que el k-NN ya aceptaba, × 1,1 de holgura por pose. No se usa TEST.

| | Valor |
| --- | ---: |
| Máximo d K01 en VALIDATION | 0,414 |
| T (× 1,1) | **0,456** |
| LFW votados K01 sin T | 1/2627 |
| LFW votados K01 con T | **0/2627** |
| K01 de VALIDATION con T | 5/5 |

Archivo privado: `experiments/identity_k01/identity_k01_compare_v1/knn_max_distance.json`.

```powershell
.\.venv\Scripts\python.exe -m scripts.calibrate_knn_distance --vault V:\FaceNexus
.\.venv\Scripts\python.exe -m scripts.live_k01 --vault V:\FaceNexus --url http://192.168.1.20:8080/video --rotation 0
```

## Lo que la defensa todavía no cubre

- K02, K03 y K04 no están en la galería: saldrán como extraños hasta el lote del celular del lunes.
- `GRANTED` es autorización simulada (`physical_open` falso). El SG90 no se mueve.
- Una foto impresa de K01 puede abrir: no hay prueba de vida.
- Cinco fotos de validación son la misma ráfaga. T no es un TEST.

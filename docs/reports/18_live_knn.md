# Demo en vivo con k-NN (modelo elegido)

21-11-2026. Tras la [comparación](17_identity_k01_comparison.md), el reconocimiento operativo de K01 usa k-NN con la galería TRAIN del mismo ensayo. La SVM permanece disponible para contrastar (`--backend svm`).

## Runtime

- Detector: YuNet (recorte).
- Identidad: 3-NN euclidiano sobre HOG L2, galería de 6.570 vectores (33 K01 + 6.537 LFW TRAIN).
- Aceptación: el voto es K01. Sin umbral extra de distancia (igual que la tabla del informe 17).
- CNN humano/no humano: modelo `human_cnn_phone_v1` ([informe 19](19_human_cnn_phone.md)); se muestra (`cnn=H|N`) y no veta un recorte YuNet.
- Autorización simulada: `GRANTED` con un K01 confirmado. Desde el [informe 22](22_live_scene_knn.md) cada caja se clasifica y la escena abre si hay al menos un K01; hay umbral de distancia T=0,456.

Galería privada: `experiments/identity_k01/identity_k01_compare_v1/gallery.npz` (6.570 vectores, SHA-256 `b0aed04ef791cd6ffe38b06d34d7559af328f20522335f2e1ad4d25c5107ed1f`).

```powershell
.\.venv\Scripts\python.exe -m scripts.live_k01 --vault V:\FaceNexus --url http://192.168.1.20:8080/video --rotation 0
```

`--backend svm` restaura la SVM de `identity_k01_v1`.

La ventana muestra `knn` y `d=` (distancia al vecino ganador; menor es más cercano). SVM muestra `m=` (margen de puntuaciones).

## Lo que no cambia

No hay cuatro identidades. No hay umbral de distancia calibrado sobre desconocidos del celular. k-NN ronda ~26 ms por consulta en la medición de validación. El SG90 no se acciona. Una foto impresa de K01 no se ensayó como ataque.

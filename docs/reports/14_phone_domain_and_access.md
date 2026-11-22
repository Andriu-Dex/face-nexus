# Dominio del celular y autorización simulada

21-11-2026. No se reentrenó el clasificador de cuatro clases: solo hay TRAIN de K01 en el celular. Los modelos SVM y MLP siguen siendo los congelados de S01.

## Lote usado

`experiments/hog_phone_adapt/K01/k01_phone_v3`: 20/20 recortes HOG usables, 1920×1080, giro 0. Informe privado `domain_vs_s01.json`.

## Coseno a las medias de S01

Sobre 20 vectores del celular, la media de S01 más cercana fue K01 en 16 casos, K03 en 3 y K02 en 1. Las medianas de coseno están muy juntas: K01 0,864; K03 0,850; K02 0,839; K04 0,832.

Los modelos congelados no siguen esas medias: SVM asignó K03 en 15/20, K01 en 3/20 y K04 en 2/20. MLP no asignó K01 (K03 11, K02 9). El recorte del celular es usable; la frontera aprendida en TMCAM no.

## Autorización

`scripts/access.py` decide `GRANTED` solo con un rostro, candidato aceptado, identidad K01–K04 y permiso activo. Cualquier otro caso es `DENIED`. El controlador simulado registra la decisión y `physical_open` queda en falso. Revocar un permiso no requiere reentrenar.

## Pendiente

Capturar K02–K04 con el mismo celular, reentrenar HOG con las cuatro en ese dominio, y recién entonces calibrar rechazo. No usar la sesión 03 de otra cámara como sustituto.

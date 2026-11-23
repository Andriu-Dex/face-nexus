# Calibración ligada al ensayo

22-11-2026. Correcciones de supervisión con NPZ sintéticos. Sin capturas nuevas ni pestillo.

Al entrenar K01–K04+OTHER se guarda `calibration.npz` con los vectores OTHER realmente usados, sus `sample_ids` e `identity_ids`, y las huellas van en `summary.json` junto a `gallery_sha256`.

El evaluador compara esa huella con el archivo suministrado y exige vectores HOG. Un NPZ de otro ensayo, o uno que solo trae etiquetas, deja la disjunción sin verificar.

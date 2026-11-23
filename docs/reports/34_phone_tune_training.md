# Entrenamiento con tune del celular

22-11-2026. Modo `--phone-tune`. Sin capturas nuevas ni pestillo.

`identity_four_other.assemble` histórico no lee el manifiesto del celular. El modo nuevo carga HOG de `tune`, comprueba K01–K04, concatena OTHER externo y registra las huellas de cada lote. Los vectores `eval` se retienen para evaluar y no se concatenan al ajuste.

La interfaz y el pestillo siguen en simulación. La captura puede seguir en paralelo, un lote a la vez.

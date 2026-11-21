"""Carregamento do classificador de intenções serializado.

O modelo é o Pipeline completo (TF-IDF + LogisticRegression) treinado no
notebook `eda/eda_tp3.ipynb` (seções "Avaliação do modelo" e "Persistência
do modelo") e salvo com joblib. A carga é lazy
(na primeira chamada) e cacheada em módulo: assim, se o arquivo estiver
ausente, a falha ocorre apenas na requisição ao `/classify`, e não no
`import` da aplicação (o que derrubaria toda a API e os testes).
"""

from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent / "intent_classifier.joblib"

_model = None


def get_model():
    """Retorna o Pipeline treinado, carregando-o do disco na primeira chamada."""
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

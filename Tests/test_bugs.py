# tests/test_bugs.py
import pandas as pd
from utils import save_bugs, load_bugs

def test_save_and_load_bugs(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.PROJECTS_DIR", tmp_path)

    df = pd.DataFrame([{
        "id": 1,
        "titulo": "Bug teste",
        "tela": "Login",
        "modulo": "Auth",
        "descricao": "Erro ao logar",
        "comportamento_ideal": "Logar",
        "comportamento_atual": "Erro",
        "bdd": "",
        "status": "Novo",
        "data_criacao": "2026-01-01"
    }])

    save_bugs("ProjetoQA", df)
    loaded = load_bugs("ProjetoQA")

    assert len(loaded) == 1
    assert loaded.iloc[0]["titulo"] == "Bug teste"

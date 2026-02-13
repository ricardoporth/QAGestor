# tests/test_bug_status.py
import pandas as pd
from utils import save_bugs, load_bugs

def test_change_bug_status(tmp_path, monkeypatch):
    # Força o diretório de projetos temporário
    monkeypatch.setattr("utils.PROJECTS_DIR", tmp_path)

    # Cria um bug de teste
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

    # Salva o bug
    save_bugs("ProjetoQA", df)

    # Carrega e muda o status
    loaded = load_bugs("ProjetoQA")
    loaded.loc[0, 'status'] = "Em Teste"
    save_bugs("ProjetoQA", loaded)

    # Verifica se mudou
    reloaded = load_bugs("ProjetoQA")
    assert reloaded.iloc[0]['status'] == "Em Teste"

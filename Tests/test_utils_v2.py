import os
import pytest
import pandas as pd
import utils # Importamos o módulo inteiro para pegar o valor atualizado pelo monkeypatch

# Fixture para garantir que os testes usem uma pasta temporária
@pytest.fixture(autouse=True)
def setup_test_env(tmpdir, monkeypatch):
    # Cria uma pasta temporária exclusiva para este teste
    temp_projects = tmpdir.mkdir("temp_projects")
    # Altera o PROJECTS_DIR dentro do módulo utils durante o teste
    monkeypatch.setattr(utils, "PROJECTS_DIR", str(temp_projects))
    return str(temp_projects)

def test_save_and_load_project_notes():
    project = "ProjetoTeste"
    content = "Minha nota de teste"
    utils.save_project_notes(project, content)
    loaded = utils.load_project_notes(project)
    assert loaded["content"] == content

def test_load_test_cases_empty_suite():
    project = "ProjetoVazio"
    suite = "SuiteVazia"
    utils.ensure_project_structure(project)
    df = utils.load_test_cases(project, suite)
    assert isinstance(df, pd.DataFrame)
    assert "report_bug_execucao_test_case" in df.columns

def test_ensure_project_structure_creates_folders():
    project = "NovoProjeto"
    utils.ensure_project_structure(project)
    
    # Usamos utils.PROJECTS_DIR para garantir que pegamos o caminho temporário
    base_path = os.path.join(utils.PROJECTS_DIR, project)
    
    assert os.path.exists(os.path.join(base_path, "bugs"))
    assert os.path.exists(os.path.join(base_path, "test_suites"))
    # Verificamos se a pasta user_stories também foi criada
    assert os.path.exists(os.path.join(base_path, "user_stories"))

def test_load_test_cases_data_cleaning():
    project = "ProjetoLimpeza"
    suite = "SuiteLimpeza"
    utils.ensure_project_structure(project)
    
    df_manual = pd.DataFrame([{
        "id": 1,
        "modulo": None,
        "titulo": "Teste"
    }])
    
    utils.save_test_cases(project, suite, df_manual)
    df_loaded = utils.load_test_cases(project, suite)
    
    # O seu código no utils.py converte None para "" (string vazia)
    assert df_loaded.loc[0, "modulo"] == ""
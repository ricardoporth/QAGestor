import os
import pytest
import pandas as pd
from utils import (
    save_project_notes, 
    load_project_notes, 
    ensure_project_structure,
    load_test_cases,
    PROJECTS_DIR
)

# Fixture para garantir que os testes usem uma pasta temporária
@pytest.fixture(autouse=True)
def setup_test_env(tmpdir, monkeypatch):
    # Muda o diretório de projetos para uma pasta temporária durante os testes
    temp_projects = tmpdir.mkdir("temp_projects")
    monkeypatch.setattr("utils.PROJECTS_DIR", str(temp_projects))
    return str(temp_projects)

def test_save_and_load_project_notes():
    project = "ProjetoTeste"
    content = "Minha nota de teste"
    
    # Testa salvar
    save_project_notes(project, content)
    
    # Testa carregar
    loaded = load_project_notes(project)
    
    assert loaded["content"] == content
    assert loaded["last_update"] is not None

def test_load_test_cases_empty_suite():
    project = "ProjetoVazio"
    suite = "SuiteVazia"
    ensure_project_structure(project)
    
    # Tenta carregar uma suite que não existe ainda
    df = load_test_cases(project, suite)
    
    # Deve retornar um DataFrame vazio mas com as colunas corretas
    assert isinstance(df, pd.DataFrame)
    assert "report_bug_execucao_test_case" in df.columns
    assert "modulo" in df.columns

def test_ensure_project_structure_creates_folders():
    project = "NovoProjeto"
    ensure_project_structure(project)
    
    base_path = os.path.join(PROJECTS_DIR, project)
    assert os.path.exists(os.path.join(base_path, "bugs"))
    assert os.path.exists(os.path.join(base_path, "test_suites"))
    assert os.path.exists(os.path.join(base_path, "notes"))

def test_load_test_cases_data_cleaning():
    # Testa se a sua "Correção Definitiva" de converter nan para string vazia funciona
    project = "ProjetoLimpeza"
    suite = "SuiteLimpeza"
    ensure_project_structure(project)
    
    # Criar um DataFrame com valores mistos
    df_manual = pd.DataFrame([{
        "id": 1,
        "modulo": None,  # Deve virar ""
        "titulo": "Teste",
        "automatizavel": "True"
    }])
    
    from utils import save_test_cases
    save_test_cases(project, suite, df_manual)
    
    # Carregar novamente
    df_loaded = load_test_cases(project, suite)
    
    # Verificar se o None virou string vazia conforme sua lógica
    assert df_loaded.loc[0, "modulo"] == ""
import os
import json
import pandas as pd
import shutil
from datetime import datetime
import uuid
import streamlit as st
import io

# ---------- Constantes ----------
PROJECTS_DIR = "projects"

def export_project_to_excel(project_name):
    """Gera um arquivo Excel em memória com todas as informações do projeto."""
    # Carrega os dados usando as funções que você já tem
    bugs_df = load_bugs(project_name)
    test_cases_df = get_all_test_cases(project_name)
    stories = load_user_stories(project_name)
    validations = load_validations(project_name)
    notes = load_project_notes(project_name)

    # Converte listas para DataFrames
    stories_df = pd.DataFrame(stories)
    validations_df = pd.DataFrame(validations)
    notes_df = pd.DataFrame([notes])

    # Cria um buffer para salvar o arquivo Excel
    output = io.BytesIO()
    
    # Usa o XlsxWriter como engine para criar abas
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if not bugs_df.empty:
            bugs_df.to_excel(writer, sheet_name='Bugs', index=False)
        
        if not test_cases_df.empty:
            test_cases_df.to_excel(writer, sheet_name='Casos de Teste', index=False)
            
        if not stories_df.empty:
            stories_df.to_excel(writer, sheet_name='User Stories', index=False)
            
        if not validations_df.empty:
            validations_df.to_excel(writer, sheet_name='Historico Validações', index=False)
            
        if not notes_df.empty:
            notes_df.to_excel(writer, sheet_name='Notas', index=False)

    return output.getvalue()

def render_sidebar():
    st.sidebar.title("Gerenciador de Projetos")
    
    # --- Seção: Criar Novo ---
    with st.sidebar.form("new_project_form"):
        new_project_name = st.text_input("Nome do Novo Projeto")
        if st.form_submit_button("Criar Projeto") and new_project_name:
            project_path = os.path.join(PROJECTS_DIR, new_project_name)
            if not os.path.exists(project_path):
                ensure_project_structure(new_project_name)
                st.sidebar.success(f"Projeto '{new_project_name}' criado!")
                st.session_state.selected_project = new_project_name
                st.rerun()
            else:
                st.sidebar.error("Projeto já existe.")

    # Lista projetos existentes
    projects = get_project_list()
    if not projects:
        st.sidebar.warning("Nenhum projeto encontrado.")
        if 'selected_project' in st.session_state:
            del st.session_state.selected_project
        st.stop()

    # --- Lógica de Seleção ---
    if "selected_project" not in st.session_state or st.session_state.selected_project not in projects:
        st.session_state.selected_project = projects[0]

    current_index = projects.index(st.session_state.selected_project)

    # Seletor Principal
    selected_project = st.sidebar.selectbox(
        "Selecione um Projeto Ativo",
        options=projects,
        index=current_index,
        key="project_selector"
    )
    st.session_state.selected_project = selected_project

    # --- NOVIDADE: GERENCIAR PROJETO SELECIONADO ---
    with st.sidebar.expander("⚙️ Configurações do Projeto"):
        st.subheader("Renomear Projeto")
        new_name_input = st.text_input("Novo nome", value=selected_project)
        
        if st.button("Confirmar Renomeação", use_container_width=True):
            if new_name_input and new_name_input != selected_project:
                success, message = rename_project(selected_project, new_name_input)
                if success:
                    # Atualiza o session_state para o novo nome imediatamente
                    st.session_state.selected_project = new_name_input
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Informe um nome diferente do atual.")

    # --- Seção de Exportação ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Exportação")
    if st.session_state.selected_project:
        project_active = st.session_state.selected_project
        try:
            excel_data = export_project_to_excel(project_active)
            st.sidebar.download_button(
                label="Baixar Excel do Projeto",
                data=excel_data,
                file_name=f"Backup_{project_active}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.sidebar.error(f"Erro no Excel: {e}")

# ---------- Helpers ----------
def ensure_project_structure(project_name):
    base = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "bugs"), exist_ok=True)
    os.makedirs(os.path.join(base, "test_suites"), exist_ok=True)
    os.makedirs(os.path.join(base, "user_stories"), exist_ok=True)
    os.makedirs(os.path.join(base, "executions"), exist_ok=True)
    os.makedirs(os.path.join(base, "notes"), exist_ok=True) # <-- ADICIONE ESTA LINHA

def _json_load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            # Lida com arquivo vazio
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []

def _json_save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)

# ---------- Projects ----------
def get_project_list():
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)
    return [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]

load_projects = get_project_list

# ---------- Bugs ----------
def load_bugs(project_name):
    ensure_project_structure(project_name)
    path = os.path.join(PROJECTS_DIR, project_name, "bugs.json")
    columns = ['id', 'titulo', 'tela', 'modulo', 'descricao', 'comportamento_ideal', 'comportamento_atual', 'bdd', 'status', 'data_criacao']
    data = _json_load(path)
    if not data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = ''
    return df[columns]

def save_bugs(project_name, df):
    ensure_project_structure(project_name)
    path = os.path.join(PROJECTS_DIR, project_name, "bugs.json")
    records = df.to_dict(orient="records")
    _json_save(path, records)

# ---------- Validations ----------
def load_validations(project_name):
    ensure_project_structure(project_name)
    path = os.path.join(PROJECTS_DIR, project_name, "validations.json")
    return _json_load(path)

def save_validation(project_name, bug_id, report_text, new_status):
    ensure_project_structure(project_name)
    validations = load_validations(project_name)
    new_validation = {
        "bug_id": bug_id, "status": new_status, "report": report_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    validations.append(new_validation)
    path = os.path.join(PROJECTS_DIR, project_name, "validations.json")
    _json_save(path, validations)

# ---------- Test Suites & Cases ----------
def get_test_suites(project_name):
    ensure_project_structure(project_name)
    suites_path = os.path.join(PROJECTS_DIR, project_name, "test_suites")
    return [d for d in os.listdir(suites_path) if os.path.isdir(os.path.join(suites_path, d))]

load_test_suites = get_test_suites

# --- INÍCIO DA VERSÃO CORRIGIDA E DEFINITIVA ---
def load_test_cases(project, suite):
    ensure_project_structure(project)
    file_path = os.path.join(PROJECTS_DIR, project, "test_suites", suite, "cases.json")
    
    # Esta é a lista completa de colunas que seu aplicativo espera.
    # Incluindo as novas e as antigas para migração.
    expected_cols = [
        "id", "id_case", "titulo", "objetivo", "requisitos", "precondicoes", "dados",
        "passos", "resultado_esperado", "criterio", "tipo", "prioridade", "tags",
        "ambiente", "automatizavel", "notas", "autor", "data_criacao",
        "status_execucao", "bug_id_relacionado", "modulo", "status",
        "report_bug_execucao_test_case"  # <- NOVA COLUNA
    ]

    data = _json_load(file_path)
    if not data:
        return pd.DataFrame(columns=expected_cols)

    if isinstance(data, dict):
        data = [data]

    df = pd.DataFrame(data)
    
    # Garante que todas as colunas esperadas existam, preenchendo com string vazia
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
            
    # Força TODAS as colunas para o tipo string para evitar NaN e problemas de tipo.
    # Esta é a correção chave para o 'modulo' e outros campos não aparecerem.
    for col in df.columns:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '')

    return df

def save_test_cases(project, suite, df):
    ensure_project_structure(project)
    file_path = os.path.join(PROJECTS_DIR, project, "test_suites", suite, "cases.json")
    
    # Antes de salvar, converte a coluna 'automatizavel' de volta para um booleano real.
    # Isso mantém seus dados no JSON limpos.
    if 'automatizavel' in df.columns:
        df['automatizavel'] = df['automatizavel'].apply(lambda x: str(x).lower() in ['true', '1', 'yes', 't'])
        
    # Remove a coluna antiga 'status_execucao' permanentemente antes de salvar.
    if 'status_execucao' in df.columns:
        df = df.drop(columns=['status_execucao'], errors='ignore')

    records = df.to_dict(orient="records")
    _json_save(file_path, records)
# --- FIM DA VERSÃO CORRIGIDA E DEFINITIVA ---


def get_all_test_cases(project_name):
    ensure_project_structure(project_name)
    all_cases = pd.DataFrame()
    suites = get_test_suites(project_name)
    for suite in suites:
        df = load_test_cases(project_name, suite)
        all_cases = pd.concat([all_cases, df], ignore_index=True)
    return all_cases

def create_test_suite(project, suite_name, description=""):
    ensure_project_structure(project)
    suite_path = os.path.join(PROJECTS_DIR, project, "test_suites", suite_name)
    os.makedirs(suite_path, exist_ok=True)
    meta_path = os.path.join(suite_path, "suite_info.json")
    info = {"nome": suite_name, "descricao": description, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    _json_save(meta_path, info)
    # Cria um arquivo 'cases.json' vazio para a nova suíte
    _json_save(os.path.join(suite_path, "cases.json"), [])
    return True

def load_suite_info(project, suite_name):
    meta_path = os.path.join(PROJECTS_DIR, project, "test_suites", suite_name, "suite_info.json")
    return _json_load(meta_path) or {"nome": suite_name, "descricao": ""}

def delete_test_suite(project, suite_name):
    suite_path = os.path.join(PROJECTS_DIR, project, "test_suites", suite_name)
    if os.path.exists(suite_path):
        shutil.rmtree(suite_path)
        return True
    return False

# ---------- User Stories, Acceptance Criteria, Scenarios... (o resto do seu código)
# ... (cole todo o resto do seu código original aqui sem alterações) ...
def create_user_story(project, story):
    ensure_project_structure(project)
    stories = load_user_stories(project)
    if "id" not in story or not story["id"]:
        story["id"] = str(uuid.uuid4())[:8]
    story.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    stories.append(story)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "stories.json")
    _json_save(path, stories)
    return story

def load_user_stories(project):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "stories.json")
    return _json_load(path)

def save_user_stories(project, stories_list):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "stories.json")
    _json_save(path, stories_list)

def delete_user_story(project, story_id):
    stories = load_user_stories(project)
    new = [s for s in stories if s.get("id") != story_id]
    save_user_stories(project, new)
    return True

def create_acceptance_criteria(project, story_id, criteria):
    ensure_project_structure(project)
    all_criteria = load_acceptance_criteria(project)
    if "id" not in criteria or not criteria["id"]:
        criteria["id"] = str(uuid.uuid4())[:8]
    criteria["story_id"] = story_id
    criteria.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    all_criteria.append(criteria)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "criteria.json")
    _json_save(path, all_criteria)
    return criteria

def load_acceptance_criteria(project):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "criteria.json")
    return _json_load(path)

def load_criteria_by_story(project, story_id):
    return [c for c in load_acceptance_criteria(project) if c.get("story_id") == story_id]

def save_acceptance_criteria(project, criteria_list):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "criteria.json")
    _json_save(path, criteria_list)

def delete_acceptance_criteria(project, criteria_id):
    crits = load_acceptance_criteria(project)
    new = [c for c in crits if c.get("id") != criteria_id]
    save_acceptance_criteria(project, new)
    return True

def create_scenario(project, criteria_id, scenario):
    ensure_project_structure(project)
    scenarios = load_scenarios(project)
    if "id" not in scenario or not scenario["id"]:
        scenario["id"] = str(uuid.uuid4())[:8]
    scenario["criteria_id"] = criteria_id
    scenario.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    scenarios.append(scenario)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "scenarios.json")
    _json_save(path, scenarios)
    return scenario

def load_scenarios(project):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "scenarios.json")
    return _json_load(path)

def load_scenarios_by_criteria(project, criteria_id):
    return [s for s in load_scenarios(project) if s.get("criteria_id") == criteria_id]

def save_scenarios(project, scenarios_list):
    ensure_project_structure(project)
    path = os.path.join(PROJECTS_DIR, project, "user_stories", "scenarios.json")
    _json_save(path, scenarios_list)

def delete_scenario(project, scenario_id):
    scs = load_scenarios(project)
    new = [s for s in scs if s.get("id") != scenario_id]
    save_scenarios(project, new)
    return True

def auto_generate_cases_from_scenario(project, suite_name, scenario, n_cases=1):
    ensure_project_structure(project)
    df = load_test_cases(project, suite_name)
    numeric_ids = pd.to_numeric(df['id'], errors='coerce').dropna()
    next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1
    created = []
    for i in range(n_cases):
        case = {
            "id": next_id, "id_case": f"TC-{next_id}", "titulo": f"CT {scenario.get('id')} - {scenario.get('title', 'Caso gerado')}",
            "objetivo": f"Validar cenário: {scenario.get('title')}", "requisitos": [], "precondicoes": scenario.get('preconditions', ''),
            "dados": scenario.get('data_inputs', ''), "passos": scenario.get('steps', "1. " + (scenario.get('steps') or "Executar passos do cenário")),
            "resultado_esperado": scenario.get('expected', ''), "criterio": scenario.get('criteria_id'), "tipo": "Funcional",
            "prioridade": "Média", "tags": [], "ambiente": "staging", "automatizavel": True,
            "notas": "Caso gerado automaticamente a partir do cenário.", "autor": "system", "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status_execucao": "Não Executado", "bug_id_relacionado": ""
        }
        df = pd.concat([df, pd.DataFrame([case])], ignore_index=True)
        created.append(case)
        next_id += 1
    save_test_cases(project, suite_name, df)
    return created


def get_project_notes_path(project):
    return os.path.join(PROJECTS_DIR, project, "notes", "notes.json")


def load_project_notes(project):
    path = get_project_notes_path(project)
    if not os.path.exists(path):
        return {"content": "", "last_update": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_project_notes(project, content):
    path = get_project_notes_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "content": content,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def export_project_to_excel(project_name):
    """Gera um buffer de memória contendo um Excel com todos os dados do projeto."""
    
    # 1. Carregar todos os dados
    bugs_df = load_bugs(project_name)
    test_cases_df = get_all_test_cases(project_name)
    validations = load_validations(project_name)
    stories = load_user_stories(project_name)
    criteria = load_acceptance_criteria(project_name)
    scenarios = load_scenarios(project_name)
    notes = load_project_notes(project_name)

    # Converter listas simples para DataFrames
    validations_df = pd.DataFrame(validations)
    stories_df = pd.DataFrame(stories)
    criteria_df = pd.DataFrame(criteria)
    scenarios_df = pd.DataFrame(scenarios)
    notes_df = pd.DataFrame([notes]) # Transforma nota única em linha

    # 2. Criar um buffer de bytes para o Excel
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Salvar cada DF em uma aba
        if not bugs_df.empty:
            bugs_df.to_excel(writer, sheet_name='Bugs', index=False)
        
        if not test_cases_df.empty:
            test_cases_df.to_excel(writer, sheet_name='Casos de Teste', index=False)
            
        if not stories_df.empty:
            stories_df.to_excel(writer, sheet_name='User Stories', index=False)
            
        if not criteria_df.empty:
            criteria_df.to_excel(writer, sheet_name='Critérios Aceite', index=False)
            
        if not scenarios_df.empty:
            scenarios_df.to_excel(writer, sheet_name='Cenários BDD', index=False)
            
        if not validations_df.empty:
            validations_df.to_excel(writer, sheet_name='Histórico Validações', index=False)
            
        notes_df.to_excel(writer, sheet_name='Notas do Projeto', index=False)

    return output.getvalue()

def rename_project(old_name, new_name):
    """Renomeia a pasta do projeto no sistema de arquivos."""
    if not new_name or old_name == new_name:
        return False, "Nome inválido ou igual ao atual."

    old_path = os.path.join(PROJECTS_DIR, old_name)
    new_path = os.path.join(PROJECTS_DIR, new_name)

    if os.path.exists(new_path):
        return False, "Já existe um projeto com esse novo nome."

    try:
        os.rename(old_path, new_path)
        return True, "Projeto renomeado com sucesso!"
    except Exception as e:
        return False, f"Erro ao renomear: {e}"

def delete_project(project_name):
    """Exclui permanentemente a pasta do projeto."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    if os.path.exists(project_path):
        try:
            shutil.rmtree(project_path)
            return True, f"Projeto '{project_name}' excluído com sucesso."
        except Exception as e:
            return False, f"Erro ao excluir pasta: {e}"
        return False, "Projeto não encontrado."

import os
import json
import openai
import pandas as pd
import shutil
from datetime import datetime
import uuid
import streamlit as st
import io

# ---------- Constantes ----------
PROJECTS_DIR = "projects"

def export_project_to_excel(project_name):
    """Gera um Excel em PT-BR com formatação Profissional."""
    bugs_df = load_bugs(project_name)
    test_cases_df = get_all_test_cases(project_name)
    validations = load_validations(project_name)
    notes = load_project_notes(project_name)

    def clean_text(val):
        if pd.isna(val) or val is None or val == 0 or str(val).strip() in ['0', '0.0', 'nan', 'None']:
            return ""
        return str(val)

    # Limpeza de dados
    if not bugs_df.empty:
        for col in bugs_df.columns: bugs_df[col] = bugs_df[col].apply(clean_text)
    
    validations_df = pd.DataFrame(validations)
    if not validations_df.empty:
        for col in validations_df.columns: validations_df[col] = validations_df[col].apply(clean_text)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Escreve os dados
        bugs_df.to_excel(writer, sheet_name='Bugs', index=False)
        validations_df.to_excel(writer, sheet_name='Histórico Validações', index=False)
        pd.DataFrame(test_cases_df).to_excel(writer, sheet_name='Casos de Teste', index=False)
        pd.DataFrame([notes]).to_excel(writer, sheet_name='Notas do Projeto', index=False)

        # --- FORMATAÇÃO VISUAL ---
        workbook = writer.book
        
        # Estilo do Cabeçalho (Azul escuro com texto branco)
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'fg_color': '#1F4E78', 'font_color': '#FFFFFF', 'border': 1
        })

        # Estilo das Células (Texto à esquerda, centralizado verticalmente)
        cell_format = workbook.add_format({
            'text_wrap': True, 'valign': 'vcenter', 'align': 'left', 'border': 1
        })

        # Estilo Centralizado (Para IDs, Datas e Status)
        center_format = workbook.add_format({
            'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'border': 1
        })

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            # Pegar o dataframe correspondente para saber o número de colunas
            df = bugs_df if sheet_name == 'Bugs' else (validations_df if sheet_name == 'Histórico Validações' else pd.DataFrame())
            
            # Aplicar formato de cabeçalho
            for col_num, value in enumerate(df.columns if not df.empty else []):
                worksheet.write(0, col_num, value, header_format)

            # Ajustar larguras e alinhamentos específicos para a aba de BUGS
            if sheet_name == 'Bugs':
                worksheet.set_column('A:A', 8, center_format)   # ID
                worksheet.set_column('B:B', 35, cell_format)    # Título
                worksheet.set_column('C:D', 25, cell_format)    # Tela/Módulo
                worksheet.set_column('E:G', 45, cell_format)    # Descrição/Ideal/Atual
                worksheet.set_column('H:H', 40, cell_format)    # BDD
                worksheet.set_column('I:K', 15, center_format)  # Status/Sev/Pri
                worksheet.set_column('L:L', 18, center_format)  # Data
            else:
                worksheet.set_column('A:Z', 25, cell_format)

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



#------------
def generate_pro_title_with_gpt(raw_text):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Você é um QA Senior especializado em escrita técnica. 
        Transforme o rascunho aprendetado (oide ser sugestao, definicaçõ de regra de negocio, ou report bug) abaixo em um título  profissional, técnico e conciso (em português).
        
        Regras:
        1. Comece com a ação,  problema principal.
        2. Seja específico sobre onde ocorre.
        3. Remova palavras desnecessárias como "Eu acho que", "Sugestão".
        
        Rascunho: {raw_text}
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return None
# ---------- Helpers ----------


#transcript to englsih 

def translate_bug_to_english_with_gpt(titulo, descricao, atual, ideal, bdd):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Você é um tradutor técnico especializado em Quality Assurance. 
        Traduza os seguintes campos de um relatório de bug para o Inglês Técnico. 
        Mantenha a terminologia correta de QA (ex: 'comportamento atual' para 'actual behavior').
        Retorne um objeto JSON com as chaves: "titulo", "descricao", "atual", "ideal", "bdd".
        
        Originais:
        - Título: {titulo}
        - Descrição: {descricao}
        - Atual: {atual}
        - Ideal: {ideal}
        - BDD: {bdd}
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na tradução: {e}"); return None

def handle_translate_bug():
    """Tradução para o modo de EDIÇÃO (usa as keys 'edit_...')"""
    # Coleta o que está atualmente nos campos da tela
    t = st.session_state.get("edit_titulo", "")
    d = st.session_state.get("edit_descricao", "")
    a = st.session_state.get("edit_atual", "")
    i = st.session_state.get("edit_ideal", "")
    b = st.session_state.get("edit_bdd", "")

    with st.spinner("🌎 Traduzindo..."):
        translated = translate_bug_to_english_with_gpt(t, d, a, i, b)
        if translated:
            # Atualiza o session_state (isso muda o texto na tela)
            st.session_state.edit_titulo = translated.get("titulo")
            st.session_state.edit_descricao = translated.get("descricao")
            st.session_state.edit_atual = translated.get("atual")
            st.session_state.edit_ideal = translated.get("ideal")
            st.session_state.edit_bdd = translated.get("bdd")
            st.toast("Traduzido!")

def handle_translate_new_bug():
    """Tradução para o modo de REVISÃO IA (usa o dicionário 'bug_analysis_result')"""
    data = st.session_state.bug_analysis_result
    with st.spinner("🌎 Traduzindo..."):
        translated = translate_bug_to_english_with_gpt(
            data.get("titulo_melhorado", ""),
            str(data.get("descricao_melhorada", "")),
            data.get("comportamento_atual_refinado", ""),
            data.get("comportamento_ideal_sugerido", ""),
            data.get("cenario_bdd", "")
        )
        if translated:
            # Atualiza o objeto de análise para que a tela mude no rerun
            st.session_state.bug_analysis_result = {
                "titulo_melhorado": translated.get("titulo"),
                "descricao_melhorada": translated.get("descricao"),
                "comportamento_atual_refinado": translated.get("atual"),
                "comportamento_ideal_sugerido": translated.get("ideal"),
                "cenario_bdd": translated.get("bdd")
            }
            st.toast("Relatório traduzido!")
# No topo do utils.py, adicione este import se não tiver:

def ensure_project_structure(project_name):
    base = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "bugs"), exist_ok=True)
    os.makedirs(os.path.join(base, "test_suites"), exist_ok=True)
    os.makedirs(os.path.join(base, "user_stories"), exist_ok=True)
    os.makedirs(os.path.join(base, "executions"), exist_ok=True)
    os.makedirs(os.path.join(base, "notes"), exist_ok=True)
    os.makedirs(os.path.join(base, "evidence"), exist_ok=True) # Essencial para não dar erro

def save_evidence(project, bug_id, uploaded_files):
    evidence_path = os.path.join(PROJECTS_DIR, project, "evidence", str(bug_id))
    os.makedirs(evidence_path, exist_ok=True)
    for file in uploaded_files:
        file_path = os.path.join(evidence_path, file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
    return True

def get_evidence_files(project, bug_id):
    evidence_path = os.path.join(PROJECTS_DIR, project, "evidence", str(bug_id))
    if not os.path.exists(evidence_path): return []
    return [os.path.join(evidence_path, f) for f in os.listdir(evidence_path)]

def delete_evidence_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

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

def delete_bug(project_name, bug_id):
    """Remove o bug do JSON e deleta suas evidências físicas."""
    # 1. Carrega os bugs atuais
    df = load_bugs(project_name)
    
    # 2. Filtra para remover o bug com o ID selecionado
    df = df[df['id'] != bug_id]
    
    # 3. Salva a nova lista no JSON
    save_bugs(project_name, df)
    
    # 4. Deleta a pasta de evidências (fotos/vídeos) do bug
    evidence_path = os.path.join(PROJECTS_DIR, project_name, "evidence", str(bug_id))
    if os.path.exists(evidence_path):
        shutil.rmtree(evidence_path)
        
    return True


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
    """Carrega todas as notas do projeto como uma lista."""
    path = os.path.join(PROJECTS_DIR, project, "notes", "notes.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Suporte para migração: se for o formato antigo (dict), converte para lista
            if isinstance(data, dict):
                return [{"id": str(uuid.uuid4())[:8], "content": data.get("content", ""), "color": "#fff9c4", "date": data.get("last_update", "")}]
            return data
    except:
        return []

def delete_project_note(project, note_id):
    """Remove uma nota específica pelo ID."""
    notes = load_project_notes(project)
    notes = [n for n in notes if n['id'] != note_id]
    path = os.path.join(PROJECTS_DIR, project, "notes", "notes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    return True

def add_project_note(project, content, color="#fff9c4"):
    """Adiciona uma nova nota ao projeto."""
    notes = load_project_notes(project)
    new_note = {
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "color": color,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    notes.append(new_note)
    path = os.path.join(PROJECTS_DIR, project, "notes", "notes.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    return True

def update_project_note(project, note_id, new_content, new_color):
    """Atualiza o conteúdo e a cor de uma nota existente."""
    notes = load_project_notes(project)
    for note in notes:
        if note['id'] == note_id:
            note['content'] = new_content
            note['color'] = new_color
            note['date'] = datetime.now().strftime("%d/%m/%Y %H:%M") + " (editada)"
            break
    
    path = os.path.join(PROJECTS_DIR, project, "notes", "notes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    return True

def save_project_notes(project, content):
    path = get_project_notes_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "content": content,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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

def export_project_to_excel_en(project_name):
    """Gera um Excel em EN com Formatação Condicional e correção de colunas."""
    bugs_df = load_bugs(project_name)
    test_cases_df = get_all_test_cases(project_name)
    validations = load_validations(project_name)

    def clean_text(val):
        if pd.isna(val) or val is None or val == 0 or str(val).strip() in ['0', '0.0', 'nan', 'None']:
            return ""
        return str(val)

    map_values = {
        "Crítico": "Critical", "Alto": "High", "Médio": "Medium", "Baixo": "Low",
        "Novo": "New", "Mapeado": "Mapped", "No Jira": "Passed to Developers", 
        "Em Teste": "Testing", "Reprovado": "Failed", "Arrumado": "Fixed", "Aprovado": "Approved"
    }

    # --- PROCESSAMENTO DE BUGS ---
    if not bugs_df.empty:
        # Garante a existência das colunas antes da tradução para evitar KeyError
        if 'severidade' not in bugs_df.columns: bugs_df['severidade'] = 'Médio'
        if 'prioridade' not in bugs_df.columns: bugs_df['prioridade'] = 'P2'
        if 'status' not in bugs_df.columns: bugs_df['status'] = 'Novo'

        # Traduzir valores
        bugs_df['status'] = bugs_df['status'].map(map_values).fillna(bugs_df['status'])
        bugs_df['severidade'] = bugs_df['severidade'].map(map_values).fillna(bugs_df['severidade'])
        
        # Limpar todos os textos (preservando quebras de linha)
        for col in bugs_df.columns:
            bugs_df[col] = bugs_df[col].apply(clean_text)

        # Renomear Cabeçalhos para Inglês
        bugs_df = bugs_df.rename(columns={
            'id': 'ID', 'titulo': 'Title', 'tela': 'Screen', 'modulo': 'Module',
            'descricao': 'Steps', 'comportamento_ideal': 'Expected',
            'comportamento_atual': 'Actual', 'bdd': 'BDD',
            'status': 'Status', 'severidade': 'Severity', 'prioridade': 'Priority', 'data_criacao': 'Date'
        })

    # --- PROCESSAMENTO DE VALIDAÇÕES ---
    validations_df = pd.DataFrame(validations)
    if not validations_df.empty:
        if 'status' in validations_df.columns:
            validations_df['status'] = validations_df['status'].map(map_values).fillna(validations_df['status'])
        for col in validations_df.columns:
            validations_df[col] = validations_df[col].apply(clean_text)
        validations_df = validations_df.rename(columns={'bug_id': 'Bug ID', 'status': 'Status', 'report': 'Report', 'date': 'Date'})

    # --- GERAÇÃO DO EXCEL ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if not bugs_df.empty: bugs_df.to_excel(writer, sheet_name='Bugs Report', index=False)
        if not validations_df.empty: validations_df.to_excel(writer, sheet_name='Validation History', index=False)

        workbook = writer.book
        # Estilos Premium
        h_fmt = workbook.add_format({'bold':True, 'valign':'vcenter', 'align':'center', 'fg_color':'#1F4E78', 'font_color':'#FFFFFF', 'border':1})
        c_fmt = workbook.add_format({'text_wrap':True, 'valign':'vcenter', 'align':'left', 'border':1})
        mid_fmt = workbook.add_format({'text_wrap':True, 'valign':'vcenter', 'align':'center', 'border':1})
        
        # Cores Condicionais
        fmt_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1, 'align': 'center'})
        fmt_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1, 'align': 'center'})
        fmt_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500', 'border': 1, 'align': 'center'})

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            df = bugs_df if sheet_name == 'Bugs Report' else (validations_df if sheet_name == 'Validation History' else pd.DataFrame())
            
            if not df.empty:
                # Cabeçalhos
                for col_num, value in enumerate(df.columns):
                    worksheet.write(0, col_num, value, h_fmt)

                # Cores no Status
                try:
                    status_idx = df.columns.get_loc('Status')
                    r_col = f"{chr(65+status_idx)}2:{chr(65+status_idx)}1000"
                    worksheet.conditional_format(r_col, {'type': 'cell', 'criteria': 'equal to', 'value': '"Approved"', 'format': fmt_green})
                    worksheet.conditional_format(r_col, {'type': 'cell', 'criteria': 'equal to', 'value': '"Fixed"', 'format': fmt_green})
                    worksheet.conditional_format(r_col, {'type': 'cell', 'criteria': 'equal to', 'value': '"Failed"', 'format': fmt_red})
                    worksheet.conditional_format(r_col, {'type': 'cell', 'criteria': 'equal to', 'value': '"Testing"', 'format': fmt_yellow})
                except: pass

                worksheet.set_column('A:Z', 25, c_fmt)

    return output.getvalue()
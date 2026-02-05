# pages/3_Scenarios.py
import streamlit as st
import json
import re
from utils import (
    render_sidebar,
    load_user_stories,
    load_acceptance_criteria,
    create_scenario,
    load_scenarios,
    delete_scenario
)
from openai import OpenAI

st.set_page_config(page_title="Cenários de Teste", layout="wide")
render_sidebar()
st.title("🧩 Cenários de Teste (do Critério para Caso)")

# --- Inicialização de Estado ---
if "new_scenario_title" not in st.session_state:
    st.session_state.new_scenario_title = ""
if "new_scenario_steps" not in st.session_state:
    st.session_state.new_scenario_steps = ""
if "new_scenario_expected" not in st.session_state:
    st.session_state.new_scenario_expected = ""
if "new_scenario_preconditions" not in st.session_state:
    st.session_state.new_scenario_preconditions = ""


# ---- Funções de Callback ----

def autofill_from_criterion():
    """Callback para preencher automaticamente os campos quando o critério muda."""
    selected_key = st.session_state.get("selected_criterion_for_scenario")
    if not selected_key:
        return

    crit_id = crit_map.get(selected_key)
    criterion = next((c for c in criteria if c.get('id') == crit_id), None)
    
    if criterion:
        description = criterion.get("description", "")
        st.session_state.new_scenario_title = description
        
        match = re.search(r'(?:Then|Então)\s*(.*)', description, re.IGNORECASE | re.DOTALL)
        if match:
            st.session_state.new_scenario_expected = match.group(1).strip()
        else:
            st.session_state.new_scenario_expected = ""
        
        st.session_state.new_scenario_steps = ""
        st.session_state.new_scenario_preconditions = ""

def handle_ai_scenario_generation():
    """Gera um cenário de teste completo com base no critério selecionado."""
    selected_crit_key = st.session_state.get("selected_criterion_for_scenario")
    title_idea = st.session_state.get("new_scenario_title", "")

    if not selected_crit_key:
        st.error("Por favor, selecione um critério de aceitação como base.")
        return

    criteria_id = crit_map.get(selected_crit_key)
    criterion_context = next((c for c in criteria if c.get('id') == criteria_id), None)
    if not criterion_context:
        st.error("Critério selecionado não foi encontrado.")
        return

    try:
        with st.spinner("Gerando sugestões de cenário com IA..."):
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            prompt = f"""
Você é um analista de QA sênior. Com base no critério de aceitação, gere um cenário de teste detalhado.
Critério de Aceitação: "{criterion_context.get('description', '')}"
Ideia para o título: "{title_idea}"
Retorne um JSON válido com chaves: "title", "steps", "expected_result".
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content.strip()
            ai_result = json.loads(text)

            if isinstance(ai_result.get("title"), str):
                st.session_state.new_scenario_title = ai_result.get("title")
            if isinstance(ai_result.get("steps"), str):
                st.session_state.new_scenario_steps = ai_result.get("steps")
            if isinstance(ai_result.get("expected_result"), str):
                st.session_state.new_scenario_expected = ai_result.get("expected_result")
            
            st.success("✅ Cenário sugerido pela IA! Os campos foram preenchidos.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a IA: {e}")

def handle_create_scenario():
    """Callback para o botão 'Criar Cenário'."""
    title = st.session_state.get("new_scenario_title", "")
    if not st.session_state.get("selected_criterion_for_scenario") or not title.strip():
        st.error("Selecione um critério e preencha o Título do Cenário.")
        return

    criteria_id = crit_map.get(st.session_state.get("selected_criterion_for_scenario"))
    scenario = {
        "title": title,
        "steps": st.session_state.get("new_scenario_steps", ""),
        "expected": st.session_state.get("new_scenario_expected", ""),
        "preconditions": st.session_state.get("new_scenario_preconditions", "")
    }
    create_scenario(project, criteria_id, scenario)
    st.success("Cenário criado com sucesso!")

    st.session_state.new_scenario_title = ""
    st.session_state.new_scenario_steps = ""
    st.session_state.new_scenario_expected = ""
    st.session_state.new_scenario_preconditions = ""


# ---- Lógica Principal da Página ----

if 'selected_project' not in st.session_state:
    st.warning("Selecione um projeto na sidebar."); st.stop()

project = st.session_state.selected_project
st.subheader(f"Projeto: {project}")

stories = load_user_stories(project)
criteria = load_acceptance_criteria(project)
scenarios = load_scenarios(project)

if not criteria:
    st.info("Nenhum critério de aceitação encontrado. Crie um na página anterior.")
else:
    crit_map = {f"{str(c.get('id', ''))[:8]} - {c.get('description', '')[:80]}...": c.get('id') for c in criteria}

    with st.expander("➕ Criar Novo Cenário", expanded=True):
        # --- CORREÇÃO: O SELECTBOX FICA FORA DO FORMULÁRIO ---
        st.selectbox(
            "1. Selecione um Critério para começar (isso irá pré-preencher os campos)",
            options=list(crit_map.keys()),
            key="selected_criterion_for_scenario",
            on_change=autofill_from_criterion,
            index=None, # Permite que a seleção comece vazia
            placeholder="Selecione um critério..."
        )
        
        # O resto dos campos e botões permanecem dentro do formulário
        with st.form("create_scenario"):
            st.markdown("---")
            st.markdown("2. Complete ou ajuste os detalhes do cenário abaixo:")
            st.text_input("Título do Cenário *", key="new_scenario_title")
            st.text_area("Passos (um por linha)", key="new_scenario_steps", height=150)
            st.text_area("Resultado Esperado", key="new_scenario_expected", height=100)
            st.text_area("Pré-condições (opcional)", key="new_scenario_preconditions")

            col1, col2, _ = st.columns([0.35, 0.3, 0.35])
            with col1:
                st.form_submit_button("✨ Analisar e Sugerir com IA", on_click=handle_ai_scenario_generation, use_container_width=True)
            with col2:
                st.form_submit_button("💾 Criar Cenário", on_click=handle_create_scenario, type="primary", use_container_width=True)

st.markdown("---")
st.subheader("📋 Cenários de Teste Existentes")

if not scenarios:
    st.info("Nenhum cenário de teste cadastrado para este projeto.")
else:
    criteria_with_scenarios = {c.get('id'): {**c, 'scenarios': []} for c in criteria}
    for s in scenarios:
        if s.get('criteria_id') in criteria_with_scenarios:
            criteria_with_scenarios[s.get('criteria_id')]['scenarios'].append(s)

    for crit_id, crit_data in criteria_with_scenarios.items():
        if crit_data['scenarios']:
            display_id = str(crit_id)[:8]
            st.markdown(f"#### Critério: `{display_id}` - {crit_data.get('description', '')[:90]}...")
            for s in crit_data['scenarios']:
                with st.container(border=True):
                    col_desc, col_btn = st.columns([0.9, 0.1])
                    with col_desc:
                        st.markdown(f"**Cenário (ID: {str(s.get('id'))[:8]})**: {s.get('title')}")
                        st.text("Passos:")
                        st.code(s.get('steps', ''), language='gherkin')
                        st.text("Resultado Esperado:")
                        st.info(s.get('expected', ''))
                    with col_btn:
                        if st.button("🗑️", key=f"del_scenario_{s.get('id')}", help="Excluir Cenário"):
                            delete_scenario(project, s.get('id'))
                            st.rerun()
            st.markdown("---")
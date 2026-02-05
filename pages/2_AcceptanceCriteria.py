# pages/2_AcceptanceCriteria.py
import streamlit as st
import json
from utils import (
    render_sidebar,
    load_user_stories,
    load_acceptance_criteria,
    create_acceptance_criteria,
    delete_acceptance_criteria
)
from openai import OpenAI

st.set_page_config(page_title="Critérios de Aceitação", layout="wide")
render_sidebar()
st.title("✅ Critérios de Aceitação")

# ---- Estados de sessão ----
if "new_criterion_description" not in st.session_state:
    st.session_state.new_criterion_description = ""
if "selected_story_for_criteria" not in st.session_state:
    st.session_state.selected_story_for_criteria = None

# ---- Funções de callback ----
def on_story_change():
    selected_story_key = st.session_state.get("selected_story_for_criteria")
    if not selected_story_key or not story_map:
        return
    story_id = story_map.get(selected_story_key)
    story_context = next((s for s in stories if s.get('id') == story_id), None)
    st.session_state.new_criterion_description = story_context.get("description", "") if story_context else ""

def handle_ai_criteria_analysis():
    description = st.session_state.get("new_criterion_description", "").strip()
    selected_story_key = st.session_state.get("selected_story_for_criteria")

    if not description:
        st.error("Insira a descrição do critério para análise.")
        return
    if not selected_story_key:
        st.error("Selecione uma história de usuário como contexto.")
        return

    story_id = story_map.get(selected_story_key)
    story_context = next((s for s in stories if s.get('id') == story_id), None)
    if not story_context:
        st.error("História selecionada não encontrada.")
        return

    prompt = f"""
Você é especialista em QA e BDD. Recebi um critério de aceitação e quero refiná-lo.
Contexto da História: "{story_context.get('title', '')}"
Critério Original: "{description}"

Regras:
- Estruture o critério em **Gherkin** (Dado, Quando, Então).
- Retorne um JSON com a chave "refined_criterion" contendo o critério em Gherkin.
- Se possível, inclua 'Feature' e 'Scenario' no texto.
- Não inclua explicações, apenas o critério refinado.

Exemplo de saída JSON:
{{
  "refined_criterion": "Feature: Login\\nScenario: Usuário válido\\nDado que o usuário está na tela de login\\nQuando ele insere credenciais válidas\\nEntão ele é redirecionado para o painel"
}}
"""

    try:
        with st.spinner("Analisando e refinando o critério com IA..."):
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content.strip()

            # Tentativa de converter JSON retornado
            try:
                ai_result = json.loads(text)
                refined = ai_result.get("refined_criterion", description)
            except json.JSONDecodeError:
                refined = text  # fallback para texto bruto

            st.session_state.new_criterion_description = refined
            st.success("✅ Critério refinado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao analisar com IA: {e}")
        st.session_state.new_criterion_description = description

def handle_create_criteria():
    description = st.session_state.get("new_criterion_description", "").strip()
    story_key = st.session_state.get("selected_story_for_criteria")
    if not story_key or not description:
        st.error("Selecione uma história e preencha a descrição do critério.")
        return

    story_id = story_map.get(story_key)
    create_acceptance_criteria(project, story_id, {
        "description": description,
        "type": st.session_state.get("new_criterion_type", "Funcional")
    })
    st.success("Critério criado com sucesso!")
    st.session_state.new_criterion_description = ""

# ---- Lógica Principal ----
if 'selected_project' not in st.session_state:
    st.warning("Selecione um projeto na sidebar."); st.stop()

project = st.session_state.selected_project
st.subheader(f"Projeto: {project}")

stories = load_user_stories(project)
criteria = load_acceptance_criteria(project)

if not stories:
    st.info("Nenhuma história de usuário encontrada. Crie uma na página 'User Stories' primeiro.")
else:
    story_map = {f"{str(s.get('id'))[:8]} - {s.get('title', '')}": s.get('id') for s in stories}

    with st.expander("➕ Criar Novo Critério", expanded=True):
        st.selectbox(
            "Selecione a História de Usuário para pré-preencher a descrição",
            options=list(story_map.keys()),
            key="selected_story_for_criteria",
            on_change=on_story_change,
            index=None,
            placeholder="Escolha uma história..."
        )

        with st.form("create_criteria"):
            selected_story_text = st.session_state.get('selected_story_for_criteria', 'Nenhuma')
            st.markdown(f"**História relacionada:** `{selected_story_text}`")

            st.text_area(
                "Descrição do Critério (Gherkin: Dado, Quando, Então)",
                key="new_criterion_description",
                height=150
            )
            st.selectbox("Tipo de Critério", ["Funcional", "Negócio", "UI"], key="new_criterion_type")

            col1, col2, _ = st.columns([0.3, 0.3, 0.4])
            with col1:
                st.form_submit_button("✨ Analisar com IA", on_click=handle_ai_criteria_analysis, use_container_width=True)
            with col2:
                st.form_submit_button("💾 Criar Critério", on_click=handle_create_criteria, type="primary", use_container_width=True)

st.markdown("---")
st.subheader("📋 Critérios de Aceitação Existentes")

if not criteria:
    st.info("Nenhum critério cadastrado para este projeto.")
else:
    stories_with_criteria = {s.get('id'): {**s, 'criteria': []} for s in stories}
    for c in criteria:
        if c.get('story_id') in stories_with_criteria:
            stories_with_criteria[c.get('story_id')]['criteria'].append(c)

    for story_id, story_data in stories_with_criteria.items():
        if story_data['criteria']:
            display_id = str(story_id)[:8]
            st.markdown(f"#### História: `{display_id}` - {story_data.get('title', 'Título não encontrado')}")
            for c in story_data['criteria']:
                with st.container():
                    col_desc, col_btn = st.columns([0.9, 0.1])
                    with col_desc:
                        st.markdown(f"**Critério (ID: {str(c.get('id'))[:8]})** - Tipo: `{c.get('type')}`")
                        st.code(c.get('description', ''), language='gherkin', line_numbers=True)
                    with col_btn:
                        if st.button("🗑️", key=f"del_crit_{c.get('id')}", help="Excluir Critério"):
                            delete_acceptance_criteria(project, c.get('id'))
                            st.rerun()
            st.markdown("---")

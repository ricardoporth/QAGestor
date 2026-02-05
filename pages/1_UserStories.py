# 📄 pages/1_UserStories.py
import streamlit as st
import json
from utils import (
    load_user_stories,
    create_user_story,
    save_user_stories,
    delete_user_story,
    render_sidebar
)
from openai import OpenAI

# ---- Configuração da página ----
st.set_page_config(page_title="Histórias de Usuário", layout="wide")
render_sidebar()
st.title("📘 User Stories (Histórias de Usuário)")

# ---- Funções de Callback ----

def handle_ai_analysis():
    """Callback para o botão 'Analisar'. Chama a IA e atualiza o estado."""
    description = st.session_state.get("new_description", "")
    if not description.strip():
        st.error("Por favor, insira uma descrição antes de enviar para análise.")
        return

    try:
        with st.spinner("Analisando e aprimorando com IA..."):
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            prompt = f"""
Melhore o texto abaixo mantendo a estrutura de uma história de usuário (Como... Quero... Para que...).
Retorne apenas JSON válido com as chaves "title" e "description".

Texto original:
{description}
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content.strip()
            ai_result = json.loads(text)

            st.session_state.new_title = ai_result.get("title", st.session_state.get("new_title", ""))
            st.session_state.new_description = ai_result.get("description", description)
            st.success("✅ Texto aprimorado! Os campos foram atualizados automaticamente.")

    except json.JSONDecodeError:
        st.warning("A IA retornou um formato inesperado.")
    except Exception as e:
        st.error(f"Erro ao chamar OpenAI: {e}")

def handle_create_story():
    """Callback para o botão 'Criar História'. Valida, cria e limpa o formulário."""
    title = st.session_state.get("new_title", "")
    if not title:
        st.error("O título é obrigatório.")
        return

    story = {
        "title": title,
        "description": st.session_state.get("new_description", ""),
        "priority": st.session_state.get("new_priority", "Média"),
        "owner": st.session_state.get("new_owner", ""),
        "status": st.session_state.get("new_status", "Backlog")
    }
    create_user_story(project, story)
    st.success("História criada com sucesso! 🎉")

    st.session_state.new_title = ""
    st.session_state.new_description = ""
    st.session_state.new_owner = ""

# ---- Lógica Principal da Página ----

if 'selected_project' not in st.session_state:
    st.warning("Selecione um projeto na barra lateral antes de continuar.")
    st.stop()

project = st.session_state.selected_project
st.subheader(f"Projeto: {project}")

stories = load_user_stories(project)

# VERSÃO CORRIGIDA COM CALLBACKS
with st.expander("➕ Criar Nova História", expanded=True):
    with st.form("create_story"):
        st.markdown("### ✏️ Nova História de Usuário")

        st.text_input("Título *", key="new_title")
        st.text_area("Descrição (Como / Quero / Para que)", key="new_description", height=150)
        st.selectbox("Prioridade", ["Alta", "Média", "Baixa"], index=1, key="new_priority")
        st.text_input("Stakeholder / Dono", key="new_owner")
        st.selectbox("Status", ["Backlog", "Em andamento", "Concluído"], index=0, key="new_status")

        col1, col2, _ = st.columns([0.3, 0.3, 0.4])
        with col1:
            st.form_submit_button(
                "✨ Analisar com IA",
                on_click=handle_ai_analysis, # Supondo que você tenha um callback para isso
                use_container_width=True
            )
        with col2:
            st.form_submit_button(
                "💾 Criar História",
                on_click=handle_create_story, # O callback que resolve o erro
                type="primary",
                use_container_width=True
            )
            
st.markdown("---")
st.subheader("📋 Histórias Existentes")

if not stories:
    st.info("Nenhuma história cadastrada ainda.")
else:
    # CORREÇÃO: Ordena os IDs como strings para suportar valores alfanuméricos
    stories_sorted = sorted(stories, key=lambda x: str(x.get('id', '')))
    for s in stories_sorted:
        with st.container(border=True):
            # Mostra apenas os 8 primeiros caracteres do ID para economizar espaço
            display_id = str(s.get('id', ''))[:8]
            st.markdown(f"##### ID: {display_id} — {s.get('title')}")
            if s.get('description'):
                st.markdown(s.get('description'))
            
            meta_cols = st.columns(3)
            meta_cols[0].markdown(f"**Prioridade:** `{s.get('priority', 'N/A')}`")
            meta_cols[1].markdown(f"**Status:** `{s.get('status', 'N/A')}`")
            meta_cols[2].markdown(f"**Dono:** `{s.get('owner', 'N/A')}`")
            
            btn_cols = st.columns([0.8, 0.1, 0.1])
            # Usa o ID completo na chave para garantir que seja único
            full_id = s.get('id')
            if btn_cols[1].button("🗑️", key=f"del_story_{full_id}", help="Excluir História"):
                delete_user_story(project, full_id)
                st.rerun()
            if btn_cols[2].button("✏️", key=f"edit_story_{full_id}", help="Editar História"):
                st.session_state.editing_story = s
                st.rerun()

if 'editing_story' in st.session_state:
    s = st.session_state.editing_story
    display_id = str(s.get('id', ''))[:8]
    @st.dialog(f"✏️ Editando História (ID: {display_id})")
    def edit_story_dialog():
        try:
            priority_index = ["Alta", "Média", "Baixa"].index(s.get('priority', "Média"))
            status_index = ["Backlog", "Em andamento", "Concluído"].index(s.get('status', "Backlog"))
        except ValueError:
            priority_index, status_index = 1, 0

        with st.form("edit_story_form_dialog"):
            title = st.text_input("Título", value=s.get('title'))
            description = st.text_area("Descrição", value=s.get('description'), height=150)
            priority = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"], index=priority_index)
            owner = st.text_input("Stakeholder / Dono", value=s.get('owner'))
            status = st.selectbox("Status", ["Backlog", "Em andamento", "Concluído"], index=status_index)

            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                current_stories = load_user_stories(project)
                for idx, item in enumerate(current_stories):
                    if item.get('id') == s.get('id'):
                        current_stories[idx].update({
                            "title": title, "description": description,
                            "priority": priority, "owner": owner, "status": status
                        })
                        break
                save_user_stories(project, current_stories)
                st.toast("História atualizada com sucesso!")
                del st.session_state['editing_story']
                st.rerun()

                # ADICIONE ESTA FUNÇÃO NO INÍCIO DO ARQUIVO pages/1_UserStories.py

def handle_create_story():
    """Callback para o botão 'Criar História'. Valida, cria e limpa o formulário."""
    title = st.session_state.get("new_title", "")
    if not title:
        st.error("O título é obrigatório.")
        return

    story = {
        "title": title,
        "description": st.session_state.get("new_description", ""),
        "priority": st.session_state.get("new_priority", "Média"),
        "owner": st.session_state.get("new_owner", ""),
        "status": st.session_state.get("new_status", "Backlog")
    }
    create_user_story(project, story)
    st.success("História criada com sucesso! 🎉")

    # Limpa os campos do formulário para a próxima entrada
    st.session_state.new_title = ""
    st.session_state.new_description = ""
    st.session_state.new_owner = ""

    edit_story_dialog()
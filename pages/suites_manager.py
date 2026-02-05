import streamlit as st
import os
from utils import load_projects, load_test_suites, create_test_suite, delete_test_suite, load_suite_info

st.set_page_config(page_title="Gerenciar Suítes de Teste", layout="wide")

st.title("🗂️ Gerenciador de Suítes de Teste")

# Seleção de Projeto
projects = load_projects()

if not projects:
    st.warning("Nenhum projeto encontrado. Crie a pasta 'projects/NomeProjeto' antes de continuar.")
else:
    project = st.selectbox("Selecione o Projeto", projects)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 Criar Nova Suíte")
        with st.form("form_create_suite", clear_on_submit=True):
            suite_name = st.text_input("Nome da Suíte *")
            description = st.text_area("Descrição (opcional)")
            create_btn = st.form_submit_button("➕ Criar Suíte")

            if create_btn and suite_name:
                create_test_suite(project, suite_name, description)
                st.success(f"✅ Suíte '{suite_name}' criada com sucesso!")
                st.rerun()

    with col2:
        st.subheader("⚙️ Suítes Existentes")
        suites = load_test_suites(project)
        if suites:
            for suite in suites:
                info = load_suite_info(project, suite)
                with st.expander(f"📁 {info['nome']}"):
                    st.write(f"📝 {info.get('descricao', 'Sem descrição.')}")
                    col_del, col_edit = st.columns(2)
                    with col_del:
                        if st.button(f"🗑️ Excluir '{suite}'", key=f"delete_{suite}"):
                            if delete_test_suite(project, suite):
                                st.warning(f"❌ Suíte '{suite}' excluída!")
                                st.rerun()
                    with col_edit:
                        st.info("✏️ Edição futura em desenvolvimento...")
        else:
            st.info("Nenhuma suíte de teste criada ainda.")

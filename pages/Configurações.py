import streamlit as st
from utils import (
    get_project_list, 
    rename_project, 
    delete_project, 
    export_project_to_excel,
    render_sidebar, export_project_to_excel_en
)

# Renderiza a sidebar para manter o seletor de projeto visível
render_sidebar()

st.title("⚙️ Configurações do Projeto")

if 'selected_project' not in st.session_state:
    st.warning("Selecione um projeto na barra lateral.")
    st.stop()

project = st.session_state.selected_project
st.subheader(f"Projeto Atual: {project}")

tab1, tab2, tab3 = st.tabs(["✏️ Renomear", "📥 Exportar", "🔥 Excluir"])

with tab1:
    st.write("### Alterar nome")
    new_name = st.text_input("Novo nome:", value=project)
    if st.button("Confirmar Renomeação"):
        success, msg = rename_project(project, new_name)
        if success:
            st.session_state.selected_project = new_name
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

with tab2:
    st.write("### 📥 Exportar Dados do Projeto")
    
    col_exp_pt, col_exp_en = st.columns(2)
    
    with col_exp_pt:
        st.info("Versão em Português (Original)")
        try:
            excel_pt = export_project_to_excel(project) # Sua função original corrigida
            st.download_button(
                label="🇧🇷 Baixar Planilha PT",
                data=excel_pt,
                file_name=f"Relatorio_{project}_PT.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erro: {e}")

    with col_exp_en:
        st.success("Versão em Inglês (Global)")
        try:
            excel_en = export_project_to_excel_en(project) # Nova função
            st.download_button(
                label="🇺🇸 Download EN Report",
                data=excel_en,
                file_name=f"Report_{project}_EN.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erro: {e}")


with tab3:
    st.write("### ⚠️ Zona de Perigo")
    st.error("A exclusão é permanente!")
    confirma = st.checkbox(f"Confirmo que desejo apagar o projeto {project}")
    
    if st.button("🔥 APAGAR PROJETO"):
        if confirma:
            if delete_project(project):
                st.success("Projeto excluído.")
                # Limpa a seleção e volta para o primeiro disponível
                projs = get_project_list()
                st.session_state.selected_project = projs[0] if projs else None
                st.rerun()
        else:
            st.warning("Marque a caixa de confirmação.")
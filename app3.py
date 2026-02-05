import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta
import json
import openai
import plotly.express as px

# Importa as funções do nosso arquivo de utilitários
from utils import (
    get_project_list,
    load_bugs,
    save_bugs,
    load_validations,
    save_validation, 
    get_all_test_cases,
    render_sidebar,
    load_project_notes,      # 👈 ADD
    save_project_notes       # 👈 ADD
)

from datetime import datetime, timedelta


def calcular_status_sla(data_criacao, severidade):
    try:
        if pd.isna(data_criacao):
            return "Sem data", "⚪"

        severidade = severidade if pd.notna(severidade) else "Médio"

        agora = datetime.now()
        prazo_sla = SLA_RULES.get(severidade)

        if not prazo_sla:
            return "Sem SLA", "⚪"

        tempo_decorrido = agora - data_criacao
        percentual_usado = tempo_decorrido / prazo_sla

        if percentual_usado < 0.7:
            return "Dentro do SLA", "🟢"
        elif percentual_usado < 1:
            return "Perto de estourar", "🟡"
        else:
            return "SLA estourado", "🔴"

    except Exception:
        # 🔥 GARANTIA ABSOLUTA
        return "Erro no SLA", "⚪"


SLA_RULES = {
    "Crítico": timedelta(hours=24),
    "Alto": timedelta(days=3),
    "Médio": timedelta(days=7),
    "Baixo": timedelta(days=14),
}


st.markdown("""
<style>
/* Caixa de notas amarela envolvendo o textarea */
div[data-testid="stTextArea"] textarea {
    background-color: #fff9c4;
    border-left: 6px solid #fbc02d;
    border-radius: 8px;
    padding: 14px;
    font-size: 15px;
}

/* Remove fundo branco externo */
div[data-testid="stTextArea"] {
    background: transparent;
}
</style>
""", unsafe_allow_html=True)


SEVERITY_OPTIONS = ["Crítico", "Alto", "Médio", "Baixo"]
PRIORITY_OPTIONS = ["P1", "P2", "P3"]

SEVERITY_COLORS = {
    "Crítico": "#ffebee",  # vermelho claro
    "Alto": "#fff3e0",     # laranja claro
    "Médio": "#fffde7",    # amarelo claro
    "Baixo": "#e8f5e9"     # verde claro
}

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard e Bugs", page_icon="🐞")

# --- Constantes ---
BUG_STATUS_OPTIONS = ["Novo", "Mapeado", "No Jira", "Em Teste", "Reprovado", "Arrumado", "Aprovado"]

# --- Funções de IA ---
def refine_bug_with_gpt(titulo, descricao, comp_atual, comp_ideal, severidade, priority, bdd_user_input):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Você é um especialista em Quality Assurance (QA) e BDD (Behavior-Driven Development).
        Sua tarefa é refinar um relatório de bug e gerar um cenário de teste em Gherkin (formato BDD) para ele.
        Retorne um objeto JSON com as chaves:
        - "titulo_melhorado": Um título curto e descritivo.
        - "descricao_melhorada": Uma lista de passos claros para reproduzir o bug.
        - "comportamento_atual_refinado": Uma descrição clara do que está acontecendo de errado.
        - "comportamento_ideal_sugerido": Uma descrição clara de como o sistema deveria se comportar.
        - "cenario_bdd": Um cenário de teste completo no formato Gherkin (Dado, Quando, Então).

        Bug Original:
        - Título: {titulo}
        - Descrição/Passos: {descricao}
        - Comportamento Atual: {comp_atual}
        - Comportamento Ideal (sugestão do usuário): {comp_ideal}
        - Severidade: {severidade}
        - Prioridade: {priority}
        -
        - Ideias para o BDD (do usuário): {bdd_user_input}
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na API da OpenAI: {e}"); return None

def refine_validation_report_with_gpt(report_text):
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        prompt = f"""
        Você é um especialista em redação técnica para equipes de desenvolvimento.
        Refine o seguinte relatório de validação de teste para que ele seja mais claro, profissional e bem estruturado. Mantenha o sentimento original (aprovado ou reprovado) e a formatação principal.

        Relatório Original:
        {report_text}
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro na API da OpenAI: {e}"); return report_text

# --- Funções de Callback ---
def start_editing_bug(bug_id): st.session_state.editing_bug_id = bug_id

def stop_editing():
    keys_to_clear = [
        'editing_bug_id', 'bug_analysis_result', 'bug_extras', 
        'bug_to_validate', 'validation_report_text', 'show_copy_dialog', 
        'bug_to_create_from_test_case',
        # Chaves de widget do formulário de edição
        'edit_titulo', 'edit_descricao', 'edit_ideal',
        'edit_atual', 'edit_bdd'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def set_bug_to_validate(bug_data, validation_type):
    st.session_state.bug_to_validate = bug_data; st.session_state.validation_type = validation_type

def show_text_in_dialog(text_to_show, title="Conteúdo para Cópia"):
    st.session_state.show_copy_dialog = True; st.session_state.text_for_dialog = text_to_show; st.session_state.title_for_dialog = title

def handle_refine_edited_bug():
    """Lê os dados do formulário, valida, chama a IA e ATUALIZA O ESTADO DOS WIDGETS DIRETAMENTE."""
    titulo = st.session_state.get("edit_titulo", "")
    descricao = st.session_state.get("edit_descricao", "")
    comp_atual = st.session_state.get("edit_atual", "")
    comp_ideal = st.session_state.get("edit_ideal", "")
    comp_severity = st.session_state.get("edit_severidade", "")
    comp_priority = st.session_state.get("edit_prioridade", "")

    bdd_input = st.session_state.get("edit_bdd", "")

    missing_fields = []
    if not descricao or not descricao.strip(): missing_fields.append("Descrição")
    if not comp_atual or not comp_atual.strip(): missing_fields.append("Atual")
    if not comp_ideal or not comp_ideal.strip(): missing_fields.append("Ideal")

    if missing_fields:
        field_names = ", ".join(missing_fields)
        st.warning(f"🤖 Para usar a IA, por favor, preencha os campos essenciais: **{field_names}**.")
        return

    with st.spinner("🤖 A IA está refinando os detalhes do bug..."):
        refined_data = refine_bug_with_gpt(
            titulo,
            descricao,
            comp_atual,
            comp_ideal,
            comp_severity,
            comp_priority,
            bdd_input
        )
        if refined_data:
            st.session_state.edit_titulo = refined_data.get("titulo_melhorado", titulo)
            desc_val = refined_data.get("descricao_melhorada", descricao)
            if isinstance(desc_val, list): desc_val = "\n".join(f"- {item}" for item in desc_val)
            st.session_state.edit_descricao = desc_val
            st.session_state.edit_atual = refined_data.get("comportamento_atual_refinado", comp_atual)
            st.session_state.edit_ideal = refined_data.get("comportamento_ideal_sugerido", comp_ideal)
            st.session_state.edit_bdd = refined_data.get("cenario_bdd", bdd_input)
            st.toast("Sugestões da IA aplicadas! Revise e salve.")
        else:
            st.error("Não foi possível obter sugestões da IA.")


# --- RENDERIZA A SIDEBAR ---
render_sidebar()


# --- Corpo Principal da Aplicação ---
st.title("🐞 Dashboard e Gerenciador de Bugs")

if 'selected_project' not in st.session_state:
    st.warning("Por favor, crie e/ou selecione um projeto na barra lateral.")
    st.stop()

project = st.session_state.selected_project
st.subheader(f"Projeto Ativo: {project}")

if 'bug_to_create_from_test_case' in st.session_state:
    bug_data = st.session_state.bug_to_create_from_test_case
    st.session_state.bug_analysis_result = {
        "titulo_melhorado": bug_data.get("titulo", ""),
        "descricao_melhorada": bug_data.get("descricao", "").split('\n'),
        "comportamento_atual_refinado": bug_data.get("comportamento_atual", ""),
        "comportamento_ideal_sugerido": bug_data.get("comportamento_ideal", ""),
        "cenario_bdd": bug_data.get("bdd", "")
    }
    st.session_state.bug_extras = { "tela": bug_data.get("tela", ""), "modulo": bug_data.get("modulo", "") }
    del st.session_state['bug_to_create_from_test_case']

if "bug_to_validate" in st.session_state:
    @st.dialog("Gerar Relatório de Validação de Teste")
    def validation_dialog():
        bug_data = st.session_state.bug_to_validate
        validation_type = st.session_state.validation_type
        bug_id = int(bug_data['id'])
        if "validation_report_text" not in st.session_state:
            if validation_type == "Aprovado":
                template = f"""[Validação de Teste - ✅ APROVADO]
Feature/Bug Testado: [{project}] - [{bug_data['tela']}] - {bug_data['titulo']}.
Resultado:
O teste foi executado no dia {datetime.now().strftime('%d/%m/%Y')} e a correção foi APROVADA com sucesso.
Detalhes:
O comportamento esperado '{bug_data['comportamento_ideal']}' foi observado. O problema original '{bug_data['comportamento_atual']}' não ocorre mais.
Nenhum efeito colateral (regressão) foi encontrado nos outros elementos da tela."""
            else:
                template = f"""[Validação de Teste - ❌ REPROVADO]
Feature/Bug Testado: [{project}] - [{bug_data['tela']}] - {bug_data['titulo']}.
Resultado:
O teste foi executado no dia {datetime.now().strftime('%d/%m/%Y')} e a correção foi REPROVADA.
Detalhes:
O problema original ainda ocorre. 
'{bug_data['comportamento_atual']}'


O comportamento esperado não foi atingido."""
            st.session_state.validation_report_text = template
        st.subheader(f"Relatório de Validação para o Bug ID: {bug_id}")
        edited_text = st.text_area("Edite o relatório abaixo:", value=st.session_state.validation_report_text, height=300)
        st.session_state.validation_report_text = edited_text
        col1, col2, col3 = st.columns([0.3, 0.4, 0.3])
        if col1.button("🤖 Melhorar com IA"):
            with st.spinner("Refinando relatório..."):
                st.session_state.validation_report_text = refine_validation_report_with_gpt(st.session_state.validation_report_text)
                st.rerun()
        if col2.button("✅ Salvar Validação", type="primary"):
            final_report = st.session_state.validation_report_text
            new_status = "Aprovado" if validation_type == "Aprovado" else "Reprovado"
            save_validation(project, bug_id, final_report, new_status)
            current_bugs_df = load_bugs(project)
            bug_index = current_bugs_df.index[current_bugs_df['id'] == bug_id].item()
            current_bugs_df.loc[bug_index, 'status'] = new_status
            save_bugs(project, current_bugs_df)
            st.toast(f"Validação do Bug {bug_id} salva!")
            stop_editing()
            st.rerun()
        if col3.button("Cancelar"):
            stop_editing()
            st.rerun()
    validation_dialog()

if st.session_state.get("show_copy_dialog", False):
    @st.dialog(st.session_state.get("title_for_dialog", "Conteúdo"))
    def show_copy_content():
        st.text_area("Selecione e copie o texto abaixo:", value=st.session_state.get("text_for_dialog", ""), height=250)
        if st.button("Fechar"):
            stop_editing()
            st.rerun()
    show_copy_content()

bugs_df = load_bugs(project)
tests_df = get_all_test_cases(project)

# Garante colunas obrigatórias
if "severidade" not in bugs_df.columns:
    bugs_df["severidade"] = "Médio"

bugs_df["severidade"] = bugs_df["severidade"].fillna("Médio")

bugs_df["data_criacao"] = pd.to_datetime(
    bugs_df["data_criacao"],
    errors="coerce"
)

if "prioridade" not in bugs_df.columns:
    bugs_df["prioridade"] = "P2"

validations = load_validations(project)

bugs_df["data_criacao"] = pd.to_datetime(
    bugs_df["data_criacao"],
    errors="coerce"
)

sla_result = bugs_df.apply(
    lambda row: calcular_status_sla(
        row["data_criacao"],
        row["severidade"]
    ),
    axis=1
)

bugs_df["status_sla"] = sla_result.apply(lambda x: x[0])
bugs_df["icone_sla"] = sla_result.apply(lambda x: x[1])


bugs_df["severidade"] = bugs_df.get("severidade", "Médio").fillna("Médio")
bugs_df[["status_sla", "icone_sla"]] = bugs_df.apply(
    lambda row: calcular_status_sla(
        row["data_criacao"],
        row["severidade"]
    ),
    axis=1,
    result_type="expand"
)



st.markdown("---")
st.subheader("📝 Notas do Projeto")

project_notes = load_project_notes(project)

notes_text = st.text_area(
    "Anotações do Projeto",
    value=project_notes.get("content", ""),
    height=200
)

col1, col2 = st.columns([0.2, 0.8])

if col1.button("💾 Salvar Notas"):
    save_project_notes(project, notes_text)
    st.toast("Notas do projeto salvas com sucesso!")

if project_notes.get("last_update"):
    col2.caption(f"Última atualização: {project_notes['last_update']}")


st.markdown("---")

if 'editing_bug_id' in st.session_state:
    bug_id = st.session_state.editing_bug_id
    bug_data = bugs_df[bugs_df['id'] == bug_id].iloc[0]
    st.subheader(f"Editando Bug ID: {int(bug_id)}")
    with st.form("edit_bug_form"):
        idx = BUG_STATUS_OPTIONS.index(bug_data['status']) if bug_data['status'] in BUG_STATUS_OPTIONS else 0
        titulo = st.text_input("Título", value=bug_data['titulo'], key="edit_titulo")
        status = st.selectbox("Status", BUG_STATUS_OPTIONS, index=idx)
        tela = st.text_input("Tela", value=bug_data['tela'])
        modulo = st.text_input("Módulo", value=bug_data['modulo'])
        descricao = st.text_area("Descrição", value=bug_data['descricao'], height=100, key="edit_descricao")
        ideal = st.text_area("Ideal", value=bug_data['comportamento_ideal'], height=100, key="edit_ideal")
        sev_index = SEVERITY_OPTIONS.index(bug_data['severidade']) if bug_data['severidade'] in SEVERITY_OPTIONS else 2
        pri_index = PRIORITY_OPTIONS.index(bug_data['prioridade']) if bug_data['prioridade'] in PRIORITY_OPTIONS else 1

        severidade = st.selectbox(
            "🚨 Severidade",
            SEVERITY_OPTIONS,
            index=sev_index,
            key="edit_severidade"
        )

        priority = st.selectbox(
            "⏱️ Prioridade",
            PRIORITY_OPTIONS,
            index=pri_index,
            key="edit_prioridade"
        )


        atual = st.text_area("Atual", value=bug_data['comportamento_atual'], height=100, key="edit_atual")
        bdd = st.text_area("Cenário BDD", value=bug_data.get('bdd', ''), height=150, key="edit_bdd")
        c1, c2, c3, _ = st.columns([.25, .2, .2, .35])
        if c1.form_submit_button("🤖 Refinar com IA", on_click=handle_refine_edited_bug):
            st.rerun()
        if c2.form_submit_button("💾 Salvar"):
            idx_to_update = bugs_df.index[bugs_df['id'] == bug_id].item()
            bugs_df.loc[idx_to_update, 'titulo'] = st.session_state.edit_titulo
            bugs_df.loc[idx_to_update, 'tela'] = tela
            bugs_df.loc[idx_to_update, 'modulo'] = modulo
            bugs_df.loc[idx_to_update, 'descricao'] = st.session_state.edit_descricao
            bugs_df.loc[idx_to_update, 'comportamento_ideal'] = st.session_state.edit_ideal
            bugs_df.loc[idx_to_update, 'comportamento_atual'] = st.session_state.edit_atual
            bugs_df.loc[idx_to_update, 'comportamento_atual'] = st.session_state.edit_atual
            bugs_df.loc[idx_to_update, 'comportamento_atual'] = st.session_state.edit_atual
            bugs_df.loc[idx_to_update, 'severidade'] = st.session_state.edit_severidade
            bugs_df.loc[idx_to_update, 'prioridade'] = st.session_state.edit_prioridade

            bugs_df.loc[idx_to_update, 'status'] = status
            bugs_df.loc[idx_to_update, 'bdd'] = st.session_state.edit_bdd
            save_bugs(project, bugs_df)
            st.success("Bug atualizado!")
            stop_editing()
            st.rerun()
        if c3.form_submit_button("Cancelar"):
            stop_editing()
            st.rerun()

elif 'bug_analysis_result' in st.session_state:
    st.subheader("Revisar Bug Refinado pela IA")
    refined_data = st.session_state.bug_analysis_result; extras = st.session_state.bug_extras
    with st.form("new_bug_form_refined"):
        st.success("Relatório refinado! Revise e salve.")
        titulo_refinado = st.text_input("Título", value=refined_data.get("titulo_melhorado", ""))
        tela_refinada = st.text_input("Tela", value=extras.get("tela", "")); modulo_refinado = st.text_input("Módulo", value=extras.get("modulo", ""))
        desc_val = refined_data.get("descricao_melhorada", "")
        if isinstance(desc_val, list): desc_val = "\n".join(f"- {item}" for item in desc_val)
        descricao_refinada = st.text_area("Descrição", value=desc_val, height=150)
        atual_refinado = st.text_area("Comportamento Atual", value=refined_data.get("comportamento_atual_refinado", ""), height=100)
        ideal_refinado = st.text_area("Comportamento Ideal", value=refined_data.get("comportamento_ideal_sugerido", ""), height=100)
        severidade_refinada = st.selectbox(
            "🚨 Severidade",
            SEVERITY_OPTIONS,
            index=SEVERITY_OPTIONS.index(st.session_state.get("severidade", "Médio"))
        )

        priority_refinada = st.selectbox(
            "⏱️ Prioridade",
            PRIORITY_OPTIONS,
            index=PRIORITY_OPTIONS.index(st.session_state.get("prioridade", "P2"))
        )
        bdd_refinado = st.text_area("Cenário BDD Sugerido", value=refined_data.get("cenario_bdd", ""), height=200)

        c1, c2, _ = st.columns([.2, .2, .6])
        if c1.form_submit_button("✅ Salvar", type="primary"):
            new_id = int(bugs_df['id'].max() + 1) if not bugs_df.empty else 1
            new_bug = {'id': new_id, 'titulo': titulo_refinado, 'tela': tela_refinada, 'modulo': modulo_refinado,
                       'descricao': descricao_refinada, 'comportamento_ideal': ideal_refinado, 'comportamento_atual': atual_refinado, 
                       'severidade': severidade_refinada, 'priority': priority_refinada,
                       'bdd': bdd_refinado, 'status': 'Novo', 'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M")}
            bugs_df = pd.concat([bugs_df, pd.DataFrame([new_bug])], ignore_index=True)
            save_bugs(project, bugs_df); st.success("Bug registrado!"); stop_editing(); st.rerun()
        if c2.form_submit_button("Descartar"): stop_editing(); st.rerun()

else:
    st.header("➕ Registrar Novo Bug")
    tab_rapido, tab_completo = st.tabs(["⚡ Registro Rápido", "🤖 Registro Completo com IA"])
    with tab_rapido:
        st.info("Use esta aba para registrar um bug rapidamente com as informações essenciais.")
        with st.form("new_bug_quick_form"):
            quick_titulo = st.text_input("Título do Bug *")
            c1, c2 = st.columns(2)
            quick_tela = c1.text_input("Tela / URL"); quick_modulo = c2.text_input("Módulo")
            if st.form_submit_button("💾 Salvar Bug Rápido", type="primary"):
                if not quick_titulo:
                    st.error("O campo 'Título' é obrigatório.")
                else:
                    new_id = int(bugs_df['id'].max() + 1) if not bugs_df.empty else 1
                    new_bug = {'id': new_id, 'titulo': quick_titulo, 'tela': quick_tela, 'modulo': quick_modulo, 'descricao': "", 'comportamento_ideal': "", 'comportamento_atual': "", 'bdd': "", 'status': 'Novo', 'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M")}
                    bugs_df = pd.concat([bugs_df, pd.DataFrame([new_bug])], ignore_index=True)
                    save_bugs(project, bugs_df); st.success(f"Bug rápido '{quick_titulo}' registrado com sucesso!"); st.rerun()
    with tab_completo:
        with st.expander("Descreva o bug em detalhes para a IA refinar e sugerir um cenário BDD", expanded=True):
                with st.form("new_bug_form_initial"):
                    titulo = st.text_input("Título *")
                    tela = st.text_input("Tela / URL")
                    modulo = st.text_input("Módulo")
                    descricao = st.text_area("Descrição / Passos")
                    atual = st.text_area("Comportamento Atual")
                    ideal = st.text_area("Comportamento Ideal (opcional)")
                    col_s, col_p = st.columns(2)

                    with col_s:
                        severidade = st.selectbox(
                            "🚨 Severidade",
                            ["Crítico", "Alto", "Médio", "Baixo"],
                            index=2  # Médio como padrão
                        )

                    with col_p:
                        priority = st.selectbox(
                            "⏱️ Prioridade",
                            ["P1", "P2", "P3"],
                            index=1  # P2 como padrão
                        )

                    bdd = st.text_area("Ideias para o Cenário BDD (opcional)")


                    c1, c2 = st.columns(2)

                    analisar_ia = c1.form_submit_button("🤖 Analisar com IA", type="primary")
                    salvar_direto = c2.form_submit_button("💾 Salvar sem IA")

                    if analisar_ia:
                        if not titulo or not descricao or not atual:
                            st.error("Preencha Título, Descrição e Comportamento Atual.")
                        else:
                            with st.spinner("Analisando com IA..."):
                                refined_data = refine_bug_with_gpt(titulo, descricao, atual, ideal, priority, severidade, bdd)
                                if refined_data:
                                    st.session_state.bug_analysis_result = refined_data
                                    st.session_state.bug_extras = {"tela": tela, "modulo": modulo}
                                    st.rerun()

                    if salvar_direto:
                        if not titulo:
                            st.error("O campo 'Título' é obrigatório.")
                        else:
                            new_id = int(bugs_df['id'].max() + 1) if not bugs_df.empty else 1

                            new_bug = {
                                        'id': new_id,
                                        'titulo': quick_titulo,
                                        'tela': quick_tela,
                                        'modulo': quick_modulo,
                                        'descricao': "",
                                        'comportamento_ideal': "",
                                        'comportamento_atual': "",
                                        'bdd': "",
                                        'status': 'Novo',
                                        'severidade': 'Médio',
                                        'prioridade': 'P2',
                                        'data_criacao': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }

                            bugs_df = pd.concat([bugs_df, pd.DataFrame([new_bug])], ignore_index=True)
                            save_bugs(project, bugs_df)

                            st.success("Bug salvo com sucesso (sem análise por IA).")
                            st.rerun()

st.subheader("Lista de Bugs por Status")
for status in BUG_STATUS_OPTIONS:
    status_bugs = bugs_df[bugs_df['status'] == status] if not bugs_df.empty else pd.DataFrame()
    if not status_bugs.empty:
        with st.expander(f"**{status}** ({len(status_bugs)})"):
            for index, bug in status_bugs.iterrows():
                bug_id = int(bug['id'])
                display_title = f"[{project}] - [{bug['tela']}] - {bug['titulo']}"
                st.markdown(f"**ID {bug_id}:** {display_title}"); st.caption(f"Módulo: {bug['modulo']}")
                action_cols_1 = st.columns([0.4, 0.15, 0.2, 0.2])
                with action_cols_1[0]:
                    idx = BUG_STATUS_OPTIONS.index(bug['status'])
                    new_status = st.selectbox("Mudar status:", BUG_STATUS_OPTIONS, index=idx, key=f"status_select_{bug_id}", label_visibility="collapsed")
                    if new_status != bug['status']:
                        bugs_df.loc[index, 'status'] = new_status
                        save_bugs(project, bugs_df); st.toast(f"Bug {bug_id} movido para '{new_status}'"); st.rerun()
                with action_cols_1[1]:
                    st.button("✏️", key=f"edit_bug_{bug_id}", on_click=start_editing_bug, args=(bug_id,), help="Editar Detalhes")
                if bug['status'] in ["Arrumado", "Em Teste", "Reprovado"]:
                    with action_cols_1[2]:
                        st.button("✅ Validar", key=f"approve_bug_{bug_id}", on_click=set_bug_to_validate, args=(bug.to_dict(), "Aprovado"), help="Gerar Relatório de Aprovação")
                    with action_cols_1[3]:
                        st.button("❌ Validar", key=f"reprove_bug_{bug_id}", on_click=set_bug_to_validate, args=(bug.to_dict(), "Reprovado"), help="Gerar Relatório de Reprovação")
                action_cols_2 = st.columns([0.5, 0.5])
                with action_cols_2[0]:
                    st.button("📋 Ver Título", key=f"view_title_{bug_id}", on_click=show_text_in_dialog, args=(display_title, "Título para Cópia"))
                with action_cols_2[1]:
                    report_text = f"Relatorio: {bug['titulo']}\n\n- Tela/URL: {bug['tela']}\n- Módulo: {bug['modulo']}\n---\n-Passos para a Reprodução:\n{bug['descricao']}\n---\n-Comportamento Ideal:\n{bug['comportamento_ideal']}\n---\n-Comportamento Atual:**\n{bug['comportamento_atual']}\n---\n-BDD: \n{bug['bdd']}"
                    st.button("📄 Ver Relatório", key=f"view_report_{bug_id}", on_click=show_text_in_dialog, args=(report_text, "Relatório para Cópia"))
                if bug['status'] in ["Aprovado", "Reprovado"]:
                    bug_validations = [v for v in validations if v.get('bug_id') == bug_id]
                    if bug_validations:
                        last_validation = bug_validations[-1]
                        with st.container(border=True):
                            st.markdown(f"**Último Relatório de Validação ({last_validation['date']}):**")
                            st.text(last_validation['report'])
                st.markdown("---")

                
st.header("📊 Dashboard do Projeto")
st.subheader("⏱️ SLA dos Bugs")


st.dataframe(
    bugs_df[
        ["icone_sla", "titulo", "severidade", "status_sla", "data_criacao"]
    ],
    use_container_width=True
)


if bugs_df.empty:
    st.info("Nenhum bug registrado ainda.")
else:
    # ===== CRIAÇÃO DOS GRÁFICOS =====

    # Gráfico de status
    fig_status = px.bar(
        bugs_df,
        x="status",
        color="status",
        title="📊 Bugs por Status",
        text_auto=True
    )
    fig_status.update_layout(
        height=350,
        showlegend=False,
        title_x=0.5
    )

    # Gráfico de severidade
    fig_severidade = None
    if 'severidade' in bugs_df.columns:
        sev_count = bugs_df['severidade'].value_counts().reset_index()
        sev_count.columns = ['Severidade', 'Quantidade']

        fig_severidade = px.pie(
            sev_count,
            names="Severidade",
            values="Quantidade",
            hole=0.5,
            color="Severidade",
            color_discrete_map={
                "Crítico": "#ef4444",
                "Alto": "#f97316",
                "Médio": "#facc15",
                "Baixo": "#22c55e"
            },
            title="🚨 Bugs por Severidade"
        )
        fig_severidade.update_layout(
            height=350,
            title_x=0.5
        )

    # ===== LAYOUT =====
    row1_col1, row1_col2 = st.columns([0.6, 0.4])
    row2_col1, row2_col2 = st.columns(2)

    with row1_col1:
        st.plotly_chart(fig_status, use_container_width=True, key="fig_status")

    with row1_col2:
        if fig_severidade:
            st.plotly_chart(fig_severidade, use_container_width=True, key="fig_severidade")
        else:
            st.info("Sem dados de severidade")

    with row2_col1:
        st.info("📈 Timeline de bugs (em breve)")

    with row2_col2:
        st.info("🧠 Insights automáticos (IA) em breve")

st.subheader("📌 Indicadores de SLA")

bugs_criticos = bugs_df[bugs_df["severidade"] == "Crítico"]

if not bugs_criticos.empty:
    total = len(bugs_criticos)
    fora_sla = len(bugs_criticos[bugs_criticos["status_sla"] == "SLA estourado"])
    percentual = round((fora_sla / total) * 100, 1)

    st.metric(
        label="🚨 Bugs Críticos fora do SLA",
        value=f"{percentual}%",
        delta=f"{fora_sla} bugs"
    )

    if percentual > 0:
        st.warning(
            f"⚠️ Seu time está com **{percentual}% dos bugs críticos fora do SLA**"
        )
else:
    st.success("✅ Nenhum bug crítico registrado")


st.markdown("---")



# 📄 pages/4_TestCases.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils import (
    render_sidebar,
    get_test_suites,
    load_test_cases,
    save_test_cases,
    load_scenarios,
)
from openai import OpenAI

# ---- Configuração da página ----
st.set_page_config(page_title="Casos de Teste", layout="wide")
render_sidebar()
st.title("📋 Casos de Teste (Gerar / Editar / Organizar)")

# ---- Inicialização de Estado ----
st.session_state.setdefault("proposed_test_cases", [])
st.session_state.setdefault("editing_case_id", None)
st.session_state.setdefault("reproving_case_id", None)
st.session_state.setdefault("bug_report_text", "")
st.session_state.setdefault("suite_for_reproval", None)
st.session_state.setdefault("bug_report_rerun_counter", 0) # Para forçar a atualização do widget de texto

# ---- Constantes ----
STATUS_OPTIONS = ["Não Executado", "Passou", "Falhou", "Bloqueado", "Em Andamento"]
PRIORITY_OPTIONS = ["Baixa", "Média", "Alta", "Crítica"]
TEST_TYPE_OPTIONS = ["Funcional", "UI/Visual", "Usabilidade", "Performance", "Segurança", "Integração"]

# ---- Callbacks ----

def handle_ai_case_generation():
    suite = st.session_state.get("suite_for_generation")
    scenario_key = st.session_state.get("scenario_for_generation")
    n_cases = st.session_state.get("n_cases_to_generate", 1)
    context = st.session_state.get("generation_context", "")
    if not suite or suite == "-- nenhuma --": st.error("Selecione uma suíte de teste."); return
    if not scenario_key: st.error("Selecione um cenário como base."); return
    scenario = scen_map.get(scenario_key)
    if not scenario: st.error("Cenário selecionado não encontrado."); return
    try:
        with st.spinner(f"Gerando {n_cases} caso(s) de teste com IA..."):
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            prompt = f"""
            Você é um Engenheiro de QA Sênior. Sua tarefa é criar casos de teste detalhados a partir de um cenário.
            Cenário Base:
            - Título: "{scenario.get('title')}" - Passos: "{scenario.get('steps')}"
            - Pré-condições: "{scenario.get('preconditions')}" - Resultado Esperado: "{scenario.get('expected')}"
            Instruções Adicionais: "{context if context else 'Nenhuma.'}"
            Gere exatamente {n_cases} caso(s) de teste.
            Retorne um JSON válido com a chave "test_cases", contendo uma lista de objetos.
            Cada objeto DEVE ter as chaves: "titulo", "objetivo", "modulo", "precondicoes", "passos", "resultado_esperado", "tipo" (de {TEST_TYPE_OPTIONS}), "prioridade" (de {PRIORITY_OPTIONS}), "status" (sempre "Não Executado"), "automatizavel" (boolean), "requisitos", "tags", "ambiente", "bug_id_relacionado".
            """
            response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.7, response_format={"type": "json_object"})
            text = response.choices[0].message.content.strip()
            ai_result = json.loads(text)
            proposed_list = ai_result.get("test_cases", [])
            if proposed_list:
                st.session_state.proposed_test_cases = proposed_list
                st.success("✅ Casos de teste propostos! Revise e edite nos formulários abaixo.")
            else:
                st.warning("A IA não retornou casos de teste.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a IA: {e}")

def handle_save_all_proposed_cases():
    suite = st.session_state.get("suite_for_generation")
    project = st.session_state.selected_project
    if not suite or suite == "-- nenhuma --": st.error("Nenhuma suíte selecionada."); return
    cases_to_save = []
    for i in range(len(st.session_state.proposed_test_cases)):
        cases_to_save.append({
            "titulo": st.session_state.get(f"prop_titulo_{i}", ""), "objetivo": st.session_state.get(f"prop_objetivo_{i}", ""), "modulo": st.session_state.get(f"prop_modulo_{i}", ""), "precondicoes": st.session_state.get(f"prop_precondicoes_{i}", ""),
            "passos": st.session_state.get(f"prop_passos_{i}", ""), "resultado_esperado": st.session_state.get(f"prop_resultado_esperado_{i}", ""), "tipo": st.session_state.get(f"prop_tipo_{i}", "Funcional"), "status": st.session_state.get(f"prop_status_{i}", "Não Executado"),
            "prioridade": st.session_state.get(f"prop_prioridade_{i}", "Média"), "automatizavel": st.session_state.get(f"prop_automatizavel_{i}", False), "requisitos": st.session_state.get(f"prop_requisitos_{i}", ""), "tags": st.session_state.get(f"prop_tags_{i}", ""),
            "ambiente": st.session_state.get(f"prop_ambiente_{i}", ""), "bug_id_relacionado": st.session_state.get(f"prop_bug_id_{i}", ""), "autor": "system", "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    if not cases_to_save: st.error("Não há casos propostos para salvar."); return
    new_cases_df = pd.DataFrame(cases_to_save)
    current_df = load_test_cases(project, suite)
    numeric_ids = pd.to_numeric(current_df['id'], errors='coerce').dropna()
    last_id = int(numeric_ids.max()) if not numeric_ids.empty else 0
    new_cases_df['id'] = range(last_id + 1, last_id + 1 + len(new_cases_df))
    combined_df = pd.concat([current_df, new_cases_df], ignore_index=True)
    save_test_cases(project, suite, combined_df)
    st.success(f"{len(new_cases_df)} caso(s) de teste salvo(s) com sucesso!")
    st.session_state.proposed_test_cases = []
    st.rerun()

def start_editing(case_id):
    st.session_state.editing_case_id = str(case_id)

def cancel_editing():
    st.session_state.editing_case_id = None

def start_reproving(case_id, suite_name):
    st.session_state.reproving_case_id = str(case_id)
    st.session_state.suite_for_reproval = suite_name
    st.session_state.bug_report_rerun_counter = 0
    st.session_state.bug_report_text = (
        "**Resumo:** \n\n"
        "**Passos para Reproduzir:**\n1. \n2. \n3. \n\n"
        "**Resultado Esperado:**\n\n"
        "**Resultado Atual (O que aconteceu de errado):**\n\n"
        "**Ambiente:**\n- Navegador/Dispositivo: \n- Versão: "
    )

def cancel_reproving():
    st.session_state.reproving_case_id = None
    st.session_state.bug_report_text = ""
    st.session_state.suite_for_reproval = None

def handle_ai_bug_report_generation():
    case_id = st.session_state.reproving_case_id
    suite = st.session_state.suite_for_reproval
    project = st.session_state.selected_project

    if not all([project, suite, case_id]):
        st.error("Erro interno: Informações do projeto, suíte ou caso estão faltando."); return
    
    current_report_text = st.session_state.get(f"bug_report_form_text_{case_id}_{st.session_state.bug_report_rerun_counter}", st.session_state.bug_report_text)
    
    df = load_test_cases(project, suite)
    case_data = df[df['id'] == case_id].iloc[0]
    try:
        with st.spinner("🤖 A IA está aprimorando o seu relatório..."):
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            prompt = f"""
            Você é um Engenheiro de QA Sênior. Aprimore o relatório de bug a seguir com base nos dados do caso de teste.
            Se o relatório estiver em branco, crie um novo. Se já tiver conteúdo, melhore-o.

            **Relatório de Bug Atual do Usuário:**
            {current_report_text}

            **Dados do Caso de Teste para Contexto:**
            - Título: {case_data.get('titulo', 'N/A')}
            - Passos: {case_data.get('passos', 'N/A')}
            - Resultado Esperado: {case_data.get('resultado_esperado', 'N/A')}

            **Instruções:**
            Gere um relatório de bug profissional em markdown com as seções: Resumo, Passos para Reproduzir, Resultado Esperado, e Resultado Atual.
            """
            response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}], temperature=0.5)
            ai_report = response.choices[0].message.content.strip()
            st.session_state.bug_report_text = ai_report
            st.session_state.bug_report_rerun_counter += 1
            st.toast("Relatório aprimorado pela IA!")
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a IA: {e}")

def handle_save_bug_report():
    project = st.session_state.selected_project
    suite = st.session_state.suite_for_reproval
    case_id = st.session_state.reproving_case_id
    report_text = st.session_state.get(f"bug_report_form_text_{case_id}_{st.session_state.bug_report_rerun_counter}", "")

    df = load_test_cases(project, suite)
    idx_to_update = df.index[df['id'] == str(case_id)].tolist()
    
    if idx_to_update:
        # 1. Salva o relatório e atualiza o status (comportamento atual)
        df.loc[idx_to_update[0], "report_bug_execucao_test_case"] = report_text
        df.loc[idx_to_update[0], "status"] = "Falhou"
        save_test_cases(project, suite, df)
        
        # 2. Prepara os dados para enviar para a página de bugs
        case_data = df.loc[idx_to_update[0]]
        
        st.session_state['bug_to_create_from_test_case'] = {
            "titulo": f"Bug encontrado no CT: {case_data.get('titulo', 'N/A')}",
            "tela": "", # Deixar em branco para o usuário preencher
            "modulo": case_data.get('modulo', ''),
            "descricao": case_data.get('passos', ''),
            "comportamento_ideal": case_data.get('resultado_esperado', ''),
            "comportamento_atual": report_text, # O relatório do bug é o comportamento atual
            "bdd": "" # Deixar em branco para a IA de bugs gerar
        }

        st.success("Relatório salvo! Redirecionando para a criação do bug...")
        cancel_reproving()
        
        # 3. Muda para a página principal. Requer Streamlit >= 1.27
        # Se sua versão for mais antiga, mostre uma mensagem para o usuário navegar manualmente.
        st.switch_page("app.py")

    else:
        st.error(f"Erro ao salvar: caso de teste com ID {case_id} não encontrado.")

def handle_status_change(project_name, suite_name, case_id, new_status):
    df = load_test_cases(project_name, suite_name)
    idx_to_update = df.index[df['id'] == str(case_id)].tolist()
    if idx_to_update:
        df.loc[idx_to_update[0], "status"] = new_status
        df.loc[idx_to_update[0], "report_bug_execucao_test_case"] = ""
        save_test_cases(project_name, suite_name, df)
        st.toast(f"Status alterado para '{new_status}'.")
        st.rerun()
    else:
        st.error(f"Erro: Não foi possível encontrar o caso de teste com ID {case_id}.")

def render_bug_report_modal():
    project = st.session_state.selected_project
    suite = st.session_state.suite_for_reproval
    case_id = st.session_state.reproving_case_id
    
    df = load_test_cases(project, suite)
    case_title = df[df['id'] == case_id].iloc[0]['titulo']

    st.warning(f"#### 🐞 Relatando Bug para o Caso: `{case_title}`")
    with st.container(border=True):
        st.text_area(
            "Descreva o bug encontrado",
            value=st.session_state.bug_report_text,
            height=350,
            key=f"bug_report_form_text_{case_id}_{st.session_state.bug_report_rerun_counter}"
        )
        c1, c2, c3, _ = st.columns([0.3, 0.2, 0.2, 0.3])
        c1.button("✨ Melhorar com IA", on_click=handle_ai_bug_report_generation, use_container_width=True)
        c2.button("💾 Salvar Relatório", on_click=handle_save_bug_report, type="primary", use_container_width=True)
        c3.button("Cancelar", on_click=cancel_reproving, use_container_width=True)
    st.stop()

# ---- Lógica Principal ----
if 'selected_project' not in st.session_state:
    st.warning("Selecione um projeto na sidebar."); st.stop()
project = st.session_state.selected_project
st.subheader(f"Projeto: {project}")

if st.session_state.reproving_case_id:
    render_bug_report_modal()

suites = get_test_suites(project)
scenarios = load_scenarios(project)
scen_map = {f"{str(s.get('id', ''))[:8]} - {s.get('title')}": s for s in scenarios}

with st.expander("🤖 Gerar Casos de Teste com IA", expanded=True):
    with st.form("generation_form"):
        st.markdown("##### 1. Selecione os Insumos")
        c1, c2 = st.columns(2)
        c1.selectbox("Salvar na Suíte de Teste", options=(suites or ["-- nenhuma --"]), key="suite_for_generation")
        c1.selectbox("Baseado no Cenário", options=list(scen_map.keys()), key="scenario_for_generation", placeholder="Selecione um cenário...")
        c2.number_input("Quantidade de casos a gerar", min_value=1, max_value=20, value=3, key="n_cases_to_generate")
        c2.text_area("Contexto Adicional", key="generation_context", placeholder="Ex: gere casos negativos")
        st.form_submit_button("✨ Gerar Casos de Teste com IA", on_click=handle_ai_case_generation, use_container_width=True)

if st.session_state.get("proposed_test_cases"):
    st.markdown("---")
    st.markdown("##### 2. Revise, Edite e Salve os Casos Propostos")
    for i, case in enumerate(st.session_state.proposed_test_cases):
        with st.container(border=True):
            st.markdown(f"**Caso de Teste Proposto #{i+1}**")
            st.text_input("Título", value=case.get("titulo", ""), key=f"prop_titulo_{i}")
            st.text_area("Objetivo", value=case.get("objetivo", ""), key=f"prop_objetivo_{i}", height=75)
            c1, c2, c3 = st.columns(3)
            c1.text_input("Módulo", value=case.get("modulo", ""), key=f"prop_modulo_{i}")
            type_index = TEST_TYPE_OPTIONS.index(case.get("tipo")) if case.get("tipo") in TEST_TYPE_OPTIONS else 0
            c2.selectbox("Tipo de Teste", options=TEST_TYPE_OPTIONS, index=type_index, key=f"prop_tipo_{i}")
            c3.toggle("Automatizável", value=case.get("automatizavel", False), key=f"prop_automatizavel_{i}")
            st.text_area("Pré-condições", value=case.get("precondicoes", ""), key=f"prop_precondicoes_{i}", height=75)
            c1, c2 = st.columns(2)
            priority_index = PRIORITY_OPTIONS.index(case.get("prioridade")) if case.get("prioridade") in PRIORITY_OPTIONS else 1
            c1.selectbox("Prioridade", options=PRIORITY_OPTIONS, index=priority_index, key=f"prop_prioridade_{i}")
            status_index = STATUS_OPTIONS.index(case.get("status")) if case.get("status") in STATUS_OPTIONS else 0
            c2.selectbox("Status", options=STATUS_OPTIONS, index=status_index, key=f"prop_status_{i}")
            st.text_area("Passos", value=case.get("passos", ""), key=f"prop_passos_{i}", height=150)
            st.text_area("Resultado Esperado", value=case.get("resultado_esperado", ""), key=f"prop_resultado_esperado_{i}", height=100)
            st.markdown("###### Detalhes Adicionais")
            c1, c2 = st.columns(2)
            c1.text_input("Requisitos", value=case.get("requisitos", ""), key=f"prop_requisitos_{i}")
            c2.text_input("Ambiente", value=case.get("ambiente", ""), key=f"prop_ambiente_{i}")
            c1.text_input("Tags", value=case.get("tags", ""), key=f"prop_tags_{i}")
            c2.text_input("ID do Bug Relacionado", value=case.get("bug_id_relacionado", ""), key=f"prop_bug_id_{i}")
    st.button("💾 Salvar Todos os Casos Propostos na Suíte", on_click=handle_save_all_proposed_cases, type="primary", use_container_width=True)

st.markdown("---")
st.subheader("Visualizar / Editar Suítes Existentes")
if not suites:
    st.info("Nenhuma suíte criada.")
else:
    suite_to_edit = st.selectbox("Selecione uma suíte para visualizar", options=suites, key="suite_to_view")
    if suite_to_edit:
        cases_df = load_test_cases(project, suite_to_edit)
        if not cases_df.empty:
            if 'status_execucao' in cases_df.columns:
                cases_df['status'] = cases_df.apply(lambda row: row['status_execucao'] if row.get('status', '') == '' else row['status'], axis=1)
                cases_df = cases_df.drop(columns=['status_execucao'], errors='ignore')
            expected_cols = ['id', 'titulo', 'objetivo', 'modulo', 'status', 'automatizavel', 'report_bug_execucao_test_case']
            for col in expected_cols:
                if col not in cases_df.columns: cases_df[col] = ''
            cases_df['automatizavel'] = cases_df['automatizavel'].apply(lambda x: str(x).lower() in ['true', '1', 't', 'y', 'yes'])

        if st.session_state.editing_case_id:
            case_data = cases_df[cases_df['id'] == st.session_state.editing_case_id].iloc[0].to_dict()
            st.markdown(f"#### ✏️ Editando Caso de Teste: `{case_data.get('titulo')}`")
            with st.form(key="edit_case_form"):
                title = st.text_input("Título", value=case_data.get("titulo", ""))
                objective = st.text_area("Objetivo", value=case_data.get("objetivo", ""), height=75)
                c1, c2, c3 = st.columns(3); module = c1.text_input("Módulo", value=case_data.get("modulo", "")); type_index = TEST_TYPE_OPTIONS.index(case_data.get("tipo")) if case_data.get("tipo") in TEST_TYPE_OPTIONS else 0; test_type = c2.selectbox("Tipo de Teste", options=TEST_TYPE_OPTIONS, index=type_index); automatable = c3.toggle("Automatizável", value=case_data.get("automatizavel", False))
                preconditions = st.text_area("Pré-condições", value=case_data.get("precondicoes", ""), height=75)
                c1, c2 = st.columns(2); priority_index = PRIORITY_OPTIONS.index(case_data.get("prioridade")) if case_data.get("prioridade") in PRIORITY_OPTIONS else 1; priority = c1.selectbox("Prioridade", options=PRIORITY_OPTIONS, index=priority_index); status_index = STATUS_OPTIONS.index(case_data.get("status", "Não Executado")) if case_data.get("status") in STATUS_OPTIONS else 0; status = c2.selectbox("Status", options=STATUS_OPTIONS, index=status_index)
                steps = st.text_area("Passos", value=case_data.get("passos", ""), height=150)
                expected = st.text_area("Resultado Esperado", value=case_data.get("resultado_esperado", ""), height=100)
                st.markdown("###### Detalhes Adicionais")
                c1, c2 = st.columns(2); requisitos = c1.text_input("Requisitos", value=case_data.get("requisitos", "")); ambiente = c2.text_input("Ambiente", value=case_data.get("ambiente", "")); tags = c1.text_input("Tags", value=case_data.get("tags", "")); bug_id = c2.text_input("ID do Bug Relacionado", value=case_data.get("bug_id_relacionado", ""))
                submit_col, cancel_col, _ = st.columns([0.2, 0.2, 0.6])
                if submit_col.form_submit_button("💾 Salvar Alterações", type="primary"):
                    idx_to_update = cases_df.index[cases_df['id'] == st.session_state.editing_case_id].item()
                    cases_df.loc[idx_to_update, "titulo"] = title; cases_df.loc[idx_to_update, "objetivo"] = objective; cases_df.loc[idx_to_update, "modulo"] = module; cases_df.loc[idx_to_update, "precondicoes"] = preconditions; cases_df.loc[idx_to_update, "passos"] = steps; cases_df.loc[idx_to_update, "resultado_esperado"] = expected; cases_df.loc[idx_to_update, "tipo"] = test_type; cases_df.loc[idx_to_update, "status"] = status; cases_df.loc[idx_to_update, "prioridade"] = priority; cases_df.loc[idx_to_update, "automatizavel"] = automatable; cases_df.loc[idx_to_update, "requisitos"] = requisitos; cases_df.loc[idx_to_update, "ambiente"] = ambiente; cases_df.loc[idx_to_update, "tags"] = tags; cases_df.loc[idx_to_update, "bug_id_relacionado"] = bug_id
                    save_test_cases(project, suite_to_edit, cases_df)
                    st.success("Caso de teste atualizado!")
                    cancel_editing(); st.rerun()
                if cancel_col.form_submit_button("Cancelar"):
                    cancel_editing(); st.rerun()
        else:
            if cases_df.empty:
                st.info(f"A suíte '{suite_to_edit}' está vazia.")
            else:
                st.markdown(f"##### Casos de Teste em '{suite_to_edit}'")
                for index, case in cases_df.iterrows():
                    status = case.get('status', '') or 'Não Executado'
                    status_emoji_map = {"Passou": "✅", "Falhou": "❌", "Não Executado": "⚪", "Bloqueado": " блокирован ", "Em Andamento": "➡️"}
                    emoji = status_emoji_map.get(status, "⚪")
                    with st.expander(f"**{emoji} {case.get('titulo', 'Caso sem título')}** (Status: {status})"):
                        st.markdown(f"**Objetivo:** {case.get('objetivo', '')}")
                        c1, c2, c3, c4 = st.columns(4); c1.markdown(f"**Módulo:** `{case.get('modulo', 'N/A')}`"); c2.markdown(f"**Tipo:** `{case.get('tipo', 'N/A')}`"); c3.markdown(f"**Prioridade:** `{case.get('prioridade', 'N/A')}`"); c4.markdown(f"**Automatizável:** {'Sim' if case.get('automatizavel') else 'Não'}")
                        details_cols = st.columns(4)
                        if case.get('requisitos'): details_cols[0].markdown(f"**Requisitos:** `{case['requisitos']}`")
                        if case.get('tags'): details_cols[1].markdown(f"**Tags:** `{case['tags']}`")
                        if case.get('ambiente'): details_cols[2].markdown(f"**Ambiente:** `{case['ambiente']}`")
                        if case.get('bug_id_relacionado'): details_cols[3].markdown(f"**Bug ID:** `{case['bug_id_relacionado']}`")
                        if case.get('precondicoes'): st.markdown("**Pré-condições:**"); st.warning(case.get('precondicoes'))
                        st.markdown("**Passos:**"); st.code(case.get('passos', 'Nenhum passo definido.'), language='text')
                        st.markdown("**Resultado Esperado:**"); st.info(case.get('resultado_esperado', 'Nenhum resultado esperado definido.'))
                        bug_report = case.get('report_bug_execucao_test_case', '')
                        if bug_report:
                            st.markdown("---"); st.markdown("##### 🐞 Relatório de Bug Anexado"); st.error(bug_report)
                        st.markdown("---")
                        action_cols = st.columns([0.2, 0.2, 0.25, 0.15, 0.2])
                        action_cols[0].button("✅ Aceitar", key=f"pass_{case['id']}", on_click=handle_status_change, args=(project, suite_to_edit, case['id'], "Passou"), use_container_width=True)
                        action_cols[1].button("❌ Reprovar", key=f"fail_{case['id']}", on_click=start_reproving, args=(case['id'], suite_to_edit), use_container_width=True)
                        action_cols[2].button("⚪ Não Testado", key=f"untested_{case['id']}", on_click=handle_status_change, args=(project, suite_to_edit, case['id'], "Não Executado"), use_container_width=True)
                        action_cols[4].button("✏️ Editar Caso", key=f"edit_{case['id']}", on_click=start_editing, args=(case['id'],), use_container_width=True)
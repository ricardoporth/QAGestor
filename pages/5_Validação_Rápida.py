# pages/5_Validação_Rápida.py

import streamlit as st
import openai
from utils import render_sidebar

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Validação Rápida", page_icon="⚡")

# --- Estado da Sessão ---
if "quick_validation_report" not in st.session_state:
    st.session_state.quick_validation_report = None

# --- Função de IA ---
def generate_quick_report_with_gpt(title, description, status):
    """Gera um relatório de validação conciso usando IA."""
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        
        status_emoji = "✅ APROVADO" if status == "Aprovado" else "❌ REPROVADO"
        
        prompt = f"""
        Você é um Engenheiro de QA Sênior escrevendo um relatório de validação de teste conciso e profissional.

        A tarefa testada foi:
        - Título: "{title}"
        - Descrição/Critérios de Aceite: "{description}"

        O resultado do teste foi: {status_emoji}.

        Sua tarefa é gerar um breve relatório em formato Markdown. O relatório deve ser claro, objetivo e seguir a estrutura abaixo:

        **[Validação de Teste - {status_emoji}]**

        **Feature Testada:**
        - Escreva um resumo da feature com base no título e descrição fornecidos.

        **Resultado:**
        - Confirme o status ({status}) e explique brevemente o motivo. Se aprovado, confirme que os critérios foram atendidos. Se reprovado, mencione que o comportamento esperado não foi observado.

        **Observações:**
        - Adicione uma breve observação. Se aprovado, mencione que o teste foi concluído com sucesso. Se reprovado, sugira a necessidade de uma investigação ou a abertura de um bug.
        """
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a API da OpenAI: {e}")
        return None

# --- RENDERIZA A SIDEBAR ---
render_sidebar()

# --- Corpo Principal da Aplicação ---
st.title("⚡ Validação Rápida de Testes")
st.markdown("Use esta ferramenta para validar tarefas simples e gerar um relatório rápido para documentação ou comunicação.")

# --- Formulário de Entrada ---
with st.form("quick_validation_form"):
    st.subheader("1. Descreva o Teste")
    task_title = st.text_input("Título da Tarefa/Teste *", placeholder="Ex: Validar login com novo botão do Google")
    task_description = st.text_area(
        "Descrição do Teste / Critérios de Aceite *", 
        placeholder="Ex: 1. Acessar a tela de login.\n2. Clicar no botão 'Entrar com Google'.\n3. Verificar se o usuário é autenticado e redirecionado para o dashboard.",
        height=150
    )
    
    st.subheader("2. Escolha o Resultado")
    c1, c2, _ = st.columns([0.3, 0.3, 0.4])
    approve_button = c1.form_submit_button("✅ Aprovar Teste", use_container_width=True, type="primary")
    reprove_button = c2.form_submit_button("❌ Reprovar Teste", use_container_width=True)

# --- Lógica de Geração do Relatório ---
if approve_button or reprove_button:
    if not task_title or not task_description:
        st.error("Por favor, preencha os campos 'Título' e 'Descrição' antes de gerar o relatório.")
    else:
        status = "Aprovado" if approve_button else "Reprovado"
        with st.spinner(f"🤖 Gerando relatório de '{status}'..."):
            report = generate_quick_report_with_gpt(task_title, task_description, status)
            if report:
                st.session_state.quick_validation_report = report

# --- Exibição do Relatório Gerado ---
if st.session_state.quick_validation_report:
    st.markdown("---")
    st.subheader("📄 Relatório Gerado")
    
    # Exibe o relatório formatado em Markdown
    with st.container(border=True):
        st.markdown(st.session_state.quick_validation_report)

    # Fornece uma área de texto para cópia fácil
    st.text_area(
        "Selecione e copie o relatório abaixo:", 
        value=st.session_state.quick_validation_report, 
        height=250
    )

    # Botão para limpar e começar de novo
    if st.button("Limpar e Validar Outro Teste"):
        st.session_state.quick_validation_report = None
        st.rerun()
# pages/6_Gerador_BDD.py

import streamlit as st
import openai
from utils import render_sidebar

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Gerador de BDD", page_icon="📝")

# --- Estado da Sessão ---
st.session_state.setdefault("bdd_refined_scenario", None)
st.session_state.setdefault("bdd_generated_scenarios", None)

# --- Funções de IA ---

def refine_scenario_with_gpt(feature, title, given, when, then):
    """Refina um único cenário BDD para melhorar a clareza e a sintaxe Gherkin."""
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        
        user_scenario = f"Funcionalidade: {feature}\nCenário: {title}\nDado {given}\nQuando {when}\nEntão {then}"
        
        prompt = f"""
        Você é um Engenheiro de QA Sênior e especialista em BDD (Behavior-Driven Development).
        Sua tarefa é refinar o cenário BDD a seguir, que está em português (Brasil).
        Melhore a clareza, a gramática e a aderência às boas práticas de Gherkin, garantindo que seja facilmente compreendido por stakeholders técnicos e não técnicos.
        Não altere a lógica central do teste.

        Cenário Original do Usuário:
        ---
        {user_scenario}
        ---

        Retorne APENAS o cenário completo e refinado, formatado em um único bloco de código Markdown. Comece com 'Funcionalidade:'.
        """
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a API da OpenAI: {e}")
        return None

def generate_new_scenarios_with_gpt(feature, base_scenario):
    """Gera novos cenários (negativos, edge cases) a partir de um cenário base."""
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        
        prompt = f"""
        Você é um Engenheiro de QA Sênior criativo e meticuloso, especialista em BDD.
        Baseado na funcionalidade e no cenário "caminho feliz" a seguir, sua tarefa é gerar de 3 a 5 cenários de teste adicionais e diversos em português (Brasil).

        Funcionalidade Base:
        ---
        {feature}
        ---

        Cenário Principal (Caminho Feliz):
        ---
        {base_scenario}
        ---

        Instruções para os novos cenários:
        1. Crie pelo menos um cenário de "caminho negativo" (ex: dados inválidos, erro do usuário).
        2. Crie pelo menos um "caso de borda" (edge case) (ex: campos vazios, valores limite).
        3. Varie as condições e os resultados esperados.
        4. Mantenha a estrutura Gherkin (Cenário, Dado, Quando, Então) para cada um.

        Retorne APENAS os novos cenários. Separe cada cenário com uma régua horizontal (`---`).
        """
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        # Retorna a string inteira, que será dividida depois
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar a API da OpenAI: {e}")
        return None

def clear_results():
    """Limpa os resultados da sessão."""
    st.session_state.bdd_refined_scenario = None
    st.session_state.bdd_generated_scenarios = None

# --- RENDERIZA A SIDEBAR ---
render_sidebar()

# --- Corpo Principal da Aplicação ---
st.title("📝 Gerador de Cenários BDD")
st.markdown("Use esta ferramenta para escrever, refinar e expandir seus cenários de teste no formato Gherkin.")

# --- Formulário de Entrada ---
with st.form("bdd_generator_form"):
    st.subheader("1. Descreva o Cenário Base")
    
    feature_input = st.text_input(
        "Funcionalidade / User Story", 
        placeholder="Ex: Como um cliente, eu quero adicionar produtos ao meu carrinho de compras"
    )
    scenario_title_input = st.text_input("Título do Cenário", placeholder="Ex: Adicionar um item disponível ao carrinho")
    
    c1, c2, c3 = st.columns(3)
    given_input = c1.text_area("Dado (Given)", placeholder="que eu estou na página de um produto")
    when_input = c2.text_area("Quando (When)", placeholder="eu clico no botão 'Adicionar ao Carrinho'")
    then_input = c3.text_area("Então (Then)", placeholder="o item deve ser adicionado ao meu carrinho")

    st.subheader("2. Escolha uma Ação com IA")
    btn_cols = st.columns(2)
    refine_button = btn_cols[0].form_submit_button("🤖 Refinar Cenário Atual", use_container_width=True)
    generate_button = btn_cols[1].form_submit_button("✨ Gerar Mais Cenários", use_container_width=True, type="primary")

# --- Lógica de Ação ---
if refine_button or generate_button:
    # Validação de entrada
    if not all([feature_input, scenario_title_input, given_input, when_input, then_input]):
        st.error("Por favor, preencha todos os campos do cenário base antes de usar a IA.")
    else:
        clear_results() # Limpa resultados antigos antes de gerar novos
        
        if refine_button:
            with st.spinner("🤖 Refinando seu cenário..."):
                result = refine_scenario_with_gpt(feature_input, scenario_title_input, given_input, when_input, then_input)
                if result:
                    st.session_state.bdd_refined_scenario = result
        
        if generate_button:
            with st.spinner("✨ Gerando novos cenários (negativos, edge cases...)..."):
                base_scenario_text = f"Cenário: {scenario_title_input}\nDado {given_input}\nQuando {when_input}\nEntão {then_input}"
                result = generate_new_scenarios_with_gpt(feature_input, base_scenario_text)
                if result:
                    # Divide os cenários pela régua horizontal e remove espaços em branco
                    st.session_state.bdd_generated_scenarios = [s.strip() for s in result.split("---") if s.strip()]

# --- Exibição dos Resultados ---
if st.session_state.get("bdd_refined_scenario") or st.session_state.get("bdd_generated_scenarios"):
    st.markdown("---")
    st.subheader("📄 Resultados da IA")

    if st.session_state.bdd_refined_scenario:
        st.markdown("#### Cenário Refinado")
        st.markdown(st.session_state.bdd_refined_scenario)
        st.text_area("Copie o cenário refinado:", value=st.session_state.bdd_refined_scenario, height=200)

    if st.session_state.bdd_generated_scenarios:
        st.markdown("#### Cenários Adicionais Gerados")
        
        # Junta todos os cenários para a caixa de cópia
        all_scenarios_text = "\n\n---\n\n".join(st.session_state.bdd_generated_scenarios)
        st.text_area("Copie todos os cenários:", value=all_scenarios_text, height=300)

        # Mostra cada cenário individualmente
        for scenario in st.session_state.bdd_generated_scenarios:
            with st.container(border=True):
                st.markdown(scenario)

    if st.button("Limpar e Começar de Novo"):
        clear_results()
        st.rerun()
# aqui vamos adicionar o streamlit como front do app

import streamlit as st
import pandas as pd
from backend import calcular_posicao_atual, get_stock_quote # Importando o SEU código!
from pathlib import Path

# =========================================================================== #

# __file__ é o app.py (src/app.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
# Se não existir, o streamlit vai criar a pasta na raiz do projeto certinho
DATA_DIR.mkdir(parents=True, exist_ok=True) 
print(DATA_DIR)

INPUT_PATH = DATA_DIR / "historico_operacoes.csv"
OUTPUT_PATH = DATA_DIR / "carteira_atualizada.csv"

# =========================================================================== #

st.title("📊 Dashboard de Investimentos")

# --- 1. BARRA LATERAL: INPUT DE DADOS ---
with st.sidebar.form("nova_operacao"):
    st.header("Cadastrar Operação")
    data = st.date_input("Data")
    ticker = st.text_input("Ticker (ex: ITUB4)").upper()
    operacao = st.selectbox("Operação", ["Compra", "Venda"])
    qtd = st.number_input("Quantidade", min_value=1)
    preco = st.number_input("Preço Unitário (R$)", min_value=0.01)
    taxas = st.number_input("Taxas (R$)", min_value=0.0)
    
    submit = st.form_submit_button("Salvar Operação")
    
    if submit:
        # 1. Cria a nova linha com as informações do formulário
        nova_linha = pd.DataFrame([{
            'Data': data,
            'Ticker': ticker,
            'Operacao': operacao,
            'Quantidade': qtd,
            'Preco_Unitario': preco,
            'Taxas': taxas
        }])
        
        # 2. Abre o histórico antigo e junta com a nova linha (ou cria um se não existir)
        if INPUT_PATH.exists():
            df_existente = pd.read_csv(INPUT_PATH, sep=';')
            df_atualizado = pd.concat([df_existente, nova_linha], ignore_index=True)
        else:
            df_atualizado = nova_linha
            
        # 3. Salva no arquivo CSV!
        df_atualizado.to_csv(INPUT_PATH, sep=';', index=False)
        
        st.success(f"{qtd} cotas de {ticker} salvas com sucesso!")

# --- 2. TELA PRINCIPAL: OUTPUT (O CARREGAMENTO DO BACKEND) ---
# st.subheader("Situação Atual da Carteira")

# =========================================================================== #
# usando um if só para verificar o caminho e separação do csv
if INPUT_PATH.exists():
    df_historico = pd.read_csv(INPUT_PATH, sep=';')
    
    # Verifica se o CSV não está apenas com os cabeçalhos vazios
    if not df_historico.empty:
        # Usa sua função matemática
        df_carteira = calcular_posicao_atual(df_historico)
        
        # Exibe na tela usando o tamanho total do container
        st.dataframe(df_carteira, use_container_width=True)
    else:
        st.info("O histórico está vazio. Cadastre uma operação ao lado.")
else:
    st.warning("Nenhum histórico encontrado. Cadastre a sua primeira operação na barra lateral!")

# =========================================================================== #

# Usa sua função matemática
df_carteira = calcular_posicao_atual(df_historico)

# Opcional: Já gera os gráficos nativos do Streamlit aqui embaixo
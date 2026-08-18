# aqui vamos adicionar o streamlit como front do app

import streamlit as st
import pandas as pd
import plotly.express as px # Nova biblioteca de gráficos
import requests

from backend import gerar_carteira_atualizada # Importando o SEU código!
from pathlib import Path

# =========================================================================== #
# layout="wide" faz o site ocupar a tela toda, estilo StatusInvest
st.set_page_config(page_title="Meu Portfólio", layout="wide", page_icon="📈")

# =========================================================================== #
# definindo o caminho para a pasta data
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True) 

INPUT_PATH = DATA_DIR / "historico_operacoes.csv"
OUTPUT_PATH = DATA_DIR / "carteira_atualizada.csv"

# =========================================================================== #
# SIDEBAR: Barra com dados para input na lateral
# =========================================================================== #

st.sidebar.header("Cadastrar Operação")

# A escolha da Classe fica FORA do form para a tela poder se adaptar instantaneamente
classe_ativo = st.sidebar.radio(
    "Classe do Investimento", 
    ["Renda Variável (Ações/FIIs)", "Renda Fixa"]
)

with st.sidebar.form("nova_operacao"):
    data = st.date_input("Data da Operação")
    
    # Dicionário base para salvar no CSV (já com campos vazios preparados)
    dados_operacao = {
        'Data': data, 'Classe': classe_ativo, 'Ticker': None, 'Operacao': None,
        'Quantidade': 0, 'Preco_Unitario': 0.0, 'Taxas': 0.0,
        'Nome_RF': None, 'Tipo_RF': None, 'Indexador_RF': None, 
        'Taxa_RF': 0.0, 'Vencimento_RF': None
    }

    # --- CAMPOS PARA RENDA VARIÁVEL ---
    if classe_ativo == "Renda Variável (Ações/FIIs)":
        dados_operacao['Ticker'] = st.text_input("Ticker (ex: ITUB4, KNRI11)", max_chars=6).upper()
        dados_operacao['Operacao'] = st.selectbox("Operação", ["Compra", "Venda"])
        dados_operacao['Quantidade'] = st.number_input("Quantidade", min_value=1)
        dados_operacao['Preco_Unitario'] = st.number_input("Preço Unitário (R$)", min_value=0.01)
        dados_operacao['Taxas'] = st.number_input("Taxas (R$)", min_value=0.0)

    # --- CAMPOS PARA RENDA FIXA ---
    elif classe_ativo == "Renda Fixa":
        dados_operacao['Nome_RF'] = st.text_input("Nome (ex: CDB Banco Itaú)")
        dados_operacao['Operacao'] = "Aplicação" # Padronizamos para facilitar
        dados_operacao['Tipo_RF'] = st.selectbox("Tipo", ["CDB", "LCI", "LCA", "Tesouro"])
        dados_operacao['Indexador_RF'] = st.selectbox("Indexador", ["CDI", "IPCA+", "Pré-fixado", "Selic"])
        dados_operacao['Taxa_RF'] = st.number_input("Taxa Contratada (%)", min_value=0.0, format="%.2f")
        dados_operacao['Preco_Unitario'] = st.number_input("Valor Aplicado (R$)", min_value=0.01)
        dados_operacao['Quantidade'] = 1 # Para RF, vamos tratar como 1 "cota" do valor total
        dados_operacao['Vencimento_RF'] = st.date_input("Data de Vencimento")

    submit = st.form_submit_button("Salvar Operação")
    
    if submit:
        # Cria a nova linha usando o dicionário preenchido
        nova_linha = pd.DataFrame([dados_operacao])
        
        if INPUT_PATH.exists():
            df_existente = pd.read_csv(INPUT_PATH, sep=';')
            df_atualizado = pd.concat([df_existente, nova_linha], ignore_index=True)
        else:
            df_atualizado = nova_linha
            
        df_atualizado.to_csv(INPUT_PATH, sep=';', index=False)
        st.success("Operação salva com sucesso!")

# =========================================================================== #
# TELA PRINCIPAL: DASHBOARD
# =========================================================================== #
st.title("📊 Visão Geral do Portfólio")

if INPUT_PATH.exists():
    df_historico = pd.read_csv(INPUT_PATH, sep=';')
    
    if not df_historico.empty:
        try:
            # Roda o nosso backend
            df_final = gerar_carteira_atualizada(df_historico)
            
            # --- 1. SEÇÃO DE KPIs (CARDS TOPO) ---
            patrimonio_total = df_final['Valor_Atual'].sum()
            investimento_total = df_final['Total_Investido'].sum()
            lucro_total = patrimonio_total - investimento_total
            rentab_geral = (lucro_total / investimento_total) * 100 if investimento_total > 0 else 0
            
            # Função rápida para formatar no padrão Brasileiro R$ 1.000,00
            def formata_br(valor):
                return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # Divide a tela em 4 colunas para os Cards
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Patrimônio Atual", formata_br(patrimonio_total))
            c2.metric("Valor Investido", formata_br(investimento_total))
            
            # O st.metric já deixa a rentabilidade verde/vermelha automaticamente!
            c3.metric("Lucro/Prejuízo", formata_br(lucro_total), f"{rentab_geral:.2f}%")
            
            # Placeholder para o DY (Futura implementação no Backend)
            c4.metric("Dividend Yield (Estimado)", "6.50 %") 
            
            st.divider() # Cria uma linha separadora elegante
            
            # --- 2. SEÇÃO DE GRÁFICOS E TABELA ---
            # Divide a tela: Gráfico ocupa peso 1.5, Tabela ocupa peso 2.5
            col_grafico, col_tabela = st.columns([1.5, 2.5]) 
            
            with col_grafico:
                st.markdown("#### Composição da Carteira")
                # Cria um Gráfico de Rosca (Donut) interativo
                fig = px.pie(
                    df_final, 
                    values='Valor_Atual', 
                    names='Ticker', 
                    hole=0.5, # Tamanho do furo no meio
                    color_discrete_sequence=px.colors.sequential.Teal
                )
                # Remove fundo e ajusta margens do gráfico
                fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_tabela:
                st.markdown("#### Meus Ativos")
                # Tabela estilizada
                st.dataframe(
                    df_final,
                    use_container_width=True,
                    hide_index=True, # Remove aqueles números 0, 1, 2 do lado esquerdo
                    column_config={
                        "logourl": st.column_config.ImageColumn("Logo"),
                        "Ticker": st.column_config.TextColumn("Ativo", width="small"),
                        "Qtd_Cotas": st.column_config.NumberColumn("Qtd"),
                        "Preco_Medio": st.column_config.NumberColumn("PM", format="R$ %.2f"),
                        "regularMarketPrice": st.column_config.NumberColumn("Cotação", format="R$ %.2f"),
                        "Total_Investido": st.column_config.NumberColumn("Investido", format="R$ %.2f"),
                        "Valor_Atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                        "Lucro_Prejuizo_R$": st.column_config.NumberColumn("Retorno (R$)", format="R$ %.2f"),
                        "Rentabilidade_%": st.column_config.NumberColumn("Rentab.", format="%.2f %%")
                    }
                )
                
        except requests.exceptions.HTTPError as e:
            st.error("🚨 Ocorreu um erro ao consultar a API. Verifique se há algum Ticker digitado errado no histórico!")
    else:
        st.info("O histórico está vazio. Cadastre uma operação ao lado.")
else:
    st.warning("Nenhum histórico encontrado. Cadastre a sua primeira operação na barra lateral!")
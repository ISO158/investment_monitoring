# aqui vamos adicionar o streamlit como front do app

import streamlit as st
import pandas as pd
import plotly.express as px # Nova biblioteca de gráficos
import requests

from backend import gerar_carteira_atualizada, get_taxas_bcb,get_stock_quote # importando as funções do backend
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
# BARRA LATERAL: INPUT DE DADOS DINÂMICO
# =========================================================================== #
st.sidebar.header("Cadastrar Operação")

# A escolha da Classe
classe_ativo = st.sidebar.radio(
    "Classe do Investimento", 
    ["Renda Variável (Ações/FIIs)", "Renda Fixa"]
)

with st.sidebar.form("nova_operacao"):
    data = st.date_input("Data da Operação")
    
    # Adicionamos 'Liquidez_Diaria' ao dicionário base
    dados_operacao = {
        'Data': data, 'Classe': classe_ativo, 'Ticker': None, 'Operacao': None,
        'Quantidade': 0, 'Preco_Unitario': 0.0, 'Taxas': 0.0,
        'Nome_RF': None, 'Tipo_RF': None, 'Indexador_RF': None, 
        'Taxa_RF': 0.0, 'Vencimento_RF': None, 'Liquidez_Diaria': False
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
        taxas_macro = get_taxas_bcb()
        dados_operacao['Nome_RF'] = st.text_input("Nome (ex: CDB Banco Itaú)")
        dados_operacao['Operacao'] = "Aplicação" 
        dados_operacao['Tipo_RF'] = st.selectbox("Tipo", ["CDB", "LCI", "LCA", "Tesouro"])
        dados_operacao['Indexador_RF'] = st.selectbox("Indexador", [f"CDI {taxas_macro['CDI']}%", 
                                                                    f"IPCA+ {taxas_macro['IPCA']}%", 
                                                                    "Pré-fixado", 
                                                                    f"Selic {taxas_macro['SELIC']}%"])
        dados_operacao['Taxa_RF'] = st.number_input("Taxa Contratada (%)", min_value=0.0, format="%.2f")
        dados_operacao['Preco_Unitario'] = st.number_input("Valor Aplicado (R$)", min_value=0.01)
        dados_operacao['Quantidade'] = 1 
        dados_operacao['Vencimento_RF'] = st.date_input("Data de Vencimento")
        # NOVO CAMPO: Checkbox de Liquidez
        dados_operacao['Liquidez_Diaria'] = st.checkbox("Liquidez Diária")

    submit = st.form_submit_button("Salvar Operação")
    
    if submit:
        ativo_valido = True
        
        # 1. VALIDAÇÃO: Se for ação, testa na API antes de salvar!
        if classe_ativo == "Renda Variável (Ações/FIIs)":
            ticker_digitado = dados_operacao['Ticker']
            
            # Impede de salvar se o usuário não digitar nada
            if not ticker_digitado:
                ativo_valido = False
                st.error("🚨 Você precisa digitar um Ticker válido!")
            else:
                try:
                    # Passa o ticker digitado na função.
                    # get_stock_quote vai lançar uma exceção se a Brapi devolver 404 (Not Found)
                    get_stock_quote([ticker_digitado])
                except Exception:
                    ativo_valido = False
                    st.error(f"🚨 Ticker '{ticker_digitado}' inválido ou não encontrado na B3! A operação NÃO foi salva.")
        
        # 2. SALVAMENTO: Só executa se passar no teste (ou se for Renda Fixa)
        if ativo_valido:
            nova_linha = pd.DataFrame([dados_operacao])
            
            if INPUT_PATH.exists():
                df_existente = pd.read_csv(INPUT_PATH, sep=';')
                df_atualizado = pd.concat([df_existente, nova_linha], ignore_index=True)
            else:
                df_atualizado = nova_linha
                
            df_atualizado.to_csv(INPUT_PATH, sep=';', index=False)
            st.success("✅ Operação salva com sucesso!")
            st.rerun() # Atualiza a tela automaticamente para limpar o form

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
            col_grafico, col_tabela = st.columns([1.5, 2.5]) 
            
            with col_grafico:
                st.markdown("#### Composição da Carteira")
                # Gráfico agora é baseado no 'Ativo' genérico
                fig = px.pie(df_final, values='Valor_Atual', names='Ativo', hole=0.5, color_discrete_sequence=px.colors.sequential.Teal)
                fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_tabela:
                st.markdown("#### Meus Ativos")
                
                filtro = st.radio("Filtrar por Classe:", ["Todas", "Renda Variável (Ações/FIIs)", "Renda Fixa"], horizontal=True)
                
                # 1. Configuração base das colunas
                col_config = {
                    "logourl": st.column_config.ImageColumn("Logo/Index"),
                    "Ativo": st.column_config.TextColumn("Ativo/Nome", width="medium"),
                    "Qtd_Cotas": st.column_config.NumberColumn("Qtd"),
                    "Preco_Medio": st.column_config.NumberColumn("PM / Aporte", format="R$ %.2f"),
                    "Total_Investido": st.column_config.NumberColumn("Investido", format="R$ %.2f"),
                    "Valor_Atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                    "Lucro_Prejuizo_R$": st.column_config.NumberColumn("Retorno (R$)", format="R$ %.2f"),
                    "Rentabilidade_%": st.column_config.NumberColumn("Rentab.", format="%.2f %%"),
                    "Classe": None,         # Esconde sempre
                    "Indexador_RF": None    # Esconde sempre (já está na logo)
                }
                
                # 2. Lógica Dinâmica para Ocultar/Mostrar colunas e Filtrar os dados
                if filtro == "Todas":
                    col_config["regularMarketPrice"] = None # Esconde Cotação
                    col_config["Taxa_RF"] = None            # Esconde Taxa %
                    df_exibicao = df_final
                    
                elif filtro == "Renda Variável (Ações/FIIs)":
                    col_config["regularMarketPrice"] = st.column_config.NumberColumn("Cotação", format="R$ %.2f")
                    col_config["Taxa_RF"] = None
                    df_exibicao = df_final[df_final['Classe'] == filtro]
                    
                elif filtro == "Renda Fixa":
                    col_config["regularMarketPrice"] = None
                    col_config["Taxa_RF"] = st.column_config.NumberColumn("Taxa Contratada", format="%.2f %%")
                    df_exibicao = df_final[df_final['Classe'] == filtro]

                # 3. Lógica de Cores (Verde/Vermelho nas linhas)
                def colorir_linhas(row):
                    rentab = row['Rentabilidade_%']
                    if rentab > 0:
                        color = 'rgba(76, 175, 80, 0.15)' # Fundo verde bem suave
                    elif rentab < 0:
                        color = 'rgba(244, 67, 54, 0.15)' # Fundo vermelho bem suave
                    else:
                        color = '' # Fica com a cor padrão do Streamlit
                    return [f'background-color: {color}' for _ in row]

                # Aplica as cores no DataFrame que será exibido
                df_styled = df_exibicao.style.apply(colorir_linhas, axis=1)

                st.dataframe(
                    df_styled, 
                    use_container_width=True,
                    hide_index=True,
                    column_config=col_config
                )
                
        except requests.exceptions.HTTPError as e:
            st.error("🚨 Ocorreu um erro ao consultar a API. Verifique se há algum Ticker digitado errado no histórico!")
    else:
        st.info("O histórico está vazio. Cadastre uma operação ao lado.")
else:
    st.warning("Nenhum histórico encontrado. Cadastre a sua primeira operação na barra lateral!")
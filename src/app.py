# aqui vamos adicionar o streamlit como front do app

import streamlit as st
import pandas as pd
import plotly.express as px # Nova biblioteca de gráficos
import requests

from backend import gerar_carteira_atualizada, get_taxas_bcb, get_stock_quote # importando as funções do backend
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
# BARRA LATERAL: INPUT DE DADOS DINÂMICO (ÁREA ISOLADA)
# =========================================================================== #

@st.fragment
def formulario_dinamico():
    # Tudo dentro desta função roda em uma "bolha" independente da tela principal!
    st.header("Cadastrar Operação")

    # Controle Mágico para limpar campos
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0
    f_id = st.session_state.form_id

    # A escolha da Classe
    classe_ativo = st.radio(
        "Classe do Investimento", 
        ["Renda Variável (Ações/FIIs)", "Renda Fixa"],
        key=f"classe_{f_id}"
    )

    data = st.date_input("Data da Operação", key=f"data_{f_id}")

    dados_operacao = {
        'Data': data, 'Classe': classe_ativo, 'Ticker': None, 'Operacao': None,
        'Quantidade': 0, 'Preco_Unitario': 0.0, 'Taxas': 0.0,
        'Nome_RF': None, 'Tipo_RF': None, 'Indexador_RF': None, 
        'Taxa_RF': 0.0, 'Vencimento_RF': None, 'Liquidez_Diaria': False
    }

    # --- CAMPOS PARA RENDA VARIÁVEL ---
    if classe_ativo == "Renda Variável (Ações/FIIs)":
        dados_operacao['Ticker'] = st.text_input("Ticker (ex: ITUB4, KNRI11)", max_chars=6, key=f"tkr_{f_id}").upper()
        dados_operacao['Operacao'] = st.selectbox("Operação", ["Compra", "Venda"], key=f"op_rv_{f_id}")
        dados_operacao['Quantidade'] = st.number_input("Quantidade", min_value=1, value=1, key=f"qtd_{f_id}")
        dados_operacao['Preco_Unitario'] = st.number_input("Preço Unitário (R$)", min_value=0.01, value=10.00, step=1.00, key=f"preco_rv_{f_id}")
        dados_operacao['Taxas'] = st.number_input("Taxas (R$)", min_value=0.0, value=0.0, step=0.50, key=f"taxa_rv_{f_id}")

    # --- CAMPOS PARA RENDA FIXA ---
    elif classe_ativo == "Renda Fixa":
        taxas_macro = get_taxas_bcb()
        dados_operacao['Nome_RF'] = st.text_input("Nome (ex: CDB Banco Itaú)", key=f"nome_rf_{f_id}")
        dados_operacao['Operacao'] = "Aplicação" 
        dados_operacao['Tipo_RF'] = st.selectbox("Tipo", ["CDB", "LCI", "LCA", "Tesouro"], key=f"tipo_rf_{f_id}")

        labels_indexador = {
            "CDI": f"CDI ({taxas_macro['CDI']}%)",
            "IPCA+": f"IPCA+ ({taxas_macro['IPCA']}%)",
            "Selic": f"Selic ({taxas_macro['SELIC']}%)",
            "Pré-fixado": "Pré-fixado"
        }
        dados_operacao['Indexador_RF'] = st.selectbox(
            "Indexador", 
            options=["CDI", "IPCA+", "Pré-fixado", "Selic"],
            format_func=lambda x: labels_indexador[x],
            key=f"idx_rf_{f_id}"
        )

        idx_escolhido = dados_operacao['Indexador_RF']
        
        if idx_escolhido in ["CDI", "Selic"]:
            lbl_taxa, val_taxa, step_taxa, dica = f"Taxa Contratada (% do {idx_escolhido})", 100.0, 1.0, f"Ex: Para 110% do {idx_escolhido}, digite 110"
        elif idx_escolhido == "IPCA+":
            lbl_taxa, val_taxa, step_taxa, dica = "Taxa Adicional (IPCA + %)", 5.0, 0.5, "Ex: Para IPCA + 5.5%, digite apenas 5.5"
        else: # Pré-fixado
            lbl_taxa, val_taxa, step_taxa, dica = "Taxa Anual (%)", 10.0, 0.5, "Ex: Para 12% ao ano, digite 12"

        dados_operacao['Taxa_RF'] = st.number_input(lbl_taxa, min_value=0.0, value=val_taxa, step=step_taxa, format="%.2f", help=dica, key=f"taxa_rf_val_{f_id}")
        dados_operacao['Preco_Unitario'] = st.number_input("Valor Aplicado (R$)", min_value=0.01, value=100.00, step=10.00, key=f"preco_rf_{f_id}")
        dados_operacao['Quantidade'] = 1 
        dados_operacao['Vencimento_RF'] = st.date_input("Data de Vencimento", key=f"venc_rf_{f_id}")
        dados_operacao['Liquidez_Diaria'] = st.checkbox("Liquidez Diária", key=f"liq_rf_{f_id}")

    st.divider()
    submit = st.button("Salvar Operação", type="primary", use_container_width=True, key=f"btn_salvar_{f_id}")

    if submit:
        ativo_valido = True
        
        if classe_ativo == "Renda Variável (Ações/FIIs)":
            ticker_digitado = dados_operacao['Ticker']
            if not ticker_digitado:
                ativo_valido = False
                st.error("🚨 Você precisa digitar um Ticker válido!")
            else:
                try:
                    get_stock_quote([ticker_digitado])
                except Exception:
                    ativo_valido = False
                    st.error(f"🚨 Ticker '{ticker_digitado}' inválido ou não encontrado na B3! A operação NÃO foi salva.")
        
        if ativo_valido:
            nova_linha = pd.DataFrame([dados_operacao])
            
            if INPUT_PATH.exists():
                df_existente = pd.read_csv(INPUT_PATH, sep=';')
                df_atualizado = pd.concat([df_existente, nova_linha], ignore_index=True)
            else:
                df_atualizado = nova_linha
                
            df_atualizado.to_csv(INPUT_PATH, sep=';', index=False)
            st.success("✅ Operação salva com sucesso!")
            
            st.session_state.form_id += 1
            st.rerun() # Como a tabela precisa puxar o novo CSV salvo, chamamos o rerun para atualizar o Dashboard

# Chamamos a nossa "bolha" mágica para dentro da barra lateral
with st.sidebar:
    formulario_dinamico()

# =========================================================================== #
# TELA PRINCIPAL: DASHBOARD
# =========================================================================== #
st.title("Minha Carteira")

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
            
            # --- NOVO: Cálculo do DY Médio da Carteira (Média Ponderada) ---
            if patrimonio_total > 0:
                dy_medio_carteira = (df_final['Valor_Atual'] * df_final['DY_%']).sum() / patrimonio_total
            else:
                dy_medio_carteira = 0.0
            
            def formata_br(valor):
                return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Patrimônio Atual", formata_br(patrimonio_total))
            c2.metric("Valor Investido", formata_br(investimento_total))
            c3.metric("Lucro/Prejuízo", formata_br(lucro_total), f"{rentab_geral:.2f}%")
            
            # O Card agora exibe o valor matemático real!
            c4.metric("Dividend Yield (12m)", f"{dy_medio_carteira:.2f}%")
            
            st.divider() # Cria uma linha separadora elegante
            
            # ==========================================================
            # --- 2. SEÇÃO DE FILTROS GLOBAIS ---
            # O filtro foi movido para cima para comandar Gráfico e Tabela
            # ==========================================================
            # st.markdown("#### 🎯 Explorar Carteira")
            filtro = st.radio(
                "Selecione a visualização:", 
                ["Todas", "Renda Variável (Ações/FIIs)", "Renda Fixa"], 
                horizontal=True,
                label_visibility="collapsed",
                key="filtro_tabela"
            )

            # 1. Configura a Lógica do Filtro: Qual fatia do bolo vamos mostrar?
            if filtro == "Todas":
                df_exibicao = df_final
                coluna_agrupamento = 'Classe' 
            else:
                df_exibicao = df_final[df_final['Classe'] == filtro]
                coluna_agrupamento = 'Ativo'

            # ==========================================================
            # --- 3. SEÇÃO DE GRÁFICOS E TABELA ---
            # ==========================================================
            col_grafico, col_tabela = st.columns([1.5, 2.5]) 
            
            with col_grafico:
                # Proteção: Só desenha o gráfico se tiver dinheiro investido nessa classe
                if df_exibicao['Valor_Atual'].sum() > 0:
                    fig = px.pie(
                        df_exibicao, 
                        values='Valor_Atual', 
                        names=coluna_agrupamento, # Dinâmico: Aqui acontece a mágica da mudança!
                        hole=0.45, 
                        color_discrete_sequence=px.colors.sequential.Teal
                    )
                    
                    # Deixa o gráfico mais bonito: legenda embaixo e % dentro das fatias
                    fig.update_traces(textposition='inside', textinfo='percent')
                    fig.update_layout(
                        margin=dict(t=10, b=10, l=0, r=0), 
                        paper_bgcolor="rgba(0,0,0,0)",
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nenhum saldo para exibir neste filtro.")
                
            with col_tabela:
                # 2. Configuração base das colunas (Adicionamos o DY)
                col_config = {
                    "logourl": st.column_config.ImageColumn("Logo"),
                    "Ativo": st.column_config.TextColumn("Ativo/Nome", width="medium"),
                    "Qtd_Cotas": st.column_config.NumberColumn("Qtd"),
                    "Preco_Medio": st.column_config.NumberColumn("PM / Aporte", format="R$ %.2f"),
                    "Total_Investido": st.column_config.NumberColumn("Investido", format="R$ %.2f"),
                    "Valor_Atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                    "Lucro_Prejuizo_R$": st.column_config.NumberColumn("Retorno (R$)", format="R$ %.2f"),
                    "Rentabilidade_%": st.column_config.NumberColumn("Rentab.", format="%.2f %%"),
                    "DY_%": st.column_config.NumberColumn("DY (12m)", format="%.2f %%"), # Nova Coluna Base
                    "Classe": None,         
                    "Indexador_RF": None    
                }
                
                # 3. Lógica para esconder colunas baseado no Filtro
                if filtro == "Todas":
                    col_config["regularMarketPrice"] = None
                    col_config["Taxa_RF"] = None
                    col_config["DY_%"] = None # Esconde o DY na visão geral
                    
                elif filtro == "Renda Variável (Ações/FIIs)":
                    col_config["regularMarketPrice"] = st.column_config.NumberColumn("Cotação", format="R$ %.2f")
                    col_config["Taxa_RF"] = None
                    # A coluna "DY_%", por não estar com 'None' aqui, aparecerá nativamente!
                    
                elif filtro == "Renda Fixa":
                    col_config["regularMarketPrice"] = None
                    col_config["Taxa_RF"] = st.column_config.NumberColumn("Taxa Contratada", format="%.2f %%")
                    col_config["DY_%"] = None # Esconde o DY na renda fixa

                # 4. Lógica de Cores (Verde/Vermelho)
                def colorir_linhas(row):
                    rentab = row['Rentabilidade_%']
                    if rentab > 0:
                        color = 'rgba(76, 175, 80, 0.15)' 
                    elif rentab < 0:
                        color = 'rgba(244, 67, 54, 0.15)' 
                    else:
                        color = '' 
                    return [f'background-color: {color}' for _ in row]

                df_styled = df_exibicao.style.apply(colorir_linhas, axis=1)

                st.dataframe(
                    df_styled, 
                    use_container_width=True,
                    hide_index=True,
                    column_config=col_config
                )
                
        except requests.exceptions.HTTPError as e:
            st.error("🚨 Ocorreu um erro ao consultar a API da B3. Verifique a conexão.")
    else:
        st.info("O histórico está vazio. Cadastre uma operação ao lado.")
else:
    st.warning("Nenhum histórico encontrado. Cadastre a sua primeira operação na barra lateral!")
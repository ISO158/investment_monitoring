# aqui vamos adicionar o streamlit como front do app

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go          
from plotly.subplots import make_subplots 
import requests

# Atualize a linha de importação do backend para puxar a função get_stock_history
from backend import gerar_carteira_atualizada, get_taxas_bcb, get_stock_quote, get_stock_history 
from pathlib import Path

# Importa o cérebro da IA de outro lugar!
from agente_ia import gerar_analise_ia

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
# BARRA LATERAL: INPUT DE DADOS DINÂMICO (ARQUITETURA HÍBRIDA E INTUITIVA)
# =========================================================================== #

@st.fragment
def formulario_dinamico():
    st.header("Cadastrar Operação")

    # Esconde a mensagem chata de "Press enter to submit"
    st.markdown(
        """<style>[data-testid="InputInstructions"] { display: none !important; }</style>""", 
        unsafe_allow_html=True
    )

    # -----------------------------------------------------------------------
    # 1. CABEÇALHO DINÂMICO (atualiza de maneira dinâmica)
    # -----------------------------------------------------------------------
    classe_ativo = st.radio("Classe do Investimento", ["Renda Variável (Ações/FIIs)", "Renda Fixa"])
    
    tipo_rf, indexador_rf = None, None
    
    # Se for Renda Fixa, o Tipo e o Indexador aparecem logo em seguida, de forma lógica!
    if classe_ativo == "Renda Fixa":
        c1, c2 = st.columns(2)
        tipo_rf = c1.selectbox("Tipo", ["CDB", "LCI", "LCA", "Tesouro"])
        
        taxas_macro = get_taxas_bcb()
        labels_indexador = {
            "CDI": f"CDI ({taxas_macro['CDI']}%)",
            "IPCA+": f"IPCA+ ({taxas_macro['IPCA']}%)",
            "Selic": f"Selic ({taxas_macro['SELIC']}%)",
            "Pré-fixado": "Pré-fixado"
        }
        indexador_rf = c2.selectbox(
            "Indexador", 
            options=["CDI", "IPCA+", "Pré-fixado", "Selic"],
            format_func=lambda x: labels_indexador[x]
        )

    # -----------------------------------------------------------------------
    # 2. CORPO DO FORMULÁRIO (Blindado - Não recarrega enquanto digita)
    # -----------------------------------------------------------------------
    with st.form("form_nova_operacao", clear_on_submit=True):
        
        dados_operacao = {
            'Classe': classe_ativo, 'Ticker': None, 'Operacao': None,
            'Quantidade': 0, 'Preco_Unitario': 0.0, 'Taxas': 0.0,
            'Nome_RF': None, 'Tipo_RF': tipo_rf, 'Indexador_RF': indexador_rf, 
            'Taxa_RF': 0.0, 'Vencimento_RF': None, 'Liquidez_Diaria': False
        }

        # --- CAMPOS PARA RENDA VARIÁVEL ---
        if classe_ativo == "Renda Variável (Ações/FIIs)":
            dados_operacao['Ticker'] = st.text_input("Ticker (ex: ITUB4, KNRI11)", max_chars=6).upper()
            dados_operacao['Operacao'] = st.selectbox("Operação", ["Compra", "Venda"])
            dados_operacao['Data'] = st.date_input("Data da Operação")
            
            c_qtd, c_preco = st.columns(2)
            dados_operacao['Quantidade'] = c_qtd.number_input("Quantidade", min_value=1, value=1)
            dados_operacao['Preco_Unitario'] = c_preco.number_input("Preço (R$)", min_value=0.01, value=10.00, step=1.00)
            dados_operacao['Taxas'] = st.number_input("Taxas (R$)", min_value=0.0, value=0.0, step=0.50)

        # --- CAMPOS PARA RENDA FIXA ---
        elif classe_ativo == "Renda Fixa":
            dados_operacao['Operacao'] = "Aplicação" 
            dados_operacao['Quantidade'] = 1  # <--- A LINHA QUE FALTAVA AQUI!
            dados_operacao['Nome_RF'] = st.text_input("Nome do Ativo (ex: CDB Banco Itaú)")
            
            if indexador_rf in ["CDI", "Selic"]:
                lbl_taxa, val_taxa, step_taxa, dica = f"Taxa (% do {indexador_rf})", 100.0, 1.0, f"Ex: Para 110% do {indexador_rf}, digite 110"
            elif indexador_rf == "IPCA+":
                lbl_taxa, val_taxa, step_taxa, dica = "Taxa Adicional (IPCA + %)", 5.0, 0.5, "Ex: Para IPCA + 5.5%, digite apenas 5.5"
            else: 
                lbl_taxa, val_taxa, step_taxa, dica = "Taxa Anual (%)", 10.0, 0.5, "Ex: Para 12% ao ano, digite 12"

            c_taxa, c_valor = st.columns(2)
            dados_operacao['Taxa_RF'] = c_taxa.number_input(lbl_taxa, min_value=0.0, value=val_taxa, step=step_taxa, format="%.2f", help=dica)
            dados_operacao['Preco_Unitario'] = c_valor.number_input("Valor Aplicado (R$)", min_value=0.01, value=100.00, step=10.00)
            
            c_data, c_venc = st.columns(2)
            dados_operacao['Data'] = c_data.date_input("Data da Aplicação")
            dados_operacao['Vencimento_RF'] = c_venc.date_input("Data de Vencimento")
            
            dados_operacao['Liquidez_Diaria'] = st.checkbox("Possui Liquidez Diária?")

        submit = st.form_submit_button("Salvar Operação", type="primary", use_container_width=True)

    # -----------------------------------------------------------------------
    # 3. LÓGICA DE SALVAMENTO
    # -----------------------------------------------------------------------
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
            st.rerun() 

# Renderiza a estrutura na tela lateral
with st.sidebar:
    formulario_dinamico()

# =========================================================================== #
# TELA PRINCIPAL: DASHBOARD (NOVA ESTRUTURA PROFISSIONAL)
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
            c4.metric("Dividend Yield (12m)", f"{dy_medio_carteira:.2f}%")
            
            st.divider()
            
            # ==========================================================
            # --- NOVO: 2. EVOLUÇÃO HISTÓRICA E AGENTE IA ---
            # ==========================================================
            col_evol, col_ai = st.columns([2.5, 1.5])
            
            with col_evol:
                # Mockup: Como ainda não temos o motor que calcula o histórico diário da carteira no passado,
                # criamos um gráfico base_100 provisório para demarcar a região visualmente.
                st.caption("Comparativo Histórico vs Benchmarks (Ilustrativo - Requer Motor Histórico)")
                datas_mock = pd.date_range(start=pd.Timestamp.today() - pd.DateOffset(months=6), periods=6, freq='ME')
                df_mock = pd.DataFrame({
                    'Data': datas_mock,
                    'Minha Carteira': [100, 102, 105, 104, 110, 115],
                    'IBOV': [100, 98, 101, 103, 102, 105],
                    'CDI': [100, 101.5, 102.5, 103.5, 104.5, 105.5]
                })
                fig_evol = px.line(df_mock, x='Data', y=['Minha Carteira', 'IBOV', 'CDI'], 
                                   color_discrete_sequence=['#00C4B4', '#1E3A8A', '#F59E0B'])
                fig_evol.update_layout(margin=dict(t=10, b=10, l=0, r=0), 
                                       legend=dict(orientation="h", y=-0.2, title=""),
                                       yaxis_title="Evolução (Base 100)", xaxis_title="")
                st.plotly_chart(fig_evol, use_container_width=True)

            # Output do Agente de IA - Gemini
            with col_ai:
                st.markdown("##### 🤖 IA Analista (Gemini)")
                
                # 1. Cria a variável na memória se ela não existir
                if "relatorio_ia" not in st.session_state:
                    st.session_state.relatorio_ia = None
                    
                # O botão agora apenas SALVA a resposta na memória
                if st.button("Gerar Análise da Carteira", type="primary", use_container_width=True):
                    with st.spinner("O Agente está avaliando seus ativos..."):
                        st.session_state.relatorio_ia = gerar_analise_ia(df_final)
                        
                # 2. Renderiza a resposta SEMPRE que houver algo na memória!
                if st.session_state.relatorio_ia:
                    with st.expander("📊 Relatório Inteligente Aberto", expanded=True):
                        st.write(st.session_state.relatorio_ia)
                else:
                    st.info(
                        "**Agente Pronto!**\n\n"
                        "Clique no botão acima para o Gemini cruzar a rentabilidade, "
                        "o DY e a alocação dos seus ativos e gerar insights."
                    )
            
            st.divider()

            # ==========================================================
            # --- SEÇÃO INFERIOR ISOLADA (NÃO RECARREGA A TELA TODA) ---
            # ==========================================================
            @st.fragment
            def painel_interativo_ativos(df_final_frag, df_historico_frag):
                
                # --- 3. SEÇÃO DE FILTROS GLOBAIS ---
                filtro = st.radio(
                    "Selecione a visualização:", 
                    ["Todas", "Renda Variável (Ações/FIIs)", "Renda Fixa"], 
                    horizontal=True,
                    label_visibility="collapsed",
                    key="filtro_tabela"
                )

                if filtro == "Todas":
                    df_exibicao = df_final_frag
                    coluna_agrupamento = 'Classe' 
                else:
                    df_exibicao = df_final_frag[df_final_frag['Classe'] == filtro]
                    coluna_agrupamento = 'Ativo'

                # --- 4. SEÇÃO DE GRÁFICOS E TABELA INTERATIVA ---
                col_grafico, col_tabela = st.columns([1.5, 2.5]) 
                
                with col_grafico:
                    if df_exibicao['Valor_Atual'].sum() > 0:
                        fig = px.pie(
                            df_exibicao, values='Valor_Atual', names=coluna_agrupamento,
                            hole=0.45, color_discrete_sequence=px.colors.sequential.Teal
                        )
                        fig.update_traces(textposition='inside', textinfo='percent')
                        fig.update_layout(
                            margin=dict(t=10, b=10, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)",
                            showlegend=True, legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Nenhum saldo para exibir neste filtro.")
                    
                with col_tabela:
                    col_config = {
                        "logourl": st.column_config.ImageColumn("Logo"),
                        "Ativo": st.column_config.TextColumn("Ativo/Nome", width="medium"),
                        "Qtd_Cotas": st.column_config.NumberColumn("Qtd"),
                        "Preco_Medio": st.column_config.NumberColumn("PM / Aporte", format="R$ %.2f"),
                        "Total_Investido": st.column_config.NumberColumn("Investido", format="R$ %.2f"),
                        "Valor_Atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                        "Lucro_Prejuizo_R$": st.column_config.NumberColumn("Retorno (R$)", format="R$ %.2f"),
                        "Rentabilidade_%": st.column_config.NumberColumn("Rentab.", format="%.2f %%"),
                        "DY_%": st.column_config.NumberColumn("DY (12m)", format="%.2f %%"),
                        "Classe": None, "Indexador_RF": None    
                    }
                    
                    if filtro == "Todas":
                        col_config["regularMarketPrice"], col_config["Taxa_RF"], col_config["DY_%"] = None, None, None 
                    elif filtro == "Renda Variável (Ações/FIIs)":
                        col_config["regularMarketPrice"] = st.column_config.NumberColumn("Cotação", format="R$ %.2f")
                        col_config["Taxa_RF"] = None
                    elif filtro == "Renda Fixa":
                        col_config["regularMarketPrice"], col_config["DY_%"] = None, None
                        col_config["Taxa_RF"] = st.column_config.NumberColumn("Taxa Contratada", format="%.2f %%")

                    def colorir_linhas(row):
                        rentab = row['Rentabilidade_%']
                        if rentab > 0: return ['background-color: rgba(76, 175, 80, 0.15)' for _ in row]
                        elif rentab < 0: return ['background-color: rgba(244, 67, 54, 0.15)' for _ in row]
                        return ['' for _ in row]

                    df_styled = df_exibicao.style.apply(colorir_linhas, axis=1)
                    st.caption("👆 *Dica: Clique em qualquer linha da tabela abaixo para ver o histórico detalhado do ativo.*")
                    
                    evento_tabela = st.dataframe(
                        df_styled, use_container_width=True, hide_index=True, column_config=col_config,
                        selection_mode="single-row", on_select="rerun" 
                    )
                    
                # --- 5. RAIO-X DO ATIVO SELECIONADO (DRILL-DOWN) ---
                linhas_selecionadas = evento_tabela.selection.rows
                
                if linhas_selecionadas:
                    st.divider()
                    idx_linha = linhas_selecionadas[0]
                    ativo_clicado = df_exibicao.iloc[idx_linha]['Ativo']
                    classe_clicada = df_exibicao.iloc[idx_linha]['Classe']
                    
                    st.markdown(f"### 🔎 Raio-X: **{ativo_clicado}**")
                    
                    if classe_clicada == "Renda Variável (Ações/FIIs)":
                        df_hist_ativo = df_historico_frag[
                            (df_historico_frag['Classe'] == classe_clicada) & 
                            (df_historico_frag['Ticker'] == ativo_clicado)
                        ].copy()
                    else:
                        df_hist_ativo = df_historico_frag[
                            (df_historico_frag['Classe'] == classe_clicada) & 
                            (df_historico_frag['Nome_RF'].apply(lambda x: str(x) in ativo_clicado))
                        ].copy()
                        
                    if not df_hist_ativo.empty:
                        df_hist_ativo['Data'] = pd.to_datetime(df_hist_ativo['Data'])
                        df_hist_ativo = df_hist_ativo.sort_values('Data')
                        df_hist_ativo['Qtd_Grafico'] = df_hist_ativo.apply(
                            lambda row: row['Quantidade'] if str(row['Operacao']).upper() in ['COMPRA', 'APLICAÇÃO', 'APLICACAO'] else -row['Quantidade'], axis=1
                        )
                        
                        col_graf_hist, col_tab_hist = st.columns([2.5, 1])
                        
                        with col_graf_hist:
                            if classe_clicada == "Renda Variável (Ações/FIIs)":
                                df_cotacoes = get_stock_history(ativo_clicado)
                                fig_hist = make_subplots(specs=[[{"secondary_y": True}]])
                                
                                if not df_cotacoes.empty:
                                    fig_hist.add_trace(go.Scatter(x=df_cotacoes['Data'], y=df_cotacoes['Fechamento'], name='Cotação de Mercado', mode='lines', line=dict(color='#1E3A8A', width=2), hovertemplate='Data: %{x}<br>Cotação: R$ %{y:.2f}<extra></extra>'), secondary_y=False)
                                    
                                compras = df_hist_ativo[df_hist_ativo['Qtd_Grafico'] > 0]
                                vendas = df_hist_ativo[df_hist_ativo['Qtd_Grafico'] < 0]
                                
                                if not compras.empty: fig_hist.add_trace(go.Bar(x=compras['Data'], y=compras['Qtd_Grafico'], name='Minhas Compras', marker_color='rgba(34, 197, 94, 0.4)', hovertemplate='Data: %{x}<br>Comprou: %{y} cotas<extra></extra>'), secondary_y=True)
                                if not vendas.empty: fig_hist.add_trace(go.Bar(x=vendas['Data'], y=vendas['Qtd_Grafico'], name='Minhas Vendas', marker_color='rgba(239, 68, 68, 0.4)', hovertemplate='Data: %{x}<br>Vendeu: %{y} cotas<extra></extra>'), secondary_y=True)
                                    
                                fig_hist.update_layout(title="Histórico de Cotação vs Meus Aportes", margin=dict(t=40, b=10, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode="x unified")
                                fig_hist.update_yaxes(title_text="Cotação (R$)", secondary_y=False)
                                fig_hist.update_yaxes(showticklabels=False, showgrid=False, secondary_y=True)
                                st.plotly_chart(fig_hist, use_container_width=True)
                            else:
                                fig_hist = px.bar(df_hist_ativo, x='Data', y='Qtd_Grafico', color='Operacao', title="Histórico de Aportes Financeiros", text='Preco_Unitario', color_discrete_map={'Compra': '#22C55E', 'Aplicação': '#22C55E', 'Venda': '#EF4444', 'Resgate': '#EF4444'})
                                fig_hist.update_traces(texttemplate='R$ %{text:.2f}', textposition='outside')
                                fig_hist.update_layout(yaxis_title="Quantidade", xaxis_title="")
                                st.plotly_chart(fig_hist, use_container_width=True)
                            
                        with col_tab_hist:
                            st.markdown("**Extrato de Operações**")
                            df_extrato = df_hist_ativo[['Data', 'Operacao', 'Quantidade', 'Preco_Unitario']].copy()
                            df_extrato['Data'] = df_extrato['Data'].dt.strftime('%d/%m/%Y')
                            df_extrato.rename(columns={'Preco_Unitario': 'Preço / Taxa'}, inplace=True)
                            st.dataframe(df_extrato, hide_index=True, use_container_width=True)

            # Chama o fragmento passando os dados!
            painel_interativo_ativos(df_final, df_historico)
                
        except requests.exceptions.HTTPError as e:
            st.error("🚨 Ocorreu um erro ao consultar a API da B3. Verifique a conexão.")
    else:
        st.info("O histórico está vazio. Cadastre uma operação ao lado.")
else:
    st.warning("Nenhum histórico encontrado. Cadastre a sua primeira operação na barra lateral!")
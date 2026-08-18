# definindo as funções de backend

import pandas as pd
import numpy as np
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# =========================================================================== #
# CAMINHOS E CONFIGURAÇÕES
# =========================================================================== #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True) 

INPUT_PATH = DATA_DIR / "historico_operacoes.csv"
OUTPUT_PATH = DATA_DIR / "carteira_atualizada.csv"

# =========================================================================== #
# FUNÇÕES CORE e API de dados das ações
# =========================================================================== #

# Mantenha o seu BASE_URL intacto lá no topo caso use em outras partes do código
BASE_URL = "https://brapi.dev/api/v2"
TOKEN = os.getenv("BRAPI_TOKEN")

def get_stock_quote(symbols):
    # 1. Usamos o endpoint principal que junta cotação e fundamentos
    tickers_str = ",".join(symbols)
    url = f"https://brapi.dev/api/quote/{tickers_str}"
    
    # 2. Solicitamos explicitamente o módulo de estatísticas
    params = {
        "token": TOKEN,
        "modules": "defaultKeyStatistics" 
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()

    json_response = response.json()
    resultados = json_response.get("results", [])
    
    dados_limpos = []
    for acao in resultados:
        # Pega as informações básicas de cotação e imagem
        dado = {
            'shortName': acao.get('shortName'),
            'regularMarketPrice': acao.get('regularMarketPrice'),
            'logourl': acao.get('logourl'),
        }
        
        # 3. Extrai o DY de dentro do bloco defaultKeyStatistics
        stats = acao.get('defaultKeyStatistics', {})
        dado['dividendYield'] = stats.get('dividendYield', 0.0)
        
        dados_limpos.append(dado)
        
    return dados_limpos

# =========================================================================== #
# FUNÇÕES CORE
# =========================================================================== #

def calcular_posicao_atual(df_ops):
    df_ops = df_ops.sort_values(by='Data')
    posicoes = {}
    
    for _, row in df_ops.iterrows():
        classe = row.get('Classe', 'Renda Variável (Ações/FIIs)')
        
        if classe == 'Renda Variável (Ações/FIIs)':
            ativo_exibicao = str(row.get('Ticker', '')).upper()
            chave_unica = ativo_exibicao
            indexador, taxa_rf, data_op = '', 0.0, ''
        else:
            nome = str(row.get('Nome_RF', '')).strip()
            tipo = str(row.get('Tipo_RF', '')).strip()
            indexador = str(row.get('Indexador_RF', '')).strip()
            taxa_rf = row.get('Taxa_RF', 0.0)
            vencimento = str(row.get('Vencimento_RF', '')).strip()
            
            # NOVO: Adicionamos a Data na chave. Aplicações em dias diferentes rendem juros diferentes!
            data_op = str(row.get('Data', '')).strip() 
            chave_unica = f"{nome}_{tipo}_{indexador}_{taxa_rf}_{vencimento}_{data_op}"
            ativo_exibicao = f"{nome} ({tipo} | Venc: {vencimento})"
            
        if pd.isna(chave_unica) or not str(chave_unica).strip():
            continue
            
        op = str(row['Operacao']).upper()
        qtd = row['Quantidade']
        preco = row['Preco_Unitario']
        taxas = row['Taxas']
        
        if chave_unica not in posicoes:
            posicoes[chave_unica] = {
                'Ativo': ativo_exibicao, 'Classe': classe, 'Qtd_Cotas': 0, 
                'Total_Investido': 0.0, 'Preco_Medio': 0.0, 
                'Indexador_RF': indexador, 'Taxa_RF': taxa_rf, 'Data_Aplicacao': data_op
            }
            
        pos = posicoes[chave_unica]
        
        if op in ['COMPRA', 'APLICAÇÃO', 'APLICACAO']:
            pos['Qtd_Cotas'] += qtd
            pos['Total_Investido'] += (qtd * preco) + taxas
            pos['Preco_Medio'] = pos['Total_Investido'] / pos['Qtd_Cotas']
            
        elif op in ['VENDA', 'RESGATE']:
            pos['Qtd_Cotas'] -= qtd
            pos['Total_Investido'] -= (qtd * pos['Preco_Medio'])
            if pos['Qtd_Cotas'] <= 0:
                pos['Qtd_Cotas'] = 0
                pos['Total_Investido'] = 0.0
                pos['Preco_Medio'] = 0.0
                
    df_carteira = pd.DataFrame(list(posicoes.values()))
    if df_carteira.empty:
        return pd.DataFrame(columns=['Ativo', 'Classe', 'Qtd_Cotas', 'Total_Investido', 'Preco_Medio', 'Indexador_RF', 'Taxa_RF', 'Data_Aplicacao'])
    return df_carteira[df_carteira['Qtd_Cotas'] > 0]

# =========================================================================== #
# FUNÇÃO MESTRA (JUNTA TUDO)
# =========================================================================== #
def gerar_carteira_atualizada(df_historico):
    df_carteira = calcular_posicao_atual(df_historico)
    if df_carteira.empty:
        return df_carteira
        
    # --- 1. BUSCA DADOS DE RENDA VARIÁVEL (API BRAPI) ---
    df_rv = df_carteira[df_carteira['Classe'] == 'Renda Variável (Ações/FIIs)']
    tickers_ativos = df_rv['Ativo'].tolist()
    
    df_mercado = pd.DataFrame()
    if tickers_ativos:
        try:
            dados_api = get_stock_quote(tickers_ativos)
            df_mercado = pd.DataFrame(dados_api)
            
            # Captura o DY real das Ações (Se não existir, assume 0)
            if 'dividendYield' in df_mercado.columns:
                df_mercado['DY_%'] = df_mercado['dividendYield'].fillna(0.0) * 100
            else:
                df_mercado['DY_%'] = 0.0
                
            colunas_presentes = [col for col in ['shortName', 'regularMarketPrice', 'logourl', 'DY_%'] if col in df_mercado.columns]
            df_mercado = df_mercado[colunas_presentes]
        except Exception as e:
            print(f"Erro na API Brapi: {e}")
            
    if not df_mercado.empty:
        df_final = pd.merge(df_carteira, df_mercado, left_on='Ativo', right_on='shortName', how='left')
        if 'shortName' in df_final.columns: df_final = df_final.drop(columns=['shortName'])
    else:
        df_final = df_carteira.copy()
        df_final['regularMarketPrice'] = np.nan
        df_final['logourl'] = None
        df_final['DY_%'] = 0.0

    # --- 2. BUSCA TAXAS MACRO PARA RENDA FIXA (API BCB) ---
    taxas_macro = get_taxas_bcb()
    cdi_atual = taxas_macro.get('CDI', 10.5) / 100
    ipca_atual = taxas_macro.get('IPCA', 4.5) / 100
    selic_atual = taxas_macro.get('SELIC', 10.5) / 100

    # --- 3. MATEMÁTICA FINANCEIRA (JUROS COMPOSTOS) ---
    def aplicar_matematica_financeira(row):
        # Se for Ação, devolve a cotação da API e o DY da API
        if row['Classe'] == 'Renda Variável (Ações/FIIs)':
            valor_atual = row['Qtd_Cotas'] * row.get('regularMarketPrice', 0)
            if pd.isna(valor_atual): valor_atual = row['Total_Investido']
            return pd.Series([valor_atual, row.get('DY_%', 0.0)])
            
        # Se for Renda Fixa, calcula o tempo passado e os Juros
        try:
            data_app = pd.to_datetime(row['Data_Aplicacao'])
            hoje = pd.Timestamp.today()
            # Calcula quantos anos se passaram (Usamos 365.25 para precisão de ano bissexto)
            anos_passados = (hoje - data_app).days / 365.25
            if anos_passados < 0: anos_passados = 0

            taxa_contratada = row['Taxa_RF'] / 100

            # Define a Taxa Anual Equivalente baseada no indexador
            if row['Indexador_RF'] == 'CDI':
                taxa_anual = taxa_contratada * cdi_atual  # Ex: 110% do CDI -> 1.10 * 0.105
            elif row['Indexador_RF'] == 'IPCA+':
                taxa_anual = ipca_atual + taxa_contratada # Ex: IPCA + 6% -> 0.045 + 0.06
            elif row['Indexador_RF'] == 'Selic':
                taxa_anual = taxa_contratada * selic_atual
            else: # Pré-fixado
                taxa_anual = taxa_contratada

            # Fórmula dos Juros Compostos: Montante = Capital * (1 + Taxa)^Tempo
            valor_atualizado = row['Total_Investido'] * ((1 + taxa_anual) ** anos_passados)
            
            # Devolve o Novo Valor e a Taxa Anual (que usaremos no lugar do DY)
            return pd.Series([valor_atualizado, taxa_anual * 100])
        except Exception:
            return pd.Series([row['Total_Investido'], 0.0])

    # Aplica a função mágica linha por linha criando as colunas definitivas
    df_final[['Valor_Atual', 'DY_%']] = df_final.apply(aplicar_matematica_financeira, axis=1)
    
    # --- 4. INDICADORES FINAIS DE PERFORMANCE ---
    df_final['Lucro_Prejuizo_R$'] = df_final['Valor_Atual'] - df_final['Total_Investido']
    df_final['Rentabilidade_%'] = np.where(
        df_final['Total_Investido'] > 0,
        (df_final['Lucro_Prejuizo_R$'] / df_final['Total_Investido']) * 100,
        0.0
    )

    # TRUQUE VISUAL DA LOGO
    df_final['Indexador_RF'] = df_final['Indexador_RF'].fillna('')
    url_rf = "https://ui-avatars.com/api/?name=" + df_final['Indexador_RF'].str.replace('+', '%2B') + "&background=0D8ABC&color=fff&length=4&font-size=0.35&bold=true"
    df_final['logourl'] = np.where(df_final['Classe'] == 'Renda Variável (Ações/FIIs)', df_final['logourl'], url_rf)
    
    df_final.to_csv(OUTPUT_PATH, index=False)
    return df_final

# =========================================================================== #
# Coletando dados do CDI, Selic e IPCA acumulado
# =========================================================================== #

# Adicione esta função no seu backend.py
def get_taxas_bcb():
    """
    Busca as taxas macroeconômicas atualizadas direto da API do Banco Central.
    """
    taxas = {'CDI': 0.0, 'IPCA': 0.0, 'SELIC': 0.0}
    try:
        # CDI Anualizado (Código SGS: 4389)
        url_cdi = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json"
        res_cdi = requests.get(url_cdi)
        if res_cdi.status_code == 200:
            taxas['CDI'] = float(res_cdi.json()[0]['valor'])
            
        # IPCA acumulado 12 Meses (Código SGS: 13522)
        url_ipca = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json"
        res_ipca = requests.get(url_ipca)
        if res_ipca.status_code == 200:
            taxas['IPCA'] = float(res_ipca.json()[0]['valor'])
            
        # Taxa Selic Meta (Código SGS: 432)
        url_selic = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        res_selic = requests.get(url_selic)
        if res_selic.status_code == 200:
            taxas['SELIC'] = float(res_selic.json()[0]['valor'])
            
    except Exception as e:
        print(f"Erro ao buscar taxas BCB: {e}")
        
    return taxas
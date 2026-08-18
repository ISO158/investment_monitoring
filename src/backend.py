# definindo as funções de backend

import pandas as pd
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

load_dotenv()
BASE_URL = "https://brapi.dev/api/v2"
TOKEN = os.getenv("BRAPI_TOKEN")

# =========================================================================== #
# FUNÇÕES CORE
# =========================================================================== #

def get_stock_quote(symbols):
    url = f"{BASE_URL}/stocks/quote"
    params = {
        "symbols": ",".join(symbols),
        "token": TOKEN
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    json_response = response.json()
    resultados = json_response.get("results", [])
    
    dados_limpos = [acao['data'] for acao in resultados if 'data' in acao]
    return dados_limpos

def calcular_posicao_atual(df_ops):
    df_ops = df_ops.sort_values(by='Data')
    posicoes = {}
    
    for _, row in df_ops.iterrows():
        ticker = row['Ticker']
        op = row['Operacao'].upper()
        qtd = row['Quantidade']
        preco = row['Preco_Unitario']
        taxas = row['Taxas']
        # REMOVIDA A LINHA DA LOGO DAQUI!
        
        if ticker not in posicoes:
            posicoes[ticker] = {'Qtd_Cotas': 0, 'Total_Investido': 0.0, 'Preco_Medio': 0.0}
            
        pos = posicoes[ticker]
        
        if op == 'COMPRA':
            custo_compra = (qtd * preco) + taxas
            pos['Qtd_Cotas'] += qtd
            pos['Total_Investido'] += custo_compra
            pos['Preco_Medio'] = pos['Total_Investido'] / pos['Qtd_Cotas']
            
        elif op == 'VENDA':
            pos['Qtd_Cotas'] -= qtd
            pos['Total_Investido'] -= (qtd * pos['Preco_Medio'])
            
            if pos['Qtd_Cotas'] <= 0:
                pos['Qtd_Cotas'] = 0
                pos['Total_Investido'] = 0.0
                pos['Preco_Medio'] = 0.0
                
    df_carteira = pd.DataFrame.from_dict(posicoes, orient='index').reset_index()
    df_carteira = df_carteira.rename(columns={'index': 'Ticker'})
    df_carteira = df_carteira[df_carteira['Qtd_Cotas'] > 0]
    
    return df_carteira

# =========================================================================== #
# FUNÇÃO MESTRA (JUNTA TUDO)
# =========================================================================== #
def gerar_carteira_atualizada(df_historico):
    """
    Recebe o histórico bruto, calcula a posição e cruza com a API para trazer
    cotação atual, rentabilidade e LOGO.
    """
    # 1. Calcula a base (suas quantidades e PM)
    df_carteira = calcular_posicao_atual(df_historico)
    
    if df_carteira.empty:
        return df_carteira
        
    # 2. Busca na Brapi apenas as ações que você tem na carteira agora
    tickers_ativos = df_carteira['Ticker'].tolist()
    dados_api = get_stock_quote(tickers_ativos)
    
    # 3. Pega as colunas da API, INCLUINDO A LOGO
    df_mercado = pd.DataFrame(dados_api)[['shortName', 'regularMarketPrice', 'regularMarketChangePercent', 'logourl']]
    
    # 4. Cruza os dados
    df_final = pd.merge(df_carteira, df_mercado, left_on='Ticker', right_on='shortName', how='left')
    
    # 5. Calcula Métricas Finais
    df_final['Valor_Atual'] = df_final['Qtd_Cotas'] * df_final['regularMarketPrice']
    df_final['Lucro_Prejuizo_R$'] = df_final['Valor_Atual'] - df_final['Total_Investido']
    df_final['Rentabilidade_%'] = (df_final['Lucro_Prejuizo_R$'] / df_final['Total_Investido']) * 100
    
    # Remove coluna duplicada e salva o Output
    df_final = df_final.drop(columns=['shortName'])
    df_final.to_csv(OUTPUT_PATH, index=False)
    
    return df_final
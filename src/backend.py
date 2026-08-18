import streamlit as st
import pandas as pd
import os
import requests

from pathlib import Path
from dotenv import load_dotenv

# __file__ é o app.py (src/app.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
# Se não existir, o streamlit vai criar a pasta na raiz do projeto certinho
DATA_DIR.mkdir(parents=True, exist_ok=True) 
print(DATA_DIR)

INPUT_PATH = DATA_DIR / "historico_operacoes.csv"
OUTPUT_PATH = DATA_DIR / "carteira_atualizada.csv"

# =========================================================================== #
load_dotenv()

BASE_URL = "https://brapi.dev/api/v2"
TOKEN = os.getenv("BRAPI_TOKEN")

def get_stock_quote(symbols):
    url = f"{BASE_URL}/stocks/quote"

    params = {
        "symbols": ",".join(symbols),
        "token": TOKEN
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    # Pega o JSON da resposta
    json_response = response.json()
    resultados = json_response.get("results", [])

    # EXTRAÇÃO DO DICIONÁRIO 'data':
    # Percorre cada ação encontrada e extrai apenas a parte que importa (a chave 'data')
    dados_limpos = [acao['data'] for acao in resultados if 'data' in acao]
    
    return dados_limpos

# =========================================================================== #

# preço médio para calcular 

def calcular_posicao_atual(df_ops):
    # Ordena por data para garantir que o cálculo cronológico esteja certo
    df_ops = df_ops.sort_values(by='Data')
    
    posicoes = {}
    
    for _, row in df_ops.iterrows():
        ticker = row['Ticker']
        op = row['Operacao'].upper()
        qtd = row['Quantidade']
        preco = row['Preco_Unitario']
        taxas = row['Taxas']
        
        # Se é a primeira vez que vemos o Ticker, cria o registro zerado
        if ticker not in posicoes:
            posicoes[ticker] = {'Qtd_Cotas': 0, 'Total_Investido': 0.0, 'Preco_Medio': 0.0}
            
        pos = posicoes[ticker]
        
        if op == 'COMPRA':
            # Custo total da compra (inclui taxas)
            custo_compra = (qtd * preco) + taxas
            
            # Atualiza totais
            pos['Qtd_Cotas'] += qtd
            pos['Total_Investido'] += custo_compra
            
            # Recalcula Preço Médio
            pos['Preco_Medio'] = pos['Total_Investido'] / pos['Qtd_Cotas']
            
        elif op == 'VENDA':
            # Venda altera a quantidade, mas o Preço Médio se mantém!
            pos['Qtd_Cotas'] -= qtd
            # Reduz o total investido proporcionalmente às cotas vendidas
            pos['Total_Investido'] -= (qtd * pos['Preco_Medio'])
            
            # Se vender tudo (zerar posição), zera tudo para evitar bugs
            if pos['Qtd_Cotas'] <= 0:
                pos['Qtd_Cotas'] = 0
                pos['Total_Investido'] = 0.0
                pos['Preco_Medio'] = 0.0
                
    # Transforma o dicionário final de volta em um DataFrame
    # E remove as ações que você zerou (vendeu tudo)
    df_carteira = pd.DataFrame.from_dict(posicoes, orient='index').reset_index()
    df_carteira = df_carteira.rename(columns={'index': 'Ticker'})
    df_carteira = df_carteira[df_carteira['Qtd_Cotas'] > 0]
    
    return df_carteira

# =========================================================================== #
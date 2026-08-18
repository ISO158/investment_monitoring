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

# =========================================================================== #
# FUNÇÕES CORE
# =========================================================================== #

def calcular_posicao_atual(df_ops):
    df_ops = df_ops.sort_values(by='Data')
    posicoes = {}
    
    for _, row in df_ops.iterrows():
        classe = row.get('Classe', 'Renda Variável (Ações/FIIs)')
        ativo = row['Ticker'] if classe == 'Renda Variável (Ações/FIIs)' else row['Nome_RF']
        
        if pd.isna(ativo) or not str(ativo).strip():
            continue
            
        op = str(row['Operacao']).upper()
        qtd = row['Quantidade']
        preco = row['Preco_Unitario']
        taxas = row['Taxas']
        
        # Salvando as características únicas da Renda Fixa
        indexador = row.get('Indexador_RF', '')
        taxa_rf = row.get('Taxa_RF', 0.0)
        
        if ativo not in posicoes:
            posicoes[ativo] = {
                'Classe': classe, 'Qtd_Cotas': 0, 'Total_Investido': 0.0, 
                'Preco_Medio': 0.0, 'Indexador_RF': indexador, 'Taxa_RF': taxa_rf
            }
            
        pos = posicoes[ativo]
        
        if op in ['COMPRA', 'APLICAÇÃO', 'APLICACAO']:
            custo_compra = (qtd * preco) + taxas
            pos['Qtd_Cotas'] += qtd
            pos['Total_Investido'] += custo_compra
            pos['Preco_Medio'] = pos['Total_Investido'] / pos['Qtd_Cotas']
            
        elif op in ['VENDA', 'RESGATE']:
            pos['Qtd_Cotas'] -= qtd
            pos['Total_Investido'] -= (qtd * pos['Preco_Medio'])
            if pos['Qtd_Cotas'] <= 0:
                pos['Qtd_Cotas'] = 0
                pos['Total_Investido'] = 0.0
                pos['Preco_Medio'] = 0.0
                
    df_carteira = pd.DataFrame.from_dict(posicoes, orient='index').reset_index()
    df_carteira = df_carteira.rename(columns={'index': 'Ativo'})
    return df_carteira[df_carteira['Qtd_Cotas'] > 0]

# =========================================================================== #
# FUNÇÃO MESTRA (JUNTA TUDO)
# =========================================================================== #
def gerar_carteira_atualizada(df_historico):
    df_carteira = calcular_posicao_atual(df_historico)
    if df_carteira.empty:
        return df_carteira
        
    df_rv = df_carteira[df_carteira['Classe'] == 'Renda Variável (Ações/FIIs)']
    tickers_ativos = df_rv['Ativo'].tolist()
    
    df_mercado = pd.DataFrame()
    if tickers_ativos:
        try:
            dados_api = get_stock_quote(tickers_ativos)
            df_mercado = pd.DataFrame(dados_api)[['shortName', 'regularMarketPrice', 'logourl']]
        except Exception as e:
            print(f"Erro na API Brapi: {e}")
            
    if not df_mercado.empty:
        df_final = pd.merge(df_carteira, df_mercado, left_on='Ativo', right_on='shortName', how='left')
        df_final = df_final.drop(columns=['shortName'])
    else:
        df_final = df_carteira.copy()
        df_final['regularMarketPrice'] = np.nan
        df_final['logourl'] = None
        
    df_final['Valor_Atual'] = np.where(
        df_final['Classe'] == 'Renda Variável (Ações/FIIs)',
        df_final['Qtd_Cotas'] * df_final['regularMarketPrice'].fillna(0),
        df_final['Total_Investido']
    )
    
    df_final['Lucro_Prejuizo_R$'] = df_final['Valor_Atual'] - df_final['Total_Investido']
    df_final['Rentabilidade_%'] = np.where(
        df_final['Total_Investido'] > 0,
        (df_final['Lucro_Prejuizo_R$'] / df_final['Total_Investido']) * 100,
        0.0
    )

    # TRUQUE VISUAL: Gera a logo da Renda Fixa usando a API UI Avatars
    # Ex: Pega "IPCA+" e transforma numa imagem azul com letras brancas
    df_final['Indexador_RF'] = df_final['Indexador_RF'].fillna('')
    url_rf = "https://ui-avatars.com/api/?name=" + df_final['Indexador_RF'].str.replace('+', '%2B') + "&background=0D8ABC&color=fff&length=4&font-size=0.35&bold=true"
    
    df_final['logourl'] = np.where(
        df_final['Classe'] == 'Renda Variável (Ações/FIIs)',
        df_final['logourl'],
        url_rf
    )
    
    df_final.to_csv(OUTPUT_PATH, index=False)
    return df_final

# =========================================================================== #
# Coletando dados do CDI e IPCA acumulado
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
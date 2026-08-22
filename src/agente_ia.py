# separamos o agente de IA para criar uma classe separada com base no princípio de separação de responsabilidades. Isso facilita a manutenção e a escalabilidade do código.

# Estou usando a API do Gemini, armazenada na .env.

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (onde está a GEMINI_API_KEY)
load_dotenv()

# Configuração da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def gerar_analise_ia(df_carteira):
    """
    Recebe o DataFrame da carteira e retorna um relatório de texto gerado pelo LLM.
    """
    if not GEMINI_API_KEY:
        return "🚨 Chave da API do Gemini não encontrada no arquivo .env!"
    
    if df_carteira.empty:
        return "Sua carteira está vazia. Adicione ativos para análise."

    # 1. Filtramos apenas as colunas úteis para não confundir a IA
    resumo = df_carteira[['Ativo', 'Classe', 'Total_Investido', 'Valor_Atual', 'Rentabilidade_%', 'DY_%']].copy()
    resumo['Rentabilidade_%'] = resumo['Rentabilidade_%'].round(2).astype(str) + "%"
    resumo['DY_%'] = resumo['DY_%'].round(2).astype(str) + "%"
    
    # 2. Transforma o DataFrame em uma tabela Markdown
    dados_texto = resumo.to_markdown(index=False)

    # 3. Engenharia de Prompt (Fica isolada aqui, fácil de editar futuramente)
    prompt = f"""
    Você é um Analista de Investimentos Quantitativo Sênior. 
    Analise a tabela abaixo representando a carteira atual de um investidor e faça um diagnóstico rápido.
    
    Estruture sua resposta estritamente nos seguintes tópicos, usando formatação Markdown amigável:
    1. 🎯 **Visão Geral:** O que está puxando a rentabilidade para cima ou para baixo.
    2. ⚠️ **Riscos Visíveis:** Excesso de concentração em um ativo/classe ou ativos com forte prejuízo.
    3. 💡 **Insight de Balanceamento:** Uma dica rápida sobre a proporção entre Renda Fixa e Renda Variável com base nos dados.
    
    Seja analítico e direto. Não dê recomendações explícitas de compra/venda de ativos específicos.
    
    DADOS DA CARTEIRA:
    {dados_texto}
    """

    # 4. Chamada ao Modelo
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🚨 Erro de conexão com o Agente IA: {e}"


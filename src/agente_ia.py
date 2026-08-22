# separamos o agente de IA para criar uma classe separada com base no princípio de separação de responsabilidades. Isso facilita a manutenção e a escalabilidade do código.

# Estou usando a API do Gemini, armazenada na .env.

import os
from google import genai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inicializa o novo Cliente Oficial do Google
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

def gerar_analise_ia(df_carteira):
    """
    Recebe o DataFrame da carteira e retorna um relatório de texto gerado pelo LLM.
    """
    if not client:
        return "🚨 Chave da API do Gemini não encontrada no arquivo .env!"
    
    if df_carteira.empty:
        return "Sua carteira está vazia. Adicione ativos para análise."

    # 1. Filtramos apenas as colunas úteis para não confundir a IA
    resumo = df_carteira[['Ativo', 'Classe', 'Total_Investido', 'Valor_Atual', 'Rentabilidade_%', 'DY_%']].copy()
    resumo['Rentabilidade_%'] = resumo['Rentabilidade_%'].round(2).astype(str) + "%"
    resumo['DY_%'] = resumo['DY_%'].round(2).astype(str) + "%"
    
    # 2. Transforma o DataFrame em uma tabela Markdown
    dados_texto = resumo.to_markdown(index=False)

    # 3. Engenharia de Prompt 
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

    # 4. Chamada ao Modelo (Com Sistema de Fallback)
    try:
        # TENTATIVA 1: O modelo principal e mais inteligente
        response = client.models.generate_content(
            model='gemini-3.7-flash', 
            contents=prompt
        )
        return response.text
        
    except Exception as e:
        # Se o erro for de congestionamento (503), acionamos o Plano B
        if "503" in str(e) or "UNAVAILABLE" in str(e) or "high demand" in str(e).lower():
            try:
                # TENTATIVA 2: O modelo "Lite" (Super rápido e com muita disponibilidade)
                response_fallback = client.models.generate_content(
                    model='gemini-flash-lite-latest',
                    contents=prompt
                )
                return response_fallback.text + "\n\n*(Nota: Análise gerada pelo modelo Lite devido à alta demanda nos servidores principais).* "
                
            except Exception as e_fallback:
                return f"🚨 Os servidores do Google estão completamente sobrecarregados no momento. Tente novamente em alguns minutos."
        
        # Se for qualquer outro erro bizarro, mostra na tela
        else:
            return f"🚨 Erro interno no Agente IA: {e}"

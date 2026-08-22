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

    # 4. Chamada ao Modelo (Cascade Fallback Inteligente de 3 Níveis) - gratuito
    modelos_prioridade = [
        'gemini-3.7-flash',           # 1º Opção: O mais avançado
        'gemini-2.5-flash',           # 2º Opção: Muito robusto e maduro
        'gemini-flash-lite-latest'    # 3º Opção: O "fusca" que nunca quebra
    ]
    
    for nome_modelo in modelos_prioridade:
        try:
            response = client.models.generate_content(
                model=nome_modelo,
                contents=prompt
            )
            
            # Se usou algum fallback, avisa o usuário no texto
            nota = ""
            if nome_modelo != modelos_prioridade[0]:
                nota = f"\n\n*(Nota: Análise gerada pelo modelo {nome_modelo} devido à alta demanda nos servidores principais).* "
                
            return response.text + nota
            
        except Exception as e:
            # Se o erro for de congestionamento, ignoramos e o 'for' passa para o próximo modelo da lista
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "high demand" in str(e).lower():
                continue
            
            # Se for um erro real (ex: falta de internet, erro na tabela), paramos tudo e avisamos
            else:
                return f"🚨 Erro interno no Agente IA ({nome_modelo}): {e}"
                
    # Se o loop terminar e todos os 3 derem erro de congestionamento:
    return "🚨 Todos os servidores da inteligência artificial estão sobrecarregados no momento. Tente novamente em alguns minutos."

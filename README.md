# 📊 Dashboard de Acompanhamento de Investimentos

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)

Um sistema completo (Back-end e Front-end) para gestão, visualização e acompanhamento de portfólio de investimentos, abrangendo Renda Variável (Ações/FIIs) e Renda Fixa. O projeto consolida cálculos automáticos de preço médio, cruzamento com dados ao vivo da B3 e indicadores macroeconômicos do Banco Central.

---

## 🚀 Funcionalidades

- **Input Dinâmico:** Formulário inteligente construído com Streamlit para registro de operações de Compra, Venda e Aplicação, com campos adaptáveis de acordo com a classe do ativo.
- **Cálculo Automático de Preço Médio:** Algoritmo de ETL no back-end que processa o histórico cronológico de transações e calcula a posição exata da carteira.
- **Validação Anti-Erros:** Verificação em tempo real de Tickers na B3 antes do salvamento de novas operações.
- **Indicadores Macroeconômicos (API BCB):** Consumo automatizado da API do Banco Central (SGS) para exibir as taxas Selic, CDI e IPCA (12m) ao vivo.
- **Cotações em Tempo Real (API Brapi):** Atualização do valor patrimonial com base no preço de mercado no momento do acesso.
- **Visualização Profissional:** Gráficos interativos (Plotly), cards de KPIs (lucro, rentabilidade, patrimônio) e tabelas customizadas com destaque visual para retornos positivos (verde) e negativos (vermelho).

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python
* **Interface Web:** Streamlit
* **Manipulação de Dados:** Pandas, NumPy
* **Visualização:** Plotly Express
* **Integrações (APIs):** Requests
* **Variáveis de Ambiente:** Python-dotenv

---

## 📂 Estrutura do Projeto

```text
investment_monitoring/
│
├── data/
│   ├── historico_operacoes.csv       # Banco de dados local (Input do usuário)
│   └── carteira_atualizada.csv       # Output processado pelo sistema
│
├── src/
│   ├── app.py                        # Interface visual (Streamlit Front-end)
│   └── backend.py                    # Lógica de negócio, cálculos e APIs (Core)
│
├── notebooks/                        # Ambientes de teste e experimentação (.ipynb)
├── .env                              # Chaves de API (não versionado)
├── .gitignore                        # Arquivos ignorados pelo Git
└── README.md                         # Documentação do projeto

```

---

## ⚙️ Como Executar o Projeto

**1. Clone o repositório**

```bash
git clone [https://github.com/seu-usuario/investment_monitoring.git](https://github.com/seu-usuario/investment_monitoring.git)
cd investment_monitoring

```

**2. Crie e ative um ambiente virtual**

```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate

```

**3. Instale as dependências**

```bash
pip install pandas numpy streamlit plotly requests python-dotenv

```

**4. Configure as Variáveis de Ambiente**
Crie um arquivo chamado `.env` na raiz do projeto e adicione o seu token da [Brapi](https://brapi.dev/):

```env
BRAPI_TOKEN=seu_token_aqui

```

**5. Inicie o Dashboard**

```bash
streamlit run src/app.py

```

---

## 🗺️ Roadmap (Próximos Passos)

* [ ] Implementar cálculo diário de juros compostos para Renda Fixa com base no indexador (CDI/IPCA).
* [ ] Adicionar tabela progressiva de IR e regras de desconto de IOF sobre o lucro.
* [ ] Incorporar painel fundamentalista (Ex: Dividend Yield).
* [ ] Integração com LLM para gerar resumos de texto com insights automáticos sobre a carteira.
* [ ] Migração do armazenamento de `.csv` para Banco de Dados Relacional (`SQLite`).

---

## 📝 Licença e Autoria

Desenvolvido por **Igor Oliveira** & **Yghor Andrade**.

Sinta-se à vontade para realizar um *fork* e contribuir com este projeto!
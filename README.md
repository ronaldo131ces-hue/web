# 🚛 SSW Custos de Coleta / Entrega

Aplicativo web em **Streamlit** para análise de custos de coleta/entrega utilizando o **Demonstrativo de Fretes** do SSW (relatório 076 em formato texto/sswweb).

Com ele você consegue enxergar, em poucos segundos:

- Quanto está gastando por **dia / placa**  
- **% de custo** em relação ao frete  
- **Custo por KG, evento e entrega**  
- **Custo por cliente** e **custo por rota (SET)** (recursos liberados pela licença)  
- Placas com **romaneios pendentes** (última página do relatório 076)  
- Exportar tudo para **Excel** para análises adicionais

> ⚠️ Este projeto **não é oficial do SSW**. É uma ferramenta independente construída a partir dos relatórios gerados pelo sistema.

---

## ✨ Principais recursos

- 📂 **Upload direto dos arquivos do Demonstrativo** (`.sswweb` ou `.txt`)  
- 📆 Filtros por **período** e **placa**  
- 📘 **Diário por Placa**
  - Frete do dia  
  - Custo do dia  
  - Eventos (coleta + entrega)  
  - Peso total (KG)  
  - Coletas / Entregas / Clientes  
  - Custo por KG / Evento / Entrega  
  - % de custo por dia, com destaque em vermelho se **> 50%**  
- 📊 **Gráficos**
  - Frete x Custo por dia  
  - Dispersão Frete x Peso (por CTRC)  
  - Gráfico da evolução do **% de custo por dia**  
- 💼 **Clientes (Custo / Cliente)** 🔒 *(recurso liberado com licença)*
  - Frete, custo rateado, eventos, peso  
  - % de custo por cliente  
  - Custo por KG por cliente  
  - Separação de clientes por **entrega** e por **coleta**  
  - Coluna com **CNPJ do cliente**  
- 🧭 **Rotas (Custo / SET)** 🔒 *(licença)*
  - Frete, custo, peso, eventos por SET  
  - % custo e custo por KG por rota  
- 📄 **Romaneios Pendentes**
  - Lê a última página do demonstrativo  
  - Lista **placa, romaneio, data de inclusão e motorista**  
- 📥 **Exportação para Excel**
  - Abas: Diário por placa, CTRCs, Clientes (geral / entrega / coleta), Rotas (SET) e Romaneios pendentes

---

## 🧩 Como funciona a licença

O controle de licença é feito **por empresa** (nome digitado na tela inicial).

### Modo Demonstração (padrão, sem chave)

Ao informar o nome da empresa e entrar no sistema, ela fica em **modo demonstração**:

✅ Acessa normalmente:
- Diário por Placa  
- Gráficos  
- Romaneios Pendentes  
- Exportação Excel com essas informações  

🔒 Ficam bloqueados até ativar a licença:
- Aba **Clientes (Custo / Cliente)**  
- Aba **Rotas (Custo / SET)**  
- Abas correspondentes no Excel

### Modo Licenciado (com chave)

Após o pagamento da licença, o desenvolvedor gera uma chave específica para a empresa com data de validade.

- A chave é validada pelo nome da empresa + data de validade.  
- Quando válida, libera automaticamente as abas de **Clientes** e **Rotas (SET)**.  
- Expirando a data, a empresa volta para modo demonstração.

Na tela de ativação o usuário encontra:

- Contato por **WhatsApp**  
- E-mail  
- Chave PIX para pagamento  

Esses dados podem ser alterados diretamente no `app.py` nas constantes:

```python
WHATSAPP_CONTATO = "..."
EMAIL_CONTATO = "..."
PIX_CHAVE = "..."

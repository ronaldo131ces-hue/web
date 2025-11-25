import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import os
import json
import hashlib
from datetime import datetime, date, timedelta

# ==========================================================
# 0. CONFIG LICENÇA (POR EMPRESA, SEM TRIAL AUTOMÁTICO)
# ==========================================================

LIC_SECRET = "HOMOLOGIX_SSW_DEMOSTRATIVO_2024"

WHATSAPP_CONTATO = "(47) 99703-7512"          # <<< ALTERE AQUI
EMAIL_CONTATO    = "ronaldo131ces@gmail.com"  # <<< ALTERE AQUI
PIX_CHAVE        = "00020126580014br.gov.bcb.pix0136f0060f21-b941-469f-b6bc-61b7e83380285204000053039865802BR5914Ronaldo Cescon6009Sao Paulo62290525REC6925BEE3021F428700219563049BED"  # <<< ALTERE AQUI

LIC_FILE = "licenca_custos.json"


def gerar_chave_licenca(nome_empresa: str, data_validade: str) -> str:
    """
    Gera uma chave de licença a partir do nome da empresa e data de validade (YYYYMMDD).
    Use essa função em um script separado (gerar_licenca.py) para gerar chaves trial ou definitivas.
    """
    base = f"{nome_empresa.strip().upper()}|{data_validade}|{LIC_SECRET}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest().upper()
    return f"{digest[:4]}-{digest[4:8]}-{data_validade}"


def validar_chave_licenca(nome_empresa: str, chave: str):
    """
    Valida a chave digitada pelo usuário.
    Formato: XXXX-YYYY-YYYYMMDD
    """
    nome_empresa = (nome_empresa or "").strip().upper()
    chave = (chave or "").strip().upper()

    if not nome_empresa:
        return False, "Informe o nome da empresa/transportadora."

    m = re.match(r"^([A-F0-9]{4})-([A-F0-9]{4})-(\d{8})$", chave)
    if not m:
        return False, "Formato de chave inválido. Exemplo: 1A2B-3C4D-20251231"

    _, _, data_str = m.groups()
    try:
        dt_validade = datetime.strptime(data_str, "%Y%m%d").date()
    except ValueError:
        return False, "Data de validade inválida na chave."

    hoje = date.today()
    if hoje > dt_validade:
        return False, f"Chave expirada em {dt_validade.strftime('%d/%m/%Y')}."

    chave_esperada = gerar_chave_licenca(nome_empresa, data_str)
    if chave_esperada != chave:
        return False, "Chave não confere para este nome de empresa."

    return True, f"Licença válida até {dt_validade.strftime('%d/%m/%Y')}."


def carregar_licencas_all():
    """
    Carrega TODAS as empresas do arquivo licenca_custos.json.
    Estrutura:
    {
        "EMPRESA A": {
            "mode": "demo" ou "licensed",
            "valid_until": "YYYYMMDD",
            "empresa_display": "Nome digitado"
        },
        ...
    }
    """
    if not os.path.exists(LIC_FILE):
        return {}
    try:
        with open(LIC_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def salvar_licencas_all(data: dict):
    try:
        with open(LIC_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def estado_licenca_empresa(nome_empresa_exibicao: str):
    """
    Controle de licença POR EMPRESA.

    - Empresa nova -> entra como DEMO (sem cliente/rota).
    - Só vira 'licensed' quando receber chave válida.
    """
    hoje = date.today()
    if not nome_empresa_exibicao.strip():
        return False, False, 0, "Informe o nome da empresa."

    key = nome_empresa_exibicao.strip().upper()

    lic_all = carregar_licencas_all()
    info = lic_all.get(key)

    # PRIMEIRA VEZ DESSA EMPRESA -> DEMO
    if info is None:
        info = {
            "mode": "demo",
            "empresa_display": nome_empresa_exibicao.strip(),
        }
        lic_all[key] = info
        salvar_licencas_all(lic_all)

    modo = info.get("mode", "demo")

    # LICENCIADA
    if modo == "licensed":
        data_str = info.get("valid_until", "20991231")
        try:
            dt_validade = datetime.strptime(data_str, "%Y%m%d").date()
        except Exception:
            dt_validade = hoje
        if hoje <= dt_validade:
            msg = (
                f"Versão licenciada para **{info.get('empresa_display', nome_empresa_exibicao)}** "
                f"(válida até {dt_validade.strftime('%d/%m/%Y')})."
            )
            return True, False, 0, msg
        else:
            # Licença venceu -> volta para DEMO
            info["mode"] = "demo"
            lic_all[key] = info
            salvar_licencas_all(lic_all)
            msg = (
                f"A licença da empresa **{info.get('empresa_display', nome_empresa_exibicao)}** venceu em "
                f"{dt_validade.strftime('%d/%m/%Y')}. Ative uma nova chave para liberar todos os recursos."
            )
            return False, False, 0, msg

    # DEMO
    msg = (
        f"Modo demonstração para **{info.get('empresa_display', nome_empresa_exibicao)}**.\n\n"
        "Você pode usar **Diário por Placa** e **Gráficos** normalmente.\n\n"
        "Para liberar **Custo por Cliente** e **Custo por Rota (SET)**, ative a licença."
    )
    return False, False, 0, msg


# ==========================================================
# 1. UTILITÁRIOS
# ==========================================================

def brl_to_float(s):
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    m = re.search(r'[\d\.\,]+', s)
    if not m:
        return 0.0
    num = m.group(0)
    num = num.replace('R$', '').replace(' ', '')
    num = num.replace('.', '').replace(',', '.')
    try:
        return float(num)
    except Exception:
        return 0.0


def clean_cliente_nome(raw):
    if raw is None:
        return ""
    txt = str(raw).strip()
    m = re.search(r'\d{11,14}\s+(.+)', txt)
    if m:
        return m.group(1).strip()
    return txt


# ======= FORMATAÇÃO BR (pt-BR) ============================

def format_number_br(value, decimals=2, prefix=""):
    """Formata número no padrão brasileiro: 172.500,00"""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    try:
        if decimals == 0:
            s = f"{int(round(value)):,}"
        else:
            s = f"{float(value):,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{prefix}{s}"
    except Exception:
        return str(value)


def format_percent_br(value, decimals=1):
    """Formata percentual no padrão brasileiro: 52,3%"""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    try:
        s = f"{float(value) * 100:.{decimals}f}"
        s = s.replace(".", ",")
        return f"{s}%"
    except Exception:
        return ""


# ==========================================================
# 2. CABEÇALHO CTRC
# ==========================================================

def encontrar_cabecalho_ctrc(linhas):
    header_idx = None
    header_line = None

    for i, lin in enumerate(linhas):
        up = lin.upper()
        if ('CTRC' in up and 'REMETENTE' in up and 'RECEBEDOR' in up
                and 'VLR' in up and 'FRETE' in up):
            header_idx = i
            header_line = lin
            break

    if header_idx is None or not header_line:
        return None, None

    up = header_line.upper()
    pos_raw = {}

    def marca(label, key=None):
        p = up.find(label)
        if p >= 0:
            pos_raw[key or label] = p

    marca('CTRC', 'CTRC')
    marca('NF', 'NF')
    marca('REMETENTE', 'REMETENTE')
    marca('EXPEDIDOR', 'EXPEDIDOR')
    marca('RECEBEDOR', 'RECEBEDOR')
    marca('CEP CALC', 'CEP_CALC')
    marca('PESO CALC', 'PESO_CALC')
    marca('QTVOL', 'QTVOL')
    marca('VAL MERC', 'VAL_MERC')

    for patt in ['VLR FRETE', 'VLR  FRETE', 'VLR   FRETE']:
        p = up.find(patt)
        if p >= 0:
            pos_raw['VLR_FRETE'] = p
            break

    if 'CEP_CALC' in pos_raw:
        start_busca = pos_raw['CEP_CALC']
        p_set = up.find('SET', start_busca)
        if p_set >= 0:
            pos_raw['SET'] = p_set

    if 'VLR_FRETE' not in pos_raw:
        return None, None

    col_items = sorted(pos_raw.items(), key=lambda x: x[1])
    col_bounds = {}
    for idx, (nome, start) in enumerate(col_items):
        end = col_items[idx + 1][1] if idx + 1 < len(col_items) else None
        col_bounds[nome] = (start, end)

    return col_bounds, header_idx


def slice_col(line, col_bounds, col_name):
    if col_name not in col_bounds:
        return ""
    start, end = col_bounds[col_name]
    if end is None:
        return line[start:].rstrip('\n')
    return line[start:end].rstrip('\n')


# ==========================================================
# 3. PARSE DEMONSTRATIVO
# ==========================================================

def parse_demonstrativo_files(uploaded_files):
    all_ctrc_rows = []
    daily_stats = {}

    if not uploaded_files:
        return pd.DataFrame(), pd.DataFrame()

    for f in uploaded_files:
        try:
            txt = f.getvalue().decode("latin-1", errors="ignore")
        except Exception:
            txt = f.getvalue().decode("utf-8", errors="ignore")

        linhas = txt.splitlines()
        if not linhas:
            continue

        col_bounds, header_idx = encontrar_cabecalho_ctrc(linhas)

        placa_atual = None
        data_atual = None
        tipo_atual = None

        for lin in linhas:
            up = lin.upper()

            m_placa = re.search(r'VEICULO:\s*([A-Z0-9\-]+)', up)
            if m_placa:
                placa_atual = m_placa.group(1)
                continue

            m_dia = re.match(r'\s*DIA\s+(\d{2}/\d{2}/\d{2,4})', up)
            if m_dia:
                dt_str = m_dia.group(1)
                fmt = "%d/%m/%y" if len(dt_str) == 8 else "%d/%m/%Y"
                try:
                    data_atual = datetime.strptime(dt_str, fmt).date()
                except Exception:
                    data_atual = None

                if 'COLETA' in up:
                    tipo_atual = 'C'
                elif 'ENTREGA' in up:
                    tipo_atual = 'E'
                else:
                    tipo_atual = None
                continue

            if placa_atual is None or data_atual is None:
                continue

            chave = (placa_atual, data_atual)
            if chave not in daily_stats:
                daily_stats[chave] = {
                    'PLACA': placa_atual,
                    'DATA': data_atual,
                    'KM_RODADOS': 0.0,
                    'CUSTO_DIA': 0.0
                }

            if 'KM RODADOS' in up:
                m_km = re.search(r'KM RODADOS\s+(\d+)', up)
                if m_km:
                    daily_stats[chave]['KM_RODADOS'] += int(m_km.group(1))
                continue

            if 'REMUNERACAO DO DIA' in up or 'REMUNERAÇÃO DO DIA' in up:
                nums = re.findall(r'[\d\.\,]+', lin)
                if nums:
                    valor = brl_to_float(nums[-1])
                    daily_stats[chave]['CUSTO_DIA'] += valor
                continue

            if not col_bounds:
                continue
            if 'CTRC' in up or 'TOTAL DO DIA' in up or 'SUB-TOTAL' in up:
                continue
            if any(p in up for p in [
                'EVENTOS/CLIENTES',
                'DIARIA',
                'DIÁRIA',
                'SOBRE FRETE',
                'OCOR ON-LINE',
                'REDUCAO',
                'REDUÇÃO'
            ]):
                continue
            if not tipo_atual:
                continue

            ctrc_str = slice_col(lin, col_bounds, 'CTRC').strip()
            if not ctrc_str or not re.search(r'\d', ctrc_str):
                continue

            vlr_frete_str = slice_col(lin, col_bounds, 'VLR_FRETE')
            vlr_frete = brl_to_float(vlr_frete_str)
            if vlr_frete <= 0:
                continue

            peso_str = slice_col(lin, col_bounds, 'PESO_CALC')
            peso_val = brl_to_float(peso_str)

            set_str = slice_col(lin, col_bounds, 'SET').strip()
            cep_str = slice_col(lin, col_bounds, 'CEP_CALC').strip()

            remetente_raw = slice_col(lin, col_bounds, 'REMETENTE')
            recebedor_raw = slice_col(lin, col_bounds, 'RECEBEDOR')

            cliente_raw = remetente_raw if tipo_atual == 'C' else recebedor_raw
            cliente_nome = clean_cliente_nome(cliente_raw)

            # Ignora linhas do próprio demonstrativo
            cliente_up = cliente_nome.strip().upper()
            if cliente_up.startswith("DEMONSTRATIVO DE FRETES") or cliente_up.startswith("DEMONSTRATIVO DE FRETE"):
                continue

            all_ctrc_rows.append({
                'PLACA': placa_atual,
                'DATA': data_atual,
                'TIPO': 'COLETA' if tipo_atual == 'C' else 'ENTREGA',
                'CTRC': ctrc_str,
                'CLIENTE': cliente_nome,
                'SET': set_str,
                'CEP': cep_str,
                'PESO_CALCULO': peso_val,
                'VLR_FRETE': vlr_frete
            })

    df_ctrc = pd.DataFrame(all_ctrc_rows)
    if df_ctrc.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_ctrc.drop_duplicates(subset=['PLACA', 'DATA', 'CTRC'], inplace=True)
    df_ctrc['DATA'] = pd.to_datetime(df_ctrc['DATA'])

    grp_evt = df_ctrc.groupby(['PLACA', 'DATA']).agg(
        EVENTOS=('CTRC', 'nunique'),
        CLIENTES=('CLIENTE', 'nunique'),
        FRETE_DIA=('VLR_FRETE', 'sum'),
        PESO_TOTAL=('PESO_CALCULO', 'sum'),
        COLETAS=('TIPO', lambda x: (x == 'COLETA').sum()),
        ENTREGAS=('TIPO', lambda x: (x == 'ENTREGA').sum())
    ).reset_index()

    df_diario = pd.DataFrame(list(daily_stats.values()))
    df_diario['DATA'] = pd.to_datetime(df_diario['DATA'])
    df_diario = df_diario.merge(grp_evt, on=['PLACA', 'DATA'], how='left')

    for col in ['EVENTOS', 'CLIENTES', 'FRETE_DIA', 'PESO_TOTAL', 'COLETAS', 'ENTREGAS']:
        df_diario[col] = df_diario[col].fillna(0)

    df_diario['CUSTO_POR_KG'] = np.where(
        df_diario['PESO_TOTAL'] > 0,
        df_diario['CUSTO_DIA'] / df_diario['PESO_TOTAL'],
        0.0
    )
    df_diario['CUSTO_POR_EVENTO'] = np.where(
        df_diario['EVENTOS'] > 0,
        df_diario['CUSTO_DIA'] / df_diario['EVENTOS'],
        0.0
    )
    df_diario['CUSTO_POR_ENTREGA'] = np.where(
        df_diario['ENTREGAS'] > 0,
        df_diario['CUSTO_DIA'] / df_diario['ENTREGAS'],
        0.0
    )
    df_diario['PCT_CUSTO'] = np.where(
        df_diario['FRETE_DIA'] > 0,
        df_diario['CUSTO_DIA'] / df_diario['FRETE_DIA'],
        0.0
    )

    return df_diario, df_ctrc


# ==========================================================
# 4. EXCEL
# ==========================================================

def gerar_excel(df_diario, df_ctrc, df_cli=None, df_set=None, df_cli_ent=None, df_cli_col=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_diario.to_excel(writer, index=False, sheet_name='Diario_Placa')
        df_ctrc.to_excel(writer, index=False, sheet_name='CTRCs')
        if df_cli is not None:
            df_cli.to_excel(writer, index=False, sheet_name='Clientes_Geral')
        if df_cli_ent is not None:
            df_cli_ent.to_excel(writer, index=False, sheet_name='Clientes_Entrega')
        if df_cli_col is not None:
            df_cli_col.to_excel(writer, index=False, sheet_name='Clientes_Coleta')
        if df_set is not None:
            df_set.to_excel(writer, index=False, sheet_name='Rotas_SET')
    return output.getvalue()


# ==========================================================
# 5. INTERFACE STREAMLIT
# ==========================================================

st.set_page_config(page_title="SSW Custos de Coleta / Entrega", page_icon="🚛", layout="wide")

st.title("SSW Custos de Coleta / Entrega")

# Nome da empresa OBRIGATÓRIO (controle de licença por empresa)
empresa_input = st.text_input(
    "Nome da empresa / filial (obrigatório para controle de licença)",
    value=""
).strip()

if not empresa_input:
    st.warning("Informe o nome da empresa/transportadora para continuar.")
    st.stop()

# Estado da licença para ESTA empresa
is_licensed, trial_active, trial_days_left, lic_msg = estado_licenca_empresa(empresa_input)

if is_licensed:
    st.success(lic_msg)
else:
    st.info(lic_msg)

# Bloco de ativação (quando NÃO licenciado)
if not is_licensed:
    with st.expander("🔑 Ativar licença completa para esta empresa"):
        st.markdown(
            f"""
Para liberar **Custo por Cliente** e **Custo por Rota (SET)** para a empresa  
**{empresa_input}**:

1. Envie o **nome da empresa/filial** para gerar sua chave;  
2. Realize o pagamento via **PIX** e envie o comprovante;  
3. Você receberá a chave de ativação e poderá colar abaixo.

**Contato para ativação**

- WhatsApp: **{WHATSAPP_CONTATO}**  
- E-mail: **{EMAIL_CONTATO}**  
- Chave PIX: **{PIX_CHAVE}**
"""
        )
        with st.form("form_licenca"):
            nome_emp_form = st.text_input(
                "Nome da empresa / transportadora (deve ser igual ao usado para gerar a chave)",
                value=empresa_input
            )
            chave_form = st.text_input("Chave de ativação", type="password")
            btn_ativar = st.form_submit_button("Validar chave e ativar licença")

            if btn_ativar:
                ok, msg = validar_chave_licenca(nome_emp_form, chave_form)
                if ok:
                    st.success(msg)
                    lic_all = carregar_licencas_all()
                    key = nome_emp_form.strip().upper()
                    lic_all[key] = {
                        "mode": "licensed",
                        "valid_until": chave_form.split("-")[-1],
                        "empresa_display": nome_emp_form.strip(),
                    }
                    salvar_licencas_all(lic_all)
                    st.experimental_rerun()
                else:
                    st.error(msg)

uploaded_files = st.file_uploader(
    "Arquivos do Demonstrativo (.sswweb / .txt)",
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("⬆️ Arraste o(s) arquivo(s) de Demonstrativo aqui.")
    st.info("Gere o arquivo na opção 076 em formato R (relatório).")
    st.stop()

with st.spinner("Processando Demonstrativos..."):
    df_diario, df_ctrc = parse_demonstrativo_files(uploaded_files)

if df_diario.empty or df_ctrc.empty:
    st.error("Não foi possível extrair dados de CTRC / Diário. Verifique se o arquivo é o Demonstrativo completo.")
    st.stop()

# ----------------------------------------------------------
# FILTROS
# ----------------------------------------------------------

min_data = df_diario['DATA'].min().date()
max_data = df_diario['DATA'].max().date()

c_f1, c_f2 = st.sidebar.columns(2)
data_ini = c_f1.date_input("De", min_value=min_data, max_value=max_data, value=min_data)
data_fim = c_f2.date_input("Até", min_value=min_data, max_value=max_data, value=max_data)

placas_unicas = sorted(df_diario['PLACA'].unique())
placas_sel = st.sidebar.multiselect("Placas", placas_unicas, default=placas_unicas)

mask_data = (df_diario['DATA'].dt.date >= data_ini) & (df_diario['DATA'].dt.date <= data_fim)
mask_placa = df_diario['PLACA'].isin(placas_sel)

df_diario_f = df_diario[mask_data & mask_placa].copy()

mask_ctrc = (df_ctrc['DATA'].dt.date >= data_ini) & (df_ctrc['DATA'].dt.date <= data_fim) & (df_ctrc['PLACA'].isin(placas_sel))
df_ctrc_f = df_ctrc[mask_ctrc].copy()

if df_diario_f.empty or df_ctrc_f.empty:
    st.warning("Nenhum dado no período/filtro selecionado.")
    st.stop()

# ----------------------------------------------------------
# KPIs GLOBAIS
# ----------------------------------------------------------

tot_frete = df_ctrc_f['VLR_FRETE'].sum()
tot_custo = df_diario_f['CUSTO_DIA'].sum()
peso_tot = df_ctrc_f['PESO_CALCULO'].sum()
eventos_tot = len(df_ctrc_f)
entregas_tot = (df_ctrc_f['TIPO'] == 'ENTREGA').sum()

pct_custo_global = (tot_custo / tot_frete) if tot_frete > 0 else 0.0
custo_kg_global = (tot_custo / peso_tot) if peso_tot > 0 else 0.0
custo_evt_global = (tot_custo / eventos_tot) if eventos_tot > 0 else 0.0
custo_entrega_global = (tot_custo / entregas_tot) if entregas_tot > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Faturamento (Frete)", format_number_br(tot_frete, 2, "R$ "))
c2.metric("Custo Total", format_number_br(tot_custo, 2, "R$ "))
c3.metric("Percentual de Custo", format_percent_br(pct_custo_global, 1))
c4.metric("Custo / KG", format_number_br(custo_kg_global, 2, "R$ "))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Peso Total (KG)", format_number_br(peso_tot, 0))
c6.metric("Eventos (Coleta+Entrega)", format_number_br(eventos_tot, 0))
c7.metric("Custo / Evento", format_number_br(custo_evt_global, 2, "R$ "))
c8.metric("Custo / Entrega", format_number_br(custo_entrega_global, 2, "R$ "))

st.markdown("---")

# ----------------------------------------------------------
# TABS (Clientes/Rotas só se LICENCIADO)
# ----------------------------------------------------------

tab_labels = ["📘 Diário por Placa", "📊 Gráficos"]
tem_clientes_rotas = is_licensed   # << só com licença agora

if tem_clientes_rotas:
    tab_labels += ["💼 Clientes (Custo / Cliente)", "🧭 Rotas (Custo / SET)"]

tabs = st.tabs(tab_labels)

# TAB 1 ----------------------------------------------------
with tabs[0]:
    df_dia_view = df_diario_f.copy()
    df_dia_view['DATA'] = df_dia_view['DATA'].dt.strftime('%d/%m/%Y')

    cols_ordem = [
        'DATA', 'PLACA',
        'EVENTOS', 'COLETAS', 'ENTREGAS', 'CLIENTES',
        'PESO_TOTAL',
        'FRETE_DIA', 'CUSTO_DIA',
        'CUSTO_POR_KG', 'CUSTO_POR_EVENTO', 'CUSTO_POR_ENTREGA',
        'PCT_CUSTO'
    ]
    cols_existentes = [c for c in cols_ordem if c in df_dia_view.columns]

    def highlight_high_cost(row):
        try:
            return ['background-color: #ffe5e5' if row['PCT_CUSTO'] > 0.5 else '' for _ in row]
        except Exception:
            return ['' for _ in row]

    styled = (
        df_dia_view[cols_existentes]
        .style
        .format({
            'EVENTOS': lambda v: format_number_br(v, 0),
            'COLETAS': lambda v: format_number_br(v, 0),
            'ENTREGAS': lambda v: format_number_br(v, 0),
            'CLIENTES': lambda v: format_number_br(v, 0),
            'PESO_TOTAL': lambda v: format_number_br(v, 0),
            'FRETE_DIA': lambda v: format_number_br(v, 2, "R$ "),
            'CUSTO_DIA': lambda v: format_number_br(v, 2, "R$ "),
            'CUSTO_POR_KG': lambda v: format_number_br(v, 2, "R$ "),
            'CUSTO_POR_EVENTO': lambda v: format_number_br(v, 2, "R$ "),
            'CUSTO_POR_ENTREGA': lambda v: format_number_br(v, 2, "R$ "),
            'PCT_CUSTO': lambda v: format_percent_br(v, 1),
        })
        .apply(highlight_high_cost, axis=1)
    )

    st.dataframe(styled, use_container_width=True, height=450)

# TAB 2 ----------------------------------------------------
with tabs[1]:
    import plotly.express as px
    import plotly.graph_objects as go

    df_plot = df_diario_f.copy().sort_values('DATA')

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df_plot['DATA'], y=df_plot['FRETE_DIA'], name='Frete'))
    fig1.add_trace(go.Bar(x=df_plot['DATA'], y=df_plot['CUSTO_DIA'], name='Custo'))
    fig1.update_layout(title="Frete x Custo por Dia", barmode='group')
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.scatter(
        df_ctrc_f,
        x='VLR_FRETE',
        y='PESO_CALCULO',
        color='PLACA',
        hover_data=['CLIENTE', 'SET', 'TIPO', 'CTRC'],
        title="Dispersão Frete x Peso (CTRC)"
    )
    st.plotly_chart(fig2, use_container_width=True)

    df_pct = df_diario_f.groupby('DATA', as_index=False).agg(
        FRETE=('FRETE_DIA', 'sum'),
        CUSTO=('CUSTO_DIA', 'sum')
    )
    df_pct['PCT_CUSTO'] = np.where(
        df_pct['FRETE'] > 0,
        df_pct['CUSTO'] / df_pct['FRETE'],
        0.0
    )

    fig3 = go.Figure()
    fig3.add_trace(
        go.Scatter(
            x=df_pct['DATA'],
            y=df_pct['PCT_CUSTO'],
            mode='lines+markers',
            name='% Custo'
        )
    )
    if not df_pct.empty:
        fig3.add_trace(
            go.Scatter(
                x=df_pct['DATA'],
                y=[0.5] * len(df_pct),
                mode='lines',
                name='Limite 50%',
                line=dict(dash='dash')
            )
        )
    fig3.update_layout(title="Percentual de Custo por Dia", yaxis_tickformat='.0%')
    st.plotly_chart(fig3, use_container_width=True)

# TABS 3 e 4 só se LICENCIADO -----------------------------
df_cli = df_set = df_cli_ent = df_cli_col = None
df_tmp = None

if tem_clientes_rotas:
    # TAB 3 - Clientes
    with tabs[2]:
        df_tmp = df_ctrc_f.copy()
        df_tmp['DATA'] = pd.to_datetime(df_tmp['DATA'])
        df_tmp['FRETE_DIA'] = df_tmp.groupby(['PLACA', 'DATA'])['VLR_FRETE'].transform('sum')

        df_custo = df_diario_f[['PLACA', 'DATA', 'CUSTO_DIA']].copy()
        df_tmp = df_tmp.merge(df_custo, on=['PLACA', 'DATA'], how='left')

        df_tmp['CUSTO_RATEADO'] = np.where(
            df_tmp['FRETE_DIA'] > 0,
            df_tmp['CUSTO_DIA'] * (df_tmp['VLR_FRETE'] / df_tmp['FRETE_DIA']),
            0.0
        )

        df_cli = df_tmp.groupby('CLIENTE', as_index=False).agg(
            FRETE=('VLR_FRETE', 'sum'),
            CUSTO=('CUSTO_RATEADO', 'sum'),
            EVENTOS=('CTRC', 'nunique'),
            PESO=('PESO_CALCULO', 'sum')
        )
        df_cli['PCT_CUSTO'] = np.where(df_cli['FRETE'] > 0, df_cli['CUSTO'] / df_cli['FRETE'], 0.0)
        df_cli['CUSTO_KG'] = np.where(df_cli['PESO'] > 0, df_cli['CUSTO'] / df_cli['PESO'], 0.0)

        st.subheader("Visão Geral por Cliente")
        st.dataframe(
            df_cli.sort_values('FRETE', ascending=False).style.format({
                'FRETE': lambda v: format_number_br(v, 2, "R$ "),
                'CUSTO': lambda v: format_number_br(v, 2, "R$ "),
                'PCT_CUSTO': lambda v: format_percent_br(v, 1),
                'EVENTOS': lambda v: format_number_br(v, 0),
                'PESO': lambda v: format_number_br(v, 0),
                'CUSTO_KG': lambda v: format_number_br(v, 2, "R$ "),
            }),
            use_container_width=True,
            height=350
        )

        df_cli_ent = df_tmp[df_tmp['TIPO'] == 'ENTREGA'].groupby('CLIENTE', as_index=False).agg(
            FRETE_ENT=('VLR_FRETE', 'sum'),
            CUSTO_ENT=('CUSTO_RATEADO', 'sum'),
            EVENTOS_ENT=('CTRC', 'nunique')
        )
        df_cli_ent['PCT_CUSTO_ENT'] = np.where(
            df_cli_ent['FRETE_ENT'] > 0,
            df_cli_ent['CUSTO_ENT'] / df_cli_ent['FRETE_ENT'],
            0.0
        )

        st.subheader("Percentual de Custo por Cliente – ENTREGAS")
        st.dataframe(
            df_cli_ent.sort_values('PCT_CUSTO_ENT', ascending=False).style.format({
                'FRETE_ENT': lambda v: format_number_br(v, 2, "R$ "),
                'CUSTO_ENT': lambda v: format_number_br(v, 2, "R$ "),
                'EVENTOS_ENT': lambda v: format_number_br(v, 0),
                'PCT_CUSTO_ENT': lambda v: format_percent_br(v, 1),
            }),
            use_container_width=True,
            height=350
        )

        df_cli_col = df_tmp[df_tmp['TIPO'] == 'COLETA'].groupby('CLIENTE', as_index=False).agg(
            FRETE_COL=('VLR_FRETE', 'sum'),
            CUSTO_COL=('CUSTO_RATEADO', 'sum'),
            EVENTOS_COL=('CTRC', 'nunique')
        )
        df_cli_col['PCT_CUSTO_COL'] = np.where(
            df_cli_col['FRETE_COL'] > 0,
            df_cli_col['CUSTO_COL'] / df_cli_col['FRETE_COL'],
            0.0
        )

        st.subheader("Percentual de Custo por Cliente – COLETAS")
        st.dataframe(
            df_cli_col.sort_values('PCT_CUSTO_COL', ascending=False).style.format({
                'FRETE_COL': lambda v: format_number_br(v, 2, "R$ "),
                'CUSTO_COL': lambda v: format_number_br(v, 2, "R$ "),
                'EVENTOS_COL': lambda v: format_number_br(v, 0),
                'PCT_CUSTO_COL': lambda v: format_percent_br(v, 1),
            }),
            use_container_width=True,
            height=350
        )

    # TAB 4 - Rotas (SET)
    with tabs[3]:
        if df_tmp is None:
            df_tmp = df_ctrc_f.copy()
            df_tmp['DATA'] = pd.to_datetime(df_tmp['DATA'])
            df_tmp['FRETE_DIA'] = df_tmp.groupby(['PLACA', 'DATA'])['VLR_FRETE'].transform('sum')
            df_custo = df_diario_f[['PLACA', 'DATA', 'CUSTO_DIA']].copy()
            df_tmp = df_tmp.merge(df_custo, on=['PLACA', 'DATA'], how='left')
            df_tmp['CUSTO_RATEADO'] = np.where(
                df_tmp['FRETE_DIA'] > 0,
                df_tmp['CUSTO_DIA'] * (df_tmp['VLR_FRETE'] / df_tmp['FRETE_DIA']),
                0.0
            )

        df_set = df_tmp.groupby('SET', as_index=False).agg(
            FRETE=('VLR_FRETE', 'sum'),
            CUSTO=('CUSTO_RATEADO', 'sum'),
            EVENTOS=('CTRC', 'nunique'),
            PESO=('PESO_CALCULO', 'sum')
        )
        df_set['PCT_CUSTO'] = np.where(df_set['FRETE'] > 0, df_set['CUSTO'] / df_set['FRETE'], 0.0)
        df_set['CUSTO_KG'] = np.where(df_set['PESO'] > 0, df_set['CUSTO'] / df_set['PESO'], 0.0)

        st.dataframe(
            df_set.sort_values('FRETE', ascending=False).style.format({
                'FRETE': lambda v: format_number_br(v, 2, "R$ "),
                'CUSTO': lambda v: format_number_br(v, 2, "R$ "),
                'PCT_CUSTO': lambda v: format_percent_br(v, 1),
                'EVENTOS': lambda v: format_number_br(v, 0),
                'PESO': lambda v: format_number_br(v, 0),
                'CUSTO_KG': lambda v: format_number_br(v, 2, "R$ "),
            }),
            use_container_width=True,
            height=450
        )

# ----------------------------------------------------------
# DOWNLOAD EXCEL
# ----------------------------------------------------------

# No DEMO: só Diário + CTRCs
if is_licensed:
    excel_bytes = gerar_excel(
        df_diario_f,
        df_ctrc_f,
        df_cli=df_cli,
        df_set=df_set,
        df_cli_ent=df_cli_ent,
        df_cli_col=df_cli_col
    )
    nome_arq = "Analise_SSW_Demonstrativo.xlsx"
else:
    excel_bytes = gerar_excel(
        df_diario_f,
        df_ctrc_f,
        df_cli=None,
        df_set=None,
        df_cli_ent=None,
        df_cli_col=None
    )
    nome_arq = "Analise_SSW_Demonstrativo_demo.xlsx"

st.download_button(
    "📥 Baixar Excel",
    data=excel_bytes,
    file_name=nome_arq,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

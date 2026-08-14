import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Vendedor - Batalha Naval",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    a[href*="/edit"] { display: none !important; }
    a[href*="github.com"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Positivação e Cobertura")
st.caption("4 Elos Distribuidora Ltda. - Centro de Custo 622")

# ============================================================
# CONEXÃO COM GOOGLE SHEETS (ABAS DE PRODUÇÃO)
# ============================================================
SHEET_ID = "100LtVtmS76bT2CJd-EIb-bHTgX3F1BVm8Er5vUa-VYQ"

@st.cache_data(ttl=300)
def load_data():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

    # ABAS DE PRODUÇÃO
    df_base = pd.read_csv(url_base + "BASE")
    df_bi   = pd.read_csv(url_base + "BI")
    df_fabricantes = pd.read_csv(url_base + "FABRICANTE")
    df_vendedores  = pd.read_csv(url_base + "VENDEDORES")

    data_dados = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')

    # Renomear colunas da BASE
    df_base = df_base.rename(columns={
        'Código Cliente': 'codigo_cliente',
        'Cliente': 'nome_cliente',
        'Vendedor': 'nome_vendedor_base',
        'Coligação': 'Cliente_Coligacao',
        'Coordenador': 'Nome_Coordenador',
        'Municipio': 'Municipio',
        'Canal': 'Canal',
        'Segmento': 'Segmento'
    })

    # Renomear colunas da BI
    df_bi = df_bi.rename(columns={
        'Código Cliente': 'codigo_cliente',
        'Nome_Vendedor_Ajustado': 'nome_vendedor_bi',
        'Ano e Mês': 'Ano_e_Mes',
        'Nome Fabricante': 'Nome_Fabricante'
    })

    # Datas
    df_bi['Data'] = pd.to_datetime(df_bi['Ano_e_Mes'] + '-01', errors='coerce')
    df_bi['Mês'] = df_bi['Data'].dt.month
    df_bi['Ano'] = df_bi['Data'].dt.year
    df_bi['Mês_Ano'] = df_bi['Data'].dt.to_period('M').astype(str)

    # Merge
    df_merged = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao', 'Nome_Coordenador',
                 'Municipio', 'Canal', 'Segmento']],
        left_on=['codigo_cliente', 'nome_vendedor_bi'],
        right_on=['codigo_cliente', 'nome_vendedor_base'],
        how='left'
    )
    df_fallback = df_bi.merge(
        df_base[['codigo_cliente', 'nome_cliente', 'nome_vendedor_base', 'Cliente_Coligacao', 'Nome_Coordenador',
                 'Municipio', 'Canal', 'Segmento']],
        on='codigo_cliente',
        how='left',
        suffixes=('', '_fb')
    )
    for col in ['nome_cliente', 'Cliente_Coligacao', 'Nome_Coordenador', 'Municipio', 'Canal', 'Segmento']:
        if col in df_merged.columns and f'{col}_fb' in df_fallback.columns:
            df_merged[col] = df_merged[col].fillna(df_fallback[f'{col}_fb'])

    df_merged['nome_vendedor'] = df_merged['nome_vendedor_bi']

    # Dicionários de pastas
    fabricante_pasta = dict(zip(df_fabricantes['Nome Fabricante'], df_fabricantes['Pasta']))
    vendedor_pasta = dict(zip(df_vendedores['Vendedor'], df_vendedores['Pasta']))

    return df_base, df_bi, df_merged, data_dados, fabricante_pasta, vendedor_pasta

# ============================================================
# BOTÃO ATUALIZAR DADOS AGORA (CORRIGIDO)
# ============================================================
if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    # Remove filtros de mês e ano para redefinir com o último disponível
    st.session_state.pop('mes', None)
    st.session_state.pop('ano', None)
    st.rerun()

df_base, df_bi, df_merged, data_dados, fabricante_pasta, vendedor_pasta = load_data()

# ============================================================
# LISTA DE INDÚSTRIAS COMPLETA
# ============================================================
TODAS_INDUSTRIAS = sorted(df_bi['Nome_Fabricante'].dropna().unique())
TODAS_INDUSTRIAS = [i for i in TODAS_INDUSTRIAS if i.strip() != '']

# ============================================================
# FILTROS (VENDEDOR OBRIGATÓRIO)
# ============================================================
st.sidebar.header("🎯 Filtros")

# Limpar filtros
st.sidebar.markdown(
    """
    <form action="" method="get" style="margin-bottom: 10px;">
        <button type="submit" style="
            width: 100%; padding: 8px 12px; border-radius: 8px; 
            border: 1px solid #555; background-color: #333; color: #f0f0f0; 
            cursor: pointer; font-size: 14px; font-family: 'Source Sans Pro', sans-serif;
            display: flex; align-items: center; justify-content: center; gap: 8px;">
        🧹 Limpar Filtros
        </button>
    </form>
    """,
    unsafe_allow_html=True
)
if not st.query_params:
    for key in ['vendedor', 'coligacao', 'ano', 'mes', 'industria_filtro', 'janela_meses']:
        st.session_state.pop(key, None)

# -------------------- VENDEDOR (OBRIGATÓRIO) --------------------
lista_vendedores = sorted(df_base['nome_vendedor_base'].dropna().unique().tolist())
if 'vendedor' not in st.session_state or st.session_state['vendedor'] not in lista_vendedores:
    st.session_state['vendedor'] = None

vendedor_selecionado = st.sidebar.selectbox(
    "Selecione o Vendedor",
    [""] + lista_vendedores,
    index=0 if st.session_state['vendedor'] is None else lista_vendedores.index(st.session_state['vendedor']) + 1,
    key='vendedor_select'
)

if vendedor_selecionado == "":
    st.session_state['vendedor'] = None
    st.warning("Por favor, selecione um vendedor para visualizar os dados.")
    st.stop()
else:
    st.session_state['vendedor'] = vendedor_selecionado

# Detectar pasta do vendedor
pasta_vendedor = vendedor_pasta.get(vendedor_selecionado, None)
if pasta_vendedor in ['PA', 'PV']:
    INDUSTRIAS_PERMITIDAS = [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == pasta_vendedor]
    selo = f"({pasta_vendedor})"
elif pasta_vendedor == 'PVA':
    INDUSTRIAS_PERMITIDAS = TODAS_INDUSTRIAS.copy()
    selo = ""
else:
    INDUSTRIAS_PERMITIDAS = TODAS_INDUSTRIAS.copy()
    selo = ""

# Exibir nome do vendedor e coordenador
vendedor_info = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado].iloc[0]
coordenador_nome = vendedor_info['Nome_Coordenador'] if pd.notna(vendedor_info['Nome_Coordenador']) else "Não informado"
st.markdown(f"**Vendedor:** {vendedor_selecionado} {selo}")
st.markdown(f"**Coordenador:** {coordenador_nome}")

# -------------------- COLIGAÇÃO --------------------
clientes_do_vendedor = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].unique()
coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_vendedor)]['Cliente_Coligacao'].dropna().unique()
lista_coligacoes = ["Todas"] + sorted(coligacoes_filtradas)
if 'coligacao' not in st.session_state: st.session_state['coligacao'] = 'Todas'
if st.session_state['coligacao'] not in lista_coligacoes: st.session_state['coligacao'] = 'Todas'
coligacao_selecionada = st.sidebar.selectbox("Coligação", lista_coligacoes, index=lista_coligacoes.index(st.session_state['coligacao']), key='coligacao_select')
st.session_state['coligacao'] = coligacao_selecionada

# -------------------- ANO (PADRÃO ÚLTIMO ANO DISPONÍVEL) --------------------
anos_disponiveis = sorted(df_merged['Ano'].dropna().unique())
lista_anos = ["Todos"] + [str(int(a)) for a in anos_disponiveis]
if 'ano' not in st.session_state:
    st.session_state['ano'] = str(int(anos_disponiveis[-1])) if anos_disponiveis else 'Todos'
if st.session_state['ano'] not in lista_anos: st.session_state['ano'] = 'Todos'
ano_selecionado = st.sidebar.selectbox("Ano", lista_anos, index=lista_anos.index(st.session_state['ano']), key='ano_select')
st.session_state['ano'] = ano_selecionado

# -------------------- MÊS (PADRÃO ÚLTIMO MÊS DISPONÍVEL) --------------------
if ano_selecionado != "Todos":
    meses_disponiveis = sorted(df_merged[df_merged['Ano'] == int(ano_selecionado)]['Mês'].dropna().unique())
else:
    meses_disponiveis = sorted(df_merged['Mês'].dropna().unique())
meses_nomes = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}
lista_meses = ["Todos"] + [f"{int(m):02d} - {meses_nomes[int(m)]}" for m in meses_disponiveis]

# Inicializa o mês com o último mês disponível, se ainda não estiver definido
if 'mes' not in st.session_state:
    if meses_disponiveis:
        ultimo_mes = meses_disponiveis[-1]
        st.session_state['mes'] = f"{ultimo_mes:02d} - {meses_nomes.get(ultimo_mes, '')}"
    else:
        st.session_state['mes'] = 'Todos'

# Garante que o valor ainda existe na lista (pode ter mudado de ano)
if st.session_state['mes'] not in lista_meses:
    st.session_state['mes'] = 'Todos'

mes_selecionado = st.sidebar.selectbox("Mês", lista_meses, index=lista_meses.index(st.session_state['mes']), key='mes_select')
st.session_state['mes'] = mes_selecionado

# -------------------- JANELA MÓVEL DA BASE ATIVA --------------------
st.sidebar.divider()
st.sidebar.header("📆 Janela da Base Ativa")
if 'janela_meses' not in st.session_state:
    st.session_state['janela_meses'] = 6
janela_meses = st.sidebar.slider("Nº de meses anteriores", min_value=3, max_value=6, value=st.session_state['janela_meses'], step=1, key='janela_slider')
st.session_state['janela_meses'] = janela_meses

# -------------------- INDÚSTRIA (MULTISELECT) --------------------
st.sidebar.divider()
st.sidebar.header("🏭 Filtro por Indústria")
if pasta_vendedor in ['PA', 'PV']:
    INDUSTRIAS_DISPONIVEIS = [ind for ind in TODAS_INDUSTRIAS if fabricante_pasta.get(ind) == pasta_vendedor]
else:
    INDUSTRIAS_DISPONIVEIS = TODAS_INDUSTRIAS.copy()
if 'industria_filtro' not in st.session_state: st.session_state['industria_filtro'] = []
industria_selecionada_lista = st.sidebar.multiselect("Indústria(s)", options=INDUSTRIAS_DISPONIVEIS, default=st.session_state['industria_filtro'], placeholder="Digite para buscar...", key='industria_multiselect')
st.session_state['industria_filtro'] = industria_selecionada_lista

# ============================================================
# APLICAR FILTROS COMUNS (exceto mês global)
# ============================================================
def aplicar_filtros_comuns(df, incluir_mes=True):
    df = df.copy()
    df = df[df['nome_vendedor'] == vendedor_selecionado]  # sempre filtra pelo vendedor
    df = df[df['Nome_Fabricante'].isin(INDUSTRIAS_PERMITIDAS)]
    if coligacao_selecionada != "Todas":
        df = df[df['Cliente_Coligacao'] == coligacao_selecionada]
    if ano_selecionado != "Todos":
        df = df[df['Ano'] == int(ano_selecionado)]
    if incluir_mes and mes_selecionado != "Todos":
        mes_num = int(mes_selecionado.split(' - ')[0])
        df = df[df['Mês'] == mes_num]
    if industria_selecionada_lista:
        df = df[df['Nome_Fabricante'].isin(industria_selecionada_lista)]
    return df

# DataFrames principais
df_filtrado = aplicar_filtros_comuns(df_merged, incluir_mes=True)
df_historico = aplicar_filtros_comuns(df_merged, incluir_mes=False)
df_relatorio_base = aplicar_filtros_comuns(df_merged, incluir_mes=False)  # para relatórios internos

# ============================================================
# APLICAR JANELA MÓVEL (BASE ATIVA)
# ============================================================
if mes_selecionado != "Todos":
    if ano_selecionado != "Todos":
        ano_ref = int(ano_selecionado)
    else:
        ano_ref = df_historico['Ano'].max()
    mes_atual = int(mes_selecionado.split(' - ')[0])
    meses_janela = []
    for i in range(1, janela_meses + 1):
        mes = mes_atual - i
        ano = ano_ref
        while mes <= 0:
            mes += 12
            ano -= 1
        meses_janela.append((ano, mes))
    cond_janela = pd.Series(False, index=df_historico.index)
    for a, m in meses_janela:
        cond_janela |= (df_historico['Ano'] == a) & (df_historico['Mês'] == m)
    df_historico_janela = df_historico[cond_janela]
else:
    df_historico_janela = df_historico

# ============================================================
# CARTEIRA ATIVA
# ============================================================
carteira_ativa_total = df_historico_janela[df_historico_janela['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
positivados_periodo = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
pct_ativa = (positivados_periodo / carteira_ativa_total * 100) if carteira_ativa_total > 0 else 0

clientes_ativos_ids = df_historico_janela[df_historico_janela['Nome_Fabricante'].notna()]['codigo_cliente'].unique()
clientes_positivados_ids = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].unique()
clientes_sem_venda_ativos = [c for c in clientes_ativos_ids if c not in clientes_positivados_ids]

st.subheader("📅 Carteira Ativa (Janela Móvel)")
col_a1, col_a2, col_a3 = st.columns(3)
col_a1.metric("Carteira Ativa (últimos {} meses)".format(janela_meses), carteira_ativa_total)
col_a2.metric("Positivados no Mês", positivados_periodo)
col_a3.metric("% Positivação (Ativa)", f"{pct_ativa:.1f}%")

st.markdown("**Clientes positivados por mês (Carteira Ativa)**")
df_mensal_ativos = df_historico[df_historico['Nome_Fabricante'].notna()]
mensal_pos = df_mensal_ativos.groupby('Mês_Ano')['codigo_cliente'].nunique().reset_index()
mensal_pos.columns = ['Mês', 'Clientes Positivados']
meses_unicos = sorted(df_historico['Mês_Ano'].dropna().unique())
meses_presentes = [m for m in meses_unicos if m in mensal_pos['Mês'].values]
mensal_pos['Mês'] = pd.Categorical(mensal_pos['Mês'], categories=meses_presentes, ordered=True)
mensal_pos = mensal_pos.sort_values('Mês')
if not mensal_pos.empty:
    fig_pos_mes = px.bar(mensal_pos, x='Mês', y='Clientes Positivados', text='Clientes Positivados', color_discrete_sequence=['#2E8B57'])
    fig_pos_mes.update_traces(textposition='outside')
    fig_pos_mes.update_layout(xaxis_title="", yaxis_title="Nº de clientes", xaxis=dict(type='category', categoryorder='array', categoryarray=meses_presentes))
    st.plotly_chart(fig_pos_mes, use_container_width=True)
else:
    st.info("Sem dados mensais para exibir.")

if clientes_sem_venda_ativos:
    df_sem_venda_ativos = df_base[df_base['codigo_cliente'].isin(clientes_sem_venda_ativos)][['codigo_cliente', 'nome_cliente', 'Cliente_Coligacao']]
    df_sem_venda_ativos.columns = ['Código', 'Nome', 'Coligação']
    with st.expander(f"🔴 {len(clientes_sem_venda_ativos)} clientes sem venda no mês (Carteira Ativa)"):
        st.dataframe(df_sem_venda_ativos, use_container_width=True, hide_index=True)
st.divider()

# ============================================================
# CARTEIRA TOTAL
# ============================================================
total_clientes_base = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].nunique()
total_positivados = len(clientes_positivados_ids)
pct_total = (total_positivados / total_clientes_base * 100) if total_clientes_base > 0 else 0
cobertura_media = df_filtrado.groupby('codigo_cliente')['Nome_Fabricante'].nunique().mean()
cobertura_total = df_filtrado[['codigo_cliente', 'Nome_Fabricante']].dropna().drop_duplicates().shape[0]

todos_ids_carteira = df_base[df_base['nome_vendedor_base'] == vendedor_selecionado]['codigo_cliente'].unique()
clientes_sem_venda_carteira = [c for c in todos_ids_carteira if c not in clientes_positivados_ids]

st.subheader("📋 Carteira Total")
col1, col2, col3 = st.columns(3)
col1.metric("Clientes na Carteira", total_clientes_base)
col2.metric("Clientes Positivados", total_positivados)
col3.metric("% Positivação (Carteira Total)", f"{pct_total:.1f}%")
col4, col5 = st.columns(2)
col4.metric("Cobertura Média", f"{cobertura_media:.1f} ind/cliente")
col5.metric("Cobertura Total", f"{cobertura_total} coberturas")

if clientes_sem_venda_carteira:
    df_sem_venda_total = df_base[df_base['codigo_cliente'].isin(clientes_sem_venda_carteira)][['codigo_cliente', 'nome_cliente', 'Cliente_Coligacao']]
    df_sem_venda_total.columns = ['Código', 'Nome', 'Coligação']
    with st.expander(f"🔴 {len(clientes_sem_venda_carteira)} clientes sem venda (Carteira Total)"):
        st.dataframe(df_sem_venda_total, use_container_width=True, hide_index=True)
st.divider()

# ============================================================
# RELATÓRIO BATALHA NAVAL (COM SELETORES DE PERÍODO, SEM CSV)
# ============================================================
st.subheader("📋 Relatório Batalha Naval")

meses_batalha = sorted(df_relatorio_base['Mês_Ano'].dropna().unique())
if not meses_batalha:
    st.warning("Nenhum dado disponível para o relatório.")
    st.stop()

col_bat1, col_bat2 = st.columns(2)
with col_bat1:
    mes_bat_inicio = st.selectbox("Mês início:", options=meses_batalha, index=0, key='mes_bat_inicio')
with col_bat2:
    mes_bat_fim = st.selectbox("Mês fim:", options=meses_batalha, index=len(meses_batalha)-1, key='mes_bat_fim')

if mes_bat_inicio <= mes_bat_fim:
    df_relatorio = df_relatorio_base[(df_relatorio_base['Mês_Ano'] >= mes_bat_inicio) & (df_relatorio_base['Mês_Ano'] <= mes_bat_fim)]
else:
    st.warning("Mês início deve ser menor ou igual ao mês fim.")
    st.stop()

matriz = df_relatorio.pivot_table(index='codigo_cliente', columns='Nome_Fabricante', aggfunc='size', fill_value=0)
mapa_nomes = df_relatorio[['codigo_cliente', 'nome_cliente']].drop_duplicates('codigo_cliente')
mapa_nomes_dict = dict(zip(mapa_nomes['codigo_cliente'], mapa_nomes['nome_cliente']))
matriz_bin = (matriz > 0).astype(int)
matriz_bin['Nome_Cliente'] = matriz.index.map(lambda x: mapa_nomes_dict.get(x, 'N/A'))
matriz_bin['Total_Indústrias'] = matriz_bin.drop(columns=['Nome_Cliente']).sum(axis=1)
matriz_bin = matriz_bin.reset_index().rename(columns={'codigo_cliente': 'Código'})
colunas_fabricantes = [c for c in matriz_bin.columns if c not in ['Código', 'Nome_Cliente', 'Total_Indústrias']]
matriz_bin = matriz_bin[['Código', 'Nome_Cliente'] + colunas_fabricantes + ['Total_Indústrias']]

st.metric("📊 Total de Clientes no Relatório", len(matriz_bin))

# Botões de download: apenas Excel e PDF
col1, col2 = st.columns(2)
with col1:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        matriz_bin.to_excel(writer, index=False, sheet_name='Batalha Naval')
    st.download_button(
        "📥 Baixar Excel",
        data=output.getvalue(),
        file_name=f'batalha_naval_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True
    )
with col2:
    html_pdf = f"""
    <html><head><meta charset="UTF-8"><style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ text-align: center; color: #1a3a4a; font-size: 18px; }}
        h2 {{ text-align: center; color: #666; font-size: 12px; font-weight: normal; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 8px; }}
        th {{ background-color: #1a3a4a; color: white; padding: 6px 4px; text-align: center; }}
        td {{ padding: 4px; text-align: center; border: 1px solid #ddd; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .positivo {{ background-color: #0F5220; color: white; }}
        .negativo {{ background-color: #8B0000; color: white; }}
        .footer {{ text-align: center; font-size: 10px; color: #999; margin-top: 20px; }}
    </style></head><body>
        <h1>Relatório Batalha Naval</h1>
        <h2>4 Elos Distribuidora Ltda. - Centro de Custo 622 | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</h2>
        <table><thead><tr><th>Código</th><th>Cliente</th>"""
    for col in colunas_fabricantes:
        html_pdf += f"<th>{col}</th>"
    html_pdf += "<th>Total</th></tr></thead><tbody>"
    for _, row in matriz_bin.iterrows():
        html_pdf += "<tr>"
        html_pdf += f"<td>{row['Código']}</td><td style='text-align:left;'>{row['Nome_Cliente']}</td>"
        for col in colunas_fabricantes:
            valor = row[col]
            classe = "positivo" if valor == 1 else "negativo"
            html_pdf += f"<td class='{classe}'>{valor}</td>"
        html_pdf += f"<td><strong>{row['Total_Indústrias']}</strong></td></tr>"
    html_pdf += f"</tbody></table><div class='footer'>4 Elos Distribuidora Ltda. - Centro de Custo 622 | Total: {len(matriz_bin)} clientes | Cobertura Total: {matriz_bin['Total_Indústrias'].sum()} coberturas</div></body></html>"
    st.download_button(
        "📥 Baixar PDF (HTML)",
        data=html_pdf.encode('utf-8'),
        file_name=f'batalha_naval_{datetime.now().strftime("%Y%m%d")}.html',
        mime='text/html',
        use_container_width=True
    )
    st.caption("💡 Abra o arquivo HTML e salve como PDF (Ctrl+P)")

with st.expander("👁️ Visualizar tabela"):
    st.dataframe(matriz_bin, use_container_width=True, hide_index=True)
st.divider()

# ============================================================
# FICHA DO CLIENTE (COM SELETORES DE PERÍODO)
# ============================================================
st.subheader("🔍 Ficha do Cliente")

meses_ficha = sorted(df_relatorio_base['Mês_Ano'].dropna().unique())
if not meses_ficha:
    st.warning("Nenhum dado disponível para a ficha.")
    st.stop()

col_fich1, col_fich2 = st.columns(2)
with col_fich1:
    mes_ficha_inicio = st.selectbox("Mês início:", options=meses_ficha, index=0, key='mes_ficha_inicio')
with col_fich2:
    mes_ficha_fim = st.selectbox("Mês fim:", options=meses_ficha, index=len(meses_ficha)-1, key='mes_ficha_fim')

if mes_ficha_inicio <= mes_ficha_fim:
    df_ficha = df_relatorio_base[(df_relatorio_base['Mês_Ano'] >= mes_ficha_inicio) & (df_relatorio_base['Mês_Ano'] <= mes_ficha_fim)]
else:
    st.warning("Mês início deve ser menor ou igual ao mês fim.")
    st.stop()

try:
    df_clientes_unicos = df_ficha[['codigo_cliente', 'nome_cliente']].drop_duplicates().dropna()
    df_clientes_unicos['cliente_label'] = df_clientes_unicos['codigo_cliente'].astype(str) + ' - ' + df_clientes_unicos['nome_cliente'].astype(str)
    lista_clientes = sorted(df_clientes_unicos['cliente_label'].unique())
except:
    lista_clientes = []

if lista_clientes:
    cliente_sel = st.selectbox("Selecione um cliente:", lista_clientes, key='ficha_cliente')
    if cliente_sel:
        codigo = cliente_sel.split(' - ')[0].strip()
        df_cliente = df_ficha[df_ficha['codigo_cliente'].astype(str).str.strip() == codigo]
        if not df_cliente.empty:
            st.write(f"**Código:** {codigo}")
            st.write(f"**Nome:** {df_cliente['nome_cliente'].iloc[0]}")
            st.write(f"**Coligação:** {df_cliente['Cliente_Coligacao'].iloc[0]}")
            st.write(f"**Vendedor:** {df_cliente['nome_vendedor'].iloc[0]}")
            st.write(f"**Coordenador:** {df_cliente['Nome_Coordenador'].iloc[0]}")

            st.write("**Positivação por Indústria e Mês:**")
            meses_disp = sorted(df_cliente['Mês_Ano'].dropna().unique())
            if meses_disp:
                tabela = []
                for ind in INDUSTRIAS_PERMITIDAS:
                    linha = {'Indústria': ind}
                    for m in meses_disp:
                        linha[m] = '✅' if ((df_cliente['Nome_Fabricante'] == ind) & (df_cliente['Mês_Ano'] == m)).any() else '❌'
                    linha['Total'] = sum(1 for m in meses_disp if linha[m] == '✅')
                    tabela.append(linha)
                df_tab = pd.DataFrame(tabela)
                st.dataframe(df_tab, use_container_width=True, hide_index=True)
                pos_industrias = sum(1 for l in tabela if l['Total'] > 0)
                st.metric("Indústrias Positivadas", f"{pos_industrias} de {len(tabela)}")
                st.metric("Cobertura Total do Cliente", df_cliente[['codigo_cliente', 'Nome_Fabricante']].dropna().drop_duplicates().shape[0])
            else:
                st.warning("Nenhum dado mensal.")
        else:
            st.warning("Cliente não encontrado.")
else:
    st.warning("Nenhum cliente encontrado.")

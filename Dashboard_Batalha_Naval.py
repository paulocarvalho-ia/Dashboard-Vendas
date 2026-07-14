import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard - Positivação & Cobertura",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard de Positivação e Cobertura")
st.caption("Distribuidora — Análise por Indústria Representada")

# ============================================================
# CONEXÃO COM GOOGLE SHEETS
# ============================================================
SHEET_ID = "1L0g4hyAM_GtEO2-7kfKpbpl_vXq_bh6t"

@st.cache_data(ttl=3600)
def load_data():
    url_base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

    df_base = pd.read_csv(url_base + "BASE")
    df_bi = pd.read_csv(url_base + "BI")

    # Converter coluna "Ano e Mês" (formato aaaa-mm) para datetime
    df_bi['Data'] = pd.to_datetime(df_bi['Ano e Mês'] + '-01', errors='coerce')
    df_bi['Mês'] = df_bi['Data'].dt.month
    df_bi['Ano'] = df_bi['Data'].dt.year
    df_bi['Mês_Ano'] = df_bi['Data'].dt.to_period('M').astype(str)

    # Renomear colunas para padronizar (se necessário)
    # BASE
    base_rename = {}
    for col in df_base.columns:
        col_lower = col.lower().replace(' ', '_')
        if 'codigo' in col_lower and 'cliente' in col_lower:
            base_rename[col] = 'codigo_cliente'
        if 'nome' in col_lower and 'cliente' in col_lower:
            base_rename[col] = 'nome_cliente'
        if 'vendedor' in col_lower:
            base_rename[col] = 'nome_vendedor'
        if 'coligacao' in col_lower:
            base_rename[col] = 'Cliente_Coligacao'
    
    df_base.rename(columns=base_rename, inplace=True)

    # BI
    bi_rename = {}
    for col in df_bi.columns:
        col_lower = col.lower().replace(' ', '_')
        if 'codigo' in col_lower and 'cliente' in col_lower:
            bi_rename[col] = 'codigo_cliente'
        if 'nome' in col_lower and 'cliente' in col_lower:
            bi_rename[col] = 'nome_cliente'
        if 'vendedor' in col_lower:
            bi_rename[col] = 'nome_vendedor'
        if 'coordenador' in col_lower:
            bi_rename[col] = 'Nome_Coordenador'
        if 'fabricante' in col_lower:
            bi_rename[col] = 'Nome_Fabricante'
    
    df_bi.rename(columns=bi_rename, inplace=True)

    # Merge
    cols_merge = ['codigo_cliente']
    if 'Cliente_Coligacao' in df_base.columns:
        cols_merge.append('Cliente_Coligacao')
    
    df_merged = df_bi.merge(
        df_base[cols_merge],
        on='codigo_cliente',
        how='left'
    )

    return df_base, df_bi, df_merged

# Botão de atualização
if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

df_base, df_bi, df_merged = load_data()

# ============================================================
# LISTA DE INDÚSTRIAS
# ============================================================
col_fabricante = 'Nome_Fabricante'
INDUSTRIAS = sorted(df_bi[col_fabricante].dropna().unique())
INDUSTRIAS = [i for i in INDUSTRIAS if i.strip() != '']

# ============================================================
# FILTROS
# ============================================================
st.sidebar.header("🎯 Filtros")

lista_vendedores = ["Todos"] + sorted(df_bi['nome_vendedor'].dropna().unique().tolist())
vendedor_selecionado = st.sidebar.selectbox("Vendedor", lista_vendedores)

col_coord = 'Nome_Coordenador'
lista_coordenadores = ["Todos"] + sorted(df_bi[col_coord].dropna().unique().tolist())
coordenador_selecionado = st.sidebar.selectbox("Coordenador", lista_coordenadores)

col_colig = 'Cliente_Coligacao'
lista_coligacoes = ["Todas"]
if col_colig in df_merged.columns:
    lista_coligacoes += sorted(df_merged[col_colig].dropna().unique().tolist())
coligacao_selecionada = st.sidebar.selectbox("Coligação", lista_coligacoes)

anos_disponiveis = sorted(df_merged['Ano'].dropna().unique())
ano_selecionado = st.sidebar.selectbox("Ano", ["Todos"] + [int(a) for a in anos_disponiveis])

# ============================================================
# APLICAR FILTROS
# ============================================================
df_filtrado = df_merged.copy()

if vendedor_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['nome_vendedor'] == vendedor_selecionado]

if coordenador_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado[col_coord] == coordenador_selecionado]

if coligacao_selecionada != "Todas" and col_colig in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado[col_colig] == coligacao_selecionada]

if ano_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano_selecionado)]

# ============================================================
# MÉTRICAS
# ============================================================
total_clientes_base = df_filtrado['codigo_cliente'].nunique()
total_clientes_positivados = df_filtrado[df_filtrado[col_fabricante].notna()]['codigo_cliente'].nunique()
pct_positivacao = (total_clientes_positivados / total_clientes_base * 100) if total_clientes_base > 0 else 0

cobertura_por_cliente = df_filtrado.groupby('codigo_cliente')[col_fabricante].nunique()
cobertura_media = cobertura_por_cliente.mean() if len(cobertura_por_cliente) > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📋 Clientes na Base", total_clientes_base)
col2.metric("✅ Clientes Positivados", total_clientes_positivados)
col3.metric("📈 % Positivação", f"{pct_positivacao:.1f}%")
col4.metric("📊 Cobertura Média", f"{cobertura_media:.1f} indústrias")
col5.metric("🏭 Indústrias", len(INDUSTRIAS))

st.divider()

# ============================================================
# BATALHA NAVAL
# ============================================================
st.subheader("🎯 Batalha Naval — Positivação por Cliente e Indústria")

matriz = df_filtrado.pivot_table(
    index='codigo_cliente',
    columns=col_fabricante,
    aggfunc='size',
    fill_value=0
)

mapa_nomes = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates('codigo_cliente')
mapa_nomes_dict = dict(zip(mapa_nomes['codigo_cliente'], mapa_nomes['nome_cliente']))

def formatar_rotulo(codigo):
    nome = mapa_nomes_dict.get(codigo, 'N/A')
    return f"{codigo} - {nome}"

matriz.index = matriz.index.map(formatar_rotulo)
matriz_bin = (matriz > 0).astype(int)

fig_heatmap = go.Figure(data=go.Heatmap(
    z=matriz_bin.values,
    x=matriz_bin.columns.tolist(),
    y=matriz_bin.index.tolist(),
    colorscale=[[0, '#8B0000'], [1, '#0F5220']],
    showscale=False,
    hoverongaps=False,
    hovertemplate='Cliente: %{y}<br>Indústria: %{x}<br>Positivado: %{z}<extra></extra>'
))

fig_heatmap.update_layout(
    height=max(400, 25 * len(matriz_bin)),
    xaxis_title="Indústria",
    yaxis_title="Cliente (Código - Nome)",
    xaxis_tickangle=-45,
    margin=dict(l=10, r=10, t=10, b=80),
    yaxis=dict(tickfont=dict(size=10))
)

st.plotly_chart(fig_heatmap, use_container_width=True)
st.caption("🟢 Verde = Positivado | 🔴 Vermelho = Não Positivado")

with st.expander("📋 Ver tabela detalhada"):
    matriz_exibicao = matriz_bin.copy()
    matriz_exibicao['Total Indústrias'] = matriz_exibicao.sum(axis=1)
    st.dataframe(matriz_exibicao, use_container_width=True)

st.divider()

# ============================================================
# PERFORMANCE
# ============================================================
st.subheader("👥 Performance por Vendedor")

perf_vendedor = df_filtrado.groupby('nome_vendedor').agg(
    Total_Clientes=('codigo_cliente', 'nunique'),
    Clientes_Positivados=('codigo_cliente', lambda x: x[df_filtrado.loc[x.index, col_fabricante].notna()].nunique()),
    Cobertura_Media=(col_fabricante, lambda x: x.nunique() / df_filtrado.loc[x.index, 'codigo_cliente'].nunique() if df_filtrado.loc[x.index, 'codigo_cliente'].nunique() > 0 else 0)
).reset_index()

perf_vendedor['%_Positivação'] = (perf_vendedor['Clientes_Positivados'] / perf_vendedor['Total_Clientes'] * 100).round(1)
perf_vendedor = perf_vendedor.sort_values('%_Positivação', ascending=False)

col1, col2 = st.columns(2)

with col1:
    fig_bar = px.bar(
        perf_vendedor, x='nome_vendedor', y='%_Positivação',
        title='% de Positivação por Vendedor',
        text=perf_vendedor['%_Positivação'].apply(lambda x: f'{x:.1f}%'),
        color='%_Positivação', color_continuous_scale='Greens'
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(xaxis_title="", yaxis_title="% Positivação", yaxis_range=[0, 105])
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    fig_bar2 = px.bar(
        perf_vendedor, x='nome_vendedor', y='Cobertura_Media',
        title='Cobertura Média por Vendedor',
        text=perf_vendedor['Cobertura_Media'].apply(lambda x: f'{x:.1f}'),
        color='Cobertura_Media', color_continuous_scale='Blues'
    )
    fig_bar2.update_traces(textposition='outside')
    fig_bar2.update_layout(xaxis_title="", yaxis_title="Cobertura Média")
    st.plotly_chart(fig_bar2, use_container_width=True)

st.dataframe(perf_vendedor, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# FICHA DO CLIENTE
# ============================================================
st.subheader("🔍 Ficha do Cliente")

df_clientes_unicos = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates()
df_clientes_unicos['cliente_label'] = df_clientes_unicos['codigo_cliente'].astype(str) + ' - ' + df_clientes_unicos['nome_cliente']
lista_clientes = sorted(df_clientes_unicos['cliente_label'].tolist())

cliente_selecionado_label = st.selectbox("Selecione um cliente:", lista_clientes, key='ficha_cliente')

if cliente_selecionado_label:
    codigo_selecionado = int(cliente_selecionado_label.split(' - ')[0])
    df_cliente = df_filtrado[df_filtrado['codigo_cliente'] == codigo_selecionado]

    if not df_cliente.empty:
        nome = df_cliente['nome_cliente'].iloc[0]
        coligacao = df_cliente[col_colig].iloc[0] if col_colig in df_cliente.columns else "N/A"
        vendedor = df_cliente['nome_vendedor'].iloc[0]
        coordenador = df_cliente[col_coord].iloc[0] if col_coord in df_cliente.columns else "N/A"

        st.write(f"**Código:** {codigo_selecionado}")
        st.write(f"**Nome:** {nome}")
        st.write(f"**Coligação:** {coligacao}")
        st.write(f"**Vendedor:** {vendedor}")
        st.write(f"**Coordenador:** {coordenador}")

        industrias_cliente = df_cliente[col_fabricante].dropna().unique()
        
        st.write("**Status por Indústria:**")
        cols = st.columns(5)
        for i, industria in enumerate(INDUSTRIAS):
            col_idx = i % 5
            if industria in industrias_cliente:
                cols[col_idx].success(f"✅ {industria}")
            else:
                cols[col_idx].error(f"❌ {industria}")
        
        total_positivado = len(industrias_cliente)
        st.metric("Total Positivado", f"{total_positivado} de {len(INDUSTRIAS)}")

st.divider()
st.caption(f"Última atualização: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')} | Fonte: Google Sheets")

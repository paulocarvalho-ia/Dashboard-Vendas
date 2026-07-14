import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

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

    df_base = df_base.rename(columns={
        'cd_clien': 'codigo_cliente',
        'nome_cliente': 'nome_cliente',
        'nome_vendedor': 'nome_vendedor',
        'Cliente_Coligacao': 'Cliente_Coligacao'
    })

    df_bi = df_bi.rename(columns={
        'Código Cliente': 'codigo_cliente',
        'Cliente': 'nome_cliente',
        'Nome_Vendedor_Ajustado': 'nome_vendedor',
        'Nome Coordenador': 'Nome_Coordenador',
        'Nome Fabricante': 'Nome_Fabricante'
    })

    df_bi['Data'] = pd.to_datetime(df_bi['Ano e Mês'] + '-01', errors='coerce')
    df_bi['Mês'] = df_bi['Data'].dt.month
    df_bi['Ano'] = df_bi['Data'].dt.year
    df_bi['Mês_Ano'] = df_bi['Data'].dt.to_period('M').astype(str)
    df_bi['Mes_Nome'] = df_bi['Data'].dt.strftime('%b/%Y')

    df_merged = df_bi.merge(
        df_base[['codigo_cliente', 'Cliente_Coligacao']],
        on='codigo_cliente',
        how='left'
    )

    return df_base, df_bi, df_merged

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

df_base, df_bi, df_merged = load_data()

# ============================================================
# LISTA DE INDÚSTRIAS
# ============================================================
INDUSTRIAS = sorted(df_bi['Nome_Fabricante'].dropna().unique())
INDUSTRIAS = [i for i in INDUSTRIAS if i.strip() != '']

# ============================================================
# FILTROS ENCADEADOS
# ============================================================
st.sidebar.header("🎯 Filtros")

lista_coordenadores = ["Todos"] + sorted(df_bi['Nome_Coordenador'].dropna().unique().tolist())
coordenador_selecionado = st.sidebar.selectbox("Coordenador", lista_coordenadores)

if coordenador_selecionado != "Todos":
    vendedores_filtrados = df_bi[df_bi['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor'].dropna().unique()
else:
    vendedores_filtrados = df_bi['nome_vendedor'].dropna().unique()

lista_vendedores = ["Todos"] + sorted(vendedores_filtrados.tolist())
vendedor_selecionado = st.sidebar.selectbox("Vendedor", lista_vendedores)

if vendedor_selecionado != "Todos":
    clientes_do_vendedor = df_base[df_base['nome_vendedor'] == vendedor_selecionado]['codigo_cliente'].unique()
    coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_vendedor)]['Cliente_Coligacao'].dropna().unique()
elif coordenador_selecionado != "Todos":
    vendedores_do_coord = df_bi[df_bi['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor'].unique()
    clientes_do_coord = df_base[df_base['nome_vendedor'].isin(vendedores_do_coord)]['codigo_cliente'].unique()
    coligacoes_filtradas = df_base[df_base['codigo_cliente'].isin(clientes_do_coord)]['Cliente_Coligacao'].dropna().unique()
else:
    coligacoes_filtradas = df_base['Cliente_Coligacao'].dropna().unique()

lista_coligacoes = ["Todas"] + sorted(coligacoes_filtradas.tolist())
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
    df_filtrado = df_filtrado[df_filtrado['Nome_Coordenador'] == coordenador_selecionado]
if coligacao_selecionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Cliente_Coligacao'] == coligacao_selecionada]
if ano_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Ano'] == int(ano_selecionado)]

# ============================================================
# MÉTRICAS
# ============================================================
if vendedor_selecionado != "Todos":
    total_clientes_base = df_base[df_base['nome_vendedor'] == vendedor_selecionado]['codigo_cliente'].nunique()
elif coordenador_selecionado != "Todos":
    vendedores_do_coord = df_bi[df_bi['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor'].unique()
    total_clientes_base = df_base[df_base['nome_vendedor'].isin(vendedores_do_coord)]['codigo_cliente'].nunique()
elif coligacao_selecionada != "Todas":
    total_clientes_base = df_base[df_base['Cliente_Coligacao'] == coligacao_selecionada]['codigo_cliente'].nunique()
else:
    total_clientes_base = df_base['codigo_cliente'].nunique()

clientes_positivados_ids = df_filtrado[df_filtrado['Nome_Fabricante'].notna()]['codigo_cliente'].unique()
total_clientes_positivados = len(clientes_positivados_ids)
pct_positivacao = (total_clientes_positivados / total_clientes_base * 100) if total_clientes_base > 0 else 0

cobertura_por_cliente = df_filtrado.groupby('codigo_cliente')['Nome_Fabricante'].nunique()
cobertura_media = cobertura_por_cliente.mean() if len(cobertura_por_cliente) > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📋 Clientes na Carteira", total_clientes_base)
col2.metric("✅ Clientes Positivados", total_clientes_positivados)
col3.metric("📈 % Positivação", f"{pct_positivacao:.1f}%")
col4.metric("📊 Cobertura Média", f"{cobertura_media:.1f} indústrias")
col5.metric("🏭 Indústrias", len(INDUSTRIAS))

st.divider()

# ============================================================
# BATALHA NAVAL - SUBSTITUÍDA POR BOTÃO PDF
# ============================================================
st.subheader("📋 Relatório de Positivação")

# Criar matriz para o relatório
matriz = df_filtrado.pivot_table(
    index='codigo_cliente',
    columns='Nome_Fabricante',
    aggfunc='size',
    fill_value=0
)

mapa_nomes = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates('codigo_cliente')
mapa_nomes_dict = dict(zip(mapa_nomes['codigo_cliente'], mapa_nomes['nome_cliente']))

matriz['Nome_Cliente'] = matriz.index.map(lambda x: mapa_nomes_dict.get(x, 'N/A'))
matriz['Total_Indústrias'] = (matriz.drop(columns=['Nome_Cliente']) > 0).sum(axis=1)
matriz_bin = (matriz.drop(columns=['Nome_Cliente', 'Total_Indústrias']) > 0).astype(int)
matriz_bin['Nome_Cliente'] = matriz['Nome_Cliente']
matriz_bin['Total_Indústrias'] = matriz['Total_Indústrias']
matriz_bin = matriz_bin.reset_index()
matriz_bin = matriz_bin.rename(columns={'codigo_cliente': 'Código'})
matriz_bin = matriz_bin[['Código', 'Nome_Cliente'] + [c for c in matriz_bin.columns if c not in ['Código', 'Nome_Cliente', 'Total_Indústrias']] + ['Total_Indústrias']]

st.metric("📊 Clientes na Matriz", len(matriz_bin))

# Botão de download
csv = matriz_bin.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar Relatório (CSV)",
    data=csv,
    file_name=f'positivacao_{datetime.now().strftime("%Y%m%d")}.csv',
    mime='text/csv'
)

st.caption("O relatório contém: Código, Nome, Indústrias (1=Positivado, 0=Não) e Total")

st.divider()

# ============================================================
# PERFORMANCE
# ============================================================
st.subheader("👥 Performance por Vendedor")

df_base_filtrada = df_base.copy()
if coordenador_selecionado != "Todos":
    vendedores_do_coord = df_bi[df_bi['Nome_Coordenador'] == coordenador_selecionado]['nome_vendedor'].unique()
    df_base_filtrada = df_base_filtrada[df_base_filtrada['nome_vendedor'].isin(vendedores_do_coord)]
if coligacao_selecionada != "Todas":
    df_base_filtrada = df_base_filtrada[df_base_filtrada['Cliente_Coligacao'] == coligacao_selecionada]

vendedores_base = df_base_filtrada['nome_vendedor'].dropna().unique()

perf_list = []
for vendedor in vendedores_base:
    clientes_carteira = df_base_filtrada[df_base_filtrada['nome_vendedor'] == vendedor]['codigo_cliente'].nunique()
    df_bi_vendedor = df_filtrado[df_filtrado['nome_vendedor'] == vendedor]
    clientes_positivados = df_bi_vendedor[df_bi_vendedor['Nome_Fabricante'].notna()]['codigo_cliente'].nunique()
    cobertura = df_bi_vendedor.groupby('codigo_cliente')['Nome_Fabricante'].nunique()
    cobertura_media = cobertura.mean() if len(cobertura) > 0 else 0
    pct = (clientes_positivados / clientes_carteira * 100) if clientes_carteira > 0 else 0
    
    perf_list.append({
        'Vendedor': vendedor,
        'Total_Clientes': clientes_carteira,
        'Clientes_Positivados': clientes_positivados,
        '%_Positivação': round(pct, 1),
        'Cobertura_Media': round(cobertura_media, 1)
    })

perf_vendedor = pd.DataFrame(perf_list)
perf_vendedor = perf_vendedor.sort_values('%_Positivação', ascending=False)

col1, col2 = st.columns(2)

with col1:
    fig_bar = px.bar(
        perf_vendedor, x='Vendedor', y='%_Positivação',
        title='% de Positivação por Vendedor',
        text=perf_vendedor['%_Positivação'].apply(lambda x: f'{x:.1f}%'),
        color='%_Positivação', color_continuous_scale='Greens'
    )
    fig_bar.update_traces(textposition='outside')
    fig_bar.update_layout(xaxis_title="", yaxis_title="% Positivação", yaxis_range=[0, 105])
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    fig_bar2 = px.bar(
        perf_vendedor, x='Vendedor', y='Cobertura_Media',
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
# FICHA DO CLIENTE - MATRIZ MENSAL
# ============================================================
st.subheader("🔍 Ficha do Cliente - Performance Mensal")

try:
    df_clientes_unicos = df_filtrado[['codigo_cliente', 'nome_cliente']].drop_duplicates()
    df_clientes_unicos = df_clientes_unicos.dropna(subset=['codigo_cliente', 'nome_cliente'])
    df_clientes_unicos['codigo_str'] = df_clientes_unicos['codigo_cliente'].astype(str).str.strip()
    df_clientes_unicos['nome_str'] = df_clientes_unicos['nome_cliente'].astype(str).str.strip()
    df_clientes_unicos['cliente_label'] = df_clientes_unicos['codigo_str'] + ' - ' + df_clientes_unicos['nome_str']
    lista_clientes = sorted(df_clientes_unicos['cliente_label'].unique().tolist())
except:
    lista_clientes = []

if len(lista_clientes) > 0:
    cliente_selecionado_label = st.selectbox("Selecione um cliente:", lista_clientes, key='ficha_cliente')

    if cliente_selecionado_label:
        try:
            codigo_selecionado = cliente_selecionado_label.split(' - ')[0].strip()
            
            df_filtrado['codigo_str'] = df_filtrado['codigo_cliente'].astype(str).str.strip()
            df_cliente = df_filtrado[df_filtrado['codigo_str'] == codigo_selecionado]

            if not df_cliente.empty:
                nome = str(df_cliente['nome_cliente'].iloc[0])
                coligacao = str(df_cliente['Cliente_Coligacao'].iloc[0])
                vendedor = str(df_cliente['nome_vendedor'].iloc[0])
                coordenador = str(df_cliente['Nome_Coordenador'].iloc[0])

                st.write(f"**Código:** {codigo_selecionado} | **Nome:** {nome}")
                st.write(f"**Coligação:** {coligacao} | **Vendedor:** {vendedor} | **Coordenador:** {coordenador}")

                # Matriz mensal: Indústrias × Meses
                st.write("**Positivação por Indústria e Mês:**")
                
                meses_ordenados = sorted(df_cliente['Mês_Ano'].dropna().unique())
                
                matriz_mensal = df_cliente.pivot_table(
                    index='Nome_Fabricante',
                    columns='Mês_Ano',
                    aggfunc='size',
                    fill_value=0
                )
                matriz_mensal = (matriz_mensal > 0).astype(int)
                
                # Reordenar colunas
                matriz_mensal = matriz_mensal.reindex(columns=meses_ordenados, fill_value=0)
                
                # Adicionar total
                matriz_mensal['Total'] = matriz_mensal.sum(axis=1)
                
                # Destacar visualmente
                def highlight(val):
                    if isinstance(val, (int, float)):
                        if val > 0:
                            return 'background-color: #0F5220; color: white'
                        else:
                            return 'background-color: #8B0000; color: white'
                    return ''
                
                st.dataframe(
                    matriz_mensal.style.applymap(highlight),
                    use_container_width=True
                )
                
                total_industrias = len(matriz_mensal)
                st.caption(f"🟢 Verde = Positivado no mês | 🔴 Vermelho = Não positivado | Total de indústrias: {total_industrias}")
                
            else:
                st.warning("Cliente não encontrado nos dados filtrados.")
        except Exception as e:
            st.warning("Erro ao carregar dados do cliente.")
else:
    st.warning("Nenhum cliente encontrado com os filtros atuais.")

st.divider()
st.caption(f"Última atualização: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')} | Fonte: Google Sheets")

import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MeliAds Strategist Pro", page_icon="🚀", layout="wide")

# --- ESTILO CSS (CORRIGIDO PARA MODO ESCURO/CLARO) ---
st.markdown("""
<style>
    /* Estilo dos Cartões de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6; /* Fundo cinza claro suave */
        border-left: 5px solid #2e86de; /* Barra lateral azul */
        padding: 15px;
        border-radius: 8px;
        color: #31333F; /* Força texto escuro dentro do cartão */
        box-shadow: 1px 1px 4px rgba(0,0,0,0.1);
    }
    
    /* Forçar a cor do rótulo (Label) da métrica para escuro */
    div[data-testid="stMetricLabel"] > label {
        color: #31333F !important;
    }
    
    /* Forçar a cor do valor da métrica para escuro */
    div[data-testid="stMetricValue"] {
        color: #31333F !important;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png", width=150)
    st.title("Configurações")
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Carregar Relatório (.csv/.xlsx)", type=['csv', 'xlsx'])
    st.markdown("---")
    st.info("💡 **Dica:** Baixe o relatório de 'Últimos 15 ou 30 dias' no painel do Mercado Livre para uma análise mais precisa.")

# --- CABEÇALHO ---
st.title("🚀 MeliAds Strategist Pro")
st.markdown("#### Inteligência Artificial para Escala e Rentabilidade")
st.markdown("---")

# Função de Limpeza
def clean_numeric(x):
    if isinstance(x, str):
        x = x.replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(x)
        except:
            return 0.0
    return x

# --- PROCESSAMENTO ---
if uploaded_file is not None:
    try:
        # Leitura
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=1)
        else:
            df = pd.read_excel(uploaded_file, header=1)

        # Limpeza Colunas
        df.columns = [c.strip().replace('\n', ' ') for c in df.columns]

        # Limpeza Numérica
        cols_to_clean = ['Investimento (Moeda local)', 'Receita (Moeda local)', 'Orçamento', 
                        'ACOS Objetivo', '% de impressões perdidas por orçamento', 
                        '% de impressões perdidas por classificação']
        
        for col in cols_to_clean:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].apply(clean_numeric)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Agrupamento (Consolidar dados da mesma campanha)
        if 'Desde' in df.columns:
            df['Desde'] = pd.to_datetime(df['Desde'], errors='coerce')
            df = df.sort_values(by=['Nome', 'Desde'])

        agg_rules = {
            'Status': 'last',
            'Orçamento': 'last',
            'ACOS Objetivo': 'last',
            'Investimento (Moeda local)': 'sum',
            'Receita (Moeda local)': 'sum',
            '% de impressões perdidas por orçamento': 'mean',
            '% de impressões perdidas por classificação': 'mean'
        }

        df_grouped = df.groupby('Nome').agg(agg_rules).reset_index()

        # Métricas Calculadas
        df_grouped['ROAS_Real'] = df_grouped.apply(lambda x: x['Receita (Moeda local)'] / x['Investimento (Moeda local)'] if x['Investimento (Moeda local)'] > 0 else 0, axis=1)
        df_grouped['ACOS_Real'] = df_grouped.apply(lambda x: (x['Investimento (Moeda local)'] / x['Receita (Moeda local)'] * 100) if x['Receita (Moeda local)'] > 0 else 0, axis=1)

        # Lógica de Decisão
        def get_recommendation(row):
            status = str(row.get('Status', '')).lower()
            if 'ativa' not in status and row['Investimento (Moeda local)'] == 0:
                return "⚪ Inativa"
            
            # Escala
            if row['% de impressões perdidas por orçamento'] > 20 and row['ROAS_Real'] > 7:
                return "🟢 AUMENTAR ORÇAMENTO"
            
            # Competitividade
            if row['% de impressões perdidas por classificação'] > 40 and row['ROAS_Real'] > 7:
                return "🟡 SUBIR ACOS ALVO"
            
            # Detratoras
            target = row['ACOS Objetivo'] if row['ACOS Objetivo'] > 0 else 15
            if row['ACOS_Real'] > (target + 5) and row['Investimento (Moeda local)'] > 50:
                return "🔴 REDUZIR META / PAUSAR"
            
            return "🔵 MANTER"

        df_grouped['Ação Recomendada'] = df_grouped.apply(get_recommendation, axis=1)

        # --- CÁLCULO DE POTENCIAL (SIMULADOR) ---
        def calc_potential(row):
            if "AUMENTAR ORÇAMENTO" in row['Ação Recomendada']:
                loss_pct = row['% de impressões perdidas por orçamento'] / 100
                if loss_pct > 0:
                    current_rev = row['Receita (Moeda local)']
                    projected_rev = current_rev / (1 - loss_pct)
                    gain = (projected_rev - current_rev) * 0.5 
                    return gain
            return 0

        df_grouped['Potencial_Ganho'] = df_grouped.apply(calc_potential, axis=1)
        potential_revenue = df_grouped['Potencial_Ganho'].sum()

        # --- DASHBOARD VISUAL ---
        
        # 1. KPIs
        col1, col2, col3, col4 = st.columns(4)
        total_inv = df_grouped['Investimento (Moeda local)'].sum()
        total_rev = df_grouped['Receita (Moeda local)'].sum()
        roas_geral = total_rev / total_inv if total_inv > 0 else 0

        col1.metric("Investimento Total", f"R$ {total_inv:,.2f}")
        col2.metric("Receita Atual", f"R$ {total_rev:,.2f}")
        col3.metric("ROAS Geral", f"{roas_geral:.2f}x")
        col4.metric("💰 Potencial Extra (Est.)", f"+ R$ {potential_revenue:,.2f}", delta="Oportunidade")

        # 2. Gráfico de Quadrantes (Scatter Plot)
        st.subheader("📊 Matriz de Oportunidade")
        st.caption("Eixo X: Investimento | Eixo Y: ROAS | Tamanho da Bolha: Receita")
        
        # Filtrar inativas para o gráfico ficar limpo
        df_chart = df_grouped[df_grouped['Receita (Moeda local)'] > 0]
        
        fig = px.scatter(
            df_chart,
            x="Investimento (Moeda local)",
            y="ROAS_Real",
            size="Receita (Moeda local)",
            color="Ação Recomendada",
            hover_name="Nome",
            color_discrete_map={
                "🟢 AUMENTAR ORÇAMENTO": "green",
                "🟡 SUBIR ACOS ALVO": "#FFC107",
                "🔵 MANTER": "blue",
                "🔴 REDUZIR META / PAUSAR": "red"
            },
            log_x=True # Escala logarítmica ajuda a ver campanhas pequenas e grandes juntas
        )
        st.plotly_chart(fig, use_container_width=True)

        # 3. Tabela de Ação
        st.markdown("---")
        st.subheader("📋 Plano de Ação Detalhado")

        # Filtros na Sidebar
        filtro_acao = st.sidebar.multiselect(
            "Filtrar Tabela por Ação:",
            options=df_grouped['Ação Recomendada'].unique(),
            default=df_grouped['Ação Recomendada'].unique()
        )
        
        df_show = df_grouped[df_grouped['Ação Recomendada'].isin(filtro_acao)].copy()
        df_show = df_show.sort_values(by='ROAS_Real', ascending=False)

        # Exibir Tabela
        st.dataframe(
            df_show[['Nome', 'Orçamento', 'ACOS Objetivo', 'ROAS_Real', '% de impressões perdidas por orçamento', '% de impressões perdidas por classificação', 'Ação Recomendada']].style.format({
                'Orçamento': 'R$ {:.2f}',
                'ACOS Objetivo': '{:.1f}%',
                'ROAS_Real': '{:.2f}',
                '% de impressões perdidas por orçamento': '{:.1f}%',
                '% de impressões perdidas por classificação': '{:.1f}%'
            }),
            use_container_width=True,
            height=500
        )

        # 4. Botão de Download (Exportar)
        csv = df_show.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Baixar Análise em Excel (CSV)",
            data=csv,
            file_name='Analise_MeliAds_Pro.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"Erro ao processar o arquivo. Detalhes: {e}")

else:
    # Tela de Boas-vindas
    st.info("👈 Faça o upload do seu relatório na barra lateral para começar.")

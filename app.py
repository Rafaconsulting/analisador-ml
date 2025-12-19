import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="MeliAds Strategist", page_icon="🚀", layout="wide")

# Estilo CSS para deixar bonito
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚀 MeliAds Strategist Pro")
st.markdown("### Inteligência Artificial para Escala de Campanhas no Mercado Livre")
st.markdown("---")

# 1. UPLOAD
uploaded_file = st.file_uploader("Arraste seu relatório aqui (.csv ou .xlsx)", type=['csv', 'xlsx'])

def clean_numeric(x):
    if isinstance(x, str):
        x = x.replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(x)
        except:
            return 0.0
    return x

if uploaded_file is not None:
    try:
        # 2. LEITURA E TRATAMENTO
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=1)
        else:
            df = pd.read_excel(uploaded_file, header=1)

        # Limpeza de colunas
        df.columns = [c.strip().replace('\n', ' ') for c in df.columns]

        # Conversão numérica
        cols_to_clean = ['Investimento (Moeda local)', 'Receita (Moeda local)', 'Orçamento', 
                        'ACOS Objetivo', '% de impressões perdidas por orçamento', 
                        '% de impressões perdidas por classificação']
        
        for col in cols_to_clean:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].apply(clean_numeric)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. AGRUPAMENTO (Consolidar dados da mesma campanha)
        # Ordenar por data se existir
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

        # Agrupar
        df_grouped = df.groupby('Nome').agg(agg_rules).reset_index()

        # Métricas Reais
        df_grouped['ROAS_Real'] = df_grouped.apply(lambda x: x['Receita (Moeda local)'] / x['Investimento (Moeda local)'] if x['Investimento (Moeda local)'] > 0 else 0, axis=1)
        df_grouped['ACOS_Real'] = df_grouped.apply(lambda x: (x['Investimento (Moeda local)'] / x['Receita (Moeda local)'] * 100) if x['Receita (Moeda local)'] > 0 else 0, axis=1)

        # 4. LÓGICA DE DECISÃO
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

        # 5. EXIBIÇÃO (DASHBOARD)
        total_inv = df_grouped['Investimento (Moeda local)'].sum()
        total_rev = df_grouped['Receita (Moeda local)'].sum()
        roas_geral = total_rev / total_inv if total_inv > 0 else 0

        # KPI Cards
        st.markdown("### 📊 Visão Geral da Conta")
        col1, col2, col3 = st.columns(3)
        col1.metric("Investimento Total", f"R$ {total_inv:,.2f}")
        col2.metric("Receita Total", f"R$ {total_rev:,.2f}")
        col3.metric("ROAS Geral", f"{roas_geral:.2f}x")

        st.markdown("---")
        
        # Filtros
        st.subheader("📋 Plano de Ação Tático")
        filtro = st.multiselect("Filtrar por Recomendação:", 
                                options=["🟢 AUMENTAR ORÇAMENTO", "🟡 SUBIR ACOS ALVO", "🔵 MANTER", "🔴 REDUZIR META / PAUSAR"],
                                default=["🟢 AUMENTAR ORÇAMENTO", "🟡 SUBIR ACOS ALVO", "🔴 REDUZIR META / PAUSAR"])
        
        df_show = df_grouped[df_grouped['Ação Recomendada'].isin(filtro)].copy()
        df_show = df_show.sort_values(by='ROAS_Real', ascending=False)

        # Tabela
        st.dataframe(
            df_show[['Nome', 'Orçamento', 'ACOS Objetivo', 'ROAS_Real', '% de impressões perdidas por orçamento', '% de impressões perdidas por classificação', 'Ação Recomendada']].style.format({
                'Orçamento': 'R$ {:.2f}',
                'ACOS Objetivo': '{:.1f}%',
                'ROAS_Real': '{:.2f}',
                '% de impressões perdidas por orçamento': '{:.1f}%',
                '% de impressões perdidas por classificação': '{:.1f}%'
            }),
            use_container_width=True,
            height=600
        )

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")

else:
    st.info("Aguardando upload do arquivo...")

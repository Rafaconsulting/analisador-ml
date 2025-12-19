import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="MeliAds Strategist", page_icon="🚀", layout="wide")

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("https://http2.mlstatic.com/frontend-assets/ml-web-navigation/ui-navigation/5.21.22/mercadolibre/logo__large_plus.png", width=150)
    st.title("MeliAds Pro")
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Importar Relatório (.csv/.xlsx)", type=['csv', 'xlsx'])
    st.info("💡 Use o relatório de 'Últimos 15 ou 30 dias' para melhor precisão.")

# --- CABEÇALHO ---
st.title("🚀 Painel de Estratégia MeliAds")
st.markdown("#### Diagnóstico de Rentabilidade e Escala")
st.markdown("---")

# Função de Limpeza Numérica
def clean_numeric(x):
    if isinstance(x, str):
        x = x.replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(x)
        except:
            return 0.0
    return x

# --- PROCESSAMENTO DE DADOS ---
if uploaded_file is not None:
    try:
        # 1. Leitura
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=1)
        else:
            df = pd.read_excel(uploaded_file, header=1)

        # 2. Limpeza
        df.columns = [c.strip().replace('\n', ' ') for c in df.columns]
        
        cols_to_clean = ['Investimento (Moeda local)', 'Receita (Moeda local)', 'Orçamento', 
                        'ACOS Objetivo', '% de impressões perdidas por orçamento', 
                        '% de impressões perdidas por classificação']
        
        for col in cols_to_clean:
            if col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].apply(clean_numeric)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 3. Agrupamento
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

        # 4. Cálculos Reais
        df_grouped['ROAS_Real'] = df_grouped.apply(lambda x: x['Receita (Moeda local)'] / x['Investimento (Moeda local)'] if x['Investimento (Moeda local)'] > 0 else 0, axis=1)
        df_grouped['ACOS_Real'] = df_grouped.apply(lambda x: (x['Investimento (Moeda local)'] / x['Receita (Moeda local)'] * 100) if x['Receita (Moeda local)'] > 0 else 0, axis=1)

        # 5. LÓGICA DE DECISÃO
        def get_recommendation(row):
            status = str(row.get('Status', '')).lower()
            if 'ativa' not in status and row['Investimento (Moeda local)'] == 0:
                return "Inativa"
            
            # Escala
            if row['% de impressões perdidas por orçamento'] > 20 and row['ROAS_Real'] > 7:
                return "AUMENTAR ORÇAMENTO 🟢"
            
            # Competitividade
            if row['% de impressões perdidas por classificação'] > 40 and row['ROAS_Real'] > 7:
                return "SUBIR ACOS ALVO 🟡"
            
            # Detratoras
            target = row['ACOS Objetivo'] if row['ACOS Objetivo'] > 0 else 15
            if row['ACOS_Real'] > (target + 5) and row['Investimento (Moeda local)'] > 50:
                return "PAUSAR / REDUZIR 🔴"
            
            return "MANTER 🔵"

        df_grouped['Ação'] = df_grouped.apply(get_recommendation, axis=1)

        # Potencial
        def calc_potential(row):
            if "AUMENTAR" in row['Ação']:
                loss_pct = row['% de impressões perdidas por orçamento'] / 100
                if loss_pct > 0 and loss_pct < 1:
                    current_rev = row['Receita (Moeda local)']
                    projected_rev = current_rev / (1 - loss_pct)
                    return (projected_rev - current_rev) * 0.5 
            return 0

        df_grouped['Potencial Extra'] = df_grouped.apply(calc_potential, axis=1)
        potential_total = df_grouped['Potencial Extra'].sum()

        # --- VISUALIZAÇÃO ---

        total_inv = df_grouped['Investimento (Moeda local)'].sum()
        total_rev = df_grouped['Receita (Moeda local)'].sum()
        roas_geral = total_rev / total_inv if total_inv > 0 else 0

        # ESTILO CSS - CARTÕES ESCUROS (NAVY BLUE)
        # Fundo: #2c3e50 (Azul escuro quase cinza)
        # Texto: #ffffff (Branco puro)
        # Isso garante contraste em qualquer tema.
        
        card_style = """
            background-color: #2c3e50; 
            border-radius: 10px; 
            padding: 20px; 
            text-align: center;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
            color: white;
            margin-bottom: 10px;
        """
        title_style = "font-size: 14px; color: #ecf0f1; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;"
        value_style = "font-size: 28px; color: #ffffff; font-weight: 700; margin: 0;"
        highlight_green = "color: #2ecc71;"
        highlight_blue = "color: #3498db;"
        highlight_gold = "color: #f1c40f;"

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{title_style}">Investimento Total</div>
                <div style="{value_style}">R$ {total_inv:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with c2:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{title_style}">Receita Atual</div>
                <div style="{value_style}">R$ {total_rev:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{title_style}">ROAS Global</div>
                <div style="{value_style}"><span style="{highlight_green}">{roas_geral:.2f}x</span></div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div style="{card_style}">
                <div style="{title_style}">Potencial Extra</div>
                <div style="{value_style}"><span style="{highlight_gold}">+ R$ {potential_total:,.2f}</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. GRÁFICO DE BARRAS
        st.subheader("📊 Distribuição de Receita por Ação")
        
        df_chart = df_grouped[df_grouped['Receita (Moeda local)'] > 0].groupby('Ação')['Receita (Moeda local)'].sum().reset_index()
        
        color_map = {
            "AUMENTAR ORÇAMENTO 🟢": "#2ecc71", 
            "SUBIR ACOS ALVO 🟡": "#f1c40f", 
            "MANTER 🔵": "#3498db", 
            "PAUSAR / REDUZIR 🔴": "#e74c3c", 
            "Inativa": "#95a5a6"
        }

        fig = px.bar(
            df_chart, 
            x='Receita (Moeda local)', 
            y='Ação', 
            orientation='h',
            text_auto='.2s',
            color='Ação',
            color_discrete_map=color_map,
            height=350
        )
        # Ajuste de layout para garantir visibilidade do texto no gráfico
        fig.update_layout(
            showlegend=False, 
            xaxis_title="Receita Total (R$)", 
            yaxis_title=None,
            font=dict(color="gray")
        )
        st.plotly_chart(fig, use_container_width=True)

        # 3. TABELA DE AÇÃO
        st.markdown("---")
        st.subheader("📋 Plano de Ação Tático")
        
        acoes_unicas = sorted(df_grouped['Ação'].unique())
        filtro_acao = st.multiselect("Filtrar por Ação:", acoes_unicas, default=acoes_unicas)
        
        df_show = df_grouped[df_grouped['Ação'].isin(filtro_acao)].copy()
        df_show = df_show.sort_values(by='ROAS_Real', ascending=False)
        
        cols_final = ['Nome', 'Ação', 'Orçamento', 'ACOS Objetivo', 'ROAS_Real', 'Potencial Extra', 
                      '% de impressões perdidas por orçamento', '% de impressões perdidas por classificação']

        st.dataframe(
            df_show[cols_final],
            column_config={
                "Nome": st.column_config.TextColumn("Campanha", width="medium"),
                "Ação": st.column_config.TextColumn("Recomendação", width="medium"),
                "Orçamento": st.column_config.NumberColumn("Orçamento", format="R$ %.2f"),
                "ACOS Objetivo": st.column_config.NumberColumn("Meta ACOS", format="%.1f%%"),
                "ROAS_Real": st.column_config.ProgressColumn("ROAS", format="%.2f", min_value=0, max_value=20),
                "Potencial Extra": st.column_config.NumberColumn("Potencial", format="R$ %.2f"),
                "% de impressões perdidas por orçamento": st.column_config.NumberColumn("Perda $$", format="%.1f%%"),
                "% de impressões perdidas por classificação": st.column_config.NumberColumn("Perda Rank", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

        # 4. Download
        csv = df_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Tabela em Excel (CSV)",
            data=csv,
            file_name='Plano_MeliAds.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"Erro ao processar: {e}")

else:
    st.info("👈 Faça o upload do relatório na barra lateral.")

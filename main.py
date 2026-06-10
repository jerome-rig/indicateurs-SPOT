import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Indicateurs SPOT", layout="wide", page_icon="🚂")

ETF_BLEU = "#1B2A6B"
ETF_ROUGE = "#E63027"
ETF_GRIS = "#F5F7FA"
PALETTE = [ETF_BLEU, ETF_ROUGE, "#4A6FA5", "#A0B0D0", "#8B0000", "#6B8CBF"]

st.markdown(f"""
    <div style="background-color:{ETF_BLEU}; padding:18px 24px; border-radius:8px; margin-bottom:16px;">
        <div style="border-left: 5px solid {ETF_ROUGE}; padding-left:14px;">
            <span style="color:white; font-size:22px; font-weight:700; letter-spacing:1px;">🚂 INDICATEURS SPOT</span><br>
            <span style="color:#A0B0D0; font-size:13px;">ETF Services — Suivi de production ferroviaire</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# ─── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────

@st.cache_data
def charger_donnees():
    import io, requests
    url = "https://github.com/jerome-rig/indicateurs-SPOT/releases/download/v1.0/Reunion.Production.2024-2025-2026.xlsx"
    fichier = io.BytesIO(requests.get(url).content)

    cols_communes = ['DATE', 'OTP', 'ST', 'CONF', 'NC', 'CAUSE NC', 'SOUS-CAUSE NC', 'CALE', 'AJOUT ACHE EN OP']
    cols_2025_2026 = ['Numéro de spot']
    cols_2026 = ['SENS DE TRAVAIL CONFORME', 'SENS DE TRAVAIL NON CONFORME']

    df_2024 = pd.read_excel(fichier, sheet_name="2024", header=2)
    df_2024 = df_2024[cols_communes].copy()
    df_2024['ANNEE'] = 2024

    df_2025 = pd.read_excel(fichier, sheet_name="2025", header=2)
    df_2025 = df_2025[cols_communes + cols_2025_2026].copy()
    df_2025['ANNEE'] = 2025

    df_2026 = pd.read_excel(fichier, sheet_name="2026", header=2)
    df_2026 = df_2026[cols_communes + cols_2025_2026 + cols_2026].copy()
    df_2026['ANNEE'] = 2026

    for df in [df_2024, df_2025, df_2026]:
        df['MOIS'] = df['DATE'].dt.month
        df['SEMAINE'] = df['DATE'].dt.isocalendar().week.astype('Int64')

    valeurs_invalides = ['OK', 'X', 'OLK', 'MANQUE PRESTA', 'ST']
    mapping_doublons = {
        'SÉCURAIL': 'SECURAIL', 'FEROMOOVE': 'FERROMOVE', 'FEROMOVE': 'FERROMOVE',
        'CLAISSE RAIL': 'CLMTP', 'CLAISSERAIL': 'CLMTP', 'INFRA': 'INFRARAIL',
        'INFRA RAIL': 'INFRARAIL', 'INFARAIL': 'INFRARAIL', 'CTSF + SNCF': 'CTSF',
        'TIME FRET': 'TFE', 'SNCF (SILLON)': 'SNCF', 'A-TEAM': 'ATEAM', 'TEAM A': 'ATEAM',
        'EIFFFAGE': 'EIFFAGE',
    }

    for df in [df_2024, df_2025, df_2026]:
        df['ST'] = df['ST'].str.strip().str.upper()
        df['ST'] = df['ST'].replace(mapping_doublons)
        df['ST'] = df['ST'].replace(valeurs_invalides, 'NON RENSEIGNE')
        df['ST'] = df['ST'].fillna('INTERNE')

    df_all = pd.concat([df_2024, df_2025, df_2026], ignore_index=True)

    mapping_client = {
        2024: {
            '701': 'TX MECA NORD', '702': 'GRAND PROJET', '705': 'GRAND PROJET',
            '707': 'GRAND PROJET', '703': 'ETF DIRECTION MATERIEL',
            '704': 'EXTERNE', '706': 'DR SUD',
        },
        2025: {
            '707': 'TX MECA NORD', '708': 'TX MECA NORD', '709': 'TX MECA NORD',
            '710': 'TX MECA NORD', '711': 'TX MECA NORD', '705': 'GRAND PROJET',
            '704': 'GRAND PROJET', '706': 'GRAND PROJET', '712': 'DR SUD',
            '701': 'CHAILLOUE', '703': 'ETF DIRECTION MATERIEL', '702': 'EXTERNE',
        },
        2026: {
            '707': 'TX MECA NORD', '705': 'GRAND PROJET', '712': 'DR SUD',
            '701': 'CHAILLOUE', '703': 'ETF DIRECTION MATERIEL', '702': 'EXTERNE',
        },
    }

    def assigner_client(row):
        try:
            otp = str(int(float(str(row['OTP']).strip())))
        except (ValueError, TypeError):
            otp = str(row['OTP']).strip()
        return mapping_client.get(row['ANNEE'], {}).get(otp, 'NON RENSEIGNE')

    df_all['CLIENT'] = df_all.apply(assigner_client, axis=1)
    return df_all


df_all = charger_donnees()

NOMS_MOIS = ['JANVIER', 'FEVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN',
             'JUILLET', 'AOUT', 'SEPTEMBRE', 'OCTOBRE', 'NOVEMBRE', 'DECEMBRE']
CLIENTS = ['TOUS', 'TX MECA NORD', 'GRAND PROJET', 'DR SUD', 'CHAILLOUE', 'ETF DIRECTION MATERIEL', 'EXTERNE']
AVERTISSEMENT_2024 = (
    "⚠️ Pour l'année 2024, la correspondance OTP → Client est une estimation. "
    "Les résultats filtrés par client sur 2024 sont à interpréter avec prudence."
)

imputations_options = ['TOUS'] + sorted(df_all['CAUSE NC'].dropna().str.strip().str.upper().unique().tolist())
motifs_options = ['TOUS'] + sorted(df_all['SOUS-CAUSE NC'].dropna().str.strip().str.upper().unique().tolist())


def clients_pour_annee(annee):
    return CLIENTS if annee != 2024 else ['TOUS']


# ─── NAVIGATION SIDEBAR ───────────────────────────────────────────────────────

st.sidebar.markdown(f"<div style='color:{ETF_ROUGE}; font-weight:700; font-size:13px; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;'>Indicateurs ST</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-size:12px; color:#888; margin-bottom:2px;'>Sous-traitants</div>", unsafe_allow_html=True)

PAGES_ST = [
    "Sillons par ST",
    "Répartition ST",
    "Top 5 ST",
    "Volume mensuel ST",
]

PAGES_SILLONS = [
    "Sillons — Volume mensuel",
    "Sillons — Tendance par client",
    "Sillons — Comparaison 3 ans",
    "Sillons — Tendance 3 ans",
]

PAGES_PREST = [
    "Prestations — Volume mensuel",
    "Prestations — Répartition par client",
]

PAGES_NC = [
    "NC — Part par mois",
    "NC — Comparaison 3 ans",
    "NC — Tendance 2025/2026",
    "NC — Répartition imputations",
    "NC — Volume par client",
]

PAGES_CALES = [
    "Calés — Part par mois",
    "Calés — Tendance 3 ans",
    "Ajouts OP — Volume mensuel",
    "Ajouts OP — Tendance 3 ans",
    "Ajouts OP — Répartition par client",
]

page = st.sidebar.radio(
    "ST",
    PAGES_ST,
    label_visibility="collapsed",
)

st.sidebar.markdown(f"<div style='color:{ETF_ROUGE}; font-weight:700; font-size:13px; text-transform:uppercase; letter-spacing:1px; margin-top:12px; margin-bottom:2px;'>Indicateurs Production</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='font-size:12px; color:#888; margin-bottom:2px;'>Sillons</div>", unsafe_allow_html=True)

page_prod = st.sidebar.radio(
    "Sillons",
    PAGES_SILLONS,
    label_visibility="collapsed",
)

st.sidebar.markdown("<div style='font-size:12px; color:#888; margin-top:6px; margin-bottom:2px;'>Prestations</div>", unsafe_allow_html=True)
page_prest = st.sidebar.radio(
    "Prestations",
    PAGES_PREST,
    label_visibility="collapsed",
)

st.sidebar.markdown("<div style='font-size:12px; color:#888; margin-top:6px; margin-bottom:2px;'>Non-conformités</div>", unsafe_allow_html=True)
page_nc = st.sidebar.radio(
    "NC",
    PAGES_NC,
    label_visibility="collapsed",
)

st.sidebar.markdown("<div style='font-size:12px; color:#888; margin-top:6px; margin-bottom:2px;'>Calés & Ajouts OP</div>", unsafe_allow_html=True)
page_cales = st.sidebar.radio(
    "Cales",
    PAGES_CALES,
    label_visibility="collapsed",
)

# Déterminer la page active (dernière cliquée)
# On utilise session_state pour tracker quel groupe a été cliqué en dernier
if 'last_group' not in st.session_state:
    st.session_state.last_group = 'st'

for grp, pages, key in [
    ('st', PAGES_ST, page),
    ('sillons', PAGES_SILLONS, page_prod),
    ('prest', PAGES_PREST, page_prest),
    ('nc', PAGES_NC, page_nc),
    ('cales', PAGES_CALES, page_cales),
]:
    if f'prev_{grp}' not in st.session_state:
        st.session_state[f'prev_{grp}'] = key
    if st.session_state[f'prev_{grp}'] != key:
        st.session_state.last_group = grp
        st.session_state[f'prev_{grp}'] = key

grp = st.session_state.last_group
if grp == 'st':
    indicateur = page
elif grp == 'sillons':
    indicateur = page_prod
elif grp == 'prest':
    indicateur = page_prest
elif grp == 'nc':
    indicateur = page_nc
else:
    indicateur = page_cales


# ═══════════════════════════════════════════════════════════════════════════════
# RENDU DES INDICATEURS
# ═══════════════════════════════════════════════════════════════════════════════

def evol(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(a == 0, None, ((b - a) / a * 100).round(1))


# ── Sillons par ST ────────────────────────────────────────────────────────────
if indicateur == "Sillons par ST":
    st.header("Sillons circulés par ST et par année")
    st.caption(AVERTISSEMENT_2024)

    client_recap = st.selectbox("Client", CLIENTS, key="recap_client")
    df_f = df_all if client_recap == 'TOUS' else df_all[df_all['CLIENT'] == client_recap]
    vol = df_f.groupby(['ANNEE', 'ST']).size().reset_index(name='count')
    recap = vol.pivot_table(index='ST', columns='ANNEE', values='count', aggfunc='sum').fillna(0).astype(int)
    recap.columns = [str(c) for c in recap.columns]
    for col in ['2024', '2025', '2026']:
        if col not in recap.columns:
            recap[col] = 0
    recap['Évol. 24→25 (%)'] = evol(recap['2024'].values, recap['2025'].values)
    recap['Évol. 25→26 (%)'] = evol(recap['2025'].values, recap['2026'].values)
    recap = recap[['2024', '2025', '2026', 'Évol. 24→25 (%)', 'Évol. 25→26 (%)']].sort_values('2025', ascending=False)
    interne = recap.loc[recap.index == 'INTERNE'] if 'INTERNE' in recap.index else pd.DataFrame()
    externe = recap.loc[recap.index != 'INTERNE']
    total_ext = pd.DataFrame({
        '2024': [int(externe['2024'].sum())], '2025': [int(externe['2025'].sum())], '2026': [int(externe['2026'].sum())],
        'Évol. 24→25 (%)': evol(externe['2024'].sum(), externe['2025'].sum()),
        'Évol. 25→26 (%)': evol(externe['2025'].sum(), externe['2026'].sum()),
    }, index=['TOTAL ST EXTERNE'])
    total_global = pd.DataFrame({
        '2024': [int(recap['2024'].sum())], '2025': [int(recap['2025'].sum())], '2026': [int(recap['2026'].sum())],
        'Évol. 24→25 (%)': evol(recap['2024'].sum(), recap['2025'].sum()),
        'Évol. 25→26 (%)': evol(recap['2025'].sum(), recap['2026'].sum()),
    }, index=['TOTAL GLOBAL'])
    st.dataframe(pd.concat([externe, total_ext, interne, total_global]), use_container_width=True)

# ── Répartition ST ────────────────────────────────────────────────────────────
elif indicateur == "Répartition ST":
    st.header("Répartition ST")
    st.caption(AVERTISSEMENT_2024)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        annee_cam = st.selectbox("Année", [2024, 2025, 2026], index=1, key="cam_annee")
    with col2:
        debut_cam = st.selectbox("Début", list(range(1, 13)), format_func=lambda x: NOMS_MOIS[x - 1], key="cam_debut")
    with col3:
        fin_cam = st.selectbox("Fin", list(range(1, 13)), index=11, format_func=lambda x: NOMS_MOIS[x - 1], key="cam_fin")
    with col4:
        client_cam = st.selectbox("Client", clients_pour_annee(annee_cam), key="cam_client")

    df_cam = df_all[
        (df_all['ANNEE'] == annee_cam) &
        (df_all['MOIS'] >= debut_cam) &
        (df_all['MOIS'] <= fin_cam) &
        (df_all['ST'] != 'INTERNE')
    ].copy()
    if client_cam != 'TOUS':
        df_cam = df_cam[df_cam['CLIENT'] == client_cam]
    vol_cam = df_cam.groupby('ST').size().reset_index(name='count')
    vol_cam['%'] = (vol_cam['count'] / vol_cam['count'].sum() * 100).round(1)
    vol_cam.loc[vol_cam['%'] < 3, 'ST'] = 'AUTRES'
    vol_cam = vol_cam.groupby('ST')[['count', '%']].sum().reset_index()
    fig_cam = px.pie(vol_cam, names='ST', values='count',
                     title=f'Répartition ST — {annee_cam} ({NOMS_MOIS[debut_cam - 1]} à {NOMS_MOIS[fin_cam - 1]})')
    fig_cam.update_traces(texttemplate='%{label}<br>%{percent:.1%} (%{value})')
    st.plotly_chart(fig_cam, use_container_width=True)

# ── Top 5 ST ──────────────────────────────────────────────────────────────────
elif indicateur == "Top 5 ST":
    st.header("Top 5 ST — Sillons circulés par année")
    st.caption(AVERTISSEMENT_2024)

    client_top5 = st.selectbox("Client", CLIENTS, key="top5_client")
    df_top5_f = df_all[df_all['ST'] != 'INTERNE']
    if client_top5 != 'TOUS':
        df_top5_f = df_top5_f[df_top5_f['CLIENT'] == client_top5]
    top5 = df_top5_f.groupby('ST').size().sort_values(ascending=False).head(5).index.tolist()
    vol_top5 = df_top5_f.groupby(['ANNEE', 'ST']).size().reset_index(name='count')
    vol_top5['ANNEE'] = vol_top5['ANNEE'].astype(str)
    fig_top5 = px.bar(
        vol_top5[vol_top5['ST'].isin(top5)], x='ST', y='count', color='ANNEE', barmode='group',
        title='Top 5 ST — Nombre de sillons circulés par année',
        labels={'count': 'Nombre de sillons circulés', 'ANNEE': 'Année'},
        color_discrete_sequence=PALETTE, text='count',
    )
    fig_top5.update_traces(textposition='outside')
    st.plotly_chart(fig_top5, use_container_width=True)

# ── Volume mensuel ST ─────────────────────────────────────────────────────────
elif indicateur == "Volume mensuel ST":
    st.header("Volume mensuel par ST")
    st.caption(AVERTISSEMENT_2024)

    st_liste = ['TOUS'] + sorted(df_all[df_all['ST'] != 'INTERNE']['ST'].dropna().unique())
    col1, col2, col3 = st.columns(3)
    with col1:
        st_sel = st.selectbox("ST", st_liste, key="mensuel_st")
    with col2:
        annee_mensuel = st.selectbox("Année", [2024, 2025, 2026], index=1, key="mensuel_annee")
    with col3:
        client_mensuel = st.selectbox("Client", clients_pour_annee(annee_mensuel), key="mensuel_client")

    df_mensuel = df_all[(df_all['ST'] != 'INTERNE') & (df_all['ANNEE'] == annee_mensuel)].dropna(subset=['MOIS']).copy()
    if st_sel != 'TOUS':
        df_mensuel = df_mensuel[df_mensuel['ST'] == st_sel]
    if client_mensuel != 'TOUS':
        df_mensuel = df_mensuel[df_mensuel['CLIENT'] == client_mensuel]
    df_mensuel['MOIS'] = df_mensuel['MOIS'].astype(int)
    vol_mensuel = df_mensuel.groupby('MOIS').size().reset_index(name='Nombre de sillons')
    vol_mensuel['PERIODE'] = vol_mensuel['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    titre = f'Volume mensuel — {"Tous les ST" if st_sel == "TOUS" else st_sel} — {annee_mensuel}'
    fig_mensuel = px.bar(vol_mensuel, x='PERIODE', y='Nombre de sillons',
                         title=titre, category_orders={'PERIODE': NOMS_MOIS},
                         text='Nombre de sillons', color_discrete_sequence=[ETF_BLEU])
    fig_mensuel.update_traces(textposition='outside')
    st.plotly_chart(fig_mensuel, use_container_width=True)

# ── Sillons — Volume mensuel ──────────────────────────────────────────────────
elif indicateur == "Sillons — Volume mensuel":
    st.header("Sillons — Volume mensuel par année")
    st.caption(AVERTISSEMENT_2024)

    col1, col2 = st.columns(2)
    with col1:
        annee_sillons = st.selectbox("Année", [2024, 2025, 2026], index=1, key="sillons_annee")
    with col2:
        client_sillons = st.selectbox("Client", clients_pour_annee(annee_sillons), key="sillons_client")

    df_s = df_all[df_all['ANNEE'] == annee_sillons].dropna(subset=['MOIS']).copy()
    if client_sillons != 'TOUS':
        df_s = df_s[df_s['CLIENT'] == client_sillons]
    df_s['MOIS'] = df_s['MOIS'].astype(int)
    vol_s = df_s.groupby('MOIS').size().reset_index(name='Nombre de sillons')
    vol_s['PERIODE'] = vol_s['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_s = px.bar(vol_s, x='PERIODE', y='Nombre de sillons',
                   title=f'Sillons circulés par mois — {annee_sillons}',
                   category_orders={'PERIODE': NOMS_MOIS}, text='Nombre de sillons',
                   color_discrete_sequence=[ETF_BLEU])
    fig_s.update_traces(textposition='outside')
    st.plotly_chart(fig_s, use_container_width=True)

# ── Sillons — Tendance par client ─────────────────────────────────────────────
elif indicateur == "Sillons — Tendance par client":
    st.header("Sillons — Tendance mensuelle par client")
    st.caption(AVERTISSEMENT_2024)

    annee_pc = st.selectbox("Année", [2024, 2025, 2026], index=1, key="sillons_par_client_annee")
    df_pc = df_all[df_all['ANNEE'] == annee_pc].dropna(subset=['MOIS']).copy()
    df_pc['MOIS'] = df_pc['MOIS'].astype(int)
    vol_pc = df_pc.groupby(['MOIS', 'CLIENT']).size().reset_index(name='Nombre de sillons')
    vol_pc['PERIODE'] = vol_pc['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_pc = px.line(vol_pc, x='PERIODE', y='Nombre de sillons', color='CLIENT', markers=True,
                     title=f'Tendance des sillons par mois et par client — {annee_pc}',
                     category_orders={'PERIODE': NOMS_MOIS}, labels={'CLIENT': 'Client'},
                     color_discrete_sequence=PALETTE)
    st.plotly_chart(fig_pc, use_container_width=True)

# ── Sillons — Comparaison 3 ans ───────────────────────────────────────────────
elif indicateur == "Sillons — Comparaison 3 ans":
    st.header("Sillons — Comparaison mensuelle 2024 / 2025 / 2026")
    st.caption(AVERTISSEMENT_2024)

    client_comp = st.selectbox("Client", CLIENTS, key="comp_client")
    df_comp = df_all.dropna(subset=['MOIS']).copy()
    if client_comp != 'TOUS':
        df_comp = df_comp[(df_comp['ANNEE'] != 2024) & (df_comp['CLIENT'] == client_comp)]
        st.warning("⚠️ Données 2024 non disponibles par client. Seules les années 2025 et 2026 sont affichées.")
        annees_aff = ['2025', '2026']
    else:
        annees_aff = ['2024', '2025', '2026']
    df_comp['MOIS'] = df_comp['MOIS'].astype(int)
    vol_comp = df_comp.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Nombre de sillons')
    vol_comp['PERIODE'] = vol_comp['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    vol_comp['ANNEE'] = vol_comp['ANNEE'].astype(str)
    fig_comp = px.bar(vol_comp, x='PERIODE', y='Nombre de sillons', color='ANNEE', barmode='group',
                      title='Comparaison mensuelle ' + ' / '.join(annees_aff) + (f' — {client_comp}' if client_comp != 'TOUS' else ''),
                      category_orders={'PERIODE': NOMS_MOIS, 'ANNEE': annees_aff},
                      labels={'ANNEE': 'Année'}, text='Nombre de sillons',
                      color_discrete_sequence=PALETTE)
    fig_comp.update_traces(textposition='outside')
    st.plotly_chart(fig_comp, use_container_width=True)

# ── Sillons — Tendance 3 ans ──────────────────────────────────────────────────
elif indicateur == "Sillons — Tendance 3 ans":
    st.header("Sillons — Tendance 2024 / 2025 / 2026")

    client_courbe = st.selectbox("Client", CLIENTS, key="courbe_client")
    df_courbe = df_all.dropna(subset=['MOIS']).copy()
    if client_courbe != 'TOUS':
        df_courbe = df_courbe[df_courbe['CLIENT'] == client_courbe]
    df_courbe['MOIS'] = df_courbe['MOIS'].astype(int)
    vol_courbe = df_courbe.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Nombre de sillons')
    vol_courbe['PERIODE'] = vol_courbe['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_courbe = px.line(vol_courbe, x='PERIODE', y='Nombre de sillons', color='ANNEE', markers=True,
                         title='Tendance des sillons circulés par mois — 2024 / 2025 / 2026',
                         category_orders={'PERIODE': NOMS_MOIS}, labels={'ANNEE': 'Année'},
                         color_discrete_sequence=PALETTE)
    st.plotly_chart(fig_courbe, use_container_width=True)

# ── Prestations — Volume mensuel ──────────────────────────────────────────────
elif indicateur == "Prestations — Volume mensuel":
    st.header("Prestations — Volume mensuel 2026")

    client_prest = st.selectbox("Client", CLIENTS, key="prest_client")
    df_prest = df_all[(df_all['ANNEE'] == 2026) & (df_all['Numéro de spot'].notna())].dropna(subset=['MOIS']).copy()
    if client_prest != 'TOUS':
        df_prest = df_prest[df_prest['CLIENT'] == client_prest]
    df_prest['MOIS'] = df_prest['MOIS'].astype(int)
    vol_prest = df_prest.groupby('MOIS')['Numéro de spot'].nunique().reset_index(name='Nombre de prestations')
    vol_prest['PERIODE'] = vol_prest['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_prest = px.bar(vol_prest, x='PERIODE', y='Nombre de prestations',
                       title='Prestations réalisées par mois — 2026' + (f' — {client_prest}' if client_prest != 'TOUS' else ''),
                       category_orders={'PERIODE': NOMS_MOIS}, text='Nombre de prestations',
                       color_discrete_sequence=[ETF_BLEU])
    fig_prest.update_traces(textposition='outside')
    st.plotly_chart(fig_prest, use_container_width=True)

# ── Prestations — Répartition par client ──────────────────────────────────────
elif indicateur == "Prestations — Répartition par client":
    st.header("Répartition par client — Sillons et Prestations")

    annee_cam_s = st.selectbox("Année (sillons)", [2025, 2026], index=1, key="cam_sillons_annee")
    vol_cam_s = df_all[df_all['ANNEE'] == annee_cam_s].groupby('CLIENT').size().reset_index(name='count')
    fig_cam_s = px.pie(vol_cam_s, names='CLIENT', values='count',
                       title=f'Répartition des sillons par client — {annee_cam_s}',
                       color_discrete_sequence=PALETTE)
    fig_cam_s.update_traces(texttemplate='%{label}<br>%{percent:.1%} (%{value})')

    df_p2026 = df_all[(df_all['ANNEE'] == 2026) & (df_all['Numéro de spot'].notna())]
    vol_cam_p = df_p2026.groupby('CLIENT')['Numéro de spot'].nunique().reset_index(name='count')
    fig_cam_p = px.pie(vol_cam_p, names='CLIENT', values='count',
                       title='Répartition des prestations par client — 2026',
                       color_discrete_sequence=PALETTE)
    fig_cam_p.update_traces(texttemplate='%{label}<br>%{percent:.1%} (%{value})')

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_cam_s, use_container_width=True)
    with col2:
        st.plotly_chart(fig_cam_p, use_container_width=True)

# ── NC — Part par mois ────────────────────────────────────────────────────────
elif indicateur == "NC — Part par mois":
    st.header("NC — Part de non-conformités par mois")
    st.caption(AVERTISSEMENT_2024)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        annee_nc = st.selectbox("Année", [2024, 2025, 2026], index=2, key="nc_annee")
    with col2:
        client_nc = st.selectbox("Client", clients_pour_annee(annee_nc), key="nc_client")
    with col3:
        imputation_nc = st.selectbox("Imputation", imputations_options, key="nc_imputation")
    with col4:
        motif_nc = st.selectbox("Motif", motifs_options, key="nc_motif")

    df_nc = df_all[df_all['ANNEE'] == annee_nc].dropna(subset=['MOIS']).copy()
    df_nc['MOIS'] = df_nc['MOIS'].astype(int)
    if client_nc != 'TOUS':
        df_nc = df_nc[df_nc['CLIENT'] == client_nc]
    df_sans = df_nc[~(df_nc['NC'].apply(lambda x: str(x).strip().upper() == 'X'))].copy()
    df_avec = df_nc[df_nc['NC'].apply(lambda x: str(x).strip().upper() == 'X')].copy()
    if imputation_nc != 'TOUS':
        df_avec = df_avec[df_avec['CAUSE NC'].str.strip().str.upper() == imputation_nc]
    if motif_nc != 'TOUS':
        df_avec = df_avec[df_avec['SOUS-CAUSE NC'].str.strip().str.upper() == motif_nc]
    df_sans['CATEGORIE'] = 'Sans NC'
    df_avec['CATEGORIE'] = 'Avec NC'
    vol_nc = pd.concat([df_sans, df_avec]).groupby(['MOIS', 'CATEGORIE']).size().reset_index(name='Nombre de sillons')
    vol_nc['PERIODE'] = vol_nc['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_nc = px.bar(vol_nc, x='PERIODE', y='Nombre de sillons', color='CATEGORIE', barmode='stack',
                    title=f'Sillons circulés par mois — dont NC — {annee_nc}' + (f' — {client_nc}' if client_nc != 'TOUS' else ''),
                    category_orders={'PERIODE': NOMS_MOIS, 'CATEGORIE': ['Sans NC', 'Avec NC']},
                    color_discrete_map={'Sans NC': ETF_BLEU, 'Avec NC': ETF_ROUGE},
                    text='Nombre de sillons')
    fig_nc.update_traces(textposition='inside')
    st.plotly_chart(fig_nc, use_container_width=True)

# ── NC — Comparaison 3 ans ────────────────────────────────────────────────────
elif indicateur == "NC — Comparaison 3 ans":
    st.header("NC — Comparaison mensuelle 2024 / 2025 / 2026")
    st.caption(AVERTISSEMENT_2024)

    col1, col2, col3 = st.columns(3)
    with col1:
        client_nc_comp = st.selectbox("Client", CLIENTS, key="nc_comp_client")
    with col2:
        imputation_nc_comp = st.selectbox("Imputation", imputations_options, key="nc_comp_imputation")
    with col3:
        motif_nc_comp = st.selectbox("Motif", motifs_options, key="nc_comp_motif")

    df_nc_comp = df_all.dropna(subset=['MOIS']).copy()
    df_nc_comp['MOIS'] = df_nc_comp['MOIS'].astype(int)
    if client_nc_comp != 'TOUS':
        df_nc_comp = df_nc_comp[(df_nc_comp['ANNEE'] != 2024) & (df_nc_comp['CLIENT'] == client_nc_comp)]
        st.warning("⚠️ Données 2024 non disponibles par client. Seules les années 2025 et 2026 sont affichées.")
    df_nc_comp = df_nc_comp[df_nc_comp['NC'].apply(lambda x: str(x).strip().upper() == 'X')]
    if imputation_nc_comp != 'TOUS':
        df_nc_comp = df_nc_comp[df_nc_comp['CAUSE NC'].str.strip().str.upper() == imputation_nc_comp]
    if motif_nc_comp != 'TOUS':
        df_nc_comp = df_nc_comp[df_nc_comp['SOUS-CAUSE NC'].str.strip().str.upper() == motif_nc_comp]
    vol_nc_comp = df_nc_comp.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Nombre de NC')
    vol_nc_comp['PERIODE'] = vol_nc_comp['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    vol_nc_comp['ANNEE'] = vol_nc_comp['ANNEE'].astype(str)
    annees_nc = sorted(df_nc_comp['ANNEE'].unique().astype(str).tolist())
    fig_nc_comp = px.bar(vol_nc_comp, x='PERIODE', y='Nombre de NC', color='ANNEE', barmode='group',
                         title='Nombre de NC par mois — ' + ' / '.join(annees_nc) + (f' — {client_nc_comp}' if client_nc_comp != 'TOUS' else ''),
                         category_orders={'PERIODE': NOMS_MOIS, 'ANNEE': annees_nc},
                         labels={'ANNEE': 'Année'}, text='Nombre de NC',
                         color_discrete_sequence=PALETTE)
    fig_nc_comp.update_traces(textposition='outside')
    st.plotly_chart(fig_nc_comp, use_container_width=True)

# ── NC — Tendance 2025/2026 ───────────────────────────────────────────────────
elif indicateur == "NC — Tendance 2025/2026":
    st.header("NC — Tendance mensuelle 2025 / 2026")

    col1, col2, col3 = st.columns(3)
    with col1:
        client_nc_courbe = st.selectbox("Client", CLIENTS, key="nc_courbe_client")
    with col2:
        imputation_nc_courbe = st.selectbox("Imputation", imputations_options, key="nc_courbe_imputation")
    with col3:
        motif_nc_courbe = st.selectbox("Motif", motifs_options, key="nc_courbe_motif")

    df_nc_courbe = df_all[df_all['ANNEE'].isin([2025, 2026])].dropna(subset=['MOIS']).copy()
    df_nc_courbe['MOIS'] = df_nc_courbe['MOIS'].astype(int)
    if client_nc_courbe != 'TOUS':
        df_nc_courbe = df_nc_courbe[df_nc_courbe['CLIENT'] == client_nc_courbe]
    df_nc_courbe = df_nc_courbe[df_nc_courbe['NC'].apply(lambda x: str(x).strip().upper() == 'X')]
    if imputation_nc_courbe != 'TOUS':
        df_nc_courbe = df_nc_courbe[df_nc_courbe['CAUSE NC'].str.strip().str.upper() == imputation_nc_courbe]
    if motif_nc_courbe != 'TOUS':
        df_nc_courbe = df_nc_courbe[df_nc_courbe['SOUS-CAUSE NC'].str.strip().str.upper() == motif_nc_courbe]
    vol_nc_courbe = df_nc_courbe.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Nombre de NC')
    vol_nc_courbe['PERIODE'] = vol_nc_courbe['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    vol_nc_courbe['ANNEE'] = vol_nc_courbe['ANNEE'].astype(str)
    fig_nc_courbe = px.line(vol_nc_courbe, x='PERIODE', y='Nombre de NC', color='ANNEE', markers=True,
                             title='Tendance des NC — 2025 / 2026' + (f' — {client_nc_courbe}' if client_nc_courbe != 'TOUS' else ''),
                             category_orders={'PERIODE': NOMS_MOIS, 'ANNEE': ['2025', '2026']},
                             labels={'ANNEE': 'Année'}, color_discrete_sequence=PALETTE)
    st.plotly_chart(fig_nc_courbe, use_container_width=True)

# ── NC — Répartition imputations ──────────────────────────────────────────────
elif indicateur == "NC — Répartition imputations":
    st.header("NC — Répartition par Imputation et par Motif")

    date_min = df_all['DATE'].dropna().min().date()
    date_max = df_all['DATE'].dropna().max().date()
    col1, col2, col3 = st.columns(3)
    with col1:
        date_debut = st.date_input("Date début", value=date_min, key="nc_cam_debut")
    with col2:
        date_fin = st.date_input("Date fin", value=date_max, key="nc_cam_fin")
    with col3:
        client_nc_cam = st.selectbox("Client", CLIENTS, key="nc_cam_client")

    if date_debut > date_fin:
        st.error("⚠️ La date de début doit être antérieure à la date de fin.")
    else:
        df_nc_cam = df_all[
            (df_all['NC'].apply(lambda x: str(x).strip().upper() == 'X')) &
            (df_all['DATE'].dt.date >= date_debut) &
            (df_all['DATE'].dt.date <= date_fin)
        ].copy()
        if client_nc_cam != 'TOUS':
            df_nc_cam = df_nc_cam[df_nc_cam['CLIENT'] == client_nc_cam]
        if df_nc_cam.empty:
            st.warning("Aucune NC trouvée sur cette période.")
        else:
            vol_imp = df_nc_cam.groupby('CAUSE NC').size().reset_index(name='count')
            fig_imp = px.pie(vol_imp, names='CAUSE NC', values='count',
                             title=f'NC par Imputation — {date_debut} au {date_fin}' + (f' — {client_nc_cam}' if client_nc_cam != 'TOUS' else ''),
                             color_discrete_sequence=PALETTE)
            fig_imp.update_traces(texttemplate='%{label}<br>%{percent:.1%} (%{value})')
            st.plotly_chart(fig_imp, use_container_width=True)

            pivot = df_nc_cam.pivot_table(index='SOUS-CAUSE NC', columns='CAUSE NC', aggfunc='size', fill_value=0)
            pivot.columns.name = None
            pivot.index.name = 'Motif'
            pivot['TOTAL'] = pivot.sum(axis=1)
            pivot['%'] = (pivot['TOTAL'] / pivot['TOTAL'].sum() * 100).round(1)
            pivot = pivot.sort_values('TOTAL', ascending=False)
            total_row = pivot.sum(numeric_only=True).to_frame().T
            total_row.index = ['TOTAL']
            total_row['%'] = 100.0
            tableau = pd.concat([pivot, total_row])
            cols_int = [c for c in tableau.columns if c != '%']
            tableau[cols_int] = tableau[cols_int].astype(int)
            st.markdown("**NC par Motif et Imputation**")
            st.dataframe(tableau, use_container_width=True)

# ── NC — Volume par client ────────────────────────────────────────────────────
elif indicateur == "NC — Volume par client":
    st.header("NC — Volume mensuel par client")
    st.caption(AVERTISSEMENT_2024)

    annee_nc_client = st.selectbox("Année", [2024, 2025, 2026], index=2, key="nc_client_annee")
    df_nc_cl = df_all[
        (df_all['ANNEE'] == annee_nc_client) &
        (df_all['NC'].apply(lambda x: str(x).strip().upper() == 'X'))
    ].dropna(subset=['MOIS']).copy()
    df_nc_cl['MOIS'] = df_nc_cl['MOIS'].astype(int)
    vol_nc_cl = df_nc_cl.groupby(['MOIS', 'CLIENT']).size().reset_index(name='Nombre de NC')
    vol_nc_cl['PERIODE'] = vol_nc_cl['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_nc_cl = px.bar(vol_nc_cl, x='PERIODE', y='Nombre de NC', color='CLIENT', barmode='group',
                       title=f'NC par client et par mois — {annee_nc_client}',
                       category_orders={'PERIODE': NOMS_MOIS}, labels={'CLIENT': 'Client'},
                       text='Nombre de NC', color_discrete_sequence=PALETTE)
    fig_nc_cl.update_traces(textposition='outside')
    st.plotly_chart(fig_nc_cl, use_container_width=True)

# ── Calés — Part par mois ─────────────────────────────────────────────────────
elif indicateur == "Calés — Part par mois":
    st.header("Sillons calés — Part par mois")
    st.caption(AVERTISSEMENT_2024)

    col1, col2 = st.columns(2)
    with col1:
        annee_cale = st.selectbox("Année", [2024, 2025, 2026], index=2, key="cale_annee")
    with col2:
        client_cale = st.selectbox("Client", clients_pour_annee(annee_cale), key="cale_client")

    df_cale = df_all[df_all['ANNEE'] == annee_cale].dropna(subset=['MOIS']).copy()
    df_cale['MOIS'] = df_cale['MOIS'].astype(int)
    if client_cale != 'TOUS':
        df_cale = df_cale[df_cale['CLIENT'] == client_cale]
    df_cale['CATEGORIE'] = df_cale['CALE'].apply(lambda x: 'Calé' if str(x).strip().upper() == 'X' else 'Non calé')
    vol_cale = df_cale.groupby(['MOIS', 'CATEGORIE']).size().reset_index(name='Nombre de sillons')
    vol_cale['PERIODE'] = vol_cale['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_cale = px.bar(vol_cale, x='PERIODE', y='Nombre de sillons', color='CATEGORIE', barmode='stack',
                      title=f'Sillons circulés — dont calés — {annee_cale}' + (f' — {client_cale}' if client_cale != 'TOUS' else ''),
                      category_orders={'PERIODE': NOMS_MOIS, 'CATEGORIE': ['Non calé', 'Calé']},
                      color_discrete_map={'Non calé': ETF_BLEU, 'Calé': ETF_ROUGE},
                      text='Nombre de sillons')
    fig_cale.update_traces(selector={'name': 'Non calé'}, textposition='inside', insidetextanchor='start')
    fig_cale.update_traces(selector={'name': 'Calé'}, textposition='outside')
    st.plotly_chart(fig_cale, use_container_width=True)

# ── Calés — Tendance 3 ans ────────────────────────────────────────────────────
elif indicateur == "Calés — Tendance 3 ans":
    st.header("Sillons calés — Tendance 2024 / 2025 / 2026")

    client_cale_courbe = st.selectbox("Client", CLIENTS, key="cale_courbe_client")
    df_cale_courbe = df_all[df_all['CALE'].apply(lambda x: str(x).strip().upper() == 'X')].dropna(subset=['MOIS']).copy()
    df_cale_courbe['MOIS'] = df_cale_courbe['MOIS'].astype(int)
    if client_cale_courbe != 'TOUS':
        df_cale_courbe = df_cale_courbe[(df_cale_courbe['ANNEE'] != 2024) & (df_cale_courbe['CLIENT'] == client_cale_courbe)]
        st.warning("⚠️ Données 2024 non disponibles par client. Seules les années 2025 et 2026 sont affichées.")
    vol_cale_courbe = df_cale_courbe.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Nombre de sillons calés')
    vol_cale_courbe['PERIODE'] = vol_cale_courbe['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    vol_cale_courbe['ANNEE'] = vol_cale_courbe['ANNEE'].astype(str)
    fig_cale_courbe = px.line(vol_cale_courbe, x='PERIODE', y='Nombre de sillons calés', color='ANNEE', markers=True,
                               title='Tendance des sillons calés par mois' + (f' — {client_cale_courbe}' if client_cale_courbe != 'TOUS' else ''),
                               category_orders={'PERIODE': NOMS_MOIS, 'ANNEE': ['2024', '2025', '2026']},
                               labels={'ANNEE': 'Année'}, color_discrete_sequence=PALETTE)
    st.plotly_chart(fig_cale_courbe, use_container_width=True)

# ── Ajouts OP — Volume mensuel ────────────────────────────────────────────────
elif indicateur == "Ajouts OP — Volume mensuel":
    st.header("Acheminements ajoutés en opérationnel — Volume mensuel")
    st.caption(AVERTISSEMENT_2024)

    col1, col2 = st.columns(2)
    with col1:
        annee_ajout = st.selectbox("Année", [2024, 2025, 2026], index=2, key="ajout_annee")
    with col2:
        client_ajout = st.selectbox("Client", clients_pour_annee(annee_ajout), key="ajout_client")

    df_ajout = df_all[df_all['ANNEE'] == annee_ajout].dropna(subset=['MOIS']).copy()
    df_ajout['MOIS'] = df_ajout['MOIS'].astype(int)
    if client_ajout != 'TOUS':
        df_ajout = df_ajout[df_ajout['CLIENT'] == client_ajout]
    df_ajout['CATEGORIE'] = df_ajout['AJOUT ACHE EN OP'].apply(
        lambda x: 'Ajouté en OP' if str(x).strip().upper() == 'X' else 'Non ajouté'
    )
    vol_ajout = df_ajout.groupby(['MOIS', 'CATEGORIE']).size().reset_index(name='Nombre')
    vol_ajout['PERIODE'] = vol_ajout['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_ajout = px.bar(vol_ajout, x='PERIODE', y='Nombre', color='CATEGORIE', barmode='stack',
                       title=f'Acheminements ajoutés en opérationnel — {annee_ajout}' + (f' — {client_ajout}' if client_ajout != 'TOUS' else ''),
                       category_orders={'PERIODE': NOMS_MOIS, 'CATEGORIE': ['Non ajouté', 'Ajouté en OP']},
                       color_discrete_map={'Non ajouté': ETF_BLEU, 'Ajouté en OP': ETF_ROUGE},
                       text='Nombre')
    fig_ajout.update_traces(selector={'name': 'Non ajouté'}, textposition='inside', insidetextanchor='start')
    fig_ajout.update_traces(selector={'name': 'Ajouté en OP'}, textposition='outside')
    st.plotly_chart(fig_ajout, use_container_width=True)

# ── Ajouts OP — Tendance 3 ans ────────────────────────────────────────────────
elif indicateur == "Ajouts OP — Tendance 3 ans":
    st.header("Acheminements ajoutés en OP — Tendance 2024 / 2025 / 2026")

    client_ajout_courbe = st.selectbox("Client", CLIENTS, key="ajout_courbe_client")
    df_ajout_courbe = df_all[df_all['AJOUT ACHE EN OP'].apply(lambda x: str(x).strip().upper() == 'X')].dropna(subset=['MOIS']).copy()
    df_ajout_courbe['MOIS'] = df_ajout_courbe['MOIS'].astype(int)
    if client_ajout_courbe != 'TOUS':
        df_ajout_courbe = df_ajout_courbe[(df_ajout_courbe['ANNEE'] != 2024) & (df_ajout_courbe['CLIENT'] == client_ajout_courbe)]
        st.warning("⚠️ Données 2024 non disponibles par client. Seules les années 2025 et 2026 sont affichées.")
    vol_ajout_courbe = df_ajout_courbe.groupby(['ANNEE', 'MOIS']).size().reset_index(name='Ajoutés en OP')
    vol_ajout_courbe['PERIODE'] = vol_ajout_courbe['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    vol_ajout_courbe['ANNEE'] = vol_ajout_courbe['ANNEE'].astype(str)
    fig_ajout_courbe = px.line(vol_ajout_courbe, x='PERIODE', y='Ajoutés en OP', color='ANNEE', markers=True,
                                title='Tendance des acheminements ajoutés en OP' + (f' — {client_ajout_courbe}' if client_ajout_courbe != 'TOUS' else ''),
                                category_orders={'PERIODE': NOMS_MOIS, 'ANNEE': ['2024', '2025', '2026']},
                                labels={'ANNEE': 'Année'}, color_discrete_sequence=PALETTE)
    st.plotly_chart(fig_ajout_courbe, use_container_width=True)

# ── Ajouts OP — Répartition par client ───────────────────────────────────────
elif indicateur == "Ajouts OP — Répartition par client":
    st.header("Acheminements ajoutés en OP — Répartition par client")

    col1, col2 = st.columns(2)
    with col1:
        annee_ajout_cam = st.selectbox("Année (camembert)", [2025, 2026], index=1, key="ajout_cam_annee")
    with col2:
        annee_ajout_client = st.selectbox("Année (par client)", [2025, 2026], index=1, key="ajout_client_annee")

    df_ajout_cam = df_all[
        (df_all['ANNEE'] == annee_ajout_cam) &
        (df_all['AJOUT ACHE EN OP'].apply(lambda x: str(x).strip().upper() == 'X'))
    ].copy()
    vol_ajout_cam = df_ajout_cam.groupby('CLIENT').size().reset_index(name='count')
    fig_ajout_cam = px.pie(vol_ajout_cam, names='CLIENT', values='count',
                            title=f'Ajouts en OP par client — {annee_ajout_cam}',
                            color_discrete_sequence=PALETTE)
    fig_ajout_cam.update_traces(texttemplate='%{label}<br>%{percent:.1%} (%{value})')

    df_ajout_cl = df_all[
        (df_all['ANNEE'] == annee_ajout_client) &
        (df_all['AJOUT ACHE EN OP'].apply(lambda x: str(x).strip().upper() == 'X'))
    ].dropna(subset=['MOIS']).copy()
    df_ajout_cl['MOIS'] = df_ajout_cl['MOIS'].astype(int)
    vol_ajout_cl = df_ajout_cl.groupby(['MOIS', 'CLIENT']).size().reset_index(name='Ajoutés en OP')
    vol_ajout_cl['PERIODE'] = vol_ajout_cl['MOIS'].apply(lambda m: NOMS_MOIS[m - 1])
    fig_ajout_cl = px.line(vol_ajout_cl, x='PERIODE', y='Ajoutés en OP', color='CLIENT', markers=True,
                            title=f'Ajouts en OP par client et par mois — {annee_ajout_client}',
                            category_orders={'PERIODE': NOMS_MOIS}, labels={'CLIENT': 'Client'},
                            color_discrete_sequence=PALETTE)

    with col1:
        st.plotly_chart(fig_ajout_cam, use_container_width=True)
    with col2:
        st.plotly_chart(fig_ajout_cl, use_container_width=True)

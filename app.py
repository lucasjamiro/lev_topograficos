import streamlit as st
import folium
from streamlit_folium import st_folium
import simulator
import pandas as pd
import numpy as np

st.set_page_config(page_title="Simulador Topográfico Interativo", layout="wide")

# --- Session State Initialization ---
if 'survey_points' not in st.session_state:
    st.session_state.survey_points = []  # List of (lat, lon)
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None
if 'user_results' not in st.session_state:
    st.session_state.user_results = {}

def reset_survey():
    st.session_state.survey_points = []
    st.session_state.survey_data = None
    st.session_state.user_results = {}

st.title("🏗️ Simulador de Levantamentos Topográficos")

# --- Sidebar ---
st.sidebar.header("Configurações do Levantamento")

survey_category = st.sidebar.selectbox(
    "1. Tipo de Levantamento",
    ["Poligonação", "Nivelamento"],
    on_change=reset_survey
)

if survey_category == "Poligonação":
    survey_type = st.sidebar.radio("1.1 Tipo de Poligonal", ["Fechada", "Enquadrada"], on_change=reset_survey)
    n_points = st.sidebar.number_input("1.1.1 Número de vértices", min_value=3, max_value=50, value=5)

    st.sidebar.subheader("1.1.2 Coordenadas Conhecidas")
    if survey_type == "Fechada":
        st.sidebar.info("Poligonal fechada precisa de um par de pontos conhecidos (P1).")
        p1_lat = st.sidebar.number_input("P1 Latitude", value=-23.5505, format="%.6f")
        p1_lon = st.sidebar.number_input("P1 Longitude", value=-46.6333, format="%.6f")
        known_points = [(p1_lat, p1_lon)]
    else:
        st.sidebar.info("Poligonal enquadrada precisa de pontos no início (P1) e no fim (Pn).")
        p1_lat = st.sidebar.number_input("P1 Latitude", value=-23.5505, format="%.6f")
        p1_lon = st.sidebar.number_input("P1 Longitude", value=-46.6333, format="%.6f")
        pn_lat = st.sidebar.number_input("Pn Latitude", value=-23.5555, format="%.6f")
        pn_lon = st.sidebar.number_input("Pn Longitude", value=-46.6383, format="%.6f")
        known_points = [(p1_lat, p1_lon), (pn_lat, pn_lon)]

    if st.sidebar.button("Gerar Coordenadas Aleatórias"):
        if "survey_map" in st.session_state and st.session_state["survey_map"].get("center"):
            c_lat = st.session_state["survey_map"]["center"]["lat"]
            c_lon = st.session_state["survey_map"]["center"]["lng"]
        else:
            c_lat, c_lon = p1_lat, p1_lon

        if survey_type == "Fechada":
            lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=c_lat, start_lon=c_lon)
        else:
            lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=c_lat, start_lon=c_lon, end_coords=(pn_lat, pn_lon))
        st.session_state.survey_points = list(zip(lats, lons))

else: # Nivelamento
    survey_type = st.sidebar.radio("1.2 Tipo de Nivelamento", ["Geométrico", "Trigonométrico"], on_change=reset_survey)
    if survey_type == "Geométrico":
        method = st.sidebar.selectbox("1.2.1 Técnica", ["visadas iguais", "visadas equivalentes", "visadas recíprocas", "visadas extremas"])
    else:
        method = "trigonométrico"

    n_points = st.sidebar.number_input("Número de Pontos", min_value=2, max_value=50, value=5)
    start_lat = st.sidebar.number_input("Latitude Inicial", value=-23.5505, format="%.6f")
    start_lon = st.sidebar.number_input("Longitude Inicial", value=-46.6333, format="%.6f")

    if st.sidebar.button("Gerar Trajeto de Nivelamento"):
        lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=start_lat, start_lon=start_lon)
        st.session_state.survey_points = list(zip(lats, lons))

# --- Main Layout ---

col_map, col_data = st.columns([1.2, 0.8])

with col_map:
    st.subheader("Mapa Interativo")

    if st.session_state.survey_points:
        center_lat = st.session_state.survey_points[0][0]
        center_lon = st.session_state.survey_points[0][1]
    else:
        center_lat, center_lon = -23.5505, -46.6333

    m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

    if st.session_state.survey_points:
        points = st.session_state.survey_points
        folium.PolyLine(points, color="blue", weight=2.5, opacity=0.8).add_to(m)
        for i, (lat, lon) in enumerate(points):
            color = "red" if (i == 0 or (survey_category == "Poligonação" and survey_type == "Enquadrada" and i == len(points)-1)) else "blue"
            folium.CircleMarker(
                [lat, lon], radius=6, color=color, fill=True,
                popup=f"Ponto {i+1}"
            ).add_to(m)

    st.info("Clique no mapa para adicionar vértices manualmente.")
    map_data = st_folium(m, width=700, height=500, key="survey_map")

    if map_data.get("last_clicked"):
        clicked_coords = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
        if clicked_coords not in st.session_state.survey_points:
            st.session_state.survey_points.append(clicked_coords)
            st.rerun()

    if st.button("Limpar Pontos"):
        reset_survey()
        st.rerun()

with col_data:
    st.subheader("Dados dos Vértices")
    if st.session_state.survey_points:
        points_df = pd.DataFrame(st.session_state.survey_points, columns=["lat", "lon"])
        points_df.index = [f"P{i+1}" for i in range(len(points_df))]
        st.dataframe(points_df, width='stretch')

        if st.button("Simular Observações de Campo"):
            lats = points_df["lat"].values
            lons = points_df["lon"].values
            if survey_category == "Poligonação":
                st.session_state.survey_data = simulator.simulate_traverse_observations(lats, lons)
            else:
                obs, elevs = simulator.simulate_leveling(len(lats), type=survey_type, method=method if survey_type == "Geométrico" else "trigonométrico")
                st.session_state.survey_data = obs
                st.session_state.true_elevations = elevs
            st.rerun()

# --- Modules Output ---
if st.session_state.survey_data is not None:
    st.write("---")
    if survey_category == "Poligonação":
        st.subheader("🌐 Resultados da Poligonação")

        start_p = st.session_state.survey_points[0]
        pre, raw_coords, errors, adj_coords = simulator.process_traverse_data(
            st.session_state.survey_data,
            (start_p[0], start_p[1], 100.0),
            survey_type=survey_type
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Dados de Campo",
            "⚙️ Dados Pré-calculados",
            "📍 Coordenadas Iniciais",
            "📊 Análise de Erros",
            "✅ Coordenadas Finais (Bowditch)"
        ])

        with tab1:
            st.write("**Direções horizontais, ângulos zenitais e distâncias inclinadas.**")
            st.dataframe(st.session_state.survey_data, width='stretch')

        with tab2:
            st.write("**Conversão de direções para ângulos horizontais e distâncias horizontais.**")
            st.dataframe(pre, width='stretch')

        with tab3:
            st.write("**Coordenadas (X, Y, Z) calculadas sem correções.**")
            st.dataframe(raw_coords, width='stretch')

        with tab4:
            st.write("**Erros de fechamento e precisão relativa.**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Erro Angular", f"{errors['Erro Angular (°)']:.5f}°")
            c2.metric("Erro Planimétrico", f"{errors['Erro Planimétrico (m)']:.3f} m")
            c3.metric("Precisão Relativa", errors['Precisão Relativa'])
            st.metric("Erro Altimétrico", f"{errors['Erro Altimétrico (m)']:.3f} m")

        with tab5:
            st.write("**Coordenadas finais ajustadas pelo método de Bowditch.**")
            st.dataframe(adj_coords, width='stretch')

    else: # Nivelamento
        st.subheader("📐 Resultados do Nivelamento")
        if survey_type == "Geométrico":
            st.header("🔍 Módulo de Leitura de Réguas")
            selected_row = st.selectbox("Selecione a Estação para leitura", range(len(st.session_state.survey_data)))
            row = st.session_state.survey_data.iloc[selected_row]

            c1, c2 = st.columns(2)
            with c1:
                st.text(f"Leitura de Ré (Ponto {selected_row+1})")
                st.code(simulator.get_rod_reading_visual(row['V. Ré (m)']))
            with c2:
                st.text(f"Leitura de Vante (Ponto {selected_row+2})")
                st.code(simulator.get_rod_reading_visual(row['V. Vante (m)']))

        st.header("🧮 Módulo de Validação de Cálculos")
        st.write("Insira as cotas calculadas para cada ponto:")
        user_elevs = []
        cols = st.columns(3)
        for i in range(len(st.session_state.survey_points)):
            with cols[i % 3]:
                val = st.number_input(f"Cota P{i+1}", value=0.0, format="%.3f", key=f"user_elev_{i}")
                user_elevs.append(val)

        if st.button("Validar Cotas", use_container_width=True):
            true_elevs = st.session_state.true_elevations
            diffs = [u - t for u, t in zip(user_elevs, true_elevs)]
            comp_df = pd.DataFrame({
                "Ponto": [f"P{i+1}" for i in range(len(true_elevs))],
                "Calculado": user_elevs,
                "Referência": true_elevs,
                "Diferença (m)": diffs
            })
            st.dataframe(comp_df, width='stretch')

            st.header("📊 Análise de Erros")
            # For leveling, we compare with the true final elevation
            closure_error = user_elevs[-1] - true_elevs[-1]
            st.metric("Erro de Cálculo (m)", f"{closure_error:.3f} m")

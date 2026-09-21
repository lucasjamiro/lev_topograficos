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
if 'point_labels' not in st.session_state:
    st.session_state.point_labels = []
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None
if 'known_points_dict' not in st.session_state:
    st.session_state.known_points_dict = {}
if 'user_results' not in st.session_state:
    st.session_state.user_results = {}
if 'map_center' not in st.session_state:
    st.session_state.map_center = [-23.5505, -46.6333]
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 16

def reset_survey():
    st.session_state.survey_points = []
    st.session_state.point_labels = []
    st.session_state.survey_data = None
    st.session_state.known_points_dict = {}
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
        st.sidebar.info("Poligonal fechada precisa de um par de pontos conhecidos (HV1 e HV2).")
        hv1_lat = st.sidebar.number_input("HV1 Latitude", value=-23.5510, format="%.6f")
        hv1_lon = st.sidebar.number_input("HV1 Longitude", value=-46.6338, format="%.6f")
        hv2_lat = st.sidebar.number_input("HV2 Latitude", value=-23.5505, format="%.6f")
        hv2_lon = st.sidebar.number_input("HV2 Longitude", value=-46.6333, format="%.6f")
        known_points = [(hv1_lat, hv1_lon), (hv2_lat, hv2_lon)]
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
        elif survey_type == "Fechada":
            c_lat, c_lon = hv2_lat, hv2_lon
        else:
            c_lat, c_lon = p1_lat, p1_lon

        if survey_type == "Fechada":
            lats, lons, labels = simulator.generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=c_lat, start_lon=c_lon)
        else:
            lats, lons, labels = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=c_lat, start_lon=c_lon, end_coords=(pn_lat, pn_lon))
        st.session_state.survey_points = list(zip([float(x) for x in lats], [float(y) for y in lons]))
        st.session_state.point_labels = list(labels)

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
        lats, lons, labels = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=start_lat, start_lon=start_lon)
        st.session_state.survey_points = list(zip([float(x) for x in lats], [float(y) for y in lons]))
        st.session_state.point_labels = [f"P{i+1}" for i in range(len(lats))]

# --- Main Layout ---

col_map, col_data = st.columns([1.2, 0.8])

with col_map:
    st.subheader("Mapa Interativo")

    m = folium.Map(
        location=[float(st.session_state.map_center[0]), float(st.session_state.map_center[1])],
        zoom_start=int(st.session_state.map_zoom)
    )

    if st.session_state.survey_points:
        points = [(float(pt[0]), float(pt[1])) for pt in st.session_state.survey_points]
        labels = st.session_state.point_labels if len(st.session_state.point_labels) == len(points) else [f"P{i+1}" for i in range(len(points))]
        
        folium.PolyLine(points, color="blue", weight=2.5, opacity=0.8).add_to(m)
        
        for i, (lat, lon) in enumerate(points):
            lbl = labels[i]
            color = "red" if "HV" in lbl else "blue"
            folium.CircleMarker(
                [lat, lon], radius=6, color=color, fill=True,
                popup=f"Ponto {lbl}", tooltip=f"Ponto {lbl}"
            ).add_to(m)

    st.info("Clique no mapa para adicionar vértices manualmente.")

    # O st_folium volta a ser o renderizador oficial
    map_data = st_folium(
        m,
        width=700,
        height=500,
        returned_objects=["last_clicked", "center", "zoom"],
        key="survey_map"
    )

    if map_data:
        if map_data.get("center"):
            st.session_state.map_center = [float(map_data["center"]["lat"]), float(map_data["center"]["lng"])]
        if map_data.get("zoom"):
            st.session_state.map_zoom = int(map_data["zoom"])

        if map_data.get("last_clicked"):
            clicked_coords = (float(map_data["last_clicked"]["lat"]), float(map_data["last_clicked"]["lng"]))
            if clicked_coords not in st.session_state.survey_points:
                st.session_state.survey_points.append(clicked_coords)
                next_idx = len(st.session_state.survey_points)
                st.session_state.point_labels.append(f"P{next_idx}")
                st.rerun()

    if st.button("Limpar Pontos"):
        reset_survey()
        st.rerun()

# --- Modules Output ---
if st.session_state.survey_data is not None:
    st.write("---")
    if survey_category == "Poligonação":
        st.subheader("🌐 Resultados da Poligonação")

        pre, azimuths_df, raw_coords, errors, adj_coords = simulator.process_traverse_data(
            st.session_state.survey_data,
            st.session_state.known_points_dict,
            survey_type=survey_type
        )

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Dados de Campo",
            "⚙️ Dados Pré-calculados",
            "🧭 Azimutes Transportados",
            "📍 Coordenadas Iniciais",
            "📊 Análise de Erros",
            "✅ Coordenadas Finais (Bowditch)"
        ])

        with tab1:
            st.write("**Direções horizontais, ângulos zenitais e distâncias inclinadas.**")
            st.dataframe(st.session_state.survey_data, use_container_width=True)

        with tab2:
            st.write("**Conversão de direções para ângulos horizontais e distâncias horizontais.**")
            st.dataframe(pre, use_container_width=True)

        with tab3:
            st.write("**Transporte e correção passo a passo dos azimutes.**")
            st.dataframe(azimuths_df, use_container_width=True)

        with tab4:
            st.write("**Coordenadas (X, Y, Z) calculadas sem correções.**")
            st.dataframe(raw_coords, use_container_width=True)

        with tab5:
            st.write("**Erros de fechamento e precisão relativa.**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Erro Angular", f"{errors['Erro Angular (°)']:.5f}°")
            c2.metric("Erro Planimétrico", f"{errors['Erro Planimétrico (m)']:.3f} m")
            c3.metric("Precisão Relativa", errors['Precisão Relativa'])
            st.metric("Erro Altimétrico", f"{errors['Erro Altimétrico (m)']:.3f} m")

        with tab6:
            st.write("**Coordenadas finais ajustadas pelo método de Bowditch.**")
            st.dataframe(adj_coords, use_container_width=True)

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
            st.dataframe(comp_df, use_container_width=True)

            st.header("📊 Análise de Erros")
            closure_error = user_elevs[-1] - true_elevs[-1]
            st.metric("Erro de Cálculo (m)", f"{closure_error:.3f} m")

import streamlit as st
import folium
from streamlit_folium import st_folium
import simulator
import pandas as pd
import numpy as np
import utm

st.set_page_config(page_title="Simulador Topográfico Interativo", layout="wide")

# --- Session State Initialization ---
if 'survey_points' not in st.session_state:
    st.session_state.survey_points = []  # List of (lat, lon)
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 16
if 'map_center_coord' not in st.session_state:
    st.session_state.map_center_coord = [-25.4484, -49.2310]

def reset_survey():
    st.session_state.survey_points = []
    st.session_state.survey_data = None

st.title("🏗️ Simulador de Levantamentos Topográficos")

# --- Sidebar ---
st.sidebar.header("Configurações do Levantamento")

survey_category = st.sidebar.selectbox(
    "1. Tipo de Levantamento",
    ["Poligonação", "Nivelamento"],
    on_change=reset_survey
)

challenge_mode = st.sidebar.toggle("🎯 Modo Desafio", help="Esconde os resultados finais para que o aluno insira seus próprios cálculos.")

if survey_category == "Poligonação":
    survey_type = st.sidebar.radio("1.1 Tipo de Poligonal", ["Fechada", "Enquadrada"], on_change=reset_survey)
    min_pts = 4 if survey_type == "Enquadrada" else 3
    n_points = st.sidebar.number_input("1.1.1 Número de vértices", min_value=min_pts, max_value=50, value=max(5, min_pts))

    st.sidebar.subheader("1.1.2 Coordenadas Conhecidas (UTM)")
    # Campus Politécnico UFPR
    default_lat, default_lon = -25.4484, -49.2310
    u_e, u_n, u_zone, u_letter = 677878.52, 7184223.31, 22, 'J'

    # Ensure sidebar keys exist in session state if we have points
    if len(st.session_state.survey_points) >= 1:
        e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[0])
        st.session_state.e1_input = round(e, 2)
        st.session_state.n1_input = round(n, 2)
    if len(st.session_state.survey_points) >= 2:
        e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[1])
        st.session_state.e2_input = round(e, 2)
        st.session_state.n2_input = round(n, 2)

    e1 = st.sidebar.number_input("HV1 Este (m)", value=u_e, format="%.2f", key="e1_input")
    n1 = st.sidebar.number_input("HV1 Norte (m)", value=u_n, format="%.2f", key="n1_input")

    # User requested HV2 as known point for azimuth
    e_hv2 = st.sidebar.number_input("HV2 Este (m)", value=u_e + 50.0, format="%.2f", key="e2_input")
    n_hv2 = st.sidebar.number_input("HV2 Norte (m)", value=u_n + 50.0, format="%.2f", key="n2_input")

    e_hv_end1, n_hv_end1, e_hv_end2, n_hv_end2 = None, None, None, None
    if survey_type == "Enquadrada":
        st.sidebar.write("Vértices de Chegada Conhecidos:")
        e_hv_end1 = st.sidebar.number_input(f"HV{n_points-1} Este (m)", value=u_e + 200.0, format="%.2f")
        n_hv_end1 = st.sidebar.number_input(f"HV{n_points-1} Norte (m)", value=u_n + 200.0, format="%.2f")
        e_hv_end2 = st.sidebar.number_input(f"HV{n_points} Este (m)", value=u_e + 250.0, format="%.2f")
        n_hv_end2 = st.sidebar.number_input(f"HV{n_points} Norte (m)", value=u_n + 250.0, format="%.2f")

    utm_zone = st.sidebar.number_input("Zona UTM", value=u_zone, min_value=1, max_value=60)
    utm_letter = st.sidebar.text_input("Letra UTM", value=u_letter).upper()

    if st.sidebar.button("Plotar Pontos Base"):
        # Convert UTM to Lat/Lon and update session state
        l1 = utm.to_latlon(e1, n1, utm_zone, utm_letter)
        l2 = utm.to_latlon(e_hv2, n_hv2, utm_zone, utm_letter)
        if len(st.session_state.survey_points) >= 2:
            st.session_state.survey_points[0] = l1
            st.session_state.survey_points[1] = l2
        else:
            st.session_state.survey_points = [l1, l2]
        st.rerun()

    if st.sidebar.button("Gerar Coordenadas Aleatórias"):
        # Use current map center if available
        start_lat, start_lon = st.session_state.map_center_coord

        gen_end_coords = None
        if survey_type == "Enquadrada" and e_hv_end1 is not None and n_hv_end1 is not None:
            # Convert UTM back to Lat/Lon for the generator
            gen_end_coords = utm.to_latlon(e_hv_end1, n_hv_end1, utm_zone, utm_letter)

        lats, lons = simulator.generate_traverse_coordinates(
            n_points,
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            start_lat=start_lat,
            start_lon=start_lon,
            end_coords=gen_end_coords
        )
        st.session_state.survey_points = list(zip(lats, lons))

else: # Nivelamento
    survey_type = st.sidebar.radio("1.2 Tipo de Nivelamento", ["Geométrico", "Trigonométrico"], on_change=reset_survey)
    method = st.sidebar.selectbox("1.2.1 Técnica", ["visadas iguais", "visadas equivalentes", "visadas recíprocas", "visadas extremas"]) if survey_type == "Geométrico" else "trigonométrico"
    n_points = st.sidebar.number_input("Número de Pontos", min_value=2, max_value=50, value=5)

    # For leveling, we still need zone/letter for coordinate display if user clicks map
    utm_zone = 22
    utm_letter = 'J'

    if st.sidebar.button("Gerar Trajeto de Nivelamento"):
        lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=-25.4484, start_lon=-49.2310)
        st.session_state.survey_points = list(zip(lats, lons))

# --- Main Layout ---
col_map, col_data = st.columns([1.2, 0.8])

with col_map:
    st.subheader("Mapa Interativo")

    # Define labels and colors based on user rules
    labels = []
    colors = []
    max_pts = 999

    if survey_category == "Poligonação":
        max_pts = n_points
        if survey_type == "Fechada":
            for i in range(max_pts):
                if i == 0: labels.append("HV1"); colors.append("red")
                elif i == 1: labels.append("HV2"); colors.append("red")
                else: labels.append(f"P{i-1}"); colors.append("blue")
        else: # Enquadrada
            for i in range(max_pts):
                if i == 0: labels.append("HV1"); colors.append("red")
                elif i == 1: labels.append("HV2"); colors.append("red")
                elif i == max_pts - 2: labels.append(f"HV{n_points-1}"); colors.append("red")
                elif i == max_pts - 1: labels.append(f"HV{n_points}"); colors.append("red")
                else: labels.append(f"P{i-1}"); colors.append("blue")
    else: # Nivelamento
        max_pts = n_points
        for i in range(max_pts):
            labels.append(f"P{i+1}")
            colors.append("red" if i == 0 else "blue")

    m = folium.Map(
        location=st.session_state.map_center_coord,
        zoom_start=st.session_state.map_zoom
    )

    if st.session_state.survey_points:
        points = st.session_state.survey_points
        # Draw polyline
        line_points = list(points)
        if survey_category == "Poligonação" and survey_type == "Fechada" and len(points) >= max_pts:
            # Explicitly close the traverse on map if limit reached
            line_points.append(points[1]) # Connect last Pi back to HV2

        folium.PolyLine(line_points, color="blue", weight=2.5, dash_array='5, 5' if survey_category=="Poligonação" else None).add_to(m)
        for i, (lat, lon) in enumerate(points):
            if i < len(labels):
                folium.CircleMarker([lat, lon], radius=6, color=colors[i], fill=True, popup=labels[i]).add_to(m)

    # Optimized st_folium call for Stlite (Pyodide)
    map_data = st_folium(
        m,
        width=None,
        height=500,
        returned_objects=["last_clicked", "center", "zoom"],
        use_container_width=True,
        key="survey_map"
    )

    if map_data:
        if map_data.get("center"):
            st.session_state.map_center_coord = [map_data["center"]["lat"], map_data["center"]["lng"]]
        if map_data.get("zoom"):
            st.session_state.map_zoom = map_data["zoom"]

        if map_data.get("last_clicked"):
            clicked_coords = (float(map_data["last_clicked"]["lat"]), float(map_data["last_clicked"]["lng"]))
            if clicked_coords not in st.session_state.survey_points:
                if len(st.session_state.survey_points) < max_pts:
                    st.session_state.survey_points.append(clicked_coords)
                    st.rerun()

    if st.button("Limpar Pontos"):
        reset_survey()
        st.rerun()

with col_data:
    st.subheader("Dados dos Vértices")
    if st.session_state.survey_points:
        # Convert Lat/Lon to UTM for display
        utm_data = []
        for i, (lat, lon) in enumerate(st.session_state.survey_points):
            e, n, zone, letter = utm.from_latlon(lat, lon)
            pt_label = labels[i] if i < len(labels) else f"P{i+1}"
            utm_data.append({"Ponto": pt_label, "Este (m)": round(e, 2), "Norte (m)": round(n, 2), "Lat": round(lat, 6), "Lon": round(lon, 6)})

        df_points = pd.DataFrame(utm_data)
        edited_df = st.data_editor(
            df_points[["Ponto", "Este (m)", "Norte (m)"]],
            use_container_width=True,
            num_rows="fixed",
            disabled=["Ponto"],
            key="vertex_editor"
        )

        # Bi-directional sync: if editor changed, update session_state.survey_points
        if not edited_df.equals(df_points[["Ponto", "Este (m)", "Norte (m)"]]):
            new_points = []
            for idx, row in edited_df.iterrows():
                try:
                    new_lat, new_lon = utm.to_latlon(row["Este (m)"], row["Norte (m)"], utm_zone, utm_letter)
                    new_points.append((new_lat, new_lon))
                except Exception as e:
                    st.error(f"Coordenada inválida na linha {idx}: {e}")
                    new_points.append(st.session_state.survey_points[idx])

            st.session_state.survey_points = new_points
            st.rerun()

        if st.button("Simular Observações de Campo"):
            e_coords = df_points["Este (m)"].values
            n_coords = df_points["Norte (m)"].values
            if survey_category == "Poligonação":
                # Ensure all points are present before simulating
                if len(st.session_state.survey_points) < max_pts:
                    st.error(f"Selecione todos os {max_pts} pontos no mapa primeiro!")
                else:
                    st.session_state.survey_data = simulator.simulate_traverse_observations(
                        e_coords, n_coords,
                        survey_type="Closed" if survey_type == "Fechada" else "Linked"
                    )
                    st.rerun()
            else:
                obs, elevs = simulator.simulate_leveling(len(e_coords), type=survey_type, method=method)
                st.session_state.survey_data = obs
                st.session_state.true_elevations = elevs
            st.rerun()

# --- Modules Output ---
if st.session_state.survey_data is not None:
    st.write("---")
    if survey_category == "Poligonação":
        st.subheader("🌐 Resultados da Poligonação (UTM)")

        end_coords_start = (e_hv_end1, n_hv_end1, 100.0) if (e_hv_end1 is not None) else None
        end_coords_end = (e_hv_end2, n_hv_end2, 100.0) if (e_hv_end2 is not None) else None

        pre, raw_coords, errors, adj_coords = simulator.process_traverse_data(
            st.session_state.survey_data,
            (e1, n1, 100.0), # HV1
            (e_hv2, n_hv2, 100.0), # HV2
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            end_coords_start=end_coords_start,
            end_coords_end=end_coords_end
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Dados de Campo", "⚙️ Dados Pré-calculados", "📍 Coordenadas Iniciais", "📊 Análise de Erros", "✅ Coordenadas Finais (Bowditch)"
        ])

        with tab1: st.dataframe(st.session_state.survey_data, use_container_width=True)

        with tab2:
            if challenge_mode: st.info("Habilitado apenas no modo normal.")
            else: st.dataframe(pre, use_container_width=True)

        with tab3:
            if challenge_mode: st.info("Habilitado apenas no modo normal.")
            else: st.dataframe(raw_coords, use_container_width=True)

        with tab4:
            if challenge_mode:
                st.write("### Insira os erros calculados:")
                u_err_ang = st.number_input("Erro Angular Calculado (°)", format="%.5f")
                u_err_plan = st.number_input("Erro Planimétrico Calculado (m)", format="%.3f")

                if st.button("Verificar Erros"):
                    diff_ang = abs(u_err_ang - errors['Erro Angular (°)'])
                    diff_plan = abs(u_err_plan - errors['Erro Planimétrico (m)'])

                    if diff_ang < 0.0001 and diff_plan < 0.01:
                        st.success("Cálculo de erros correto!")
                    else:
                        st.error(f"Erro na análise: Dif. Angular: {diff_ang:.5f}°, Dif. Planimétrica: {diff_plan:.3f}m")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Erro Angular", f"{errors['Erro Angular (°)']:.5f}°")
                c2.metric("Erro Planimétrico", f"{errors['Erro Planimétrico (m)']:.3f} m")
                c3.metric("Precisão Relativa", errors['Precisão Relativa'])
                st.metric("Erro Altimétrico", f"{errors['Erro Altimétrico (m)']:.3f} m")

        with tab5:
            if challenge_mode:
                st.write("### Validação de Coordenadas Finais")
                st.info("Insira as coordenadas compensadas (Bowditch) do último ponto levantado.")
                last_pt_label = adj_coords.iloc[-1]['Ponto']
                u_e_final = st.number_input(f"Este Final ({last_pt_label})", format="%.3f")
                u_n_final = st.number_input(f"Norte Final ({last_pt_label})", format="%.3f")

                if st.button("Verificar Coordenadas"):
                    correct_e = adj_coords.iloc[-1]['E']
                    correct_n = adj_coords.iloc[-1]['N']
                    diff_e = abs(u_e_final - correct_e)
                    diff_n = abs(u_n_final - correct_n)

                    if diff_e < 0.01 and diff_n < 0.01:
                        st.success("Coordenadas finais corretas! Compensação realizada com sucesso.")
                    else:
                        st.error(f"Divergência: Dif E: {diff_e:.3f}m, Dif N: {diff_n:.3f}m")
            else:
                # Reorder columns to have corrections in the middle as requested
                cols = adj_coords.columns.tolist()
                # If corrections exist, move them
                if "Correção E" in cols:
                    # Target order: Ponto, Correção E, Correção N, Correção Z, E, N, Z
                    new_order = ["Ponto", "Correção E", "Correção N", "Correção Z", "E", "N", "Z"]
                    # Keep other columns if any
                    other_cols = [c for c in cols if c not in new_order]
                    adj_coords = adj_coords[new_order + other_cols]
                st.dataframe(adj_coords, use_container_width=True)

    else: # Nivelamento
        st.subheader("📐 Resultados do Nivelamento")

        if not challenge_mode:
            st.dataframe(st.session_state.survey_data, use_container_width=True)

        if survey_type == "Geométrico":
            st.header("🔍 Módulo de Leitura de Réguas")
            selected_row = st.selectbox("Selecione a Estação para leitura", range(len(st.session_state.survey_data)))
            row = st.session_state.survey_data.iloc[selected_row]
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Ré**")
                st.code(simulator.get_rod_reading_visual(row['V. Ré (m)']))
                if not challenge_mode:
                    st.caption(f"Leitura: {row['V. Ré (m)']:.3f}m")
            with c2:
                st.write("**Vante**")
                st.code(simulator.get_rod_reading_visual(row['V. Vante (m)']))
                if not challenge_mode:
                    st.caption(f"Leitura: {row['V. Vante (m)']:.3f}m")

        st.header("🧮 Módulo de Validação de Cálculos")
        st.info("Calcule as cotas de todos os pontos com base nas leituras acima.")

        user_elevs = []
        cols = st.columns(3)
        for i in range(len(st.session_state.survey_points)):
            with cols[i % 3]:
                val = st.number_input(f"Cota P{i+1}", value=0.0, format="%.3f", key=f"user_elev_{i}")
                user_elevs.append(val)

        if st.button("Verificar Resultados", use_container_width=True):
            # Comparison logic
            correct_elevs = st.session_state.true_elevations
            diffs = [abs(u - c) for u, c in zip(user_elevs, correct_elevs)]
            avg_err = np.mean(diffs)

            if avg_err < 0.005:
                st.success(f"Excelente! Seus cálculos estão corretos. Erro médio: {avg_err:.4f} m")
            else:
                st.error(f"Há divergências nos cálculos. Erro médio: {avg_err:.4f} m. Verifique as cotas intermediárias.")

            if not challenge_mode:
                st.write("Cotas Corretas:")
                st.write(correct_elevs)

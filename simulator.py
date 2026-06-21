import numpy as np
import pandas as pd

def calculate_azimuth_flat(e1, n1, e2, n2):
    """Calculates azimuth between two points in a flat coordinate system (UTM)."""
    de = e2 - e1
    dn = n2 - n1
    azimuth = np.degrees(np.arctan2(de, dn))
    return (azimuth + 360) % 360

def generate_traverse_coordinates(n_intermediate, survey_type="Closed", start_lat=-23.5505, start_lon=-46.6333, scale=0.001):
    """
    Generates coordinates for traverse.
    - Closed: HV1, HV2, P1...Pn-2 (Total points = n_intermediate + 2)
    - Linked: HV1, HV2, P1...Pn, HV4, HV5 (Total points = n_intermediate + 4)
    """
    if survey_type == "Closed":
        n_total = n_intermediate + 2
        angles = np.linspace(0, 2 * np.pi, n_total, endpoint=False)
        radius = scale * (n_total / (2 * np.pi))
        lats = []
        lons = []
        for angle in angles:
            r = radius * np.random.uniform(0.8, 1.2)
            lats.append(start_lat + np.cos(angle) * r)
            lons.append(start_lon + np.sin(angle) * r)

        # Align HV2 to start_lat/lon
        offset_lat = start_lat - lats[1]
        offset_lon = start_lon - lons[1]
        lats = [lat + offset_lat for lat in lats]
        lons = [lon + offset_lon for lon in lons]
        return np.array(lats), np.array(lons)

    else: # Linked
        n_total = n_intermediate + 4
        # HV1, HV2
        lats = [start_lat - scale, start_lat]
        lons = [start_lon, start_lon]

        current_lat, current_lon = start_lat, start_lon
        base_angle = 0

        # P1...Pn
        for i in range(n_intermediate):
            angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
            current_lat += np.cos(angle) * scale
            current_lon += np.sin(angle) * scale
            lats.append(current_lat)
            lons.append(current_lon)

        # HV4, HV5
        # HV4 continues the path
        angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
        current_lat += np.cos(angle) * scale
        current_lon += np.sin(angle) * scale
        lats.append(current_lat)
        lons.append(current_lon)
        # HV5 adds one more for orientation
        angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
        current_lat += np.cos(angle) * scale
        current_lon += np.sin(angle) * scale
        lats.append(current_lat)
        lons.append(current_lon)

        return np.array(lats), np.array(lons)

def simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.005, dist_sigma=0.005):
    """
    Simulates raw field observations.
    """
    n = len(e_coords)
    observations = []

    # Elevations (Z)
    elevations = np.zeros(n)
    elevations[0] = 100.0 # HV1
    for i in range(1, n):
        elevations[i] = elevations[i-1] + np.random.normal(0, 0.5)

    def get_label(idx):
        if survey_type == "Closed":
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            return f"P{idx-1}"
        else: # Linked
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            if idx == n-2: return "HV4"
            if idx == n-1: return "HV5"
            return f"P{idx-1}"

    stations = []
    if survey_type == "Closed":
        # Stations: HV2, P1...Pn-2, then back to HV2
        # Sequence indices: 0(HV1), 1(HV2), 2(P1), ..., n-1(P_n-2)
        # 1: R=0, V=2
        stations.append((1, 0, 2))
        # i: R=i-1, V=i+1
        for i in range(2, n - 1):
            stations.append((i, i-1, i+1))
        # Last station: n-1, R=n-2, V=1
        stations.append((n-1, n-2, 1))
        # Closure station at HV2: R=n-1, V=2
        stations.append((1, n-1, 2))

    else: # Linked
        # Sequence indices: 0(HV1), 1(HV2), 2(P1), ..., n-3(Pn), n-2(HV4), n-1(HV5)
        # Stations: 1(HV2), 2(P1)...n-2(HV4)
        for i in range(1, n - 1):
            stations.append((i, i-1, i+1))

    for s_idx, re_idx, v_idx in stations:
        d_horiz_true = np.sqrt((e_coords[v_idx]-e_coords[s_idx])**2 + (n_coords[v_idx]-n_coords[s_idx])**2)
        d_inc_true = np.sqrt(d_horiz_true**2 + (elevations[v_idx]-elevations[s_idx])**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        dir_re = np.random.uniform(0, 360)
        az_fs = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[v_idx], n_coords[v_idx])
        az_re = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[re_idx], n_coords[re_idx])

        true_angle = (az_fs - az_re + 360) % 360
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        slope_angle = np.degrees(np.arctan2(elevations[v_idx] - elevations[s_idx], d_horiz_true))
        zenith_measured = 90 - slope_angle + np.random.normal(0, angle_sigma)

        observations.append({
            "Estação": get_label(s_idx),
            "Ré": get_label(re_idx),
            "Vante": get_label(v_idx),
            "Dir. Ré (°)": round(dir_re, 4),
            "Dir. Vante (°)": round(dir_vante, 4),
            "Ângulo Zenital (°)": round(zenith_measured, 4),
            "Dist. Inclinada (m)": round(d_inc_measured, 3)
        })

    return pd.DataFrame(observations)

def process_traverse_data(df, start_coords, hv2_coords, survey_type="Closed", end_coords_start=None, end_coords_end=None):
    """
    Strict calculation workflow for Linked and Closed traverses.
    """
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    # 1. Initial Azimuth (HV1 -> HV2)
    az_hv1_hv2 = calculate_azimuth_flat(start_coords[0], start_coords[1], hv2_coords[0], hv2_coords[1])

    # 2. Azimuth Propagation and Angular Closure
    n_setups = len(pre)
    az_back = (az_hv1_hv2 + 180) % 360

    propagated_azimuths = []
    curr_az = (az_back + pre.iloc[0]["Ângulo Horiz. (°)"]) % 360
    propagated_azimuths.append(curr_az)

    for i in range(1, n_setups):
        # Az(i -> i-1) = Az(i-1 -> i) + 180
        curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"]) % 360
        propagated_azimuths.append(curr_az)

    if survey_type == "Closed":
        # Expected last azimuth: Az(HV2 -> P1)
        az_target = propagated_azimuths[0]
        err_ang = (propagated_azimuths[-1] - az_target)
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360
        # Correction per station (applied to each measured angle except first? No, distribute among all setups)
        corr_ang_per_station = -err_ang / (n_setups - 1)

    else: # Linked
        # Expected last azimuth: Az(HV4 -> HV5)
        az_target = calculate_azimuth_flat(end_coords_start[0], end_coords_start[1], end_coords_end[0], end_coords_end[1])
        err_ang = (propagated_azimuths[-1] - az_target)
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360
        corr_ang_per_station = -err_ang / n_setups

    # 3. Corrected Azimuths
    adj_azimuths = []
    # Re-propagate with corrections
    curr_az = (az_back + pre.iloc[0]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
    adj_azimuths.append(curr_az)
    for i in range(1, n_setups):
        curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
        adj_azimuths.append(curr_az)

    # 4. Provisional Coordinates
    # Sequence starts at HV2
    raw_coords = [
        {"Ponto": "HV1", "E": start_coords[0], "N": start_coords[1], "Z": start_coords[2]},
        {"Ponto": "HV2", "E": hv2_coords[0], "N": hv2_coords[1], "Z": hv2_coords[2]}
    ]

    # We calculate points up to HV4 (the last station setup's "Vante" is HV5)
    # Actually, the last station HV4 has Vante HV5.
    # We need linear closure at HV4.
    # setups: HV2 -> P1, P1 -> P2, ..., Pn -> HV4, HV4 -> HV5
    # indices: 0, 1, ..., n_setups-2, n_setups-1

    # Coordinates calculation loop
    for i in range(n_setups - 1): # Exclude last setup (HV4-HV5) for coordinate propagation to HV4
        dist = pre.iloc[i]["Dist. Horizontal (m)"]
        az = adj_azimuths[i]
        de = dist * np.sin(np.radians(az))
        dn = dist * np.cos(np.radians(az))
        dz = pre.iloc[i]["ΔH (m)"]

        last = raw_coords[-1]
        raw_coords.append({
            "Ponto": pre.iloc[i]["Vante"],
            "E": last["E"] + de,
            "N": last["N"] + dn,
            "Z": last["Z"] + dz
        })

    # Final point in raw_coords is HV4. Add HV5 just for labeling purposes in final table?
    # No, linear closure is at HV4.

    # 5. Linear Closure (Bowditch)
    total_dist = pre.iloc[:n_setups-1]["Dist. Horizontal (m)"].sum()
    if survey_type == "Closed":
        err_e = raw_coords[-1]["E"] - hv2_coords[0]
        err_n = raw_coords[-1]["N"] - hv2_coords[1]
        err_z = raw_coords[-1]["Z"] - hv2_coords[2]
    else:
        err_e = raw_coords[-1]["E"] - end_coords_start[0]
        err_n = raw_coords[-1]["N"] - end_coords_start[1]
        err_z = raw_coords[-1]["Z"] - end_coords_start[2]

    err_plan = np.sqrt(err_e**2 + err_n**2)

    errors = {
        "Erro Angular (°)": round(float(err_ang), 5),
        "Erro Planimétrico (m)": round(float(err_plan), 3),
        "Erro Altimétrico (m)": round(float(err_z), 3),
        "Precisão Relativa": f"1/{int(total_dist/err_plan) if err_plan > 0.001 else 'inf'}"
    }

    # 6. Final Adjusted Coordinates
    adj_coords = [raw_coords[0].copy(), raw_coords[1].copy()] # HV1, HV2
    # Apply Bowditch to P1...HV4
    cum_dist = 0
    for i in range(n_setups - 1):
        cum_dist += pre.iloc[i]["Dist. Horizontal (m)"]
        corr_e = -err_e * (cum_dist / total_dist)
        corr_n = -err_n * (cum_dist / total_dist)
        corr_z = -err_z * (cum_dist / total_dist)

        pt = raw_coords[i+2].copy()
        pt["Correção E"] = round(corr_e, 3)
        pt["Correção N"] = round(corr_n, 3)
        pt["Correção Z"] = round(corr_z, 3)
        pt["E"] = round(pt["E"] + corr_e, 3)
        pt["N"] = round(pt["N"] + corr_n, 3)
        pt["Z"] = round(pt["Z"] + corr_z, 3)
        adj_coords.append(pt)

    # For linked, add HV5 at the end
    if survey_type == "Linked":
        # HV5 position can be calculated from adjusted HV4 + corrected Az(HV4-HV5)
        last_adj = adj_coords[-1] # HV4
        dist_final = pre.iloc[-1]["Dist. Horizontal (m)"]
        az_final = adj_azimuths[-1]
        hv5_e = last_adj["E"] + dist_final * np.sin(np.radians(az_final))
        hv5_n = last_adj["N"] + dist_final * np.cos(np.radians(az_final))
        hv5_z = last_adj["Z"] + pre.iloc[-1]["ΔH (m)"]

        adj_coords.append({
            "Ponto": "HV5", "E": round(hv5_e, 3), "N": round(hv5_n, 3), "Z": round(hv5_z, 3),
            "Correção E": 0.0, "Correção N": 0.0, "Correção Z": 0.0
        })
        raw_coords.append({"Ponto": "HV5", "E": round(hv5_e, 3), "N": round(hv5_n, 3), "Z": round(hv5_z, 3)})

    raw_df = pd.DataFrame(raw_coords)
    for col in ["E", "N", "Z"]: raw_df[col] = raw_df[col].round(3)

    return pre, raw_df, errors, pd.DataFrame(adj_coords)

def simulate_leveling(n_points, type="Geometric", method="visadas iguais", start_elev=100.0, error_per_km=0.005):
    """
    Simulates leveling observations.
    """
    elevations = [start_elev]
    current_elev = start_elev
    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80)
        delta_h = np.random.uniform(-0.5, 0.5)
        measured_delta_h = delta_h + np.random.normal(0, error_per_km * np.sqrt(dist/1000))

        prev_elev = current_elev
        current_elev += delta_h
        elevations.append(current_elev)

        if type in ["Geometric", "Geométrico"]:
            bs = np.random.uniform(1.0, 2.5)
            ai = prev_elev + bs
            fs = ai - (prev_elev + measured_delta_h)

            obs = {
                "Estação": f"E{i}",
                "Ponto": f"P{i+1}",
                "V. Ré (m)": round(bs, 3),
                "AI (m)": round(ai, 3),
                "V. Vante (m)": round(fs, 3),
                "Dist (m)": round(dist, 1),
                "Método": method
            }
            observations.append(obs)
        else: # Trigonométrico
            slope_dist = np.sqrt(dist**2 + measured_delta_h**2)
            vert_angle = np.degrees(np.arctan2(measured_delta_h, dist))
            observations.append({
                "De": f"P{i}",
                "Para": f"P{i+1}",
                "Dist. Inclinada (m)": round(slope_dist, 3),
                "Ângulo Vertical (deg)": round(vert_angle, 4),
                "Alt. Instrumento (m)": 1.500,
                "Alt. Sinal (m)": 1.500
            })

    return pd.DataFrame(observations), elevations

def get_rod_reading_visual(value):
    """
    Returns an ASCII representation of a topographical rod.
    """
    v = round(value, 3)
    v_cm = int(v * 100)
    mm_part = int(round((v * 100 - v_cm) * 10))

    lines = []
    lines.append(f"   MIRA (Leitura: {v:.3f}m)")
    lines.append("   +----------+")
    for cm in range(v_cm + 5, v_cm - 6, -1):
        m_val = cm / 100.0
        pattern = "#####     " if cm % 2 == 0 else "     #####"
        pointer = ">" if cm == v_cm else " "
        mm_label = f" [+{mm_part}mm]" if cm == v_cm else ""
        lines.append(f"{m_val:5.2f} |{pattern}| {pointer}{mm_label}")
    lines.append("   +----------+")
    lines.append("   (Intervalos de 1cm)")
    return "\n".join(lines)

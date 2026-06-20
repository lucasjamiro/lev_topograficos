import numpy as np
import pandas as pd

def calculate_azimuth_flat(e1, n1, e2, n2):
    """Calculates azimuth between two points in a flat coordinate system (UTM)."""
    de = e2 - e1
    dn = n2 - n1
    azimuth = np.degrees(np.arctan2(de, dn))
    return (azimuth + 360) % 360

def calculate_azimuth(lat1, lon1, lat2, lon2):
    dlon = lon2 - lon1
    y = np.sin(np.radians(dlon)) * np.cos(np.radians(lat2))
    x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
        np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(np.radians(dlon))
    azimuth = np.degrees(np.arctan2(y, x))
    return (azimuth + 360) % 360

def generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=-23.5505, start_lon=-46.6333, scale=0.001, end_coords=None):
    """
    Generates exactly n_points for a traverse survey.
    """
    if survey_type == "Closed":
        # Sequence: HV1, HV2, P1, ..., P(n-2)
        # We'll make HV1 and HV2 have a specific orientation
        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        radius = scale * (n_points / (2 * np.pi))

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

    else: # Linked
        # Sequence: HV1, HV2, P1... P(n-4), HV(n-1), HV(n)
        lats = [start_lat - scale, start_lat] # HV1, HV2
        lons = [start_lon, start_lon]

        current_lat, current_lon = start_lat, start_lon
        base_angle = 0

        # Generate intermediate points and endpoint knowns
        # Number of intermediate points: n - 4
        # If n=5, 1 intermediate point.
        for i in range(n_points - 2):
            angle = base_angle + np.random.uniform(-np.pi/6, np.pi/6)
            current_lat += np.cos(angle) * scale
            current_lon += np.sin(angle) * scale
            lats.append(current_lat)
            lons.append(current_lon)

        # Truncate if we exceeded n_points due to logic
        lats = lats[:n_points]
        lons = lons[:n_points]

    return np.array(lats), np.array(lons)

def simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.005, dist_sigma=0.005, elev_sigma=0.02):
    """
    Simulates raw field observations for a traverse using UTM-like coordinates (meters).
    """
    n = len(e_coords)
    observations = []

    # Elevations for points
    elevations = np.zeros(n)
    elevations[0] = 100.0 # HV1
    elevations[1] = 100.0 # HV2
    for i in range(2, n):
        elevations[i] = elevations[i-1] + np.random.normal(0, 0.5)

    def get_label(idx):
        if survey_type == "Closed":
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            return f"P{idx-1}"
        else: # Linked
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            if idx == n-2: return f"HV{n-1}"
            if idx == n-1: return f"HV{n}"
            return f"P{idx-1}"

    stations = []
    if survey_type == "Closed":
        # Sequence of points: 0(HV1), 1(HV2), 2(P1), ..., n-1(P_n-2)
        # Stations: 1, 2, ..., n-1, then back to 1 for closing
        # 1: R=0, V=2
        stations.append((1, 0, 2))
        # i: R=i-1, V=i+1
        for i in range(2, n - 1):
            stations.append((i, i-1, i+1))
        # n-1: R=n-2, V=1
        stations.append((n-1, n-2, 1))
        # 1 (closing): R=n-1, V=2
        stations.append((1, n-1, 2))

    else: # Linked (Enquadrada)
        # Sequence: 0(HV1), 1(HV2), 2(P1), ..., n-2(HV_n-1), n-1(HV_n)
        # Stations where we actually measure: 1, 2, ..., n-2
        # 1: R=0, V=2
        # i: R=i-1, V=i+1
        # n-2: R=n-3, V=n-1
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
    Full processing with correct order:
    1. Angular Closure
    2. Correct Azimuths
    3. Provisional Coordinates
    4. Linear Closure (Bowditch)
    """
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    az_hv1_hv2 = calculate_azimuth_flat(start_coords[0], start_coords[1], hv2_coords[0], hv2_coords[1])

    # --- 1. Angular Closure ---
    n_stations = len(pre)
    if survey_type == "Closed":
        # Sum of angles in a closed traverse with n vertices.
        # Here we have n-1 vertices + 1 closure station.
        # Actually it's simpler to track azimuths and check closure.

        azimuths = []
        # First azimuth: HV2 -> P1
        az_hv2_hv1 = (az_hv1_hv2 + 180) % 360
        curr_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"]) % 360
        azimuths.append(curr_az)

        for i in range(1, n_stations):
            # curr_az is Az(Station_i-1 -> Station_i)
            # Az(Station_i -> Station_i-1) = curr_az + 180
            # Az(Station_i -> Station_i+1) = (Az(Station_i -> Station_i-1) + Angle) % 360
            curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"]) % 360
            azimuths.append(curr_az)

        # Last azimuth should be Az(HV2 -> P1) again!
        err_ang = (azimuths[-1] - azimuths[0])
        # Normalize error
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360

        corr_ang_per_station = -err_ang / (n_stations - 1)

    else: # Linked
        azimuths = []
        az_hv2_hv1 = (az_hv1_hv2 + 180) % 360
        curr_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"]) % 360
        azimuths.append(curr_az)

        for i in range(1, n_stations):
            curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"]) % 360
            azimuths.append(curr_az)

        # Expected last azimuth: Az(HV(n+1) -> HV(n+2))
        az_end_target = calculate_azimuth_flat(end_coords_start[0], end_coords_start[1], end_coords_end[0], end_coords_end[1])
        err_ang = (azimuths[-1] - az_end_target)
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360

        corr_ang_per_station = -err_ang / n_stations

    # --- 2. Correct Azimuths ---
    adj_azimuths = []
    if survey_type == "Closed":
        curr_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"] + corr_ang_per_station*0) % 360 # Usually first angle doesn't get correction or gets it?
        # Standard: distribute across all measured angles.
        # Let's apply correction to each measured angle.
        curr_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
        adj_azimuths.append(curr_az)
        for i in range(1, n_stations):
            curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
            adj_azimuths.append(curr_az)
    else:
        curr_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
        adj_azimuths.append(curr_az)
        for i in range(1, n_stations):
            curr_az = (curr_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
            adj_azimuths.append(curr_az)

    # --- 3. Provisional Coordinates ---
    raw_coords = [
        {"Ponto": "HV1", "E": start_coords[0], "N": start_coords[1], "Z": start_coords[2]},
        {"Ponto": "HV2", "E": hv2_coords[0], "N": hv2_coords[1], "Z": hv2_coords[2]}
    ]

    # In both cases, the last station is used for angular closure check only.
    # Closed: Last station is HV2 again (checking Az(HV2-P1))
    # Linked: Last station is HV(n-1) (checking Az(HV(n-1)-HV(n)))
    calc_limit = n_stations - 1

    for i in range(calc_limit):
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

    # --- 4. Linear Closure (Bowditch) ---
    total_dist = pre.iloc[:calc_limit]["Dist. Horizontal (m)"].sum()
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

    adj_coords = [raw_coords[0].copy(), raw_coords[1].copy()]
    cum_dist = 0
    for i in range(calc_limit):
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

    # Round raw_coords for display
    raw_df = pd.DataFrame(raw_coords)
    for col in ["E", "N", "Z"]: raw_df[col] = raw_df[col].round(3)

    return pre, raw_df, errors, pd.DataFrame(adj_coords)

def simulate_leveling(n_points, type="Geometric", method="visadas iguais", start_elev=100.0, error_per_km=0.005):
    """
    Simulates leveling observations including Instrument Height (AI).
    """
    elevations = [start_elev]
    current_elev = start_elev
    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80)
        delta_h = np.random.uniform(-0.5, 0.5)
        measured_delta_h = delta_h + np.random.normal(0, error_per_km * np.sqrt(dist/1000))

        # true elevation for validation
        prev_elev = current_elev
        current_elev += delta_h
        elevations.append(current_elev)

        if type in ["Geometric", "Geométrico"]:
            bs = np.random.uniform(1.0, 2.5)
            ai = prev_elev + bs
            fs = ai - (prev_elev + measured_delta_h) # Simulated reading

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
    Returns an ASCII representation of a topographical rod (mira falante).
    Highlights the reading with '>>'.
    """
    v = round(value, 3)
    v_cm = int(v * 100)
    mm_part = int(round((v * 100 - v_cm) * 10))

    lines = []
    lines.append(f"   MIRA (Leitura: {v:.3f}m)")
    lines.append("   +----------+")

    # Display 10cm range around the reading
    for cm in range(v_cm + 5, v_cm - 6, -1):
        m_val = cm / 100.0
        # Alternating 'E' pattern typical of topographical rods
        # Even cm: block on left, Odd cm: block on right
        pattern = "#####     " if cm % 2 == 0 else "     #####"

        pointer = " "
        mm_label = ""
        if cm == v_cm:
            pointer = ">"
            # Show mm level detail at the exact reading line
            # We insert the mm indicator inside the pattern area or next to it
            mm_label = f" [+{mm_part}mm]"

        lines.append(f"{m_val:5.2f} |{pattern}| {pointer}{mm_label}")

    lines.append("   +----------+")
    lines.append("   (Intervalos de 1cm)")
    return "\n".join(lines)

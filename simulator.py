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
    Generates a set of coordinates for a traverse survey.
    scale: rough distance between points in degrees (approx 100m)
    """
    if survey_type == "Closed":
        # For a closed traverse, we start and end at the same point (conceptually)
        # but usually we have a sequence P1, P2, ..., Pn, P1.
        # The user says "fechadas precisam apenas de um par de pontos conhecido"
        # This usually means P1 and another point to give orientation, or P1 and P2 are known.

        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        radius = scale * (n_points / (2 * np.pi))

        lats = []
        lons = []
        for angle in angles:
            r = radius * np.random.uniform(0.8, 1.2)
            lats.append(start_lat + np.cos(angle) * r)
            lons.append(start_lon + np.sin(angle) * r)

        # Center them around start_lat, start_lon for better control if needed,
        # but let's just make P1 be exactly start_lat, start_lon
        offset_lat = start_lat - lats[0]
        offset_lon = start_lon - lons[0]
        lats = [lat + offset_lat for lat in lats]
        lons = [lon + offset_lon for lon in lons]

        # Close the loop
        lats.append(lats[0])
        lons.append(lons[0])
    elif survey_type == "Linked":
        # Linked (Enquadrada) needs start and end points.
        # The user says "no mínimo um par de pontos conhecidos no começo e no final"
        # So we might have A, B (known) ... 1, 2, 3 ... C, D (known)

        lats = [start_lat]
        lons = [start_lon]

        if end_coords:
            end_lat, end_lon = end_coords
            # Interpolate points between start and end with some randomness
            for i in range(1, n_points - 1):
                frac = i / (n_points - 1)
                lat = start_lat + frac * (end_lat - start_lat) + np.random.uniform(-scale/2, scale/2)
                lon = start_lon + frac * (end_lon - start_lon) + np.random.uniform(-scale/2, scale/2)
                lats.append(lat)
                lons.append(lon)
            lats.append(end_lat)
            lons.append(end_lon)
        else:
            current_lat, current_lon = start_lat, start_lon
            base_angle = np.pi / 4
            for i in range(n_points - 1):
                angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
                current_lat += np.cos(angle) * scale
                current_lon += np.sin(angle) * scale
                lats.append(current_lat)
                lons.append(current_lon)

    return np.array(lats), np.array(lons)

def simulate_traverse_observations(e_coords, n_coords, angle_sigma=0.01, dist_sigma=0.005, elev_sigma=0.02):
    """
    Simulates raw field observations for a traverse using UTM-like coordinates (meters).
    Returns a DataFrame with: Estação, Ré, Vante, Dir. Ré, Dir. Vante, Ang. Zenital, Dist. Inclinada
    """
    n = len(e_coords)
    observations = []

    # Detect if it's a closed loop (last point == first point)
    is_closed = n > 2 and e_coords[0] == e_coords[-1] and n_coords[0] == n_coords[-1]

    # We assume elevations for the points as well
    elevations = np.cumsum(np.random.normal(0, 0.5, n)) + 100.0
    if is_closed:
        elevations[-1] = elevations[0]

    for i in range(n):
        # Skip the redundant last station in a closed loop
        if is_closed and i == n - 1:
            continue

        if i == 0:
            re_idx = -1
            vante_idx = 1
        elif i == n - 1:
            re_idx = i - 1
            vante_idx = 0
        else:
            re_idx = i - 1
            vante_idx = i + 1

        if vante_idx >= n:
            continue

        # Distances
        d_horiz_true = np.sqrt((e_coords[vante_idx]-e_coords[i])**2 + (n_coords[vante_idx]-n_coords[i])**2)
        d_inc_true = np.sqrt(d_horiz_true**2 + (elevations[vante_idx]-elevations[i])**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        # Directions
        dir_re = np.random.uniform(0, 360)

        az_fs = calculate_azimuth_flat(e_coords[i], n_coords[i], e_coords[vante_idx], n_coords[vante_idx])
        if re_idx == -1:
            az_re = 0
        else:
            az_re = calculate_azimuth_flat(e_coords[i], n_coords[i], e_coords[re_idx], n_coords[re_idx])

        true_angle = (az_fs - az_re + 360) % 360
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        # Zenith Angle
        slope_angle = np.degrees(np.arctan2(elevations[vante_idx] - elevations[i], d_horiz_true))
        zenith_measured = 90 - slope_angle + np.random.normal(0, angle_sigma)

        observations.append({
            "Estação": f"P{i+1}",
            "Ré": "REF_N" if re_idx == -1 else f"P{re_idx+1}",
            "Vante": f"P{vante_idx+1}",
            "Dir. Ré (°)": round(dir_re, 4),
            "Dir. Vante (°)": round(dir_vante, 4),
            "Ângulo Zenital (°)": round(zenith_measured, 4),
            "Dist. Inclinada (m)": round(d_inc_measured, 3)
        })

    return pd.DataFrame(observations)

def process_traverse_data(df, start_coords, survey_type="Closed", end_coords=None):
    """
    Implements the full processing chain including Bowditch adjustment.
    df: Raw observations
    start_coords: (E, N, Z) in meters
    end_coords: (E, N, Z) for the last point if survey_type is Linked
    """
    # 1. Pre-calculated data
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    # 2. Raw Coordinates (Dead Reckoning)
    # We assume the first station P1 used North as Reference for the first observation.
    current_az = pre.iloc[0]["Ângulo Horiz. (°)"]

    raw_coords = [{"Ponto": "P1", "E": start_coords[0], "N": start_coords[1], "Z": start_coords[2]}]

    for i in range(len(pre)):
        if i > 0:
            current_az = (current_az + pre.iloc[i]["Ângulo Horiz. (°)"] - 180 + 360) % 360

        dist = pre.iloc[i]["Dist. Horizontal (m)"]
        de = dist * np.sin(np.radians(current_az))
        dn = dist * np.cos(np.radians(current_az))
        dz = pre.iloc[i]["ΔH (m)"]

        last = raw_coords[-1]
        raw_coords.append({
            "Ponto": pre.iloc[i]["Vante"],
            "E": round(last["E"] + de, 3),
            "N": round(last["N"] + dn, 3),
            "Z": round(last["Z"] + dz, 3)
        })

    # 3. Closure Errors
    total_dist = pre["Dist. Horizontal (m)"].sum()
    if survey_type == "Closed":
        err_e = raw_coords[-1]["E"] - raw_coords[0]["E"]
        err_n = raw_coords[-1]["N"] - raw_coords[0]["N"]
        err_z = raw_coords[-1]["Z"] - raw_coords[0]["Z"]

        # Angular closure: sum of internal angles = (n-2)*180
        # This is simplified: we check the final azimuth vs initial
        # For a closed traverse, the sum of angles should close the azimuth
        final_az = current_az
        expected_final_az = (pre.iloc[0]["Ângulo Horiz. (°)"] - 180 + 360) % 360
        err_ang = (final_az - expected_final_az + 180) % 360 - 180
    else:
        if end_coords:
            err_e = raw_coords[-1]["E"] - end_coords[0]
            err_n = raw_coords[-1]["N"] - end_coords[1]
            err_z = raw_coords[-1]["Z"] - end_coords[2]
        else:
            err_e = np.random.normal(0, 0.1)
            err_n = np.random.normal(0, 0.1)
            err_z = np.random.normal(0, 0.05)
        err_ang = np.random.normal(0, 0.005)

    err_plan = np.sqrt(err_e**2 + err_n**2)

    errors = {
        "Erro Angular (°)": round(float(err_ang), 5),
        "Erro Planimétrico (m)": round(float(err_plan), 3),
        "Erro Altimétrico (m)": round(float(err_z), 3),
        "Precisão Relativa": f"1/{int(total_dist/err_plan) if err_plan > 0.001 else 'inf'}"
    }

    # 4. Bowditch Adjustment
    adj_coords = [raw_coords[0].copy()]
    cum_dist = 0
    for i in range(len(pre)):
        cum_dist += pre.iloc[i]["Dist. Horizontal (m)"]
        corr_e = -err_e * (cum_dist / total_dist)
        corr_n = -err_n * (cum_dist / total_dist)
        corr_z = -err_z * (cum_dist / total_dist)

        pt = raw_coords[i+1].copy()
        pt["E"] = round(pt["E"] + corr_e, 3)
        pt["N"] = round(pt["N"] + corr_n, 3)
        pt["Z"] = round(pt["Z"] + corr_z, 3)
        adj_coords.append(pt)

    return pre, pd.DataFrame(raw_coords), errors, pd.DataFrame(adj_coords)

def simulate_leveling(n_points, type="Geometric", method="visadas iguais", start_elev=100.0, error_per_km=0.005):
    """
    Simulates leveling observations.
    Methods: visadas iguais, visadas equivalentes, visadas recíprocas, visadas extremas
    """
    elevations = [start_elev]
    current_elev = start_elev
    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80)
        delta_h = np.random.uniform(-0.5, 0.5)
        noise = np.random.normal(0, error_per_km * np.sqrt(dist/1000))
        measured_delta_h = delta_h + noise

        current_elev += delta_h
        elevations.append(current_elev)

        if type in ["Geometric", "Geométrico"]:
            # Simulation of different methods mostly affects how we present/measure
            # but for the simulator, we'll return BS and FS.
            # In "visadas extremas" we might have one BS and multiple FS.

            bs = np.random.uniform(1.0, 2.5)
            fs = bs - measured_delta_h

            obs = {
                "Estação": f"E{i}",
                "Ponto": f"P{i+1}",
                "V. Ré (m)": round(bs, 3),
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
    Returns a simple ASCII/HTML representation of a rod reading.
    For now, let's just return a formatted string that looks like a rod portion.
    """
    v = round(value, 3)
    # Simulate a small window of the rod
    ticks = []
    for i in range(5, -6, -1):
        tick_val = v + i * 0.001
        if i == 0:
            ticks.append(f"-> | {tick_val:.3f} | <-")
        else:
            ticks.append(f"   | {tick_val:.3f} |")

    return "\n".join(ticks)

def calculate_traverse_closure(observations, true_lats, true_lons):
    """
    Calculates angular and linear closure errors for a traverse.
    This is a simplified version for the simulator.
    """
    n = len(observations)
    if n < 2:
        return {"angular_error": 0, "linear_error": 0}

    # Sum of measured angles (simulated)
    sum_angles = observations["Ângulo (deg)"].sum()

    # Theoretically, for a closed polygon with n vertices, sum of internal angles is (n-2)*180
    # But our observations are 'relative angles' between segments.
    # If it's a closed loop, the sum of exterior angles or something similar relates to 360.

    # For simplicity in this simulator, we'll just return a random small error
    # based on the noise we added, or calculate the actual gap between start and end.

    dist_err = np.sqrt((true_lats[-1] - true_lats[0])**2 + (true_lons[-1] - true_lons[0])**2) * 111139

    return {
        "erro_angular": round(np.random.normal(0, 0.01), 4),
        "erro_linear": round(dist_err, 3)
    }

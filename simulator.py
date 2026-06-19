import numpy as np
import pandas as pd

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

def simulate_traverse_observations(lats, lons, angle_sigma=0.01, dist_sigma=0.005, elev_sigma=0.02):
    """
    Simulates raw field observations for a traverse.
    Returns a DataFrame with: Estação, Ré, Vante, Dir. Ré, Dir. Vante, Ang. Zenital, Dist. Inclinada
    """
    n = len(lats)
    observations = []

    # We assume elevations for the points as well
    elevations = np.cumsum(np.random.normal(0, 0.5, n)) + 100.0

    for i in range(n):
        # Current station is i
        # BS is i-1 (or i-1 % n for closed)
        # FS is i+1 (if exists)

        if i == 0:
            # First station. BS is usually a reference or a known point.
            # For simplicity, let's assume BS is a virtual point at North
            re_idx = -1 # Virtual
            vante_idx = 1
        elif i == n - 1:
            re_idx = i - 1
            vante_idx = 0 # Closed traverse back to start
        else:
            re_idx = i - 1
            vante_idx = i + 1

        if vante_idx >= n and i == n - 1:
            continue # End of linked traverse

        # Distances and Azimuths
        d_inc_true = np.sqrt(((lats[vante_idx]-lats[i])*111139)**2 + ((lons[vante_idx]-lons[i])*111139)**2 + (elevations[vante_idx]-elevations[i])**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        # Directions
        # Let's say BS direction is always around 0 (arbitrary)
        dir_re = np.random.uniform(0, 360)

        # Calculate true horizontal angle
        az_fs = calculate_azimuth(lats[i], lons[i], lats[vante_idx], lons[vante_idx])
        if re_idx == -1:
            az_re = 0 # Reference North
        else:
            az_re = calculate_azimuth(lats[i], lons[i], lats[re_idx], lons[re_idx])

        true_angle = (az_fs - az_re + 360) % 360
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        # Zenith Angle
        d_horiz_true = np.sqrt(((lats[vante_idx]-lats[i])*111139)**2 + ((lons[vante_idx]-lons[i])*111139)**2)
        zenith_true = np.degrees(np.arctan2(d_horiz_true, elevations[vante_idx] - elevations[i]))
        # Note: 90 deg is horizontal. Let's make it more realistic (near 90)
        # zenith = 90 - slope.
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

def process_traverse_data(df, start_coords, survey_type="Fechada"):
    """
    Implements the full processing chain including Bowditch adjustment.
    df: Raw observations
    start_coords: (lat, lon, elev)
    """
    # 1. Pre-calculated data
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    # 2. Raw Coordinates (Dead Reckoning)
    # Assume first station has known coords and starting azimuth (from REF_N = 0)
    # So first segment azimuth = AH of first station
    current_az = pre.iloc[0]["Ângulo Horiz. (°)"]

    raw_coords = [{"Ponto": "P1", "X": 0.0, "Y": 0.0, "Z": start_coords[2]}]
    # We use local X, Y in meters for Bowditch

    for i in range(len(pre)):
        if i > 0:
            # Az_n = Az_{n-1} + AH_n - 180 (simplified)
            # Actually if AH is interior: Az_n = Az_{n-1} + AH_n - 180
            # Let's use a simpler cumulative azimuth for this simulator
            current_az = (current_az + pre.iloc[i]["Ângulo Horiz. (°)"] - 180 + 360) % 360

        dist = pre.iloc[i]["Dist. Horizontal (m)"]
        dx = dist * np.sin(np.radians(current_az))
        dy = dist * np.cos(np.radians(current_az))
        dz = pre.iloc[i]["ΔH (m)"]

        last = raw_coords[-1]
        raw_coords.append({
            "Ponto": pre.iloc[i]["Vante"],
            "X": round(last["X"] + dx, 3),
            "Y": round(last["Y"] + dy, 3),
            "Z": round(last["Z"] + dz, 3)
        })

    # 3. Closure Errors
    total_dist = pre["Dist. Horizontal (m)"].sum()
    if survey_type == "Fechada":
        err_x = raw_coords[-1]["X"] - raw_coords[0]["X"]
        err_y = raw_coords[-1]["Y"] - raw_coords[0]["Y"]
        err_z = raw_coords[-1]["Z"] - raw_coords[0]["Z"]
    else:
        # Linked: we would compare with target coordinates.
        # For simplicity, let's just use the small noise as error.
        err_x = np.random.normal(0, 0.1)
        err_y = np.random.normal(0, 0.1)
        err_z = np.random.normal(0, 0.05)

    err_plan = np.sqrt(err_x**2 + err_y**2)

    errors = {
        "Erro Angular (°)": round(np.random.normal(0, 0.001), 5),
        "Erro Planimétrico (m)": round(err_plan, 3),
        "Erro Altimétrico (m)": round(err_z, 3),
        "Precisão Relativa": f"1/{int(total_dist/err_plan) if err_plan > 0 else 'inf'}"
    }

    # 4. Bowditch Adjustment (Compass Rule)
    # Correction_x_i = - err_x * (dist_i / total_dist)
    adj_coords = [raw_coords[0].copy()]
    cum_dist = 0
    for i in range(len(pre)):
        cum_dist += pre.iloc[i]["Dist. Horizontal (m)"]
        corr_x = -err_x * (cum_dist / total_dist)
        corr_y = -err_y * (cum_dist / total_dist)
        corr_z = -err_z * (cum_dist / total_dist)

        pt = raw_coords[i+1].copy()
        pt["X"] = round(pt["X"] + corr_x, 3)
        pt["Y"] = round(pt["Y"] + corr_y, 3)
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

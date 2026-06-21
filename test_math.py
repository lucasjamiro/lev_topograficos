
import numpy as np
import pandas as pd
import simulator

def test_linked_traverse_math():
    print("Testing Linked Traverse Math...")
    # 5 stations -> 7 points
    # HV1, HV2, P1, P2, P3, HV4, HV5
    # Let's define some true coordinates in UTM
    # HV1 (0,0), HV2 (100,0) -> Azimuth 90
    # P1 (200, 100)
    # P2 (300, 0)
    # P3 (400, 100)
    # HV4 (500, 0), HV5 (600, 0) -> Azimuth 90

    e_coords = np.array([0, 100, 200, 300, 400, 500, 600], dtype=float)
    n_coords = np.array([0, 0, 100, 0, 100, 0, 0], dtype=float)

    # Simulate observations
    obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Linked", angle_sigma=0.0001, dist_sigma=0.001)
    print("\nSimulated Observations:")
    print(obs)

    # Process
    start_coords = (0, 0, 100.0)
    hv2_coords = (100, 0, 100.0)
    end_coords_start = (500, 0, 100.0)
    end_coords_end = (600, 0, 100.0)

    pre, raw, errors, adj = simulator.process_traverse_data(
        obs, start_coords, hv2_coords, survey_type="Linked",
        end_coords_start=end_coords_start, end_coords_end=end_coords_end
    )

    print("\nErrors:")
    print(errors)

    print("\nAdjusted Coordenates:")
    print(adj[['Ponto', 'E', 'N']])

    # Check if final point is close to target
    target_e = 500
    target_n = 0
    calc_e = adj.iloc[-1]['E']
    calc_n = adj.iloc[-1]['N']

    assert abs(calc_e - target_e) < 0.1, f"Expected E={target_e}, got {calc_e}"
    assert abs(calc_n - target_n) < 0.1, f"Expected N={target_n}, got {calc_n}"
    print("\nLinked Traverse Math Test Passed!")

def test_closed_traverse_math():
    print("\nTesting Closed Traverse Math...")
    # 5 stations -> 5 points
    # HV1, HV2, P1, P2, P3
    # Traverse: HV2 -> P1 -> P2 -> P3 -> HV2
    e_coords = np.array([0, 100, 200, 100, 0], dtype=float)
    n_coords = np.array([0, 0, 100, 200, 100], dtype=float)

    obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.0001, dist_sigma=0.001)

    start_coords = (0, 0, 100.0)
    hv2_coords = (100, 0, 100.0)

    pre, raw, errors, adj = simulator.process_traverse_data(
        obs, start_coords, hv2_coords, survey_type="Closed"
    )

    print("Errors:")
    print(errors)

    # For closed traverse, the last point in adj should be HV2 again
    calc_e = adj.iloc[-1]['E']
    calc_n = adj.iloc[-1]['N']

    assert abs(calc_e - 100) < 0.1, f"Expected E=100, got {calc_e}"
    assert abs(calc_n - 0) < 0.1, f"Expected N=0, got {calc_n}"
    print("Closed Traverse Math Test Passed!")

if __name__ == "__main__":
    test_linked_traverse_math()
    test_closed_traverse_math()

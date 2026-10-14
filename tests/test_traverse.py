import unittest
import numpy as np
import pandas as pd
import utm
import simulator

class TestTraverseSimulation(unittest.TestCase):

    def test_azimuth_calculation(self):
        # 45 degree azimuth from (0, 0) to (100, 100) in plane
        az = simulator.calculate_azimuth_flat(0, 0, 100, 100)
        self.assertAlmostEqual(az, 45.0, places=4)

        # 135 degree azimuth from (0, 0) to (100, -100)
        az2 = simulator.calculate_azimuth_flat(0, 0, 100, -100)
        self.assertAlmostEqual(az2, 135.0, places=4)

    def test_linked_traverse_coordinate_generation(self):
        n = 5
        lats, lons = simulator.generate_traverse_coordinates(n, survey_type="Linked")
        self.assertEqual(len(lats), n + 4)
        self.assertEqual(len(lons), n + 4)

    def test_closed_traverse_coordinate_generation(self):
        n = 5
        lats, lons = simulator.generate_traverse_coordinates(n, survey_type="Closed")
        self.assertEqual(len(lats), n + 2)
        self.assertEqual(len(lons), n + 2)

    def test_linked_observations_setups(self):
        n = 3
        lats, lons = simulator.generate_traverse_coordinates(n, survey_type="Linked")
        e_coords = lats # dummy flat/UTM coords for observation setup test
        n_coords = lons
        obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Linked")
        self.assertEqual(obs.iloc[0]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[0]['Ré'], 'HV1')
        self.assertEqual(obs.iloc[0]['Vante'], 'P1')

        self.assertEqual(obs.iloc[-1]['Estação'], 'HV4')
        self.assertEqual(obs.iloc[-1]['Ré'], f'P{n}')
        self.assertEqual(obs.iloc[-1]['Vante'], 'HV5')

    def test_closed_observations_setups(self):
        n = 3
        lats, lons = simulator.generate_traverse_coordinates(n, survey_type="Closed")
        e_coords = lats
        n_coords = lons
        obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Closed")
        self.assertEqual(obs.iloc[0]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[0]['Ré'], 'HV1')
        self.assertEqual(obs.iloc[0]['Vante'], 'P1')

        self.assertEqual(obs.iloc[-1]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[-1]['Vante'], 'P1')

    def test_traverse_processing_columns_and_rigorous_chain(self):
        e_coords = np.array([0, 100, 200, 300, 400, 500, 600], dtype=float)
        n_coords = np.array([0, 0, 100, 0, 100, 0, 0], dtype=float)
        obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Linked", angle_sigma=0.0001, dist_sigma=0.001)

        start_coords = (0, 0, 100.0)
        hv2_coords = (100, 0, 100.0)
        end_coords_start = (500, 0, 100.0)
        end_coords_end = (600, 0, 100.0)

        pre, az_df, raw_df, errors, adj_df = simulator.process_traverse_data(
            obs, start_coords, hv2_coords, survey_type="Linked",
            end_coords_start=end_coords_start, end_coords_end=end_coords_end
        )

        az_cols = ['Estação', 'Ré', 'Vante', 'Azimute Transportado (°)', 'Correção (°)', 'Azimute Corrigido (°)']
        self.assertTrue(all(col in az_df.columns for col in az_cols))

        expected_cols = ['Ponto', 'Correção E', 'Correção N', 'Correção Z', 'E', 'N', 'Z']
        self.assertTrue(all(col in adj_df.columns for col in expected_cols))

        self.assertIn('Erro Angular (°)', errors)
        self.assertIn('Erro Planimétrico (m)', errors)
        self.assertIn('Erro Altimétrico (m)', errors)
        self.assertIn('Precisão Relativa', errors)

        self.assertEqual(raw_df.iloc[0]['Ponto'], 'HV1')
        self.assertEqual(raw_df.iloc[1]['Ponto'], 'HV2')
        self.assertEqual(raw_df.iloc[-1]['Ponto'], 'HV5')

    def test_leveling_ai_column(self):
        obs, elevs = simulator.simulate_leveling(4, type="Geometric")
        self.assertIn('AI (m)', obs.columns)

    def test_get_automatic_backsight(self):
        # Closed traverse sequence: HV1, HV2, P1, P2, P3
        closed_labels = ["HV1", "HV2", "P1", "P2", "P3"]
        self.assertEqual(simulator.get_automatic_backsight("HV2", closed_labels), "HV1")
        self.assertEqual(simulator.get_automatic_backsight("P1", closed_labels), "HV2")
        self.assertEqual(simulator.get_automatic_backsight("P2", closed_labels), "P1")
        self.assertEqual(simulator.get_automatic_backsight("P3", closed_labels), "P2")

        # Linked traverse sequence: HV1, HV2, P1, P2, HV4, HV5
        linked_labels = ["HV1", "HV2", "P1", "P2", "HV4", "HV5"]
        self.assertEqual(simulator.get_automatic_backsight("HV2", linked_labels), "HV1")
        self.assertEqual(simulator.get_automatic_backsight("P1", linked_labels), "HV2")
        self.assertEqual(simulator.get_automatic_backsight("HV4", linked_labels), "P2")
        self.assertEqual(simulator.get_automatic_backsight("HV5", linked_labels), "HV4")

    def test_radiation_simulation_and_processing(self):
        e_coords = np.array([0, 100, 100, 0, 0], dtype=float)
        n_coords = np.array([0, 0, 100, 100, 0], dtype=float)

        radiation_data = [
            {
                "name": "IRR1",
                "station": "P1",
                "re": "HV2",
                "e": 150.0,
                "n": 50.0,
                "Z": 100.0
            },
            {
                "name": "IRR2",
                "station": "HV2",
                "re": "HV1",
                "e": 120.0,
                "n": -20.0,
                "Z": 100.0
            }
        ]

        obs = simulator.simulate_traverse_observations(
            e_coords, n_coords, survey_type="Closed",
            angle_sigma=0.0001, dist_sigma=0.001,
            radiation_data=radiation_data
        )

        vante_list = obs["Vante"].tolist()
        self.assertIn("IRR1", vante_list)
        self.assertIn("IRR2", vante_list)

        start_coords = (0, 0, 100.0)
        hv2_coords = (100, 0, 100.0)
        pre, az_df, raw_df, errors, adj_df = simulator.process_traverse_data(
            obs, start_coords, hv2_coords, survey_type="Closed"
        )

        adj_points = adj_df["Ponto"].tolist()
        self.assertIn("IRR1", adj_points)
        self.assertIn("IRR2", adj_points)

        irr1_row = adj_df[adj_df["Ponto"] == "IRR1"].iloc[0]
        self.assertAlmostEqual(irr1_row["E"], 150.0, delta=0.5)
        self.assertAlmostEqual(irr1_row["N"], 50.0, delta=0.5)

    def test_circular_mean_deg_wrap_around(self):
        # 359.9972222° (359° 59' 50") and 0.0027778° (0° 00' 10")
        angle1 = 359.0 + 59.0/60.0 + 50.0/3600.0
        angle2 = 0.0 + 0.0/60.0 + 10.0/3600.0
        mean_angle = simulator.circular_mean_deg([angle1, angle2])
        self.assertAlmostEqual(mean_angle, 0.0, delta=0.0001)

    def test_nbr_13133_error_injection(self):
        e_coords = np.array([0, 100, 100, 0, 0], dtype=float)
        n_coords = np.array([0, 0, 100, 100, 0], dtype=float)
        # Closed traverse with n=5 -> occupied stations N = 4
        N = 4
        max_err_sec = 9.0 * np.sqrt(N) + 15.0 # 33 arcseconds
        max_err_deg = max_err_sec / 3600.0

        # Simulate observations multiple times and verify angular error within limit range
        for _ in range(10):
            obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Closed")
            pre, az_df, raw_df, errors, adj_df = simulator.process_traverse_data(
                obs, (0, 0, 100), (100, 0, 100), survey_type="Closed"
            )
            err_ang = abs(errors["Erro Angular (°)"])
            self.assertLessEqual(err_ang, max_err_deg + 1e-6)

    def test_conjugated_simulation_and_reduction(self):
        e_coords = np.array([0, 100, 100, 0, 0], dtype=float)
        n_coords = np.array([0, 0, 100, 100, 0], dtype=float)
        radiation_data = [{"name": "IRR1", "station": "P1", "re": "HV2", "e": 150.0, "n": 50.0, "Z": 100.0}]

        # Test C=0 on radiation points
        obs_c0 = simulator.simulate_traverse_observations(
            e_coords, n_coords, survey_type="Closed",
            radiation_data=radiation_data,
            conjugated_mode=True, n_conj_vertices=2, n_conj_rad=0
        )
        rad_rows_c0 = obs_c0[obs_c0["Vante"] == "IRR1"]
        self.assertEqual(len(rad_rows_c0), 1)
        self.assertEqual(rad_rows_c0.iloc[0]["Posição"], "PD")
        self.assertEqual(rad_rows_c0.iloc[0]["Série"], 1)

        # Test C=2 on vertices and radiation
        obs_c2 = simulator.simulate_traverse_observations(
            e_coords, n_coords, survey_type="Closed",
            radiation_data=radiation_data,
            conjugated_mode=True, n_conj_vertices=2, n_conj_rad=2
        )
        self.assertIn("Posição", obs_c2.columns)
        self.assertIn("Série", obs_c2.columns)
        self.assertTrue((obs_c2["Posição"] == "PD").any())
        self.assertTrue((obs_c2["Posição"] == "PI").any())

        # Test Reduction
        reduced_df = simulator.reduce_conjugated_observations(obs_c2)
        self.assertNotIn("Posição", reduced_df.columns)
        self.assertNotIn("Série", reduced_df.columns)

        # Ensure reduced DataFrame can be passed into process_traverse_data without error
        pre, az_df, raw_df, errors, adj_df = simulator.process_traverse_data(
            reduced_df, (0, 0, 100), (100, 0, 100), survey_type="Closed"
        )
        self.assertIn("IRR1", adj_df["Ponto"].values)

if __name__ == '__main__':
    unittest.main()

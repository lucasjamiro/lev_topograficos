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

if __name__ == '__main__':
    unittest.main()

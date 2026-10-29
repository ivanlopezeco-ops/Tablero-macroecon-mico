"""Controles de fórmulas, fechas comunes y conservación ante fallas de fuentes."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
import ampliacion as A


def fuentes():
    fechas = ["2023-12-01", "2024-01-02", "2024-01-03", "2024-02-01"]
    b = {str(i): {f: 1.0 for f in fechas} for i in A.IDS}
    for f in fechas:
        b["77"][f] = 5.0
        b["46"][f] = 13.0
        b["19"][f], b["91"][f] = 10, 100
    salarios = {k: {"2023-12-01": 100, "2024-01-01": 120, "2024-02-01": 150} for k in ["salario_privado", "salario_publico"]}
    return {"bcra": b, "salarios": salarios, "empleo": {"empleo_privado_desest": {"2024-01-01": 6000}}}


class Calculos(unittest.TestCase):
    def construir(self, raw=None):
        return A.construir(raw or fuentes(), {"2023-12-01": 100, "2024-01-01": 120}, dt.date(2024, 2, 15))

    def test_liquidez_y_salario_real(self):
        out = self.construir()["series"]
        self.assertEqual(out["amp_liquidez"]["d"][-1][1], 10)
        self.assertAlmostEqual(out["amp_salario_privado"]["d"][-1][1], 100)
        self.assertEqual(out["amp_salario_privado"]["d"][-1][0], "2024-01-01")

    def test_flujos_solo_fechas_comunes(self):
        raw = fuentes()
        del raw["bcra"]["79"]["2024-01-03"]
        out = self.construir(raw)["series"]
        self.assertEqual(dict(out["amp_m77"]["d"])["2024-01-01"], 5)
        self.assertEqual(dict(out["amp_m78"]["d"])["2024-01-01"], 1)

    def test_diferencia_material_rechazada(self):
        raw = fuentes()
        raw["bcra"]["77"]["2024-01-03"] += 100
        with self.assertRaisesRegex(ValueError, "no concilian"):
            self.construir(raw)

    def test_mes_ausente_no_es_cero(self):
        m = A.mensual({"2024-01-02": 2, "2024-03-01": 4})
        self.assertNotIn("2024-02-01", m)

    def test_credito_promedia_saldos_y_excluye_mes_abierto(self):
        raw = fuentes()
        raw["bcra"]["110"].update({"2023-12-01": 10, "2024-01-02": 20, "2024-01-03": 40})
        out = self.construir(raw)["series"]["amp_credito_real_110"]["d"]
        self.assertAlmostEqual(out[-1][1], 250)  # promedio 30 / inflación 1,2 / base 10
        self.assertEqual(out[-1][0], "2024-01-01")

    def test_parser_sipa_fechas_mixtas_y_provisorias(self):
        self.assertEqual(A.fecha_empleo("jul-26*"), "2026-07-01")
        self.assertEqual(A.fecha_empleo(dt.datetime(2017, 10, 1)), "2017-10-01")
        self.assertIsNone(A.fecha_empleo("Notas: datos provisorios"))

    def test_falla_red_conserva_datos_y_se_informa(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "raw").mkdir()
            cache = {k: {"series": v, "ok_utc": "2024-01-01T00:00:00+00:00"} for k, v in fuentes().items()}
            (root / "raw/ampliacion-cache.json").write_text(json.dumps(cache))
            base = pd.DataFrame({"fecha": ["2023-12-01", "2024-01-01"], "variable": ["ipc_nivel_general"] * 2, "valor": [100, 120]})
            with patch.object(A, "DATA", root), patch.object(A.F, "HOY", dt.date(2024, 2, 15)), patch.object(A.F, "_get", side_effect=RuntimeError("sin red")):
                n, errores = A.actualizar(base, force=True)
            self.assertGreater(n, 20)
            self.assertTrue(errores)
            saved = json.loads((root / "ampliacion.json").read_text(encoding="utf8"))
            self.assertEqual(saved["series"]["amp_liquidez"]["d"][-1][1], 10)
            self.assertTrue(saved["fuentes"]["salarios"]["errores"])


if __name__ == "__main__":
    unittest.main()

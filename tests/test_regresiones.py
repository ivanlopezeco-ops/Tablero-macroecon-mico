"""Pruebas locales, determinísticas y sin descargas ni cambios en la base."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
import alerta
import bonos
import fuentes
import forwards
from salud import normalizar


class EstadoFuentes(unittest.TestCase):
    def test_parcial_persistente_no_reinicia_reloj(self):
        actual = {"x": {"estado": "ok", "filas": 5, "error": "falla"}}
        previo = {"x": {"estado": "ok", "error": "falla", "ok_utc": "2026-10-20T10:00:00"}}
        normalizar(actual, previo, "2026-10-20T14:00:00")
        self.assertEqual(actual["x"]["estado"], "PARCIAL")
        self.assertEqual(actual["x"]["error_desde"], "2026-10-20T10:00:00")

    def test_cero_filas_con_error_no_es_ok(self):
        actual = {"x": {"estado": "ok", "filas": 0, "error": "lxml"}}
        normalizar(actual, {}, "2026-10-20T10:00:00")
        self.assertEqual(actual["x"]["estado"], "ERROR")

    def test_cero_filas_fuera_de_rueda_no_es_error(self):
        actual = {"x": {"estado": "ok", "filas": 0}}
        normalizar(actual, {}, "2026-10-20T10:00:00")
        self.assertEqual(actual["x"]["estado"], "ok")

    def test_recuperacion_borra_antiguedad(self):
        actual = {"x": {"estado": "ok", "filas": 5, "error_desde": "ayer"}}
        normalizar(actual, {}, "hoy")
        self.assertNotIn("error_desde", actual["x"])


class Alertas(unittest.TestCase):
    def comprobar(self, fuente, horas=4):
        ahora = dt.datetime.utcnow()
        estado = {"corrida_utc": ahora.isoformat(), "fuentes": {"x": {
            **fuente, "error_desde": (ahora - dt.timedelta(hours=horas)).isoformat()}}}
        with tempfile.TemporaryDirectory() as d, patch.object(alerta, "DATA", pathlib.Path(d)):
            pathlib.Path(d, "estado.json").write_text(json.dumps(estado), encoding="utf-8")
            with patch.dict("os.environ", {"PIPELINE_FALLO": "0"}):
                return alerta.armar()

    def test_error_parcial_persistente_avisa(self):
        self.assertTrue(self.comprobar({"estado": "PARCIAL", "error": "lxml"})[0])

    def test_estado_legacy_ok_con_error_tambien_avisa(self):
        self.assertTrue(self.comprobar({"estado": "ok", "error": "lxml"})[0])

    def test_falla_reciente_espera_tres_horas(self):
        self.assertFalse(self.comprobar({"estado": "PARCIAL", "error": "transitorio"}, 1)[0])

    def test_recuperacion_cierra_alerta(self):
        self.assertFalse(self.comprobar({"estado": "ok"})[0])

    def test_fallo_workflow_sin_error_txt_avisa(self):
        with tempfile.TemporaryDirectory() as d, patch.object(alerta, "DATA", pathlib.Path(d)), patch.dict("os.environ", {"PIPELINE_FALLO": "1"}):
            self.assertTrue(alerta.armar()[0])


class IndiceByma(unittest.TestCase):
    def consultar(self, fila):
        respuesta = Mock()
        respuesta.json.return_value = {"data": [fila]}
        with patch.object(fuentes.requests, "post", return_value=respuesta):
            return fuentes.byma_indices()

    def test_cierre_con_fecha_se_conserva(self):
        df = self.consultar({"symbol": "MMSCI", "date": "2026-10-20T17:00:00", "closingPrice": 100321})
        self.assertEqual(df.iloc[-1]["valor"], 100321)
        self.assertEqual(df.iloc[-1]["fecha"], dt.date(2026, 10, 20))
        self.assertFalse(df.attrs["errores"])

    def test_precio_sin_fecha_no_se_asigna_a_hoy(self):
        df = self.consultar({"symbol": "MMSCI", "closingPrice": 102277.62})
        self.assertTrue(df.attrs["errores"])
        self.assertFalse(df["valor"].eq(102277.62).any())

    def test_simbolo_ausente_falla(self):
        with self.assertRaisesRegex(ValueError, "ausente"):
            self.consultar({"symbol": "M"})

    def test_error_http_no_se_oculta(self):
        respuesta = Mock(); respuesta.raise_for_status.side_effect = RuntimeError("HTTP 500")
        with patch.object(fuentes.requests, "post", return_value=respuesta), self.assertRaisesRegex(RuntimeError, "500"):
            fuentes.byma_indices()


class Licitaciones(unittest.TestCase):
    def test_numeros_argentinos_y_numeros_ya_convertidos(self):
        self.assertEqual(fuentes._num_ar("1.000,50"), 1000.5)
        self.assertEqual(fuentes._num_ar(1000.5), 1000.5)
        self.assertEqual(fuentes._num_ar(1000), 1000)
        self.assertEqual(fuentes._num_ar("27,47%"), 27.47)
        self.assertIsNone(fuentes._num_ar(float("nan")))

    def test_falla_relectura_no_borra_historia(self):
        anterior = {"url": "/noticias/resultado-licitacion-1", "v": 1, "f": "2026-10-01", "adjudicado": 100, "inst": []}
        respuesta = Mock(text='<a href="/noticias/resultado-licitacion-1">Resultado</a>')
        with patch.object(fuentes, "_get", side_effect=[respuesta, Mock(text="fin")]), patch.object(fuentes, "_licitacion", side_effect=RuntimeError("fallo parser")):
            datos, errores = fuentes.licitaciones([anterior])
        self.assertEqual(datos, [anterior]); self.assertTrue(errores)


class CalculosFinancieros(unittest.TestCase):
    def test_bono_cero_cupon_rinde_diez_por_ciento(self):
        flujos = [{"f": "2026-01-01", "int": 0, "am": 110}]
        self.assertAlmostEqual(bonos.tir(flujos, 100, dt.date(2025, 1, 1)), 10, places=8)
        self.assertIsNone(bonos.tir(flujos, 100, dt.date(2026, 1, 1)))

    def test_forward_curva_plana(self):
        # 21% efectivo anual equivale a 20% nominal con capitalización semestral.
        self.assertAlmostEqual(float(forwards.forward(21, 1, 21, 2)), 20, places=8)


if __name__ == "__main__":
    unittest.main()

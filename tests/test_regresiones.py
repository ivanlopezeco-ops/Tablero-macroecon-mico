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


class Descargas(unittest.TestCase):
    def respuesta(self, status=200):
        r = Mock(status_code=status)
        if status >= 400:
            r.raise_for_status.side_effect = fuentes.requests.HTTPError(str(status))
        return r

    def test_descarga_cortada_reintenta_misma_url(self):
        ok = self.respuesta()
        cortada = fuentes.requests.exceptions.ChunkedEncodingError("archivo incompleto")
        with patch.object(fuentes.requests, "get", side_effect=[cortada, ok]) as get, patch("time.sleep"):
            self.assertIs(fuentes._get(fuentes.F_BC), ok)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0], get.call_args_list[1])

    def test_descarga_cortada_persistente_no_se_oculta(self):
        with patch.object(fuentes.requests, "get", side_effect=fuentes.requests.exceptions.ChunkedEncodingError("incompleto")) as get, patch("time.sleep"):
            with self.assertRaises(fuentes.requests.exceptions.ChunkedEncodingError):
                fuentes._get(fuentes.F_BC)
        self.assertEqual(get.call_count, 3)

    def test_error_500_sigue_reintentando(self):
        mal, ok = self.respuesta(503), self.respuesta()
        with patch.object(fuentes.requests, "get", side_effect=[mal, ok]), patch("time.sleep"):
            self.assertIs(fuentes._get("https://ejemplo.test"), ok)
        mal.close.assert_called_once()

    def test_error_400_generico_no_se_reintenta(self):
        with patch.object(fuentes.requests, "get", return_value=self.respuesta(400)) as get, patch("time.sleep"):
            with self.assertRaises(fuentes.requests.HTTPError):
                fuentes._get("https://ejemplo.test")
        self.assertEqual(get.call_count, 1)

    def test_byma_400_transitorio_mismos_parametros(self):
        mal, ok = self.respuesta(400), self.respuesta()
        ok.json.return_value = {"t": [1792512000], "c": [65.25]}
        with patch.object(fuentes.requests, "get", side_effect=[mal, ok]) as get, patch("time.sleep"):
            df = fuentes._byma_historia({"AL30D 24HS": ("al30_usd_mep", "USD")})
        self.assertFalse(df.attrs["errores"])
        self.assertEqual(df.iloc[0]["valor"], 65.25)
        self.assertEqual(df.iloc[0]["unidad"], "USD")
        self.assertEqual(df.iloc[0]["fuente"], "BYMA (AL30D 24HS)")
        self.assertEqual(get.call_args_list[0], get.call_args_list[1])
        self.assertEqual(get.call_args.kwargs["params"]["symbol"], "AL30D 24HS")

    def test_byma_400_persistente_se_informa_despues_de_tres_intentos(self):
        with patch.object(fuentes.requests, "get", return_value=self.respuesta(400)) as get, patch("time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "AL30D 24HS: 400"):
                fuentes._byma_historia({"AL30D 24HS": ("al30_usd_mep", "USD")})
        self.assertEqual(get.call_count, 3)

    def test_byma_un_simbolo_fallido_no_descarta_los_demas(self):
        ok = self.respuesta()
        ok.json.return_value = {"t": [1792512000], "c": [65.25]}
        def descargar(url, **kw):
            if kw["params"]["symbol"] == "AL30D 24HS":
                raise fuentes.requests.HTTPError("400")
            return ok
        with patch.object(fuentes, "_get", side_effect=descargar):
            df = fuentes.byma_historicos()
        self.assertEqual(set(df["variable"]), {v for s, (v, _) in fuentes.BYMA_SIMBOLOS.items() if s != "AL30D 24HS"})
        self.assertEqual(len(df.attrs["errores"]), 1)
        self.assertIn("AL30D 24HS", df.attrs["errores"][0])
        self.assertTrue(df["valor"].eq(65.25).all())


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


class RezagosPublicacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import run
        cls.pipeline = run

    def test_recaudacion_no_exige_un_mes_sin_cerrar(self):
        for hoy in [dt.date(2026, 10, 29), dt.date(2026, 10, 31)]:
            self.assertFalse(self.pipeline.rezago_de("recaudacion_total", dt.date(2026, 9, 1), hoy)[3])

    def test_alerta_despues_de_cinco_habiles(self):
        fecha = dt.date(2026, 9, 1)
        self.assertEqual(self.pipeline.limite_mensual_habil(fecha, 5), dt.date(2026, 11, 6))
        self.assertFalse(self.pipeline.rezago_de("recaudacion_dgi", fecha, dt.date(2026, 11, 6))[3])
        self.assertTrue(self.pipeline.rezago_de("recaudacion_dgi", fecha, dt.date(2026, 11, 7))[3])

    def test_excluye_feriados_nacionales(self):
        # Abril cierra el 30; el 1 de mayo es feriado y el fin de semana no cuenta.
        self.assertEqual(self.pipeline.limite_mensual_habil(dt.date(2026, 3, 1), 5), dt.date(2026, 5, 8))

    def test_cierre_de_anio_y_feriado_de_enero(self):
        self.assertEqual(self.pipeline.limite_mensual_habil(dt.date(2026, 11, 1), 5), dt.date(2027, 1, 8))

    def test_mes_bisiesto(self):
        self.assertEqual(self.pipeline.limite_mensual_habil(dt.date(2024, 1, 1), 5), dt.date(2024, 3, 7))

    def test_los_otros_criterios_no_cambian(self):
        fecha = dt.date(2026, 9, 1)
        self.assertFalse(self.pipeline.rezago_de("ipc_nivel_general", fecha, dt.date(2026, 11, 20))[3])
        self.assertTrue(self.pipeline.rezago_de("ipc_nivel_general", fecha, dt.date(2026, 11, 21))[3])

    def test_itcrm_ruta_nueva_no_espera_la_cache_anterior(self):
        estado = {"estado": "ok", "ok_utc": dt.datetime.utcnow().isoformat()}
        with patch.object(fuentes, "COMPLETO", False):
            self.assertTrue(self.pipeline.toca("itcrm", {"itcrm": estado}))
            self.assertFalse(self.pipeline.toca("itcrm", {"itcrm": {**estado, "url": fuentes.F_ITCRM}}))


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

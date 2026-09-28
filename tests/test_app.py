import os
import unittest
from decimal import Decimal


os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import app, calcular_cashback, db  # noqa: E402


class CashbackTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def test_calcula_cashback_vip_com_bonus(self):
        resultado = calcular_cashback("VIP", 600, 0)

        self.assertEqual(resultado["valor_final"], Decimal("600.00"))
        self.assertEqual(resultado["cashback"], Decimal("66.00"))

    def test_api_calcula_e_registra_historico(self):
        response = self.client.post(
            "/api/calcular",
            json={
                "tipo_cliente": "NORMAL",
                "valor": 200,
                "desconto_percentual": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["valor_final"], 180.0)

        history = self.client.get("/api/historico")

        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.get_json()), 1)

    def test_api_rejeita_payload_invalido(self):
        response = self.client.post("/api/calcular", json={"tipo_cliente": "VIP", "valor": 0})

        self.assertEqual(response.status_code, 400)
        self.assertIn("erro", response.get_json())

    def test_api_rejeita_nan(self):
        response = self.client.post(
            "/api/calcular",
            json={"tipo_cliente": "VIP", "valor": "NaN"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "Valor numerico invalido")

    def test_limite_500_nao_dobra_e_500_01_dobra(self):
        resultado = calcular_cashback("NORMAL", 500, 0)
        self.assertEqual(resultado["cashback"], Decimal("25.00"))

        resultado = calcular_cashback("NORMAL", "500.01", 0)
        self.assertEqual(resultado["cashback"], Decimal("50.00"))

    def test_desconto_total_zera_cashback(self):
        resultado = calcular_cashback("VIP", 100, 100)
        self.assertEqual(resultado["valor_final"], Decimal("0.00"))
        self.assertEqual(resultado["cashback"], Decimal("0.00"))

    def test_api_simula_cenarios_de_regras(self):
        response = self.client.post("/api/simular", json={})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreaterEqual(data["total_cenarios"], 4)
        self.assertIn("maior_cashback", data)

    def test_api_relatorio_resume_consultas_do_ip(self):
        self.client.post(
            "/api/calcular",
            json={"tipo_cliente": "VIP", "valor": 600, "desconto_percentual": 0},
        )

        response = self.client.get("/api/relatorio")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total_consultas"], 1)
        self.assertEqual(data["por_tipo"]["VIP"], 1)


if __name__ == "__main__":
    unittest.main()

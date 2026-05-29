from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timezone
import os
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

database_url = os.getenv("DATABASE_URL")
allow_sqlite_fallback = os.getenv("ALLOW_SQLITE_FALLBACK", "false").lower() == "true"

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
elif allow_sqlite_fallback:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
else:
    raise RuntimeError(
        "DATABASE_URL não configurada. Use Postgres ou MySQL. "
        "Para desenvolvimento local, defina ALLOW_SQLITE_FALLBACK=true."
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

TIPOS_CLIENTE_VALIDOS = {"NORMAL", "VIP"}
CENT = Decimal("0.01")
APP_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Sao_Paulo"))


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_local_timestamp(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(APP_TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")


class Consulta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), nullable=False, index=True)
    tipo_cliente = db.Column(db.String(10), nullable=False)
    valor_original = db.Column(db.Numeric(10, 2), nullable=False)
    desconto_percentual = db.Column(db.Numeric(5, 2), nullable=False)
    valor_final = db.Column(db.Numeric(10, 2), nullable=False)
    cashback = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now_naive, nullable=False)

    def to_dict(self):
        return {
            "tipo_cliente": self.tipo_cliente,
            "valor_original": float(self.valor_original),
            "desconto_percentual": float(self.desconto_percentual),
            "valor_final": float(self.valor_final),
            "cashback": float(self.cashback),
            "timestamp": format_local_timestamp(self.timestamp),
        }


with app.app_context():
    db.create_all()


def round_money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Valor numerico invalido")


def get_request_ip():
    return request.remote_addr or "desconhecido"


def api_response(payload, status=200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def calcular_cashback(tipo_cliente, valor_original, desconto_percentual):
    tipo_cliente = str(tipo_cliente).upper()
    if tipo_cliente not in TIPOS_CLIENTE_VALIDOS:
        raise ValueError("Tipo de cliente invalido")

    valor_original = to_decimal(valor_original)
    desconto_percentual = to_decimal(desconto_percentual)

    if valor_original <= 0:
        raise ValueError("O valor da compra deve ser maior que zero")
    if desconto_percentual < 0 or desconto_percentual > 100:
        raise ValueError("O desconto deve estar entre 0 e 100")

    fator_desconto = Decimal("1") - (desconto_percentual / Decimal("100"))
    valor_final = round_money(valor_original * fator_desconto)
    cashback = valor_final * Decimal("0.05")

    if tipo_cliente == "VIP":
        cashback += cashback * Decimal("0.10")

    if valor_final > Decimal("500"):
        cashback *= Decimal("2")

    cashback = round_money(cashback)

    return {
        "tipo_cliente": tipo_cliente,
        "valor_original": round_money(valor_original),
        "desconto_percentual": round_money(desconto_percentual),
        "valor_final": valor_final,
        "cashback": cashback,
    }


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/calcular", methods=["POST"])
def api_calcular():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return api_response({"erro": "Envie um JSON valido"}, 400)

        resultado = calcular_cashback(
            data.get("tipo_cliente"),
            data.get("valor"),
            data.get("desconto_percentual", 0),
        )

        consulta = Consulta(
            ip=get_request_ip(),
            tipo_cliente=resultado["tipo_cliente"],
            valor_original=resultado["valor_original"],
            desconto_percentual=resultado["desconto_percentual"],
            valor_final=resultado["valor_final"],
            cashback=resultado["cashback"],
        )
        db.session.add(consulta)
        db.session.commit()

        return api_response(
            {
                "tipo_cliente": resultado["tipo_cliente"],
                "valor_original": float(resultado["valor_original"]),
                "desconto_percentual": float(resultado["desconto_percentual"]),
                "valor_final": float(resultado["valor_final"]),
                "cashback": float(resultado["cashback"]),
            }
        )
    except ValueError as exc:
        return api_response({"erro": str(exc)}, 400)
    except Exception as exc:
        app.logger.exception("Erro ao calcular cashback: %s", exc)
        return api_response({"erro": "Erro interno"}, 500)


@app.route("/api/historico", methods=["GET"])
def api_historico():
    ip = get_request_ip()
    consultas = (
        Consulta.query.filter_by(ip=ip)
        .order_by(Consulta.timestamp.desc())
        .all()
    )
    return api_response([consulta.to_dict() for consulta in consultas])


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

# Cashback Nology

Aplicação Flask com frontend estático para calcular cashback, registrar histórico por IP e demonstrar regras de negócio em uma API simples.

## Problema

Uma operação comercial precisa simular cashback considerando tipo de cliente, valor da compra e regras promocionais. O projeto centraliza esse cálculo em uma API e mantém o histórico das consultas feitas pelo usuário.

## Funcionalidades

- Cálculo de cashback para cliente normal e VIP
- Histórico de consultas por IP
- API Flask com respostas JSON
- Persistência com SQLAlchemy
- Suporte a Postgres, MySQL ou SQLite em desenvolvimento
- Frontend estático com formulário e tabela de histórico

## Regras de negócio

1. O cashback é calculado sobre o valor final da compra.
2. O cashback base é de 5% sobre o valor final.
3. Clientes VIP recebem 10% adicional sobre o cashback base.
4. Compras com valor final acima de R$ 500 recebem o dobro de cashback.

## Endpoints

```text
GET   /
POST  /api/calcular
GET   /api/historico
```

Exemplo de payload:

```json
{
  "tipo_cliente": "VIP",
  "valor": 600,
  "desconto_percentual": 0
}
```

## Stack

- Python
- Flask
- Flask-SQLAlchemy
- HTML, CSS e JavaScript
- SQLite para desenvolvimento local
- Postgres ou MySQL via `DATABASE_URL`

## Rodar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ALLOW_SQLITE_FALLBACK="true"
python app.py
```

Depois acesse:

```text
http://127.0.0.1:5000
```

Para rodar com banco externo, defina `DATABASE_URL` com Postgres ou MySQL.

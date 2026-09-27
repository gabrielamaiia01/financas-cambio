import re
from datetime import date, datetime

from flask import Flask, jsonify, request

from config import MOEDA_PADRAO, PORTA
from cache import inicializar_cache, buscar_no_cache, salvar_no_cache
from cliente_awesome_api import (
    ApiExternaIndisponivelError,
    MoedaInvalidaError,
    buscar_cotacao_atual,
    buscar_cotacao_historica,
)

app = Flask(__name__)
app.json.ensure_ascii = False

inicializar_cache()


def _erro(mensagem, status):
    return jsonify({"erro": mensagem}), status


@app.route("/cotacao", methods=["GET"])
def obter_cotacao():
    """Retorna a cotação de uma moeda contra o BRL.

    Query params:
    - moeda: opcional, padrão USD (ex: ?moeda=EUR)
    - data: opcional, formato AAAA-MM-DD. Se omitida, retorna a cotação
      atual (não cacheada). Se informada, primeiro olha o cache local;
      só chama a API externa se ainda não tiver essa (moeda, data).

    Erros: 400 (moeda/data inválida ou data futura), 404 (sem cotação),
    502 (API externa fora do ar).
    """
    moeda = request.args.get("moeda", MOEDA_PADRAO).strip().upper()
    data = request.args.get("data")

    if not re.fullmatch(r"[A-Z]{3}", moeda):
        return _erro(f"Moeda inválida: '{moeda}'. Use um código de 3 letras, ex: USD.", 400)

    if moeda == "BRL":
        return jsonify(
            {"moeda": "BRL", "data": data or date.today().isoformat(), "valor": 1.0, "origem": "fixo"}
        ), 200

    if data:
        try:
            data_pedida = datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            return _erro(f"Data inválida: '{data}'. Use o formato AAAA-MM-DD.", 400)

        if data_pedida > date.today():
            return _erro(f"A data {data} está no futuro; não existe cotação para ela.", 400)

        em_cache = buscar_no_cache(moeda, data)
        if em_cache is not None:
            return jsonify(
                {
                    "moeda": moeda,
                    "data": data,
                    "data_cotacao": em_cache["data_cotacao"],
                    "valor": em_cache["valor"],
                    "origem": "cache",
                }
            ), 200

        try:
            resultado = buscar_cotacao_historica(moeda, data)
        except MoedaInvalidaError:
            return _erro(f"Moeda '{moeda}' não é suportada pela API de câmbio.", 400)
        except ApiExternaIndisponivelError:
            return _erro("Não foi possível consultar a API externa de câmbio.", 502)

        if resultado is None:
            return _erro(f"Não há cotação de {moeda} para {data} nem nos dias úteis anteriores.", 404)

        # A cotação do dia de hoje ainda pode mudar até o fechamento,
        # então só guarda em cache datas passadas.
        if data_pedida < date.today():
            salvar_no_cache(moeda, data, resultado["valor"], resultado["data_cotacao"])

        return jsonify(
            {
                "moeda": moeda,
                "data": data,
                "data_cotacao": resultado["data_cotacao"],
                "valor": resultado["valor"],
                "origem": "api_externa",
            }
        ), 200

    # Sem data: cotação em tempo real, sempre buscada na API (não cacheada)
    try:
        resultado = buscar_cotacao_atual(moeda)
    except MoedaInvalidaError:
        return _erro(f"Moeda '{moeda}' não é suportada pela API de câmbio.", 400)
    except ApiExternaIndisponivelError:
        return _erro("Não foi possível consultar a API externa de câmbio.", 502)

    return jsonify(
        {
            "moeda": moeda,
            "data": resultado["data"],
            "valor": resultado["valor"],
            "origem": "api_externa",
        }
    ), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=PORTA)

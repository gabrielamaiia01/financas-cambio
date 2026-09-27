from datetime import datetime, timedelta, timezone

import requests
from config import AWESOME_API_BASE_URL, DIAS_BUSCA_RETROATIVA

# Horário de Brasília (sem horário de verão desde 2019)
FUSO_BRASILIA = timezone(timedelta(hours=-3))


class MoedaInvalidaError(Exception):
    """A AwesomeAPI não conhece o par <moeda>-BRL."""


class ApiExternaIndisponivelError(Exception):
    """A AwesomeAPI está fora do ar, lenta demais ou devolveu algo inesperado."""


def _get(url):
    try:
        resposta = requests.get(url, timeout=10)
    except requests.RequestException as erro:
        raise ApiExternaIndisponivelError(str(erro)) from erro

    # A AwesomeAPI responde 404 ("CoinNotExists") para moedas que não existem
    if resposta.status_code == 404:
        raise MoedaInvalidaError()
    if resposta.status_code != 200:
        raise ApiExternaIndisponivelError(f"HTTP {resposta.status_code}")

    try:
        return resposta.json()
    except ValueError as erro:
        raise ApiExternaIndisponivelError("Resposta inválida da API externa") from erro


def _data_do_item(item):
    """Converte o timestamp (unix) de um item da AwesomeAPI em 'AAAA-MM-DD'."""
    instante = datetime.fromtimestamp(int(item["timestamp"]), tz=FUSO_BRASILIA)
    return instante.date().isoformat()


def buscar_cotacao_historica(moeda, data_iso):
    """Busca a cotação de fechamento de `moeda` (ex: USD) contra o BRL
    na data `data_iso` (formato 'AAAA-MM-DD').

    Se não houve pregão nessa data (fim de semana/feriado), usa o último
    dia útil anterior, dentro de uma janela de DIAS_BUSCA_RETROATIVA dias.

    Retorna {"valor": float, "data_cotacao": "AAAA-MM-DD"} ou None se não
    houver nenhuma cotação na janela.
    """
    fim = datetime.strptime(data_iso, "%Y-%m-%d").date()
    inicio = fim - timedelta(days=DIAS_BUSCA_RETROATIVA)
    url = (
        f"{AWESOME_API_BASE_URL}/json/daily/{moeda}-BRL/{DIAS_BUSCA_RETROATIVA + 1}"
        f"?start_date={inicio:%Y%m%d}&end_date={fim:%Y%m%d}"
    )
    dados = _get(url)

    if not isinstance(dados, list):
        raise ApiExternaIndisponivelError("Formato de resposta inesperado")

    # Descarta itens posteriores à data pedida e fica com o mais recente
    candidatos = [item for item in dados if _data_do_item(item) <= data_iso]
    if not candidatos:
        return None

    item = max(candidatos, key=lambda i: int(i["timestamp"]))
    return {"valor": float(item["bid"]), "data_cotacao": _data_do_item(item)}


def buscar_cotacao_atual(moeda):
    """Busca a cotação mais recente de `moeda` contra o BRL.

    Retorna {"valor": float, "data": "AAAA-MM-DD"}.
    """
    dados = _get(f"{AWESOME_API_BASE_URL}/json/last/{moeda}-BRL")

    try:
        item = dados[f"{moeda}BRL"]
        return {"valor": float(item["bid"]), "data": item["create_date"][:10]}
    except (KeyError, TypeError, ValueError) as erro:
        raise ApiExternaIndisponivelError("Formato de resposta inesperado") from erro

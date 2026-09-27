from datetime import date, datetime, timedelta, timezone

import requests

import cliente_awesome_api

BRT = timezone(timedelta(hours=-3))


def _ts(data_iso):
    return str(int(datetime.strptime(data_iso, "%Y-%m-%d").replace(hour=17, tzinfo=BRT).timestamp()))


class RespostaFalsa:
    def __init__(self, status_code, corpo):
        self.status_code = status_code
        self._corpo = corpo

    def json(self):
        return self._corpo


def _mock_get(monkeypatch, resposta):
    chamadas = []

    def get(url, timeout):
        chamadas.append(url)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    monkeypatch.setattr(cliente_awesome_api.requests, "get", get)
    return chamadas


def test_historica_usa_cache_na_segunda_chamada(client, monkeypatch):
    chamadas = _mock_get(
        monkeypatch,
        RespostaFalsa(200, [{"bid": "5.43", "timestamp": _ts("2026-08-14")}]),
    )

    r1 = client.get("/cotacao?data=2026-08-14&moeda=usd")
    r2 = client.get("/cotacao?data=2026-08-14&moeda=USD")

    assert r1.status_code == 200 and r1.json["origem"] == "api_externa"
    assert r2.status_code == 200 and r2.json["origem"] == "cache"
    assert r2.json["valor"] == 5.43
    assert len(chamadas) == 1


def test_fim_de_semana_usa_ultimo_dia_util(client, monkeypatch):
    # 2026-08-15 é sábado: a API devolve sexta e quinta
    _mock_get(
        monkeypatch,
        RespostaFalsa(
            200,
            [
                {"bid": "5.40", "timestamp": _ts("2026-08-13")},
                {"bid": "5.43", "timestamp": _ts("2026-08-14")},
            ],
        ),
    )
    r = client.get("/cotacao?data=2026-08-15&moeda=USD")
    assert r.status_code == 200
    assert r.json["valor"] == 5.43
    assert r.json["data_cotacao"] == "2026-08-14"


def test_data_futura(client):
    amanha = (date.today() + timedelta(days=1)).isoformat()
    r = client.get(f"/cotacao?data={amanha}&moeda=USD")
    assert r.status_code == 400
    assert "futuro" in r.json["erro"]


def test_data_mal_formatada(client):
    r = client.get("/cotacao?data=15/08/2026&moeda=USD")
    assert r.status_code == 400


def test_moeda_mal_formatada(client):
    r = client.get("/cotacao?data=2026-08-14&moeda=DOLAR")
    assert r.status_code == 400


def test_moeda_inexistente(client, monkeypatch):
    _mock_get(monkeypatch, RespostaFalsa(404, {"code": "CoinNotExists"}))
    r = client.get("/cotacao?data=2026-08-14&moeda=XYZ")
    assert r.status_code == 400
    assert "XYZ" in r.json["erro"]


def test_api_fora_do_ar(client, monkeypatch):
    _mock_get(monkeypatch, requests.ConnectionError("sem rede"))
    r = client.get("/cotacao?data=2026-08-14&moeda=USD")
    assert r.status_code == 502
    r = client.get("/cotacao?moeda=USD")
    assert r.status_code == 502


def test_sem_cotacao_na_janela(client, monkeypatch):
    _mock_get(monkeypatch, RespostaFalsa(200, []))
    r = client.get("/cotacao?data=2026-08-14&moeda=USD")
    assert r.status_code == 404


def test_cotacao_atual(client, monkeypatch):
    _mock_get(
        monkeypatch,
        RespostaFalsa(200, {"USDBRL": {"bid": "5.60", "create_date": "2026-09-25 17:00:00"}}),
    )
    r = client.get("/cotacao?moeda=USD")
    assert r.status_code == 200
    assert r.json == {"moeda": "USD", "data": "2026-09-25", "valor": 5.6, "origem": "api_externa"}

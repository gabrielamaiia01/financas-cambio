import sqlite3
from config import DATABASE_PATH


def get_conexao():
    conexao = sqlite3.connect(DATABASE_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao


def inicializar_cache():
    """Cria a tabela de cache caso não exista.

    Cada linha guarda a cotação de fechamento de uma moeda em uma data
    específica, para não repetir a chamada à API externa quando a mesma
    data for consultada de novo (ex: outra transação na mesma data).

    `data_cotacao` é o dia útil de onde a cotação veio: é igual a `data`
    em dias de pregão, e o último dia útil anterior em fins de semana/feriados.
    """
    conexao = get_conexao()
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS cotacoes_cache (
            moeda TEXT NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            data_cotacao TEXT,
            obtido_em TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (moeda, data)
        )
        """
    )
    # Bancos criados antes da coluna data_cotacao existir
    colunas = [linha["name"] for linha in conexao.execute("PRAGMA table_info(cotacoes_cache)")]
    if "data_cotacao" not in colunas:
        conexao.execute("ALTER TABLE cotacoes_cache ADD COLUMN data_cotacao TEXT")
    conexao.commit()
    conexao.close()


def buscar_no_cache(moeda, data):
    """Retorna {"valor", "data_cotacao"} em cache para (moeda, data), ou None."""
    conexao = get_conexao()
    linha = conexao.execute(
        "SELECT valor, data_cotacao FROM cotacoes_cache WHERE moeda = ? AND data = ?",
        (moeda, data),
    ).fetchone()
    conexao.close()
    if linha is None:
        return None
    return {"valor": linha["valor"], "data_cotacao": linha["data_cotacao"] or data}


def salvar_no_cache(moeda, data, valor, data_cotacao):
    """Grava (ou substitui) a cotação de uma moeda em uma data no cache."""
    conexao = get_conexao()
    conexao.execute(
        """
        INSERT INTO cotacoes_cache (moeda, data, valor, data_cotacao)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(moeda, data) DO UPDATE SET
            valor = excluded.valor,
            data_cotacao = excluded.data_cotacao
        """,
        (moeda, data, valor, data_cotacao),
    )
    conexao.commit()
    conexao.close()

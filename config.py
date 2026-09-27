import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("CAMBIO_DATABASE_PATH", os.path.join(BASE_DIR, "cache_cambio.db"))

MOEDA_PADRAO = "USD"

# API externa usada para consultar cotações (AwesomeAPI, gratuita, sem chave)
AWESOME_API_BASE_URL = os.environ.get("AWESOME_API_BASE_URL", "https://economia.awesomeapi.com.br")

# Quantos dias voltar procurando um dia útil quando a data pedida cair em
# fim de semana ou feriado
DIAS_BUSCA_RETROATIVA = 7

PORTA = 5001

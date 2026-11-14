"""Leitura SOMENTE LEITURA do Snowflake.

A conexão usa o arquivo ~/.snowflake/connections.toml (nome em CSIR_SNOWFLAKE_CONNECTION).
Em desenvolvimento é a conta pessoal (OAuth pelo navegador); em produção, um usuário de
serviço somente leitura configurado no mesmo arquivo ou por variáveis de ambiente.
"""

import re

from django.conf import settings

_INICIO_OK = re.compile(r"^\s*(SELECT|WITH|SHOW)\b", re.IGNORECASE)
_ESCRITA = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|PUT|REMOVE|GRANT|REVOKE|"
    r"CALL|EXECUTE|UNDROP)\b",
    re.IGNORECASE,
)
_NOME_TABELA = re.compile(r"^[A-Za-z0-9_$]+\.[A-Za-z0-9_$]+\.[A-Za-z0-9_$]+$")


class SnowflakeIndisponivel(RuntimeError):
    pass


def checar_leitura(sql):
    sem_literais = re.sub(r"'(?:[^']|'')*'", "''", sql)
    if not _INICIO_OK.match(sem_literais) or _ESCRITA.search(sem_literais):
        raise RuntimeError("Comando bloqueado: a integração com o Snowflake é somente leitura.")


def ler_tabela_notas():
    """Devolve (colunas, linhas) da tabela de notas IR configurada."""
    tabela = settings.CSIR_SNOWFLAKE_TABELA
    if not _NOME_TABELA.match(tabela):
        raise SnowflakeIndisponivel("Nome de tabela inválido em CSIR_SNOWFLAKE_TABELA.")
    try:
        import snowflake.connector
    except ImportError as exc:
        raise SnowflakeIndisponivel(
            "Instale o pacote snowflake-connector-python para sincronizar."
        ) from exc
    sql = f"SELECT * FROM {tabela}"
    checar_leitura(sql)
    try:
        con = snowflake.connector.connect(
            connection_name=settings.CSIR_SNOWFLAKE_CONNECTION,
            login_timeout=300,
            session_parameters={
                "QUERY_TAG": "csir-sincronizacao-somente-leitura",
                "STATEMENT_TIMEOUT_IN_SECONDS": settings.CSIR_SNOWFLAKE_TIMEOUT,
            },
        )
    except Exception as exc:  # credencial, rede, OAuth cancelado
        raise SnowflakeIndisponivel(f"Não foi possível conectar ao Snowflake: {exc}") from exc
    try:
        cur = con.cursor()
        cur.execute(sql)
        colunas = [c[0] for c in cur.description]
        return colunas, cur.fetchall()
    finally:
        con.close()

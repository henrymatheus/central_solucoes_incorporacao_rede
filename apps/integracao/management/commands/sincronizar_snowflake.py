from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from apps.integracao.sincronizacao import ler_csv, sincronizar
from apps.integracao.snowflake import SnowflakeIndisponivel, ler_tabela_notas


class Command(BaseCommand):
    help = (
        "Sincroniza a base do Dashboard com SB_TATICO_PA.OBRAS.TB_NOTAS_IR_CORPORATIVO "
        "(somente leitura) e grava a foto do dia no histórico das notas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--csv", help="Carrega de um CSV em vez do Snowflake (contingência).")
        parser.add_argument(
            "--sem-foto", action="store_true", help="Não grava a foto do dia no histórico."
        )
        parser.add_argument("--data", help="Data da foto (AAAA-MM-DD). Padrão: hoje.")

    def handle(self, *args, **opts):
        if opts["csv"]:
            caminho = Path(opts["csv"])
            if not caminho.is_file():
                raise CommandError(f"Arquivo não encontrado: {caminho}")
            linhas, fonte = ler_csv(caminho.read_bytes()), f"CSV {caminho.name}"
        else:
            self.stdout.write("Lendo o Snowflake (pode abrir o navegador para login)…")
            try:
                colunas, registros = ler_tabela_notas()
            except SnowflakeIndisponivel as exc:
                raise CommandError(str(exc)) from exc
            linhas = [dict(zip(colunas, r)) for r in registros]
            fonte = "Snowflake"
        data_ref = None
        if opts["data"]:
            data_ref = parse_date(opts["data"])
            if not data_ref:
                raise CommandError("Data inválida. Use AAAA-MM-DD.")
        try:
            execucao = sincronizar(linhas, fonte, snapshot=not opts["sem_foto"], data_ref=data_ref)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(execucao.mensagem))

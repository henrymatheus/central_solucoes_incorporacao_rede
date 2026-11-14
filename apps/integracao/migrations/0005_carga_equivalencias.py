from django.db import migrations

# Medido em 14/11/2026 nas notas do Pará, onde existem o DE-PARA e a GERENCIA do SQL:
# todas as notas com esta GERENCIA no SQL caem nesta gerência no DE-PARA.
EQUIVALENCIAS = [
    ("RELACIONAMENTO", "RELACIONAMENTO", "PA: 793 notas, 100% RELACIONAMENTO no DE-PARA"),
    ("RELACIONAMENTO CLIENTE", "RELACIONAMENTO", "PA: 5 notas, 100% RELACIONAMENTO no DE-PARA"),
    ("CONTROLADORIA", "ATIVOS", "PA: 507 notas, 100% ATIVOS no DE-PARA"),
    ("EXPANSÃO", "TÁTICO", "PA: 207 notas, 100% TÁTICO no DE-PARA"),
    ("OPERAÇÃO", "CADASTRO", "PA: 146 notas, 100% CADASTRO no DE-PARA"),
    ("ARRECADAÇÃO E FINANÇAS", "FINANCEIRO", "PA: 17 notas, 100% FINANCEIRO no DE-PARA"),
]


def carregar(apps, schema_editor):
    Equivalencia = apps.get_model("integracao", "EquivalenciaGerencia")
    for sql, gerencia, obs in EQUIVALENCIAS:
        Equivalencia.objects.update_or_create(
            gerencia_sql=sql, defaults={"gerencia": gerencia, "observacao": obs}
        )


class Migration(migrations.Migration):
    dependencies = [("integracao", "0004_equivalenciagerencia")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

from django.db import migrations


def carregar(apps, schema_editor):
    from apps.integracao.carga import carregar_tabelas_apoio

    StatusFiscalizacao = apps.get_model("integracao", "StatusFiscalizacao")
    StatusFiscalizacao.objects.all().delete()  # remove os status provisórios do seed antigo
    carregar_tabelas_apoio(apps.get_model("integracao", "DeParaMedidaGerencia"), StatusFiscalizacao)


class Migration(migrations.Migration):
    dependencies = [("integracao", "0002_deparamedidagerencia_alter_execucaoetl_options_and_more")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]

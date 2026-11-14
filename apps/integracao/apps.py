from django.apps import AppConfig


class IntegracaoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integracao"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.integracao.models import DeParaMedidaGerencia, EquivalenciaGerencia

        def recalcular(sender, **kwargs):
            if kwargs.get("raw"):
                return
            from apps.integracao.gerencia import recalcular_gerencias

            recalcular_gerencias()

        for modelo in (DeParaMedidaGerencia, EquivalenciaGerencia):
            post_save.connect(
                recalcular, sender=modelo, dispatch_uid=f"recalc_save_{modelo.__name__}"
            )
            post_delete.connect(
                recalcular, sender=modelo, dispatch_uid=f"recalc_del_{modelo.__name__}"
            )

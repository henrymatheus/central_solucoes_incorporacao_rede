from django.core.exceptions import PermissionDenied


def is_dev(user):
    perfil = getattr(user, "perfil", None)
    return bool(user.is_superuser or (perfil and perfil.tipo == "DEV"))


def usuario_tem_distribuidora(user, distribuidora):
    if is_dev(user):
        return True
    perfil = getattr(user, "perfil", None)
    return bool(perfil and perfil.distribuidoras.filter(pk=distribuidora.pk).exists())


def exigir_distribuidora(user, distribuidora):
    if not usuario_tem_distribuidora(user, distribuidora):
        raise PermissionDenied("Seu perfil não tem acesso a esta distribuidora.")


def distribuidoras_visiveis(user):
    """Queryset das distribuidoras ativas que o usuário pode ver."""
    from apps.core.models import Distribuidora

    qs = Distribuidora.objects.filter(ativa=True)
    if is_dev(user):
        return qs
    perfil = getattr(user, "perfil", None)
    return qs.filter(pk__in=perfil.distribuidoras.values("pk")) if perfil else qs.none()


def ufs_visiveis(user):
    """UFs (PA, MA…) visíveis ao usuário. None = todas (Desenvolvedor)."""
    if is_dev(user):
        return None
    return set(distribuidoras_visiveis(user).values_list("uf", flat=True))

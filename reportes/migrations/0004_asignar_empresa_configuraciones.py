from django.db import migrations


TIPOS_ASISTENCIA = ('diario', 'semanal', 'quincenal')


def asignar_empresa_default(apps, schema_editor):
    Empresa = apps.get_model('organizacion', 'Empresa')
    ConfiguracionReporte = apps.get_model('reportes', 'ConfiguracionReporte')

    empresa, _ = Empresa.objects.get_or_create(
        codigo='LOGINCO',
        defaults={'nombre': 'Loginco', 'activo': True}
    )

    ConfiguracionReporte.objects.filter(
        tipo__in=TIPOS_ASISTENCIA, empresa__isnull=True
    ).update(empresa=empresa)


def revertir_asignacion(apps, schema_editor):
    # No-op intencional: no desasignamos empresas al revertir.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0002_empresa'),
        ('reportes', '0003_configuracionreporte_empresa_logreporte_empresa_and_more'),
    ]

    operations = [
        migrations.RunPython(asignar_empresa_default, revertir_asignacion),
    ]

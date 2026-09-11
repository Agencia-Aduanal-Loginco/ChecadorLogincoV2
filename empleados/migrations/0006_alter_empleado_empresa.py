from django.db import migrations, models
import django.db.models.deletion


def asignar_empresa_default(apps, schema_editor):
    Empresa = apps.get_model('organizacion', 'Empresa')
    Empleado = apps.get_model('empleados', 'Empleado')

    empresa, _ = Empresa.objects.get_or_create(
        codigo='LOGINCO',
        defaults={'nombre': 'Loginco', 'activo': True}
    )
    Empleado.objects.filter(empresa__isnull=True).update(empresa=empresa)


def revertir_asignacion(apps, schema_editor):
    # No-op intencional: no desasignamos empresas al revertir.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0002_empresa'),
        ('empleados', '0005_empleado_empresa'),
    ]

    operations = [
        migrations.RunPython(asignar_empresa_default, revertir_asignacion),
        migrations.AlterField(
            model_name='empleado',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='empleados',
                to='organizacion.empresa',
                verbose_name='Empresa',
            ),
        ),
    ]

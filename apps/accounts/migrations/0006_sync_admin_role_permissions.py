from django.db import migrations


def sync_admin_permissions(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='ADMIN').update(is_staff=True, is_superuser=True)
    User.objects.exclude(role='ADMIN').filter(is_superuser=False).update(is_staff=False)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_accesstoken_options_and_more'),
    ]

    operations = [
        migrations.RunPython(sync_admin_permissions, noop),
    ]

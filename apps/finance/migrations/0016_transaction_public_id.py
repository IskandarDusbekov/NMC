import uuid

from django.db import migrations, models


def fill_transaction_public_ids(apps, schema_editor):
    Transaction = apps.get_model('finance', 'Transaction')
    for transaction in Transaction.objects.filter(public_id__isnull=True).iterator():
        transaction.public_id = uuid.uuid4()
        transaction.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_alter_exchangerate_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='public_id',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(fill_transaction_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='transaction',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

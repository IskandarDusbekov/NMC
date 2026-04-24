import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_alter_exchangerate_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

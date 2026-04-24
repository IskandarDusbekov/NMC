import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0005_alter_constructionobject_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='constructionobject',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name='workitem',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

import uuid

from django.db import migrations, models


def fill_object_public_ids(apps, schema_editor):
    ConstructionObject = apps.get_model('objects', 'ConstructionObject')
    WorkItem = apps.get_model('objects', 'WorkItem')

    for construction_object in ConstructionObject.objects.filter(public_id__isnull=True).iterator():
        construction_object.public_id = uuid.uuid4()
        construction_object.save(update_fields=['public_id'])

    for work_item in WorkItem.objects.filter(public_id__isnull=True).iterator():
        work_item.public_id = uuid.uuid4()
        work_item.save(update_fields=['public_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0005_alter_constructionobject_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='constructionobject',
            name='public_id',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='workitem',
            name='public_id',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(fill_object_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='constructionobject',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='workitem',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

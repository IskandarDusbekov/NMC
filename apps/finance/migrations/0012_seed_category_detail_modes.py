from django.db import migrations


def set_detail_modes(apps, schema_editor):
    transaction_category = apps.get_model('finance', 'TransactionCategory')
    material_names = {'Material', 'Qurilish materiali', 'Ish turi to`lovi'}
    food_names = {'Oziq-ovqat', 'Oziq ovqat', 'Obed', 'Non', 'Produkta'}
    fuel_names = {'Yoqilg`i', 'Yoqilgi', 'Transport', 'Texnika', 'Dizel'}

    for category in transaction_category.objects.all():
        normalized = category.name.strip()
        if normalized in material_names:
            category.detail_mode = 'MATERIAL'
        elif normalized in food_names:
            category.detail_mode = 'FOOD'
        elif normalized in fuel_names:
            category.detail_mode = 'FUEL'
        else:
            category.detail_mode = category.detail_mode or 'SIMPLE'
        category.save(update_fields=['detail_mode'])


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0011_transactioncategory_detail_mode'),
    ]

    operations = [
        migrations.RunPython(set_detail_modes, migrations.RunPython.noop),
    ]

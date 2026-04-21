from django.db import migrations


def seed_default_income_categories(apps, schema_editor):
    transaction_category = apps.get_model('finance', 'TransactionCategory')
    categories = [
        ('Investor mablag`i', 'Investor yoki owner mablag`i'),
        ('Buyurtmachidan tushum', 'Buyurtmachidan kelgan tushum'),
        ('Avans tushumi', 'Oldindan olingan to`lov'),
        ('Boshlang`ich mablag`', 'Company hisobiga boshlang`ich pul kiritish'),
        ('Boshqa kirim', 'Boshqa kirimlar'),
    ]
    for name, description in categories:
        transaction_category.objects.get_or_create(
            name=name,
            type='INCOME',
            defaults={
                'description': description,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0006_alter_transaction_entry_type'),
    ]

    operations = [
        migrations.RunPython(seed_default_income_categories, migrations.RunPython.noop),
    ]

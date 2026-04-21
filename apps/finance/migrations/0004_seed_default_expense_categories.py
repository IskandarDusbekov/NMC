from django.db import migrations


def seed_default_expense_categories(apps, schema_editor):
    transaction_category = apps.get_model('finance', 'TransactionCategory')
    categories = [
        ('Material', 'Qurilish materiallari'),
        ('Elektr energiya', 'Elektr energiya xarajatlari'),
        ('Yoqilg`i', 'Yoqilg`i va transport uchun sarf'),
        ('Oziq-ovqat', 'Obyekt yoki brigada oziq-ovqat xarajatlari'),
        ('Texnika', 'Texnika ijarasi yoki servis xarajatlari'),
        ('Ish turi to`lovi', 'Obyekt ichidagi ish turlariga berilgan to`lovlar'),
        ('Boshqa', 'Boshqa umumiy xarajatlar'),
    ]
    for name, description in categories:
        transaction_category.objects.get_or_create(
            name=name,
            type='EXPENSE',
            defaults={
                'description': description,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_alter_managertransfer_date_alter_transaction_date'),
    ]

    operations = [
        migrations.RunPython(seed_default_expense_categories, migrations.RunPython.noop),
    ]

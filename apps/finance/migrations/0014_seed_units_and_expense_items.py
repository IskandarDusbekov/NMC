from django.db import migrations


def seed_units_and_items(apps, schema_editor):
    measurement_unit = apps.get_model('finance', 'MeasurementUnit')
    transaction_category = apps.get_model('finance', 'TransactionCategory')
    expense_item = apps.get_model('finance', 'ExpenseItem')

    units = {
        'Kub metr': 'kub',
        'Metr': 'm',
        'Kilogram': 'kg',
        'Litr': 'l',
        'Qop': 'qop',
        'Dona': 'dona',
        'Kvadrat metr': 'm2',
    }
    unit_objects = {}
    for name, short_name in units.items():
        unit, _ = measurement_unit.objects.get_or_create(
            name=name,
            defaults={'short_name': short_name, 'is_active': True},
        )
        unit_objects[short_name] = unit

    defaults = {
        'Material': [
            ('Beton', 'kub'),
            ('Kabel', 'm'),
            ('Armatura', 'kg'),
            ('G`isht', 'dona'),
            ('Sement', 'qop'),
        ],
        'Oziq-ovqat': [
            ('Non', 'dona'),
            ('Kartoshka', 'qop'),
            ('Piyoz', 'qop'),
            ('Sabzi', 'qop'),
            ('Guruch', 'qop'),
            ('Mosh', 'kg'),
            ('Ziravor', ''),
        ],
        'Oziq ovqat': [
            ('Non', 'dona'),
            ('Kartoshka', 'qop'),
            ('Piyoz', 'qop'),
            ('Sabzi', 'qop'),
        ],
        'Yoqilg`i': [
            ('Dizel', 'l'),
            ('Benzin', 'l'),
            ('Gaz', ''),
        ],
        'Yoqilgi': [
            ('Dizel', 'l'),
            ('Benzin', 'l'),
            ('Gaz', ''),
        ],
        'Texnika': [
            ('JCB', ''),
            ('Tractor', ''),
            ('Mashinaga yoqilg`i', ''),
        ],
    }
    for category_name, item_rows in defaults.items():
        category = transaction_category.objects.filter(name=category_name).first()
        if not category:
            continue
        for item_name, unit_key in item_rows:
            expense_item.objects.get_or_create(
                category=category,
                name=item_name,
                defaults={'default_unit': unit_objects.get(unit_key), 'is_active': True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0013_measurementunit_expenseitem'),
    ]

    operations = [
        migrations.RunPython(seed_units_and_items, migrations.RunPython.noop),
    ]

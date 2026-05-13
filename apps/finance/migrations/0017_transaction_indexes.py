"""
Transaction jadvaliga tez-tez ishlatiladigan maydonlar uchun DB indekslari.
Bu migratsiya so'rov tezligini sezilarli darajada oshiradi.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0016_transaction_public_id'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['is_deleted', 'date'], name='tx_active_date_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['is_deleted', 'wallet_type'], name='tx_active_wallet_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['is_deleted', 'type'], name='tx_active_type_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['is_deleted', 'entry_type'], name='tx_active_entry_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['is_deleted', 'currency'], name='tx_active_currency_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(
                fields=['is_deleted', 'wallet_type', 'type', 'currency'],
                name='tx_balance_compound_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(
                fields=['is_deleted', 'date', 'type', 'currency'],
                name='tx_chart_compound_idx',
            ),
        ),
    ]

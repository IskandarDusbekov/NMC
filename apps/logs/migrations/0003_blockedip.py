from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0002_alter_auditlog_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlockedIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ip_address', models.GenericIPAddressField(unique=True)),
                ('failed_attempts', models.PositiveIntegerField(default=0)),
                ('window_started_at', models.DateTimeField(blank=True, null=True)),
                ('last_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('blocked_until', models.DateTimeField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'verbose_name': 'Bloklangan IP',
                'verbose_name_plural': 'Bloklangan IP lar',
                'ordering': ('-blocked_until', '-last_attempt_at'),
            },
        ),
    ]

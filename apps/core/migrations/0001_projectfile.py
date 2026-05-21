import uuid
import apps.core.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('objects', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=255, verbose_name='Sarlavha')),
                ('description', models.TextField(blank=True, verbose_name='Izoh')),
                ('category', models.CharField(
                    choices=[
                        ('contract', 'Shartnoma'), ('estimate', 'Smeta'),
                        ('permit', 'Ruxsatnoma'), ('photo', 'Foto'),
                        ('report', 'Hisobot'), ('invoice', 'Hisob-faktura'),
                        ('other', 'Boshqa'),
                    ],
                    default='other', max_length=20, verbose_name='Kategoriya',
                )),
                ('file', models.FileField(
                    upload_to=apps.core.models._file_upload_path,
                    validators=[apps.core.models._validate_project_file],
                    verbose_name='Fayl',
                )),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('file_size', models.PositiveIntegerField(default=0)),
                ('file_ext', models.CharField(blank=True, max_length=10)),
                ('object', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='files',
                    to='objects.constructionobject',
                    verbose_name='Obyekt',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_files',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Yuklagan',
                )),
            ],
            options={
                'verbose_name': 'Loyiha fayli',
                'verbose_name_plural': 'Loyiha fayllari',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='projectfile',
            index=models.Index(fields=['object', '-created_at'], name='pf_object_date_idx'),
        ),
        migrations.AddIndex(
            model_name='projectfile',
            index=models.Index(fields=['category', '-created_at'], name='pf_category_date_idx'),
        ),
        migrations.AddIndex(
            model_name='projectfile',
            index=models.Index(fields=['uploaded_by', '-created_at'], name='pf_uploader_date_idx'),
        ),
    ]

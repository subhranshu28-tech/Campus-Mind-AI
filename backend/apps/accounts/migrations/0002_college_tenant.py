from django.db import migrations, models
import django.db.models.deletion


def create_default_college(apps, schema_editor):
    College = apps.get_model('accounts', 'College')
    User = apps.get_model('accounts', 'User')
    college, _ = College.objects.get_or_create(
        slug='legacy-campus', defaults={'name': 'Legacy Campus', 'code': 'LEGACY'}
    )
    User.objects.filter(college__isnull=True).update(college=college)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel(name='College', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=180)),
            ('slug', models.SlugField(max_length=200, unique=True)),
            ('code', models.CharField(max_length=24, unique=True)),
            ('email', models.EmailField(blank=True, max_length=254)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ], options={'ordering': ['name']}),
        migrations.AddField(model_name='user', name='college', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='accounts.college')),
        migrations.RunPython(create_default_college, migrations.RunPython.noop),
    ]

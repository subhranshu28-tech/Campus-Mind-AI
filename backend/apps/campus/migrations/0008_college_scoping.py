from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_college(apps, schema_editor):
    College = apps.get_model('accounts', 'College')
    Department = apps.get_model('campus', 'Department')
    AcademicYear = apps.get_model('campus', 'AcademicYear')
    Classroom = apps.get_model('campus', 'Classroom')
    college, _ = College.objects.get_or_create(slug='legacy-campus', defaults={'name':'Legacy Campus','code':'LEGACY'})
    for Model in (Department, AcademicYear, Classroom):
        Model.objects.filter(college__isnull=True).update(college=college)


class Migration(migrations.Migration):
    dependencies = [('campus', '0007_previousyearquestionpaper'), ('accounts', '0002_college_tenant')]
    operations = [
        migrations.AddField(model_name='department', name='college', field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='departments', to='accounts.college')),
        migrations.AddField(model_name='academicyear', name='college', field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='academic_years', to='accounts.college')),
        migrations.AddField(model_name='classroom', name='college', field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='classrooms', to='accounts.college')),
        migrations.AlterField(model_name='department', name='name', field=models.CharField(max_length=120)),
        migrations.AlterField(model_name='department', name='code', field=models.CharField(max_length=12)),
        migrations.AlterField(model_name='academicyear', name='name', field=models.CharField(max_length=32)),
        migrations.AlterField(model_name='course', name='code', field=models.CharField(max_length=20)),
        migrations.AlterField(model_name='subject', name='code', field=models.CharField(max_length=20)),
        migrations.AlterField(model_name='classroom', name='code', field=models.CharField(max_length=20)),
        migrations.RemoveConstraint(model_name='academicyear', name='one_active_academic_year'),
        migrations.RunPython(assign_legacy_college, migrations.RunPython.noop),
        migrations.AlterField(model_name='department', name='college', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='departments', to='accounts.college')),
        migrations.AlterField(model_name='academicyear', name='college', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='academic_years', to='accounts.college')),
        migrations.AlterField(model_name='classroom', name='college', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='classrooms', to='accounts.college')),
        migrations.AddConstraint(model_name='course', constraint=models.UniqueConstraint(fields=('department','code'), name='unique_department_course_code')),
        migrations.AddConstraint(model_name='subject', constraint=models.UniqueConstraint(fields=('course','code'), name='unique_course_subject_code')),
        migrations.AddConstraint(model_name='department', constraint=models.UniqueConstraint(fields=('college','name'), name='uniq_college_department_name')),
        migrations.AddConstraint(model_name='department', constraint=models.UniqueConstraint(fields=('college','code'), name='uniq_college_department_code')),
        migrations.AddConstraint(model_name='academicyear', constraint=models.UniqueConstraint(fields=('college','name'), name='uniq_college_academic_year_name')),
        migrations.AddConstraint(model_name='academicyear', constraint=models.UniqueConstraint(condition=models.Q(is_active=True), fields=('college',), name='one_active_academic_year_per_college')),
        migrations.AddConstraint(model_name='classroom', constraint=models.UniqueConstraint(fields=('college','code'), name='uniq_college_classroom_code')),
    ]

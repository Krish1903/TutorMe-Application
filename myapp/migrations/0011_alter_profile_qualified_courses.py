# Generated by Django 4.0.3 on 2023-04-30 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0010_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='qualified_courses',
            field=models.ManyToManyField(blank=True, to='myapp.course'),
        ),
    ]

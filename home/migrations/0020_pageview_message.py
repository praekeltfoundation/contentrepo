# Generated by Django 4.0.6 on 2022-08-17 08:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0019_contentpage_related_pages'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageview',
            name='message',
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]

# Generated by Django 5.0.6 on 2024-06-14 18:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store_app', '0009_cart_total_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_intent_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
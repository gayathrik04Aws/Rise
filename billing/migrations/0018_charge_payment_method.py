# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_payment_method(apps, schema_editor):
    Charge = apps.get_model('billing', 'Charge')

    for charge in Charge.objects.all():
        if charge.vault_id is not None:
            charge.payment_method = 'C'
        else:
            charge.payment_method = 'M'
        charge.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0017_auto_20150129_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='charge',
            name='payment_method',
            field=models.CharField(default=b'M', max_length=1, choices=[(b'M', b'Manual'), (b'B', b'Bank Account'), (b'C', b'Card')]),
            preserve_default=True,
        ),
        migrations.RunPython(set_payment_method)
    ]

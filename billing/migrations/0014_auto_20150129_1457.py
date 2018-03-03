# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def migration_to_account_from_customer(apps, schema_editor):
    Card = apps.get_model('billing', 'Card')

    for card in Card.objects.all():
        card.account = card.customer.account
        card.save()

    Invoice = apps.get_model('billing', 'Invoice')

    for invoice in Invoice.objects.all():
        invoice.account = invoice.customer.account
        invoice.save()

    InvoiceLineItem = apps.get_model('billing', 'InvoiceLineItem')

    for invoice_line_item in InvoiceLineItem.objects.all():
        invoice_line_item.account = invoice_line_item.customer.account
        invoice_line_item.save()

    Subscription = apps.get_model('billing', 'Subscription')

    for subscription in Subscription.objects.all():
        subscription.account = subscription.customer.account
        subscription.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0044_auto_20150129_1334'),
        ('billing', '0013_bankaccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='account',
            field=models.OneToOneField(null=True, blank=True, to='accounts.Account'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='account',
            field=models.ForeignKey(blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoicelineitem',
            name='account',
            field=models.ForeignKey(blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='account',
            field=models.ForeignKey(null=True, blank=True, to='accounts.Account'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='account',
            field=models.OneToOneField(to='accounts.Account'),
            preserve_default=True,
        ),
        migrations.RunPython(migration_to_account_from_customer),
    ]

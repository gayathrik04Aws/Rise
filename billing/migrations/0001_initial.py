# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('last4', models.CharField(max_length=4)),
                ('brand', models.CharField(max_length=32)),
                ('exp_month', models.PositiveIntegerField()),
                ('exp_year', models.PositiveIntegerField()),
                ('fingerprint', models.CharField(max_length=64)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Charge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('amount', models.DecimalField(null=True, max_digits=10, decimal_places=2)),
                ('amount_refunded', models.DecimalField(null=True, max_digits=10, decimal_places=2)),
                ('description', models.CharField(max_length=256, null=True, blank=True)),
                ('captured', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('disputed', models.BooleanField(default=False)),
                ('refunded', models.BooleanField(default=False)),
                ('failure_code', models.CharField(max_length=64, null=True, blank=True)),
                ('failure_message', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField()),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.Card', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('delinquent', models.BooleanField(default=False)),
                ('account_balance', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('account', models.OneToOneField(to='accounts.Account')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('amount_due', models.DecimalField(max_digits=10, decimal_places=2)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('attempted', models.BooleanField(default=False)),
                ('closed', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('forgiven', models.BooleanField(default=False)),
                ('period_start', models.DateTimeField(null=True, blank=True)),
                ('period_end', models.DateTimeField(null=True, blank=True)),
                ('subtotal', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('total', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('description', models.CharField(max_length=256, null=True, blank=True)),
                ('next_payment_attempt', models.DateTimeField(null=True, blank=True)),
                ('charge', models.ForeignKey(related_name=b'invoice_charges', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.Charge', null=True)),
                ('customer', models.ForeignKey(to='billing.Customer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceLineItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('proration', models.BooleanField(default=False)),
                ('description', models.CharField(max_length=256)),
                ('customer', models.ForeignKey(to='billing.Customer')),
                ('invoice', models.ForeignKey(blank=True, to='billing.Invoice', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('interval', models.CharField(default=b'month', max_length=16, choices=[(b'day', b'Daily'), (b'week', b'Weekly'), (b'month', b'Monthly'), (b'year', b'Yearly')])),
                ('interval_count', models.PositiveIntegerField(default=1)),
                ('reservations', models.PositiveIntegerField(default=1)),
                ('companion_passes', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('status', models.CharField(default=b'active', max_length=16, choices=[(b'trialing', b'Trial'), (b'active', b'Acitve'), (b'past_due', b'Past Due'), (b'canceled', b'Cancelled'), (b'unpaid', b'Unpaid')])),
                ('customer', models.ForeignKey(to='billing.Customer')),
                ('plan', models.ForeignKey(to='billing.Plan')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name=b'charges', to='billing.Customer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='invoice',
            field=models.ForeignKey(related_name=b'charges', on_delete=django.db.models.deletion.SET_NULL, to='billing.Invoice', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='card',
            name='customer',
            field=models.ForeignKey(to='billing.Customer'),
            preserve_default=True,
        ),
    ]

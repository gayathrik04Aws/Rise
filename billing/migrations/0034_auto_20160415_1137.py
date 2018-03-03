# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

from django.db import migrations, models
from django.db.models import Q

def add_contracts(apps, schema_editor):
        contracts = apps.get_model("billing", "PlanContractPrice")
        plans = apps.get_model("billing", "Plan")
        for plan in plans.objects.filter(anywhere_only=False).all():
            if plan.name == 'Express':
                contract=contracts()
                contract.plan=plan
                contract.contract_length=3
                contract.selectable=True
                contract.amount=2350
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=6
                contract.selectable=True
                contract.amount=2200
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=12
                contract.selectable=True
                contract.amount=1850
                contract.save()
            if plan.name == 'Executive':
                contract=contracts()
                contract.plan=plan
                contract.contract_length=3
                contract.selectable=True
                contract.amount=2850
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=6
                contract.selectable=True
                contract.amount=2700
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=12
                contract.selectable=True
                contract.amount=2350
                contract.save()
            if plan.name == 'Chairman':
                contract=contracts()
                contract.plan=plan
                contract.contract_length=3
                contract.selectable=True
                contract.amount=3350
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=6
                contract.selectable=True
                contract.amount=3200
                contract.save()
                contract=contracts()
                contract.plan=plan
                contract.contract_length=12
                contract.selectable=True
                contract.amount=2850
                contract.save()

def create_default_account_contracts(apps, schema_editor):
    contracts = apps.get_model("billing", "PlanContractPrice")
    plans = apps.get_model("billing", "Plan")
    accounts = apps.get_model("accounts", "Account")
    now = datetime.date.today()
    statuses = ['C','S']
    regularplans = ['Express', 'Executive', 'Chairman']
    # accts that are suspended or cancelled will need to be set up when they reactivate.
    for acct in accounts.objects.exclude(status__in=statuses).exclude(account_type='C'):
        plan=acct.plan
        if acct.plan and next((x for x in regularplans if x == acct.plan.name), None):
            contract = contracts.objects.filter(Q(plan_id=plan.id) & Q(contract_length=12)).first()
            acct.contract = contract
            if acct.contract:
                if acct.activated:
                    delta = now - acct.activated.date()
                    if delta.days > 365:
                        acct.contract_start_date = now
                    else:
                        acct.contract_start_date = acct.activated
                else:
                    acct.contract_start_date = now
                acct.contract_end_date = acct.contract_start_date + datetime.timedelta(days=365)
                acct.save()
            else:
                acct.contract = None
                acct.contract_end_date = None
                acct.contract_start_date = None
                acct.save()
        else: #plan does not have a contract
            acct.contract = None
            acct.contract_end_date = None
            acct.contract_start_date = None
            acct.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0033_plancontractprice'),
        ('accounts','0057_auto_20160415_1135')
    ]

    operations = [
                migrations.RunPython(add_contracts),
                migrations.RunPython(create_default_account_contracts)

    ]

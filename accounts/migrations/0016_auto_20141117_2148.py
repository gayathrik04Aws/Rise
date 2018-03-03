# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def create_roles(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    admin, created = Group.objects.get_or_create(name='Admin')

    pilot, created = Group.objects.get_or_create(name='Pilot')
    permissions = Permission.objects.filter(codename__in=('can_view_flights', 'can_update_flights', 'can_view_members'))
    pilot.permissions.add(*permissions)

    concierge, created = Group.objects.get_or_create(name='Concierge')
    permissions = Permission.objects.filter(codename__in=('can_view_flights', 'can_update_flights', 'can_view_members', 'can_edit_members', 'can_book_members'))
    concierge.permissions.add(*permissions)

    support, created = Group.objects.get_or_create(name='Support')
    permissions = Permission.objects.filter(codename__in=('can_view_flights', 'can_update_flights', 'can_view_members', 'can_edit_members', 'can_book_members'))
    support.permissions.add(*permissions)

    companion, created = Group.objects.get_or_create(name='Companion')
    permissions = Permission.objects.filter(codename__in=('can_fly',))
    companion.permissions.add(*permissions)

    individual_admin, created = Group.objects.get_or_create(name='Individual Account Admin')
    permissions = Permission.objects.filter(codename__in=('can_manage_companions', 'can_fly', 'can_manage_plan', 'can_manage_billing', 'can_mange_invites', 'can_book_flights', 'can_book_promo_flights', 'can_buy_companion_passes', 'can_buy_passes'))
    individual_admin.permissions.add(*permissions)

    corporate_admin, created = Group.objects.get_or_create(name='Corporate Account Admin')
    permissions = Permission.objects.filter(codename__in=('can_manage_team', 'can_fly', 'can_manage_plan', 'can_manage_billing', 'can_book_flights', 'can_book_promo_flights', 'can_buy_companion_passes', 'can_buy_passes', 'can_book_team'))
    corporate_admin.permissions.add(*permissions)

    coordinator, created = Group.objects.get_or_create(name='Coordinator')
    permissions = Permission.objects.filter(codename__in=('can_manage_team', 'can_book_flights', 'can_book_promo_flights', 'can_buy_companion_passes', 'can_buy_passes', 'can_book_team'))
    coordinator.permissions.add(*permissions)

    account_member, created = Group.objects.get_or_create(name='Account Member')
    permissions = Permission.objects.filter(codename__in=('can_fly', 'can_book_flights',))
    account_member.permissions.add(*permissions)

    non_member, created = Group.objects.get_or_create(name='Non-Member')
    permissions = Permission.objects.filter(codename__in=('can_fly',))
    non_member.permissions.add(*permissions)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_auto_20141117_2148'),
    ]

    operations = [
        migrations.RunPython(create_roles),
    ]

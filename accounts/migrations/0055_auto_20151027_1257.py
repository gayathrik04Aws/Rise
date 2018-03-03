# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0054_auto_20151013_1357'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': (('can_manage_companions', 'Can manage companions'), ('can_manage_team', 'Can manage team members for corporations'), ('can_manage_plan', 'Can manage account plan'), ('can_manage_billing', 'Can manage account billing information'), ('can_mange_invites', 'Can manage account invites'), ('can_fly', 'User can fly on flights'), ('can_book_flights', 'User can book their own flights'), ('can_book_team', 'User can book on behalf of other account users'), ('can_book_promo_flights', 'User can book their own promo flights'), ('can_buy_companion_passes', 'User can purchase companion passes'), ('can_buy_passes', 'User can purchase additional save my seat passes'), ('can_view_flights', 'Admin user can view flights'), ('can_update_flights', 'Admin user can update flight details'), ('can_edit_flights', 'Admin user can create or edit flights'), ('can_edit_flights_limited', 'Admin user can create or edit limited flight data'), ('can_view_members', 'Admin user can view member profile details'), ('can_edit_members', 'Admin user can edit member profile details'), ('can_book_members', 'Admin user can book flights on behalf of members'), ('can_charge_members', "Admin user can make charges to a member's account"), ('can_background_check', 'Admin user can do background checks'), ('can_edit_account_status', 'Rise Admin user can edit account status'), ('can_merge_accounts', 'Rise Admin user can merge accounts'), ('can_reset_user_password', "Rise Admin user can reset a user's password."), ('can_edit_user_role', "Rise Admin user can edit a user's role."), ('can_edit_account_price', 'Rise Admin user can edit account price.'), ('can_manage_staff', 'Super Admin user can manage staff'), ('can_view_reports', 'Admin can view reports'), ('can_manage_announcements', 'Rise Admin user can manage announcements'))},
        ),
    ]

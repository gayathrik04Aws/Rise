# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_auto_20141229_1456'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': (('can_manage_companions', 'Can manage companions'), ('can_manage_team', 'Can manage team members for corporations'), ('can_manage_plan', 'Can manage account plan'), ('can_manage_billing', 'Can manage account billing information'), ('can_mange_invites', 'Can manage account invites'), ('can_fly', 'User can fly on flights'), ('can_book_flights', 'User can book their own flights'), ('can_book_team', 'User can book on behalf of other account users'), ('can_book_promo_flights', 'User can book their own promo flights'), ('can_buy_companion_passes', 'User can purchase companion passes'), ('can_buy_passes', 'User can purchase additional save my seat passes'), ('can_view_flights', 'Admin user can view flights'), ('can_update_flights', 'Admin user can update flight details'), ('can_edit_flights', 'Admin user can create or edit flights'), ('can_edit_flights_limited', 'Admin user can create or edit limited flight data'), ('can_view_members', 'Admin user can view member profile details'), ('can_edit_members', 'Admin user can edit member profile details'), ('can_book_members', 'Admin user can book flights on behalf of members'), ('can_background_check', 'Admin user can do background checks'), ('can_suspend_accounts', 'Rise Admin user can suspend accounts'), ('can_reset_passwords', "Rise Admin user can reset a user's password."), ('can_change_user_role', "Rise Admin user can change a user's role."), ('can_change_price', 'Rise Admin user can change price.'), ('can_change_member_tier', "Rise Admin user can change a member's tier."))},
        ),
    ]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Account, User, UserProfile, Invite, City, WaitList, Address, FoodOption, UserNote
from .admin_forms import CustomUserChangeForm, CustomUserCreationForm


class UserInline(admin.TabularInline):
    model = User


class UserProfileInline(admin.TabularInline):
    model = UserProfile


class AddressInline(admin.TabularInline):
    model = Address


class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'account_type')

admin.site.register(Account, AccountAdmin)
#
# class UserProfileAdmin(admin.ModelAdmin):
#     search_fields = ('email', 'last_name')
#     list_display= ('email','first_name','last_name')
#     fieldsets = (
#         ('Personal info', {'fields': ('title','first_name','last_name','date_of_birth','weight','allergies')}),
#         ('Contact info', {'fields': ('email','phone','mobile_phone','billing_address_id','shipping_address_id')}),
#         ('Other', {'fields': ('background_status')}),
#         ('Preferences', {'fields': ('origin_airport_id')})
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('first_name',  'last_name', 'phone', 'mobile_phone','email', 'date_of_birth','weight','allergies'),
#         }),
#     )
#     ordering = ('last_name', )
#     inlines = (UserInline,)
#
# admin.site.register(UserProfile, UserProfileAdmin)


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password', 'account')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email', )
    # inlines = (UserProfileInline,)

admin.site.register(User, UserAdmin)


class InviteAdmin(admin.ModelAdmin):
    list_display = ('code', 'email', 'redeemed')
    list_filter = ('redeemed',)
    search_fields = ('code', 'email',)
    raw_id_fields = ('account', 'created_by', 'redeemed_by',)

admin.site.register(Invite, InviteAdmin)


class CityAdmin(admin.ModelAdmin):
    pass

admin.site.register(City, CityAdmin)


class WaitListAdmin(admin.ModelAdmin):
    pass

admin.site.register(WaitList, WaitListAdmin)


class FoodOptionAdmin(admin.ModelAdmin):
    pass

admin.site.register(FoodOption, FoodOptionAdmin)


class AddressAdmin(admin.ModelAdmin):
    pass

admin.site.register(Address, AddressAdmin)


class UserNoteAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserNote, UserNoteAdmin)

from django.contrib import admin

from .models import Card, Charge, Plan, Subscription, Invoice, InvoiceLineItem, ChargeRefund, BankAccount


class CardInline(admin.TabularInline):
    model = Card
    extra = 0

admin.site.register(Card)


class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 0

admin.site.register(BankAccount)


class ChargeRefundInline(admin.TabularInline):
    model = ChargeRefund
    extra = 0


class ChargeAdmin(admin.ModelAdmin):
    inlines = (ChargeRefundInline,)
    list_display = ('amount', 'created')

admin.site.register(Charge, ChargeAdmin)


class ChargeInline(admin.TabularInline):
    model = Charge
    extra = 0


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0


class PlanAdmin(admin.ModelAdmin):
    pass

admin.site.register(Plan, PlanAdmin)


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


class InvoiceAdmin(admin.ModelAdmin):
    inlines = (InvoiceLineItemInline,)

admin.site.register(Invoice, InvoiceAdmin)


class InvoiceLineItemAdmin(admin.ModelAdmin):
    pass

admin.site.register(InvoiceLineItem, InvoiceLineItemAdmin)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('account', 'created')

admin.site.register(Subscription, SubscriptionAdmin)

from django.contrib import admin
from .models import Goal, Transaction, RecurringItem

@admin.register(RecurringItem)
class RecurringItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'frequency_type', 'user', 'start_date')
    list_filter = ('frequency_type', 'user')

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'target_amount', 'deadline', 'is_active')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'user', 'date')
    list_filter = ('user', 'date')

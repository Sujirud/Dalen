from django.contrib import admin
from .models import Goal, Transaction, RecurringItem, Category

@admin.register(RecurringItem)
class RecurringItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'amount', 'frequency_type', 'start_date', 'interval_days', 'end_date')
    list_filter = ('frequency_type', 'user')

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'target_amount', 'created_at', 'deadline', 'is_active')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'amount', 'date')
    list_filter = ('user', 'date')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'icon')

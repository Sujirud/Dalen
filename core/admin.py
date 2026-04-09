from django.contrib import admin

from .models import RecurringItem, Category, Transaction, SavingGoal, CategoryLimit


@admin.register(RecurringItem)
class RecurringItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'amount', 'frequency_type', 'start_date', 'interval_days', 'end_date')
    list_filter = ('user', 'frequency_type')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'icon')
    list_filter = ('user',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'category', 'amount', 'date')
    list_filter = ('user', 'date')

@admin.register(SavingGoal)
class SavingGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'target_amount', 'created_at', 'deadline', 'is_active')
    list_filter = ('user', 'is_active', 'deadline')

@admin.register(CategoryLimit)
class CategoryLimitAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'limit_amount', 'created_at')
    list_filter = ('user',)

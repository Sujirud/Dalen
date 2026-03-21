from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    theme = models.CharField(max_length=10, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    currency_symbol = models.CharField(max_length=5, default='$')
    timezone = models.CharField(max_length=63, default='UTC')

    def __str__(self):
        return f"{self.user.username}'s Profile"

class RecurringItem(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('custom', 'Custom Interval'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    frequency_type = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    start_date = models.DateField()
    interval_days = models.IntegerField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_frequency_type_display()})"

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    target_amount = models.DecimalField(max_digits=19, decimal_places=2)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=19, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=200)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} : {self.amount}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create UserProfile
        UserProfile.objects.get_or_create(user=instance)

        # Create Default Categories
        default_categories = [
            {'name': 'Food & Dining', 'icon': 'fork-knife'},
            {'name': 'Transportation', 'icon': 'car'},
            {'name': 'Housing', 'icon': 'house-line'},
            {'name': 'Utilities', 'icon': 'lightning'},
            {'name': 'Shopping', 'icon': 'shopping-cart-simple'},
            {'name': 'Entertainment', 'icon': 'film-strip'},
            {'name': 'Health & Medical', 'icon': 'first-aid'},
            {'name': 'Education', 'icon': 'book-open'},
            {'name': 'Personal Care', 'icon': 'sparkle'},
            {'name': 'Bills & Fees', 'icon': 'receipt'},
            {'name': 'Income', 'icon': 'coins'},
            {'name': 'Salary', 'icon': 'wallet'},
            {'name': 'Business', 'icon': 'storefront'},
        ]

        Category.objects.bulk_create([
            Category(user=instance, name=cat['name'], icon=cat['icon'])
            for cat in default_categories
        ])

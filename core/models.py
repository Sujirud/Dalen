from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    theme = models.CharField(max_length=10, default='dark', choices=[('light', 'Light'), ('dark', 'Dark')])
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

class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50)
    icon_color = models.CharField(max_length=7)

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

class BaseObjective(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class SavingGoal(BaseObjective):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    icon_color = models.CharField(max_length=7)
    target_amount = models.DecimalField(max_digits=19, decimal_places=2)
    deadline = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class CategoryLimit(BaseObjective):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='category_limits',)
    limit_amount = models.DecimalField(max_digits=19, decimal_places=2)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.category.name} limit: {self.limit_amount}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create UserProfile
        UserProfile.objects.get_or_create(user=instance)

        # Create Default Categories
        default_categories = [
            {'name': 'Food & Dining', 'icon': 'fork-knife', 'color': '#DF1242'},
            {'name': 'Transportation', 'icon': 'car', 'color': '#40AAFF'},
            {'name': 'Housing', 'icon': 'house-line', 'color': '#FFB880'},
            {'name': 'Utilities', 'icon': 'lightning', 'color': '#FFF231'},
            {'name': 'Shopping', 'icon': 'shopping-cart-simple', 'color': '#FF5ED7'},
            {'name': 'Entertainment', 'icon': 'film-strip', 'color': '#C68DFF'},
            {'name': 'Health & Medical', 'icon': 'first-aid', 'color': '#FF1B1B'},
            {'name': 'Education', 'icon': 'book-open', 'color': '#14C8FF'},
            {'name': 'Personal Care', 'icon': 'sparkle', 'color': '#FFBFDB'},
            {'name': 'Bills & Fees', 'icon': 'receipt', 'color': '#FF9440'},
            {'name': 'Income', 'icon': 'coins', 'color': '#DFD42B'},
            {'name': 'Salary', 'icon': 'wallet', 'color': '#6BDF58'},
            {'name': 'Business', 'icon': 'storefront', 'color': '#5E86FF'},
        ]

        Category.objects.bulk_create([
            Category(user=instance, name=cat['name'], icon=cat['icon'], icon_color=cat['color'])
            for cat in default_categories
        ])

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone as django_timezone
from .models import UserProfile, Goal, Transaction, RecurringItem, Category
from .services import FinancialGPS
from datetime import timedelta, datetime
from decimal import Decimal
import json
import zoneinfo

CURRENCIES = {
    'د.إ': ['AED'],
    'AR$': ['ARS'],
    '$': ['AUD', 'CAD', 'NZD', 'SGD', 'USD'],
    'KM': ['BAM'],
    '৳': ['BDT'],
    'BGN': ['BGN'],
    '.د.ب': ['BHD'],
    'Bs.': ['BOB'],
    'R$': ['BRL'],
    'CHF': ['CHF'],
    'CL$': ['CLP'],
    '¥': ['CNY', 'JPY'],
    'CO$': ['COP'],
    'Kč': ['CZK'],
    'kr': ['DKK', 'ISK', 'NOK', 'SEK'],
    'E£': ['EGP'],
    '€': ['EUR'],
    '£': ['GBP'],
    'GH₵': ['GHS'],
    'HK$': ['HKD'],
    'Ft': ['HUF'],
    'Rp': ['IDR'],
    '₪': ['ILS'],
    '₹': ['INR'],
    'ع.د': ['IQD'],
    'د.ا': ['JOD'],
    'KSh': ['KES'],
    '៛': ['KHR'],
    '₩': ['KRW'],
    'د.ك': ['KWD'],
    '₭': ['LAK'],
    'ل.ل': ['LBP'],
    'Rs': ['LKR', 'PKR'],
    'MAD': ['MAD'],
    'K': ['MMK'],
    '₮': ['MNT'],
    'MOP$': ['MOP'],
    'MX$': ['MXN'],
    'RM': ['MYR'],
    '₦': ['NGN'],
    'रू': ['NPR'],
    'ر.ع.': ['OMR'],
    'S/': ['PEN'],
    '₱': ['PHP'],
    'zł': ['PLN'],
    '₲': ['PYG'],
    'ر.ق': ['QAR'],
    'lei': ['RON'],
    'дин.': ['RSD'],
    '₽': ['RUB'],
    '﷼': ['SAR'],
    '฿': ['THB'],
    '₺': ['TRY'],
    'NT$': ['TWD'],
    'TSh': ['TZS'],
    '₴': ['UAH'],
    'USh': ['UGX'],
    '$U': ['UYU'],
    '₫': ['VND'],
    'ZAR': ['ZAR']
}

ICON_CHOICES = [
    # General & Finance
    ('flag', 'Objective'),
    ('coins', 'Coins'),
    ('money', 'Cash'),
    ('credit-card', 'Credit Card'),
    ('receipt', 'Bills'),
    ('wallet', 'Wallet'),
    ('piggy-bank', 'Savings'),
    ('vault', 'Vault'),
    ('bank', 'Bank'),
    ('chart-bar', 'Investment'),
    ('shield-check', 'Insurance'),

    # Travel
    ('airplane-tilt', 'Travel'),
    ('backpack', 'Backpack'),
    ('suitcase-rolling', 'Luggage'),
    ('building', 'Hotel'),
    ('tent', 'Camping'),
    ('island', 'Island'),

    # Food & Dining
    ('shopping-cart-simple', 'Shopping'),
    ('fork-knife', 'Food'),
    ('gift', 'Gifts'),
    ('cake', 'Celebration'),
    ('storefront', 'Store'),

    # Home & Family
    ('house-line', 'House'),
    ('armchair', 'Furniture'),
    ('paint-roller', 'Renovation'),
    ('heart', 'Relationship'),
    ('paw-print', 'Pets'),
    ('baby-carriage', 'Kids'),
    ('person', 'Person'),

    # Education & Career
    ('books', 'Books'),
    ('certificate', 'Certificate'),
    ('graduation-cap', 'Education'),
    ('briefcase', 'Business'),

    # Hobbies & Entertainment
    ('ticket', 'Events'),
    ('palette', 'Art'),
    ('music-notes', 'Music'),
    ('game-controller', 'Gaming'),
    ('barbell', 'Gym'),

    # Gadgets & Tech
    ('t-shirt', 'Shirt'),
    ('pants', 'Pants'),
    ('sneaker', 'Shoes'),
    ('watch', 'Watch'),
    ('headphones', 'Headphones'),
    ('camera', 'Photography'),
    ('device-mobile', 'Smartphone'),
    ('laptop', 'Laptop'),
    ('desktop', 'Desktop'),
    ('television', 'TV'),

    # Vehicles
    ('bicycle', 'Bicycle'),
    ('motorcycle', 'Motorcycle'),
    ('car', 'Car'),
    ('wrench', 'Maintenance'),

    # Health & Emergency
    ('warning-octagon', 'Emergency Fund'),
    ('first-aid', 'Medical'),
    ('heartbeat', 'Health'),
]

# --- HELPERS ---

def _get_today(user):
    """Returns the current date in the user's configured timezone."""
    user_tz = zoneinfo.ZoneInfo(user.userprofile.timezone)
    return django_timezone.now().astimezone(user_tz).date()

# --- PUBLIC VIEWS ---

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) 
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

# --- PROTECTED VIEWS ---

@login_required
def dashboard(request):
    today_date = _get_today(request.user).strftime("%A, %B %d")

    user_tz = zoneinfo.ZoneInfo(request.user.userprofile.timezone)
    local_hour = django_timezone.now().astimezone(user_tz).hour

    if local_hour < 12:
        greeting = "Good morning"
    elif local_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    gps = FinancialGPS(request.user)
    data = gps.get_status()

    chart_data = gps.get_chart_data(days=30)
    chart_data_json = json.dumps(chart_data) if chart_data else None

    recent_transactions = Transaction.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')[:5]

    context = {
        'base_template': 'core/base_partial.html' if request.htmx else 'core/base.html',
        'page_title': 'Dashboard | Dalen',
        'today_date': today_date,
        'greeting': greeting,
        'data': data,
        'chart_data': chart_data_json,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'core/dashboard.html', context)

@login_required
def transactions(request):
    transactions = Transaction.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')

    context = {
        'base_template': 'core/base_partial.html' if request.htmx else 'core/base.html',
        'page_title': 'Transactions | Dalen',
        'transactions': transactions,
    }

    return render(request, 'core/transactions.html', context)

@login_required
def planning(request):
    user = request.user

    current_goal = Goal.objects.filter(user=user, is_active=True).first()
    completed_goals = Goal.objects.filter(user=user, is_active=False).order_by('-deadline')
    recurring_items = RecurringItem.objects.filter(user=user).order_by('start_date')
    today = _get_today(user)

    if request.method == 'POST':
        action = request.POST.get('action')

        # --- RECURRING ITEM DELETE LOGIC ---
        if action == 'delete_recurring':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(RecurringItem, id=item_id, user=user)
            item.delete()
            messages.success(request, "Item removed.")
            return redirect('planning')

        # --- RECURRING ITEM CREATE LOGIC ---
        elif action == 'create_recurring':
            try:
                rec_name = request.POST.get('rec_name')
                rec_amount = Decimal(request.POST.get('rec_amount', 0))
                rec_type = request.POST.get('rec_type')
                freq_type = request.POST.get('frequency_type')

                if rec_type == 'expense':
                    rec_amount = -abs(rec_amount)
                else:
                    rec_amount = abs(rec_amount)

                start_date_str = request.POST.get('start_date_custom')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

                end_date_str = request.POST.get('end_date_custom')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

                interval = None
                if freq_type == 'custom':
                    interval_raw = request.POST.get('interval_days')
                    interval = int(interval_raw) if interval_raw else 0
                    if interval <= 0:
                        messages.error(request, "Interval must be at least 1 day.")
                        return redirect('planning')

                RecurringItem.objects.create(
                    user=user,
                    name=rec_name,
                    amount=rec_amount,
                    frequency_type=freq_type,
                    start_date=start_date,
                    end_date=end_date,
                    interval_days=interval
                )
                messages.success(request, "Recurring item added.")
                return redirect('planning')
            except Exception:
                messages.error(request, "Error adding item.")

        # --- GOAL SETUP LOGIC ---
        else: 
            try:
                goal_name = request.POST.get('goal_name')
                goal_icon = request.POST.get('goal_icon')
                target_amount = Decimal(request.POST.get('goal_amount', 0))
                deadline_str = request.POST.get('deadline')
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

                if current_goal:
                    # Update existing goal
                    current_goal.name = goal_name
                    current_goal.icon = goal_icon
                    current_goal.target_amount = target_amount
                    current_goal.deadline = deadline
                    current_goal.save()
                    messages.success(request, "Goal updated successfully.")
                else:
                    # Create new goal
                    Goal.objects.create(
                        user=user,
                        name=goal_name,
                        icon=goal_icon,
                        target_amount=target_amount,
                        deadline=deadline
                    )
                    messages.success(request, "New goal created!")

                return redirect('planning')
            except ValueError:
                messages.error(request, "Invalid input. Please check your numbers.")

    min_date = today + timedelta(days=1)

    context = {
        'base_template': 'core/base_partial.html' if request.htmx else 'core/base.html',
        'page_title': 'Planning | Dalen',
        'current_goal': current_goal,
        'completed_goals': completed_goals,
        'recurring_items': recurring_items, 
        'min_date': min_date,
        'icon_choices': ICON_CHOICES
    }

    return render(request, 'core/planning.html', context)

@login_required
def delete_goal(request):
    if request.method == 'POST':
        Goal.objects.filter(user=request.user, is_active=True).delete()
    return redirect('planning')

@login_required
def settings(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    password_form = PasswordChangeForm(user)
    available_timezones = sorted(list(zoneinfo.available_timezones()))

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_username':
            new_username = request.POST.get('username', '').strip()

            if not new_username:
                messages.error(request, "Username cannot be empty.")

            elif User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                messages.error(request, "This username is already taken. Please choose another one.")

            else:
                user.username = new_username
                user.save()
                messages.success(request, "Username updated successfully.")

            return redirect('settings')

        elif action == 'change_password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed.")
                return redirect('settings')

        elif action == 'update_theme':
            profile.theme = request.POST.get('theme')
            profile.save()
            return redirect('settings')

        elif action == 'update_currency-symbol':
            profile.currency_symbol = request.POST.get('currency_symbol')
            profile.save()
            messages.success(request, "Currency symbol updated.")
            return redirect('settings')

        elif action == 'update_timezone':
            tz = request.POST.get('timezone')
            if tz in available_timezones:
                profile.timezone = tz
                profile.save()
                messages.success(request, "Time zone updated.")
            return redirect('settings')

    context = {
        'base_template': 'core/base_partial.html' if request.htmx else 'core/base.html',
        'page_title': 'Setting | Dalen',
        'profile': profile,
        'password_form': password_form,
        'timezones': available_timezones,
        'currencies': CURRENCIES
    }

    return render(request, 'core/settings.html', context)

@login_required
def add_transaction(request):
    today = _get_today(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        # --- CATEGORY MANAGEMENT LOGIC ---
        if action == 'add_category':
            cat_name = request.POST.get('category_name')
            cat_icon = request.POST.get('category_icon')
            if cat_name and cat_icon:
                Category.objects.create(user=request.user, name=cat_name, icon=cat_icon)
                messages.success(request, f"Category '{cat_name}' added.")
            return redirect('add_transaction')

        elif action == 'delete_category':
            cat_id = request.POST.get('category_id')
            Category.objects.filter(user=request.user, id=cat_id).delete()
            messages.success(request, "Category deleted.")
            return redirect('add_transaction')

        # --- TRANSACTION LOGIC ---
        # Handles receipt upload
        images = request.FILES.getlist('receipt_images')
        if images:
            count = len(images)
            total_cost = Decimal('100.00') * count * Decimal(-1)
            Transaction.objects.create(
                user=request.user,
                amount=total_cost,
                description=f"Scanned Receipt ({count} items)",
                date=today
            )
            messages.success(request, f"Processed {count} receipts!")
            return redirect('dashboard')

        # Handles manual entry
        try:
            amount_val = request.POST.get('amount')
            trans_type = request.POST.get('type')
            description = request.POST.get('description')
            date_val = request.POST.get('txn_date')
            category_id = request.POST.get('category')

            if amount_val:
                amount = Decimal(amount_val)
                final_amount = amount if trans_type == 'income' else -abs(amount)

                # Parse Date or Default to Today
                if date_val:
                    txn_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                else:
                    txn_date = today

                # Fetch selected category
                category = Category.objects.filter(id=category_id, user=request.user).first() if category_id else None

                Transaction.objects.create(
                    user=request.user,
                    amount=final_amount,
                    description=description,
                    date=txn_date,
                    category=category
                )
                messages.success(request, "Transaction added.")
                redirect('add_transaction')
        except Exception as e:
            print(e)
            messages.error(request, "Error adding transaction.")

    categories = Category.objects.filter(user=request.user)

    context = {
        'base_template': 'core/base_partial.html' if request.htmx else 'core/base.html',
        'page_title': 'Transaction | Dalen',
        'categories': categories,
        'icon_choices': ICON_CHOICES,
    }

    return render(request, 'core/add_transaction.html', context)

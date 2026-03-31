import json
import zoneinfo
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as django_timezone
from django.views.decorators.http import require_POST

from .constants import CURRENCIES, ICON_CHOICES
from .models import Category, Goal, RecurringItem, Transaction, UserProfile
from .services import FinancialGPS

# ==========================================
# HELPERS
# ==========================================

def _get_today(user):
    """Returns the current date in the user's configured timezone."""
    user_tz = zoneinfo.ZoneInfo(user.userprofile.timezone)
    return django_timezone.now().astimezone(user_tz).date()

# ==========================================
# AUTH & PUBLIC VIEWS
# ==========================================

class NoAutofocusUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.pop('autofocus', None)

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = NoAutofocusUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = NoAutofocusUserCreationForm()

    return render(request, 'core/landing.html', {'form': form})


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

# ==========================================
# DASHBOARD VIEW
# ==========================================

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

# ==========================================
# TRANSACTIONS & CATEGORIES VIEWS
# ==========================================

@login_required
def transactions(request):
    txn_list = Transaction.objects.filter(user=request.user).select_related('category').order_by('-date', '-created_at')
    categories = Category.objects.filter(user=request.user)

    # Filtering
    search_query = request.GET.get('search', '').strip()
    category_ids = request.GET.getlist('categories')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if search_query:
        txn_list = txn_list.filter(description__icontains=search_query)
    if category_ids:
        txn_list = txn_list.filter(category__id__in=category_ids)
    if start_date:
        txn_list = txn_list.filter(date__gte=start_date)
    if end_date:
        txn_list = txn_list.filter(date__lte=end_date)

    # Determine if any filters are applied for UI purposes
    filters_applied = any([search_query, category_ids, start_date, end_date])

    # Pagination
    paginator = Paginator(txn_list, 20)
    page_number = request.GET.get('page', 1)
    transactions_page = paginator.get_page(page_number)
    last_date = request.GET.get('last_date')

    # Construct load more URL for HTMX
    load_more_url = None
    if transactions_page.has_next():
        last_txn = list(transactions_page.object_list)[-1]

        query_params = {
            'page': transactions_page.next_page_number(),
            'last_date': last_txn.date.strftime('%Y-%m-%d'),
        }

        if search_query:
            query_params['search'] = search_query
        if category_ids:
            query_params['categories'] = category_ids 
        if start_date:
            query_params['start_date'] = start_date
        if end_date:
            query_params['end_date'] = end_date

        base_url = reverse('transactions')
        query_string = urlencode(query_params, doseq=True)
        load_more_url = f"{base_url}?{query_string}"

    context = {
        'page_title': 'Transactions | Dalen',
        'transactions': transactions_page,
        'last_date': last_date,
        'categories': categories,
        'load_more_url': load_more_url,
        'filters_applied': filters_applied
    }

    is_partial = request.htmx and request.headers.get('HX-Target') == 'txnListContainer'
    is_pagination = request.htmx and request.GET.get('page')

    if is_partial or is_pagination:
        return render(request, 'core/partial/transaction_list.html', context)

    context['base_template'] = 'core/base_partial.html' if request.htmx else 'core/base.html'
    return render(request, 'core/transactions.html', context)


@login_required
def add_transaction(request):
    today = _get_today(request.user)

    if request.method == 'POST':
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

                txn_date = datetime.strptime(date_val, '%Y-%m-%d').date() if date_val else today
                category = Category.objects.filter(id=category_id, user=request.user).first() if category_id else None

                Transaction.objects.create(
                    user=request.user,
                    amount=final_amount,
                    description=description,
                    date=txn_date,
                    category=category
                )
                messages.success(request, "Transaction added.")
                return redirect('add_transaction')
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


@login_required
def edit_transactions(request):
    if request.method == 'POST':
        txn_ids = request.POST.getlist('txn_ids')

        if not txn_ids:
            messages.warning(request, "No transactions selected.")
            return redirect('transactions')

        new_description = request.POST.get('new_description', '').strip()
        new_category = request.POST.get('new_category')
        new_date = request.POST.get('new_date')
        new_amount = request.POST.get('new_amount')

        update_kwargs = {}
        errors = []

        if new_description:
            update_kwargs['description'] = new_description

        if new_date:
            try:
                update_kwargs['date'] = datetime.strptime(new_date, '%Y-%m-%d').date()
            except ValueError:
                errors.append("Invalid date format.")

        if new_amount:
            try:
                update_kwargs['amount'] = Decimal(new_amount)
            except (ValueError, InvalidOperation):
                errors.append("Invalid amount format. Please enter a valid number.")

        if new_category and new_category != 'no_change':
            if new_category == 'none':
                update_kwargs['category'] = None
            else:
                if Category.objects.filter(id=new_category, user=request.user).exists():
                    update_kwargs['category_id'] = new_category
                else:
                    errors.append("Selected category does not exist or access denied.")

        if errors:
            for error in errors:
                messages.error(request, error)
        elif update_kwargs:
            updated_count = Transaction.objects.filter(id__in=txn_ids, user=request.user).update(**update_kwargs)
            messages.success(request, f"Updated {len(update_kwargs)} field(s) for {updated_count} transactions.")
        else:
            messages.info(request, "No changes were made.")

    return redirect('transactions')


@login_required
def delete_transactions(request):
    if request.method == 'POST':
        txn_ids = request.POST.getlist('txn_ids')
        if txn_ids:
            deleted_count, _ = Transaction.objects.filter(id__in=txn_ids, user=request.user).delete()
            messages.success(request, f"Deleted {deleted_count} transactions.")
        else:
            messages.warning(request, "No transactions selected to delete.")

    return redirect('transactions')


@login_required
@require_POST
def add_category(request):
    cat_name = request.POST.get('category_name')
    cat_icon = request.POST.get('category_icon')
    cat_icon_color = request.POST.get('category_icon_color')
    if cat_name and cat_icon:
        Category.objects.create(user=request.user, name=cat_name, icon=cat_icon, icon_color=cat_icon_color)
        messages.success(request, f"Category '{cat_name}' added.")
    return redirect('add_transaction')


@login_required
@require_POST
def delete_category(request):
    cat_id = request.POST.get('category_id')
    Category.objects.filter(user=request.user, id=cat_id).delete()
    messages.success(request, "Category deleted.")
    return redirect('add_transaction')

# ==========================================
# PLANNING VIEWS (GOALS & RECURRING)
# ==========================================

@login_required
def planning(request):
    user = request.user

    current_goal = Goal.objects.filter(user=user, is_active=True).first()
    completed_goals = Goal.objects.filter(user=user, is_active=False).order_by('-deadline')
    recurring_items = RecurringItem.objects.filter(user=user).order_by('start_date')
    today = _get_today(user)

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
@require_POST
def add_goal(request):
    if Goal.objects.filter(user=request.user, is_active=True).exists():
        messages.error(request, "You already have an active financial plan.")
        return redirect('planning')

    try:
        goal_name = request.POST.get('goal_name')
        goal_icon = request.POST.get('goal_icon')
        goal_icon_color = request.POST.get('goal_icon_color')
        target_amount = Decimal(request.POST.get('goal_amount', 0))
        deadline_str = request.POST.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        Goal.objects.create(
            user=request.user,
            name=goal_name,
            icon=goal_icon,
            icon_color=goal_icon_color,
            target_amount=target_amount,
            deadline=deadline
        )
        messages.success(request, "New goal created!")
    except (ValueError, InvalidOperation):
        messages.error(request, "Invalid input. Please check your numbers and date.")

    return redirect('planning')


@login_required
@require_POST
def edit_goal(request):
    try:
        current_goal = Goal.objects.filter(user=request.user, is_active=True).first()

        if not current_goal:
            messages.error(request, "No active plan found to edit.")
            return redirect('planning')

        goal_name = request.POST.get('goal_name')
        goal_icon = request.POST.get('goal_icon')
        goal_icon_color = request.POST.get('goal_icon_color')
        target_amount = Decimal(request.POST.get('goal_amount', 0))
        deadline_str = request.POST.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

        current_goal.name = goal_name
        current_goal.icon = goal_icon
        current_goal.icon_color = goal_icon_color
        current_goal.target_amount = target_amount
        current_goal.deadline = deadline
        current_goal.save(update_fields=['name', 'icon', 'icon_color', 'target_amount', 'deadline'])

        messages.success(request, "Goal updated successfully.")
    except (ValueError, InvalidOperation):
        messages.error(request, "Invalid input. Please check your numbers and date.")

    return redirect('planning')


@login_required
def delete_goal(request):
    if request.method == 'POST':
        Goal.objects.filter(user=request.user, is_active=True).delete()
    return redirect('planning')


@login_required
@require_POST
def add_recurring(request):
    try:
        rec_name = request.POST.get('rec_name')
        rec_amount = Decimal(request.POST.get('rec_amount', 0))
        rec_type = request.POST.get('rec_type')
        freq_type = request.POST.get('frequency_type')

        rec_amount = -abs(rec_amount) if rec_type == 'expense' else abs(rec_amount)

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
            user=request.user,
            name=rec_name,
            amount=rec_amount,
            frequency_type=freq_type,
            start_date=start_date,
            end_date=end_date,
            interval_days=interval
        )
        messages.success(request, "Recurring item added.")
    except Exception:
        messages.error(request, "Invalid input format. Please check your numbers and dates.")
        
    return redirect('planning')


@login_required
@require_POST
def delete_recurring(request):
    item_id = request.POST.get('item_id')
    item = get_object_or_404(RecurringItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, "Item removed.")
    return redirect('planning')

# ==========================================
# SETTINGS VIEW
# ==========================================

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

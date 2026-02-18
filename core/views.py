from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile, Goal, Transaction, RecurringItem
from .services import FinancialGPS
from datetime import date, timedelta, datetime
from decimal import Decimal
import json

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
    gps = FinancialGPS(request.user)
    data = gps.get_status()
    
    # 1. Fetch historical data (90 days buffer)
    history = gps.get_historical_data(days=90)
    
    # 2. Prepare JSON for Frontend
    if history:
        chart_dates = json.dumps(history['dates'])
        chart_safe = json.dumps(history['safe_spend'])
        chart_actual = json.dumps(history['actual_spend'])
    else:
        chart_dates = None
        chart_safe = None
        chart_actual = None

    context = { 
        'data': data,
        'chart_dates': chart_dates,
        'chart_safe': chart_safe,
        'chart_actual': chart_actual,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def transaction_api(request):
    """
    API Endpoint to fetch transactions via AJAX
    """
    days = int(request.GET.get('days', 30))
    start_date = date.today() - timedelta(days=days)

    transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date
    ).order_by('-date', '-created_at')

    data = []
    for t in transactions:
        data.append({
            'id': t.id,
            'date': t.date.strftime("%b %d, %Y"),
            'description': t.description,
            'amount': float(t.amount),
            'is_expense': t.amount < 0
        })

    return JsonResponse({'transactions': data})

@login_required
def setup_goal(request):
    current_goal = Goal.objects.filter(user=request.user, is_active=True).first()

    if request.method == 'POST':
        user = request.user

        try:
            goal_name = request.POST.get('goal_name')
            target_amount = Decimal(request.POST.get('goal_amount', 0))

            deadline_str = request.POST.get('deadline')
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()

            if current_goal:
                # Update existing goal
                current_goal.name = goal_name
                current_goal.target_amount = target_amount
                current_goal.deadline = deadline
                current_goal.save()
                messages.success(request, "Goal updated successfully.")
            else:
                # Create new goal
                Goal.objects.filter(user=user).update(is_active=False)
                Goal.objects.create(
                    user=user,
                    name=goal_name,
                    target_amount=target_amount,
                    deadline=deadline
                )
                messages.success(request, "New goal created!")

            return redirect('dashboard')
        except ValueError:
            messages.error(request, "Invalid input. Please check your numbers.")

    # Calculate min_date for the date picker (Tomorrow)
    min_date = date.today() + timedelta(days=1)

    return render(request, 'core/goal_setup.html', {'current_goal': current_goal, 'min_date': min_date})

@login_required
def delete_goal(request):
    if request.method == 'POST':
        Goal.objects.filter(user=request.user, is_active=True).delete()
    return redirect('dashboard')

@login_required
def recurring_management(request):
    user = request.user
    items = RecurringItem.objects.filter(user=user).order_by('start_date')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(RecurringItem, id=item_id, user=user)
            item.delete()
            messages.success(request, "Item removed.")
            return redirect('fixed_flows')

        elif action == 'create':
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
                    interval = int(request.POST.get('interval_days'))

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
                return redirect('fixed_flows')
            except Exception as e:
                print(e)
                messages.error(request, "Error adding item.")

    return render(request, 'core/fixed_flows.html', {'items': items})

@login_required
def add_transaction(request):
    if request.method == 'POST':
        # Handles receipt upload via 'receipt_images' input
        images = request.FILES.getlist('receipt_images')
        if images:
            count = len(images)
            total_cost = Decimal('100.00') * count * Decimal(-1)
            Transaction.objects.create(
                user=request.user,
                amount=total_cost,
                description=f"Scanned Receipt ({count} items)"
            )
            messages.success(request, f"Processed {count} receipts!")
            return redirect('dashboard')

        # Handles manual entry
        try:
            amount_val = request.POST.get('amount')
            trans_type = request.POST.get('type')
            description = request.POST.get('description', 'Transaction')
            date_val = request.POST.get('txn_date')

            if amount_val:
                amount = Decimal(amount_val)
                final_amount = amount if trans_type == 'income' else -abs(amount)
                
                # Parse Date or Default to Today
                if date_val:
                    txn_date = datetime.strptime(date_val, '%Y-%m-%d').date()
                else:
                    txn_date = date.today()

                Transaction.objects.create(
                    user=request.user,
                    amount=final_amount,
                    description=description,
                    date=txn_date
                )
                return redirect('dashboard')
        except Exception as e:
            print(e)
            messages.error(request, "Error adding transaction.")
            
    return render(request, 'core/transaction.html')

@login_required
def settings(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_username':
            user.username = request.POST.get('username')
            user.save()
            messages.success(request, "Username updated.")
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
            return redirect('settings')

    return render(request, 'core/settings.html', {
        'profile': profile,
        'password_form': password_form
    })

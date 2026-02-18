from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import Goal, Transaction, RecurringItem
import zoneinfo

class FinancialGPS:
    def __init__(self, user):
        self.user = user
        self.goal = Goal.objects.filter(user=user, is_active=True).first()
        self.user_tz = zoneinfo.ZoneInfo(self.user.userprofile.timezone)

    def get_today(self):
        """Returns the current date in the user's local timezone."""
        return timezone.now().astimezone(self.user_tz).date()

    def _calculate_future_recurring(self, start_date, end_date):
        """
        Helper: Calculates the sum of all recurring items between start_date and end_date.
        """
        future_sum = Decimal(0)
        recurring_items = RecurringItem.objects.filter(user=self.user)

        for item in recurring_items:        
            current_check_date = item.start_date
            target_day_of_month = item.start_date.day

            # 1. Fast forward to the simulation window (start_date)
            while current_check_date <= start_date:
                if item.frequency_type == 'monthly':
                    next_month = current_check_date + relativedelta(months=1)
                    max_day = (next_month + relativedelta(day=31)).day
                    current_check_date = next_month.replace(day=min(target_day_of_month, max_day))
                else: 
                    current_check_date += timedelta(days=item.interval_days)

            # 2. Sum up occurrences until end_date
            while current_check_date <= end_date:
                if item.end_date and current_check_date > item.end_date:
                    break

                future_sum += item.amount

                # Advance Date
                if item.frequency_type == 'monthly':
                    next_month = current_check_date + relativedelta(months=1)
                    max_day = (next_month + relativedelta(day=31)).day
                    current_check_date = next_month.replace(day=min(target_day_of_month, max_day))
                else:
                    current_check_date += timedelta(days=item.interval_days)
        
        return future_sum

    def get_status(self):
        """
        Returns the current real-time status.
        """
        if not self.goal:
            return None

        today = self.get_today()
        deadline = self.goal.deadline

        # 1. Timeline
        remaining_days = (deadline - today).days
        remaining_days_safe = max(remaining_days, 1)

        # 2. Current Net Worth
        current_net_worth = Transaction.objects.filter(
            user=self.user,
            date__lte=today
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        # 3. Today's Spend
        todays_transactions = Transaction.objects.filter(user=self.user, date=today)
        spent_today = sum(abs(t.amount) for t in todays_transactions if t.amount < 0)

        start_of_day_net_worth = current_net_worth + spent_today

        # 4. Future Cashflow
        future_recurring_sum = self._calculate_future_recurring(today, deadline)

        # 5. Safe-to-Spend Calculation
        # Formula: (Current Money + Future Money - Target Goal) / Days Left
        total_pool_available = start_of_day_net_worth + future_recurring_sum
        safe_pool = total_pool_available - self.goal.target_amount

        base_daily_budget = safe_pool / Decimal(remaining_days_safe)
        remaining_today_actual = base_daily_budget - spent_today

        # 6. Progress
        progress = 0
        if self.goal.target_amount > 0:
            progress = (current_net_worth / self.goal.target_amount) * 100

        return {
            'goal_name': self.goal.name,
            'remaining_days': remaining_days,
            'progress_percent': int(max(0, min(100, progress))),
            'base_budget': round(base_daily_budget, 2),
            'spent_today': round(spent_today, 2),
            'remaining_today': round(remaining_today_actual, 2),
            'status': 'off_track' if remaining_today_actual < 0 else 'on_track'
        }

    def get_historical_data(self, days=30):
        """
        Reconstructs the 'Safe to Spend' vs 'Actual' for the past N days.
        """
        if not self.goal:
            return None

        today = self.get_today()

        goal_start_date = self.goal.created_at.date()
        requested_start = today - timedelta(days=days)
        start_date = max(requested_start, goal_start_date)
        days_to_process = (today - start_date).days

        if days_to_process < 1:
            return None

        # Pre-fetch transactions to minimize DB hits
        all_txns = Transaction.objects.filter(
            user=self.user, 
            date__gte=start_date, 
            date__lte=today
        ).values('date', 'amount')

        # Initial Net Worth (Prior to the chart window)
        running_net_worth = Transaction.objects.filter(
            user=self.user,
            date__lt=start_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        chart_data = {
            'dates': [],
            'safe_spend': [],
            'actual_spend': []
        }

        # Iterate day by day using the calculated range
        for i in range(days_to_process + 1):
            current_date = start_date + timedelta(days=i)
            
            # Filter transactions for this specific day
            day_txns = [t for t in all_txns if t['date'] == current_date]
            
            day_income = sum(t['amount'] for t in day_txns if t['amount'] > 0)
            day_expenses = sum(abs(t['amount']) for t in day_txns if t['amount'] < 0)
            net_change = day_income - day_expenses

            # Update Running Balance (End of Day)
            running_net_worth += net_change

            # RECONSTRUCTION: What was the budget at the START of this day?
            morning_balance = running_net_worth - net_change

            # Calculate Future Recurring from THAT date
            future_cash = self._calculate_future_recurring(current_date, self.goal.deadline)

            # Calculate Days Remaining from THAT date
            days_left = max((self.goal.deadline - current_date).days, 1)

            # Calculate Historical Safe-to-Spend
            pool = morning_balance + future_cash - self.goal.target_amount
            historical_budget = pool / Decimal(days_left)

            chart_data['dates'].append(current_date.strftime("%Y-%m-%d"))
            chart_data['safe_spend'].append(float(round(historical_budget, 2)))
            chart_data['actual_spend'].append(float(round(day_expenses, 2)))

        return chart_data

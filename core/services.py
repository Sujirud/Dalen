from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import SavingGoal, Transaction, RecurringItem
import zoneinfo

class FinancialGPS:
    def __init__(self, user):
        self.user = user
        self.goals = list(SavingGoal.objects.filter(user=user, is_active=True).order_by('deadline'))
        self.recurring_items = list(RecurringItem.objects.filter(user=user))

        user_tz = zoneinfo.ZoneInfo(self.user.userprofile.timezone)
        self.today = timezone.now().astimezone(user_tz).date()

    def _calculate_future_recurring(self, start_date, end_date):
        """
        Helper: Calculates the sum of all recurring items between start_date and end_date.
        """
        future_sum = Decimal(0)

        for item in self.recurring_items:        
            current_check_date = item.start_date
            target_day_of_month = item.start_date.day

            # 1. Fast forward to the simulation window (start_date)
            while current_check_date < start_date:
                if item.frequency_type == 'monthly':
                    next_month = current_check_date + relativedelta(months=1)
                    max_day = (next_month + relativedelta(day=31)).day
                    current_check_date = next_month.replace(day=min(target_day_of_month, max_day))
                else: 
                    interval = item.interval_days if item.interval_days and item.interval_days > 0 else 1
                    current_check_date += timedelta(days=interval)

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
                    interval = item.interval_days if item.interval_days and item.interval_days > 0 else 1
                    current_check_date += timedelta(days=interval)

        return future_sum

    def get_status(self):
        """
        Returns the current real-time status using the Cumulative Bottleneck Algorithm.
        """
        if not self.goals:
            return None

        # 1. Current Net Worth
        current_net_worth = Transaction.objects.filter(
            user=self.user,
            date__lte=self.today
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        # 2. Today's Spend
        todays_transactions = Transaction.objects.filter(user=self.user, date=self.today)
        spent_today = sum(abs(t.amount) for t in todays_transactions if t.amount < 0)

        # 3. Cumulative Bottleneck Algorithm
        min_base_budget = Decimal('Infinity')
        cumulative_target = Decimal(0)

        for goal in self.goals:
            remaining_days = max((goal.deadline - self.today).days, 1)
            cumulative_target += goal.target_amount

            future_recurring_sum = self._calculate_future_recurring(self.today, goal.deadline)
            total_pool_available = (current_net_worth + spent_today) + future_recurring_sum

            safe_pool = total_pool_available - cumulative_target
            target_daily_budget = safe_pool / Decimal(remaining_days)

            # The strict bottleneck rules the daily budget
            if target_daily_budget < min_base_budget:
                min_base_budget = target_daily_budget

        # 4. Final Calculations
        if min_base_budget == Decimal('Infinity'):
            min_base_budget = Decimal(0)

        remaining_today = min_base_budget - spent_today

        # Overall Cumulative Progress
        if cumulative_target > 0:
            progress = int(max(0, min(100, (current_net_worth / cumulative_target) * 100)))
        else:
            progress = 0

        return {
            'goals': self.goals,
            'cumulative_target': round(cumulative_target, 2),
            'net_worth': round(current_net_worth, 2),
            'progress_percent': progress,
            'base_budget': round(min_base_budget, 2),
            'remaining_today': round(remaining_today, 2)
        }

    def get_chart_data(self, days):
        """
        Reconstructs the 'Safe to Spend' vs 'Actual' for the past N days across all goals.
        """
        if not self.goals:
            return None

        earliest_goal_start = min(g.created_at.date() for g in self.goals)
        requested_start = self.today - timedelta(days=days)
        start_date = max(requested_start, earliest_goal_start)
        days_to_process = (self.today - start_date).days

        if days_to_process < 3:
            return None

        all_txns = Transaction.objects.filter(
            user=self.user, 
            date__gte=start_date, 
            date__lte=self.today
        ).values('date', 'amount')

        running_net_worth = Transaction.objects.filter(
            user=self.user,
            date__lt=start_date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

        chart_data = {
            'dates': [],
            'safe_spend': [],
            'actual_spend': []
        }

        for i in range(days_to_process + 1):
            current_date = start_date + timedelta(days=i)

            day_txns = [t for t in all_txns if t['date'] == current_date]
            day_income = sum(t['amount'] for t in day_txns if t['amount'] > 0)
            day_expenses = sum(abs(t['amount']) for t in day_txns if t['amount'] < 0)
            net_change = day_income - day_expenses

            running_net_worth += net_change
            morning_balance = running_net_worth - net_change

            # RECONSTRUCTION: Apply Cumulative Bottleneck logic for this specific past day
            min_historical_budget = Decimal('Infinity')
            cumulative_target = Decimal(0)

            # Only consider goals that were active on or before this historical day
            active_goals_on_date = [g for g in self.goals if g.created_at.date() <= current_date]

            if not active_goals_on_date:
                historical_budget = Decimal(0)
            else:
                for goal in active_goals_on_date:
                    cumulative_target += goal.target_amount
                    future_cash = self._calculate_future_recurring(current_date, goal.deadline)
                    days_left = max((goal.deadline - current_date).days, 1)

                    pool = morning_balance + future_cash - cumulative_target
                    budget = pool / Decimal(days_left)

                    if budget < min_historical_budget:
                        min_historical_budget = budget

                historical_budget = min_historical_budget

            chart_data['dates'].append(current_date.strftime("%Y-%m-%d"))
            chart_data['safe_spend'].append(float(round(historical_budget, 2)))
            chart_data['actual_spend'].append(float(round(day_expenses, 2)))

        return chart_data

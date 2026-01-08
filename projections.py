from datetime import datetime, timedelta
from typing import List, Dict
from dateutil.relativedelta import relativedelta


def calculate_projections(
    current_balance: float,
    months: int,
    recurring_deposits: List[Dict],
    recurring_withdrawals: List[Dict]
) -> Dict:
    """
    Calculate future balance projections based on recurring transactions

    Args:
        current_balance: Starting balance
        months: Number of months to project
        recurring_deposits: List of recurring deposit dicts with 'amount' and 'frequency'
        recurring_withdrawals: List of recurring withdrawal dicts with 'amount' and 'frequency'

    Frequency can be: 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly'

    Returns:
        Dictionary with projections including monthly breakdown and summary
    """

    # Convert frequency to occurrences per month
    frequency_map = {
        'weekly': 52 / 12,
        'biweekly': 26 / 12,
        'monthly': 1,
        'quarterly': 1 / 3,
        'yearly': 1 / 12
    }

    # Calculate monthly recurring amounts
    monthly_deposits = 0
    for deposit in recurring_deposits:
        amount = float(deposit.get('amount', 0))
        frequency = deposit.get('frequency', 'monthly').lower()
        occurrences_per_month = frequency_map.get(frequency, 1)
        monthly_deposits += amount * occurrences_per_month

    monthly_withdrawals = 0
    for withdrawal in recurring_withdrawals:
        amount = float(withdrawal.get('amount', 0))
        frequency = withdrawal.get('frequency', 'monthly').lower()
        occurrences_per_month = frequency_map.get(frequency, 1)
        monthly_withdrawals += abs(amount) * occurrences_per_month

    # Calculate monthly net change
    monthly_net = monthly_deposits - monthly_withdrawals

    # Generate monthly projections
    projections = []
    current_date = datetime.now()
    balance = current_balance

    for i in range(months + 1):
        month_date = current_date + relativedelta(months=i)

        projection = {
            'month': month_date.strftime('%Y-%m'),
            'month_name': month_date.strftime('%B %Y'),
            'deposits': monthly_deposits if i > 0 else 0,
            'withdrawals': monthly_withdrawals if i > 0 else 0,
            'net_change': monthly_net if i > 0 else 0,
            'projected_balance': balance
        }

        projections.append(projection)

        # Update balance for next month
        if i < months:
            balance += monthly_net

    # Calculate summary statistics
    final_balance = balance
    total_deposits = monthly_deposits * months
    total_withdrawals = monthly_withdrawals * months
    total_change = final_balance - current_balance

    # Determine if projection is positive or negative
    trend = 'positive' if monthly_net > 0 else 'negative' if monthly_net < 0 else 'neutral'

    # Calculate months until zero balance (if negative trend)
    months_until_zero = None
    if monthly_net < 0 and current_balance > 0:
        months_until_zero = int(current_balance / abs(monthly_net))

    summary = {
        'current_balance': current_balance,
        'final_balance': final_balance,
        'total_change': total_change,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'monthly_net': monthly_net,
        'trend': trend,
        'months_until_zero': months_until_zero
    }

    return {
        'projections': projections,
        'summary': summary,
        'recurring_deposits': recurring_deposits,
        'recurring_withdrawals': recurring_withdrawals
    }


def analyze_recurring_from_transactions(transactions: List[Dict], min_occurrences: int = 3) -> Dict:
    """
    Analyze transactions to identify recurring patterns

    Args:
        transactions: List of transaction dictionaries
        min_occurrences: Minimum number of occurrences to consider as recurring

    Returns:
        Dictionary with identified recurring deposits and withdrawals
    """

    # Group transactions by description
    from collections import defaultdict

    deposits = defaultdict(list)
    withdrawals = defaultdict(list)

    for txn in transactions:
        amount = txn.get('amount', 0)
        description = txn.get('description', '')

        if amount > 0:
            deposits[description].append(txn)
        else:
            withdrawals[description].append(txn)

    # Identify recurring patterns
    recurring_deposits = []
    for description, txns in deposits.items():
        if len(txns) >= min_occurrences:
            amounts = [t['amount'] for t in txns]
            avg_amount = sum(amounts) / len(amounts)

            # Try to determine frequency
            dates = sorted([datetime.strptime(t['transaction_date'], '%Y-%m-%d') for t in txns])
            if len(dates) > 1:
                avg_days_between = sum([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]) / (len(dates) - 1)

                # Classify frequency
                if avg_days_between <= 10:
                    frequency = 'weekly'
                elif avg_days_between <= 17:
                    frequency = 'biweekly'
                elif avg_days_between <= 35:
                    frequency = 'monthly'
                elif avg_days_between <= 100:
                    frequency = 'quarterly'
                else:
                    frequency = 'yearly'
            else:
                frequency = 'monthly'

            recurring_deposits.append({
                'description': description,
                'amount': avg_amount,
                'frequency': frequency,
                'occurrences': len(txns)
            })

    recurring_withdrawals = []
    for description, txns in withdrawals.items():
        if len(txns) >= min_occurrences:
            amounts = [abs(t['amount']) for t in txns]
            avg_amount = sum(amounts) / len(amounts)

            dates = sorted([datetime.strptime(t['transaction_date'], '%Y-%m-%d') for t in txns])
            if len(dates) > 1:
                avg_days_between = sum([(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]) / (len(dates) - 1)

                if avg_days_between <= 10:
                    frequency = 'weekly'
                elif avg_days_between <= 17:
                    frequency = 'biweekly'
                elif avg_days_between <= 35:
                    frequency = 'monthly'
                elif avg_days_between <= 100:
                    frequency = 'quarterly'
                else:
                    frequency = 'yearly'
            else:
                frequency = 'monthly'

            recurring_withdrawals.append({
                'description': description,
                'amount': avg_amount,
                'frequency': frequency,
                'occurrences': len(txns)
            })

    return {
        'recurring_deposits': sorted(recurring_deposits, key=lambda x: x['amount'], reverse=True),
        'recurring_withdrawals': sorted(recurring_withdrawals, key=lambda x: x['amount'], reverse=True)
    }

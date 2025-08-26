# management/views.py

from django.shortcuts import render, get_object_or_404
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import Bill, BillItem, WheatPurchase, Expense, Production

def bill_print_view(request, bill_id):
    """
    Renders a printable bill template for a specific bill ID.
    It retrieves bill and bill items data from the database.
    """
    bill = get_object_or_404(Bill, id=bill_id)
    bill_items = BillItem.objects.filter(bill=bill).annotate(
        total_price=F('quantity_kg') * F('price_per_unit')
    )
    
    context = {
        'bill': bill,
        'bill_items': bill_items,
        # Reusing methods from the Bill model for consistency
        'subtotal': bill.get_subtotal(),
        'gst': bill.get_gst_amount(),
        'grand_total': bill.get_grand_total(),
    }
    return render(request, 'management/bill_print.html', context)

def report_panel_view(request):
    """
    Handles all reporting types based on query parameters.
    It uses database aggregation for efficiency.
    """
    report_type = request.GET.get('report_type', 'daily_sales')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    try:
        if start_date and end_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            start_date = thirty_days_ago
            end_date = today
    except (ValueError, TypeError):
        start_date = thirty_days_ago
        end_date = today

    report_data = {}
    
    bills = Bill.objects.filter(bill_date__date__range=[start_date, end_date])
    expenses = Expense.objects.filter(date__date__range=[start_date, end_date])
    productions = Production.objects.filter(production_date__date__range=[start_date, end_date])

    if report_type in ['daily_sales', 'weekly_sales', 'monthly_sales']:
        date_grouping = None
        if report_type == 'daily_sales':
            date_grouping = TruncDay('bill_date')
        elif report_type == 'weekly_sales':
            date_grouping = TruncWeek('bill_date')
        elif report_type == 'monthly_sales':
            date_grouping = TruncMonth('bill_date')
        
        sales_data = bills.annotate(date=date_grouping).values('date').annotate(
            total_sales=Sum(F('get_grand_total'))
        ).order_by('date')
        report_data['sales'] = sales_data
        
    elif report_type == 'sales_profit':
        total_sales = bills.aggregate(total_sales=Sum(F('get_grand_total')))['total_sales'] or 0
        total_expenses = expenses.aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        total_wheat_purchase = WheatPurchase.objects.filter(
            purchase_date__date__range=[start_date, end_date]
        ).aggregate(total_purchase=Sum(F('quantity_kg') * F('price_per_unit')))['total_purchase'] or 0
        
        report_data['profit_loss'] = {
            'total_sales': total_sales,
            'total_expenses': total_expenses + total_wheat_purchase,
            'profit_or_loss': total_sales - (total_expenses + total_wheat_purchase)
        }

    elif report_type == 'production_summary':
        production_data = productions.values('product__name').annotate(
            total_quantity=Sum(F('quantity_kg'))
        ).order_by('product__name')
        report_data['production'] = production_data
        
    elif report_type == 'expense_summary':
        expense_data = expenses.values('description').annotate(
            total_amount=Sum('amount')
        ).order_by('description')
        report_data['expenses'] = expense_data

    elif report_type == 'inventory_summary':
        from .models import RawMaterial, FinishedProduct
        raw_materials = RawMaterial.objects.all()
        finished_products = FinishedProduct.objects.all()
        report_data['inventory'] = {
            'raw_materials': raw_materials,
            'finished_products': finished_products
        }
        
    context = {
        'report_type': report_type,
        'report_data': report_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'management/report_panel.html', context)
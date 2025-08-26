from django.urls import path
from . import views

urlpatterns = [
    # URL to print a specific bill from the admin panel
    path('bill/<int:bill_id>/', views.bill_print_view, name='bill_print'),
    
    # URL for the comprehensive reports panel
    path('report-panel/', views.report_panel_view, name='report_panel'),
]
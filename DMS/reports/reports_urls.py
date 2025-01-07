from django.urls import path
from reports.reports_views import OrderReportView, CustomerReportView, CompanyCommissionReportView, RiderReportView

urlpatterns = [
    path('reports/orders/', OrderReportView.as_view(), name='order_reports'),
    path('reports/customers/', CustomerReportView.as_view(), name='customer_reports'),
    path('reports/company/', CompanyCommissionReportView.as_view(), name='company_commission_report'),
    path('reports/riders/', RiderReportView.as_view(), name='rider_reports'),
]
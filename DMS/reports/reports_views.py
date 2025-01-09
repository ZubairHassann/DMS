from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from delivery.models import ManualOrder
from Orders.order_serializers import ManualOrderSerializer
from django.db import models
from datetime import datetime
from delivery.models import Customer, CompanyWallet, RiderWallet, Rider


class OrderReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status = request.query_params.get('status')

        # Query orders based on filters
        orders = ManualOrder.objects.all()
        if start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        if status:
            orders = orders.filter(status=status)

        serializer = ManualOrderSerializer(orders, many=True)
        return Response({
            "total_orders": orders.count(),
            "orders": serializer.data
        })


class CustomerReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customers = Customer.objects.all()
        customer_data = []
        for customer in customers:
            total_orders = ManualOrder.objects.filter(
                customer=customer).count()
            total_spent = ManualOrder.objects.filter(customer=customer).aggregate(
                total_price=models.Sum('total_price'))['total_price'] or 0
            
            customer_data.append({
                "customer_name": f"{customer.user.first_name} {customer.user.last_name}",
                "email": customer.user.email,
                "total_orders": total_orders,
                "total_spent": total_spent
            })

        return Response({"customers": customer_data})


class CompanyCommissionReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = CompanyWallet.objects.first()
        total_commission = wallet.balance if wallet else 0

        return Response({
            "total_commission": total_commission
        })


class RiderReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        riders = Rider.objects.all()
        rider_data = []
        for rider in riders:
            total_deliveries = ManualOrder.objects.filter(
                rider=rider, status='delivered').count()
            pending_orders = ManualOrder.objects.filter(
                rider=rider).exclude(status='delivered').count()
            earnings = RiderWallet.objects.filter(rider=rider).first()
            total_earnings = earnings.balance if earnings else 0

            rider_data.append({
                "rider_name": f"{rider.user.first_name} {rider.user.last_name}",
                "total_deliveries": total_deliveries,
                "pending_orders": pending_orders,
                "total_earnings": total_earnings
            })

        return Response({"riders": rider_data})

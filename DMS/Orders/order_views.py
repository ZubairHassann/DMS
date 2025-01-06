from delivery.models import *
from rest_framework import viewsets, status
from .order_serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from delivery.permissions import IsSuperUser, IsRider
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError


class ManualOrderViewSet(viewsets.ModelViewSet):
    queryset = ManualOrder.objects.all()
    serializer_class = ManualOrderSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def list(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_superuser:
            # Separate completed and active orders
            completed_orders = ManualOrder.objects.filter(status='delivered')
            active_orders = ManualOrder.objects.exclude(
                Q(status='delivered') | Q(rider__isnull=True))
            unassigned_orders = ManualOrder.objects.filter(
                Q(rider=user) | Q(rider__isnull=True))
        elif user.is_staff:
            # Riders see only orders assigned to them
            completed_orders = ManualOrder.objects.filter(
                rider=user, status='delivered')
            active_orders = ManualOrder.objects.filter(
                rider=user).exclude(status='delivered')
            unassigned_orders = None
        else:
            # Normal users see only their own orders
            completed_orders = ManualOrder.objects.filter(
                user=user, status='delivered')
            active_orders = ManualOrder.objects.filter(
                user=user).exclude(status='delivered')
            unassigned_orders = None

        # Serialize the querysets
        completed_orders = self.get_serializer(
            completed_orders, many=True).data
        active_orders = self.get_serializer(active_orders, many=True).data
        unassigned_orders = self.get_serializer(
            unassigned_orders, many=True).data if unassigned_orders else []

        return Response({
            "completed_orders": completed_orders,
            "active_orders": active_orders,
            'unassigned_orders': unassigned_orders,
        })

    def perform_create(self, serializer):
        user = self.request.user

        if not user.is_superuser:
            # Get the order address from the serializer's validated data
            order_address = serializer.validated_data.get('address')

            # Check for available rider based on address
            rider = User.objects.filter(
                Q(is_superuser=False) & Q(is_staff=True))
            rider = rider.filter(profile__address=order_address).first()

            if rider:
                serializer.save(user=user, rider=rider)
            else:
                rider = User.objects.filter(
                    Q(is_superuser=True) & Q(is_staff=False)).first()
                if rider:
                    serializer.save(user=user, rider=rider)
                else:
                    return Response(
                        {'detail': 'No available riders for the specified address, Order has been shifted to unassigned orders'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            serializer.save(user=user)

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance

        if user.is_staff and not user.is_superuser:
            # Staff users can only update price, status, and invoice fields
            serializer.save(
                total_price=serializer.validated_data.get(
                    'total_price', instance.total_price),
                status=serializer.validated_data.get(
                    'status', instance.status),
                invoice=serializer.validated_data.get(
                    'invoice', instance.invoice),
                rider=instance.rider,  # Preserve rider
                user=instance.user  # Preserve user
            )
        elif user.is_superuser:
            # Superuser can change all fields
            serializer.save()
        else:
            # If user is not permitted to update this order, deny access
            return Response(
                {'detail': 'You do not have permission to update this order.'},
                status=status.HTTP_403_FORBIDDEN
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    if not request.user.is_staff:
        return Response({"error": "Only admin and rider users can complete orders."}, status=status.HTTP_403_FORBIDDEN)
    try:
        order = ManualOrder.objects.get(id=order_id)

        # Convert order values to Decimal to avoid float issues
        ride_charges = Decimal(order.ride_charges)
        paid_amount = Decimal(order.paid_amount)
        total_price = Decimal(order.total_price)

        total_required = total_price + ride_charges

        if paid_amount > total_required:
            excess_amount = paid_amount - total_required
            customer_wallet, _ = CustomerWallet.objects.get_or_create(
                customer=order.user)
            customer_wallet.add_funds(excess_amount)

        elif paid_amount < total_required:
            deficit_amount = total_required - paid_amount
            customer_wallet, _ = CustomerWallet.objects.get_or_create(
                customer=order.user)

            if customer_wallet.balance >= deficit_amount:
                customer_wallet.deduct_funds(deficit_amount)
            else:
                return Response({"error": "Insufficient funds in customer's wallet to cover the deficit."},
                                status=status.HTTP_400_BAD_REQUEST)

        # Distribution Logic
        company_share_percentage = Decimal('0.07')
        company_share = order.ride_charges * company_share_percentage
        rider_share = order.ride_charges - company_share

        # Ensure Company Wallet exists or create it
        company_wallet, created = CompanyWallet.objects.get_or_create(id=1)
        company_wallet.add_funds(company_share)

        # Update the rider's wallet or create if not available
        rider_wallet, _ = RiderWallet.objects.get_or_create(rider=order.rider)
        rider_wallet.add_funds(rider_share)

        # Mark the order as completed (delivered)
        order.status = 'delivered'
        order.save()

        return Response({"message": "Order completed and wallets updated successfully."}, status=status.HTTP_200_OK)
    except ManualOrder.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateManualOrder(APIView):
    """
    API view to create a manual order. 
    Only authenticated customers can create an order for themselves.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Ensure that the logged-in user is allowed to create the order
        if not request.user.is_authenticated:
            raise ValidationError(
                "Authentication is required to create an order.")

        # Add the logged-in user to the data for the serializer
        request_data = request.data
        request_data['user'] = request.user.id

        # Serialize the data using ManualOrderSerializer
        serializer = ManualOrderSerializer(
            data=request_data, context={'request': request})

        if serializer.is_valid():
            # Save the order to the database
            manual_order = serializer.save()
            return Response(
                {"message": "Order created successfully.", "order": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        # If the data is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminOrderListView(APIView):
    permission_classes = [IsSuperUser]  # Only admin can view

    def get(self, request):
        orders = ManualOrder.objects.all()
        serializer = ManualOrderSerializer(orders, many=True)
        return Response(serializer.data)


class RiderOrderListView(ListAPIView):
    serializer_class = ManualOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            # Get the Rider instance for the current user
            rider = Rider.objects.get(user=user)
            print(rider)
        except Rider.DoesNotExist:
            # Return an empty queryset if the user is not a rider
            return ManualOrder.objects.all()

        # Filter orders assigned to this rider
        return ManualOrder.objects.all()

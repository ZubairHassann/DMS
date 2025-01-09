from delivery.models import *
from rest_framework import status
from .order_serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from delivery.permissions import IsSuperUser
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import ValidationError, NotFound
from delivery.views import GetCustomerLocationView
from rest_framework.exceptions import NotFound, PermissionDenied
import requests


class ManualOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Determine user role and fetch orders accordingly
        if user.is_superuser:
            # Admin: Fetch all orders
            completed_orders = ManualOrder.objects.filter(status='delivered')
            active_orders = ManualOrder.objects.exclude(status='delivered')
        elif hasattr(user, 'rider'):
            # Rider: Fetch orders assigned to them
            completed_orders = ManualOrder.objects.filter(
                rider=user.rider, status='delivered')
            active_orders = ManualOrder.objects.filter(
                rider=user.rider).exclude(status='delivered')
        elif hasattr(user, 'customer'):
            # Customer: Fetch orders they created
            completed_orders = ManualOrder.objects.filter(
                customer=user.customer, status='delivered')
            active_orders = ManualOrder.objects.filter(
                customer=user.customer).exclude(status='delivered')
        else:
            raise NotFound("You do not have permission to view orders.")

        # Serialize the data
        serializer = ManualOrderSerializer(
            {
                "completed_orders": completed_orders,
                "active_orders": active_orders,
            },
            context={"request": request},
            many=True,
        )

        # Return response
        return Response(
            {
                "completed_orders": serializer.data.get("completed_orders", []),
                "active_orders": serializer.data.get["manual_orders_text_view"],
            }
        )
# class ManualOrderViewSet(viewsets.ModelViewSet):
#     queryset = ManualOrder.objects.all()
#     serializer_class = ManualOrderSerializer
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [SessionAuthentication, JWTAuthentication]

#     def list(self, request, *args, **kwargs):
#         user = self.request.user
#         if user.is_superuser:
#             completed_orders = ManualOrder.objects.filter(status='delivered')
#             active_orders = ManualOrder.objects.exclude(
#                 Q(status='delivered') | Q(rider__isnull=True)
#             )
#             unassigned_orders = ManualOrder.objects.filter(
#                 Q(rider=user) | Q(rider__isnull=True)
#             )
#         elif user.is_staff:
#             completed_orders = ManualOrder.objects.filter(rider=user, status='delivered')
#             active_orders = ManualOrder.objects.filter(rider=user).exclude(status='delivered')
#             unassigned_orders = None
#         else:
#             completed_orders = ManualOrder.objects.filter(user=user, status='delivered')
#             active_orders = ManualOrder.objects.filter(user=user).exclude(status='delivered')
#             unassigned_orders = None

#         completed_orders = self.get_serializer(completed_orders, many=True).data
#         active_orders = self.get_serializer(active_orders, many=True).data
#         unassigned_orders = self.get_serializer(unassigned_orders, many=True).data if unassigned_orders else []

#         return Response({
#             "completed_orders": completed_orders,
#             "active_orders": active_orders,
#             'unassigned_orders': unassigned_orders,
#         })


#     def perform_create(self, serializer):
#         user = self.request.user

#         if not user.is_superuser:
#             order_address = serializer.validated_data.get('address')

#             # Ensure you're querying against the appropriate model
#             rider = Rider.objects.filter(
#                 Q(user__is_superuser=False, user__is_staff=True),
#                 user__profile__address=order_address
#             ).first()

#             if rider:
#                 serializer.save(user=user, rider=rider)
#             else:
#                 return Response(
#                     {'detail': 'No available riders for the specified address, order has been shifted to unassigned orders'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#         else:
#             serializer.save(user=user)


#     def perform_update(self, serializer):
#         user = self.request.user
#         instance = serializer.instance

#         if user.is_staff and not user.is_superuser:

#             serializer.save(
#                 total_price=serializer.validated_data.get(
#                     'total_price', instance.total_price),
#                 status=serializer.validated_data.get(
#                     'status', instance.status),
#                 invoice=serializer.validated_data.get(
#                     'invoice', instance.invoice),
#                 rider=instance.rider,
#                 user=instance.user
#             )
#         elif user.is_superuser:
#             serializer.save()
#         else:
#             return Response(
#                 {'detail': 'You do not have permission to update this order.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )


class CreateManualOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise ValidationError(
                "Authentication is required to create an order.")

        request_data = request.data
        request_data['user'] = request.user.id

        # Validation for required fields
        required_fields = ['mobile_number', 'product_name',
                           'order_details', 'ride_charges']
        missing_fields = [
            field for field in required_fields if not request_data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {
                                  ', '.join(missing_fields)}")

        # Validate mobile_number
        mobile_number = request_data.get('mobile_number')
        if not (mobile_number.isdigit() and 10 <= len(mobile_number) <= 12):
            raise ValidationError(
                "Invalid mobile number. Must be a numeric value with 10-12 digits.")

        # Validate product_name
        product_name = request_data.get('product_name')
        if len(product_name.strip()) < 3:
            raise ValidationError(
                "Product name must be at least 3 characters long.")

        # Validate order_details
        order_details = request_data.get('order_details')
        if len(order_details.strip()) < 10:
            raise ValidationError(
                "Order details must be at least 10 characters long.")

        # Validate ride_charges
        ride_charges = request_data.get('ride_charges')
        try:
            ride_charges = float(ride_charges)
            if ride_charges <= 0:
                raise ValidationError(
                    "Ride charges must be a positive number.")
        except ValueError:
            raise ValidationError("Ride charges must be a valid number.")

        try:
            valid_customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            raise NotFound("Customer matching query does not exist.")

        customer_lat = valid_customer.address_latitude
        customer_lon = valid_customer.address_longitude
        customer_address = valid_customer.address

        # Fetch and validate customer's location if missing
        if not customer_lat or not customer_lon or not customer_address:
            location_response = GetCustomerLocationView().get(request)
            if location_response.status_code == 200:
                location_data = location_response.data
                customer_lat = location_data.get('latitude')
                customer_lon = location_data.get('longitude')
                customer_address = location_data.get(
                    'address', 'Unknown Address')

                valid_customer.address_latitude = customer_lat
                valid_customer.address_longitude = customer_lon
                valid_customer.address = customer_address
                valid_customer.save()
            else:
                raise ValidationError("Customer must have a valid address with latitude and longitude. "
                                      "Please update your location details.")

        if not customer_lat or not customer_lon or not customer_address:
            raise ValidationError("Customer must have a valid address with latitude, longitude, and address. "
                                  "Please update your location details.")

        request_data['address'] = customer_address

        # Find the nearest rider
        nearest_rider = None
        min_distance = float('inf')
        riders = Rider.objects.filter(
            latitude__isnull=False, longitude__isnull=False)
        customer_coordinates = (float(customer_lat), float(customer_lon))

        for rider in riders:
            rider_coordinates = (float(rider.latitude), float(rider.longitude))
            distance = calculate_distance(
                *customer_coordinates, *rider_coordinates)
            if distance < min_distance:
                min_distance = distance
                nearest_rider = rider

        if not nearest_rider:
            raise NotFound("No available riders.")

        request_data['rider'] = nearest_rider.id

        serializer = ManualOrderSerializer(
            data=request_data, context={'request': request})
        if serializer.is_valid():
            manual_order = serializer.save(
                customer=valid_customer, rider=nearest_rider)
            return Response(
                {"message": "Order created successfully.", "order": serializer.data},
                status=200,
            )

        return Response(serializer.errors, status=400)

    def get_address_from_coordinates(self, latitude, longitude):
        """Fetch address from latitude and longitude using LocationIQ API."""
        try:
            api_url = "https://us1.locationiq.com/v1/reverse.php"
            api_key = "pk.8dcc4459a73a29fa7b1d8c7f011d1d7f"
            params = {
                "key": api_key,
                "lat": latitude,
                "lon": longitude,
                "format": "json",
            }

            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", "Unknown Address")
            return "Unknown Address"
        except Exception as e:
            print(f"Error: {e}")
            return "Error fetching address"


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    
    if not request.user.is_rider:
        return Response({"error": "Only admin and rider users can complete orders."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        try:
            # Fetch the order
            order = ManualOrder.objects.get(id=order_id)

            # Ensure all numeric fields are converted to Decimal
            ride_charges = Decimal(str(order.ride_charges))
            paid_amount = Decimal(str(order.paid_amount))
            total_price = Decimal(str(order.total_price))

            total_required = total_price + ride_charges

            # Debugging logs
            print(f"Order ID: {order_id}")
            print(f"Ride Charges: {ride_charges}, Paid Amount: {
                  paid_amount}, Total Price: {total_price}")
            print(f"Total Required: {total_required}")

            # Handle excess or deficit payment by the customer
            if paid_amount > total_required:
                excess_amount = paid_amount - total_required
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                customer_wallet.add_funds(excess_amount)
                print(f"Excess Amount: {
                      excess_amount} added to Customer Wallet.")
            elif paid_amount < total_required:
                deficit_amount = total_required - paid_amount
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                if customer_wallet.balance >= deficit_amount:
                    customer_wallet.deduct_funds(deficit_amount)
                    print(f"Deficit Amount: {
                          deficit_amount} deducted from Customer Wallet.")
                else:
                    return Response({"error": "Insufficient funds in customer's wallet to cover the deficit."},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Calculate shares for company and rider
            company_share_percentage = Decimal('0.07')
            company_share = ride_charges * company_share_percentage
            rider_share = ride_charges - company_share

            print(f"Company Share: {
                  company_share}, Rider Share: {rider_share}")

            # Update the company wallet
            company_wallet, _ = CompanyWallet.objects.get_or_create(
                id=1)  # Assuming single wallet for company
            company_wallet.add_funds(company_share)
            print("Company Wallet updated.")

            # Update the rider wallet
            rider_wallet, _ = RiderWallet.objects.get_or_create(
                rider=order.rider)
            rider_wallet.add_funds(rider_share)
            print("Rider Wallet updated.")

            # Mark the order as delivered
            order.status = 'delivered'
            order.save()
            print(f"Order {order_id} marked as delivered.")

            return Response({"message": "Order completed and wallets updated successfully."}, status=status.HTTP_200_OK)

        except ManualOrder.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error completing order: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'POST':
        # POST method: Rider submits total price, ride charges, and paid amount

        # Validate input data
        total_price = request.data.get('total_price')
        ride_charges = request.data.get('ride_charges')
        paid_amount = request.data.get('paid_amount')

        if not total_price or not ride_charges or not paid_amount:
            return Response({"error": "Total price, ride charges, and paid amount are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            total_price = Decimal(str(total_price))
            ride_charges = Decimal(str(ride_charges))
            paid_amount = Decimal(str(paid_amount))

            # Fetch the rider using the User instance related to the request.user
            try:
                rider = Rider.objects.get(user=request.user)
                # Ensure that the rider is the one for the order
                order = ManualOrder.objects.get(id=order_id, rider=rider)
            except ManualOrder.DoesNotExist:
                return Response({"error": "Order not found or you are not assigned to this order."},
                                status=status.HTTP_404_NOT_FOUND)

            total_required = total_price + ride_charges

            # Handle excess or deficit payment by the customer
            if paid_amount > total_required:
                excess_amount = paid_amount - total_required
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                customer_wallet.add_funds(excess_amount)
                print(f"Excess Amount: {
                      excess_amount} added to Customer Wallet.")
            elif paid_amount < total_required:
                deficit_amount = total_required - paid_amount
                customer_wallet, _ = CustomerWallet.objects.get_or_create(
                    customer=order.customer)
                if customer_wallet.balance >= deficit_amount:
                    customer_wallet.deduct_funds(deficit_amount)
                    print(f"Deficit Amount: {
                          deficit_amount} deducted from Customer Wallet.")
                else:
                    return Response({"error": "Insufficient funds in customer's wallet to cover the deficit."},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Calculate shares for company and rider
            company_share_percentage = Decimal('0.07')
            company_share = ride_charges * company_share_percentage
            rider_share = ride_charges - company_share

            print(f"Company Share: {
                  company_share}, Rider Share: {rider_share}")

            # Update the company wallet
            company_wallet, _ = CompanyWallet.objects.get_or_create(
                id=1)  # Assuming single wallet for company
            company_wallet.add_funds(company_share)
            print("Company Wallet updated.")

            # Update the rider wallet
            rider_wallet, _ = RiderWallet.objects.get_or_create(
                rider=order.rider)
            rider_wallet.add_funds(rider_share)
            print("Rider Wallet updated.")

            # Mark the order as delivered
            order.status = 'delivered'
            order.save()
            print(f"Order {order_id} marked as delivered.")

            return Response({"message": "Order completed and wallets updated successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error completing order: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminOrderListView(APIView):
    permission_classes = [IsSuperUser]

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
            rider = Rider.objects.get(user=user)
            print(rider)
        except Rider.DoesNotExist:
            return ManualOrder.objects.all()
        return ManualOrder.objects.all()


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        try:
            # Retrieve the order by ID
            order = ManualOrder.objects.get(id=order_id)

            # Check if the user is either the customer who placed the order or an admin
            if order.customer.user != request.user and not request.user.is_staff:
                raise PermissionDenied(
                    "You do not have permission to view this order.")

        except ManualOrder.DoesNotExist:
            raise NotFound("Order with the given ID does not exist.")

        # Serialize the order data
        serializer = ManualOrderSerializer(order, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

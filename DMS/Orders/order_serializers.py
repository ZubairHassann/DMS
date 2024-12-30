from rest_framework import serializers
from delivery.models import Order, ManualOrder
from datetime import timezone, timedelta


class ManualOrderSerializer(serializers.ModelSerializer):
    product_image = serializers.ImageField(required=False, allow_null=True)
    invoice = serializers.ImageField(required=False, allow_null=True)
    time_remaining = serializers.SerializerMethodField()
    # user = FKUserSerializer()
    # rider = FKRiderSerializer()

    class Meta:
        model = ManualOrder
        fields = ['id', 'user', 'name', 'mobile_number', 'address', 'product_name', 'product_image', 'quantity', 'unit', 'order_details',
                  'total_price', 'ride_charges', 'paid_amount', 'status', 'rider', 'invoice', 'created_at', 'updated_at', 'time_remaining']
        read_only_fields = ['id', 'created_at', 'updated_at',
                            'user', 'rider']  # User cannot set rider

    def get_time_remaining(self, obj):
        # Calculate time remaining until the 20-minute mark
        elapsed_time = timezone.now() - obj.created_at
        remaining_time = timedelta(minutes=20) - elapsed_time

        # Return remaining time if it's still within the 20-minute window, otherwise indicate expiration
        if remaining_time.total_seconds() > 0:
            return str(remaining_time)
        else:
            return "Expired"

    def __init__(self, *args, **kwargs):
        # Pop the request from the context
        request = kwargs['context']['request']
        super().__init__(*args, **kwargs)

        # Hide certain fields for normal users
        if not request.user.is_superuser and not request.user.is_staff:
            self.fields.pop('total_price')
            self.fields.pop('ride_charges')
            self.fields.pop('paid_amount')
            self.fields.pop('invoice')
            self.fields.pop('status')
        if not request.user.is_superuser and request.user.is_staff:
            self.fields.pop('mobile_number')

    def validate(self, data):
        if not data.get('name') or not data.get('address'):
            raise serializers.ValidationError(
                "Name, mobile number, and address are required.")
        if 'total_price' in data and data.get('total_price') <= 0:
            raise serializers.ValidationError(
                "Total price must be greater than 0.")
        if not data.get('product_name'):
            raise serializers.ValidationError("Product name is required.")
        if 'quantity' in data and (data.get('quantity') <= 0):
            raise serializers.ValidationError(
                "Quantity must be greater than 0.")

        # total_price = data.get('total_price', 0)
        # ride_charges = data.get('ride_charges', 0)
        # paid_amount = data.get('paid_amount', 0)

        # if paid_amount <= (total_price + ride_charges):
        #     raise serializers.ValidationError("Paid amount must be greater than the sum of total price and ride charges.")

        return data

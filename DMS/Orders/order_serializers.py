from rest_framework import serializers
from delivery.models import ManualOrder, CustomUser
from django.utils import timezone
from datetime import timedelta


class ManualOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    product_image = serializers.ImageField(required=False, allow_null=True)
    invoice = serializers.ImageField(required=False, allow_null=True)
    time_remaining = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()

    class Meta:
        model = ManualOrder
        fields = [
            'id', 'customer', 'customer_name',  'mobile_number', 'address', 'product_name',
            'product_image', 'quantity', 'unit', 'order_details', 'total_price',
            'ride_charges', 'paid_amount', 'status', 'rider', 'invoice', 'created_at',
            'updated_at', 'time_remaining',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'rider']

    def create(self, validated_data):
        customer = validated_data.pop('customer')
        order = ManualOrder.objects.create(customer=customer, **validated_data)
        return order

    def get_customer_name(self, obj):
        """Retrieve the customer's full name."""
        if obj.customer and obj.customer.user:
            return f"{obj.customer.user.first_name} {obj.customer.user.last_name}"
        return None

    def get_time_remaining(self, obj):
        elapsed_time = timezone.now() - obj.created_at
        remaining_time = timedelta(minutes=20) - elapsed_time

        if remaining_time.total_seconds() > 0:
            return remaining_time.total_seconds()
        else:
            return 0

    def get_mobile_number(self, obj):
        """Return mobile number if the user is an admin or the customer who placed the order."""
        request = self.context.get('request')
        if request and request.user.is_staff:
            return obj.mobile_number
        elif request and request.user == obj.customer:
            return obj.mobile_number
        return None

    def __init__(self, *args, **kwargs):
        request = kwargs['context'].get(
            'request') if 'context' in kwargs else None
        super().__init__(*args, **kwargs)

        if request and not (request.user.is_staff or request.user.is_superuser):
            self.fields.pop('total_price')
            self.fields.pop('ride_charges')
            self.fields.pop('paid_amount')
            self.fields.pop('invoice')
            self.fields.pop('status')

        if request and not request.user.is_staff:
            self.fields.pop('mobile_number')


def validate(self, data):
    errors = {}

    # Debug: Print incoming data
    print("Incoming data:", data)

    # Validate total_price
    if 'total_price' not in data:
        errors['total_price'] = ["Total price is required."]
    elif not isinstance(data['total_price'], (int, float)):
        try:
            # Try converting to float
            data['total_price'] = float(data['total_price'])
        except ValueError:
            errors['total_price'] = ["Total price must be a valid number."]
    elif data['total_price'] <= 0:
        errors['total_price'] = ["Total price must be greater than 0."]

    # Validate quantity
    if 'quantity' not in data:
        errors['quantity'] = ["Quantity is required."]
    elif not isinstance(data['quantity'], (int, float)):
        try:
            data['quantity'] = int(data['quantity'])  # Try converting to int
        except ValueError:
            errors['quantity'] = ["Quantity must be a valid number."]
    elif data['quantity'] <= 0:
        errors['quantity'] = ["Quantity must be greater than 0."]

    # Debug: Print validated data after processing
    print("Validated data:", data)

    if errors:
        raise serializers.ValidationError(errors)

    return data

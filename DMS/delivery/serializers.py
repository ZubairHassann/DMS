from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser, Rider, Customer, CustomerWallet, RiderWallet, CompanyWallet


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name',
                  'is_owner', 'is_active', 'is_staff']
        read_only_fields = ['is_active', 'is_staff', 'is_owner']


class RiderRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name',
                  'password', 'is_owner', 'is_staff']
        extra_kwargs = {
            'password': {'write_only': True},
            'is_owner': {'default': False},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_staff=True,
            is_owner=validated_data.get('is_owner', False)
        )
        return user


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            request=self.context.get('request'),
            email=data['email'],
            password=data['password']
        )

        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")


class RiderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Rider
        fields = ['id', 'user', 'vehicle_type',
                  'license_number', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'address',
                  'contact_number',]


class RiderSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Rider
        fields = ['email', 'first_name', 'last_name', 'password',
                  'vehicle_type', 'license_number', 'contact_number', 'address']

    def create(self, validated_data):
        # Extract user data
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        password = validated_data.pop('password')

        # Create the user
        user = CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )

        # Create the rider
        rider = Rider.objects.create(user=user, **validated_data)

        # Create the rider's wallet
        rider_wallet = RiderWallet.objects.create(rider=rider)

        # Optionally, you can add default funds to the wallet if required
        rider_wallet.add_funds(0)  # Add zero or default value

        return rider


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}


class CustomerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})
    address = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Customer
        fields = ['email', 'first_name', 'last_name',
                  'password', 'address', 'contact_number']

    def create(self, validated_data):
        # Extract user data
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        password = validated_data.pop('password')

        # Create the user
        user = CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        user.set_password(password)  # Set password using set_password for security
        user.save()

        customer = Customer.objects.create(user=user, **validated_data)
        return customer


class RiderWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderWallet
        fields = ['rider', 'balance']


class CustomerWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerWallet
        fields = ['balance']


class CustomerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Customer
        fields = ['email', 'first_name', 'last_name',
                  'password', 'address', 'contact_number']

    def create(self, validated_data):
        # Extract user data
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        password = validated_data.pop('password')

        # Create the user
        user = CustomUser.objects.create(
            email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save()

        # Create the customer
        customer = Customer.objects.create(user=user, **validated_data)
        return customer


class CompanyWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyWallet
        fields = ['balance']


class RiderSerializer(serializers.ModelSerializer):
    # To represent user by first name and last name
    user = serializers.StringRelatedField()

    class Meta:
        model = Rider
        fields = ['id', 'user', 'vehicle_type', 'license_number',
                  'contact_number', 'address',  'is_available', 'created_at', 'updated_at']

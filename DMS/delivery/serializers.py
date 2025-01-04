from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import (
    CustomUser,
    Rider,
    Customer,
    CustomerWallet,
    RiderWallet,
    CompanyWallet,
)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_owner",
            "is_active",
            "is_staff",
        ]
        read_only_fields = ["is_active", "is_staff", "is_owner"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            request=self.context.get("request"),
            email=data["email"],
            password=data["password"],
        )

        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")


class RiderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Rider
        fields = [
            "id",
            "user",
            "vehicle_type",
            "license_number",
            "created_at",
            "updated_at",
        ]


class CustomerSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "user",
            "address",
            "phone_number",
        ]


class RiderSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"})

    class Meta:
        model = Rider
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "vehicle_type",
            "license_number",
            "contact_number",
            "address",
        ]

    def create(self, validated_data):
        email = validated_data.pop("email")
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        password = validated_data.pop("password")
        user = CustomUser.objects.create(
            email=email, first_name=first_name, last_name=last_name,
            # is_rider=True
            is_staff=True,
            is_owner=validated_data.get("is_owner", False),
        )
        user.set_password(password)
        user.save()
        rider = Rider.objects.create(user=user, **validated_data)

        rider_wallet = RiderWallet.objects.create(rider=rider)

        rider_wallet.add_funds(0)

        return rider


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}


class CustomerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"})
    address = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Customer
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "address",
            "phone_number",
        ]

    def create(self, validated_data):
        email = validated_data.pop("email")
        first_name = validated_data.pop("first_name")
        last_name = validated_data.pop("last_name")
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(
            email=email, first_name=first_name, last_name=last_name, password=password
        )
        user.set_password(password)
        user.is_staff = True
        user.save()

        customer = Customer.objects.create(user=user, **validated_data)
        return customer


class RiderWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderWallet
        fields = ["rider", "balance"]


class CustomerWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerWallet
        fields = ["balance"]


class CompanyWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyWallet
        fields = ["balance"]


class RiderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Rider
        fields = [
            "id",
            "user",
            "vehicle_type",
            "license_number",
            "contact_number",
            "address",
            "is_available",
            "created_at",
            "updated_at",
        ]

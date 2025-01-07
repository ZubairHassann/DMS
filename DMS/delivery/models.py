from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
from decimal import Decimal
from django.dispatch import receiver
from django.db.models.signals import post_save
from geopy.distance import geodesic


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('A valid email address must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',
        blank=True
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_rider = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def update_email(self, new_email):
        if CustomUser.objects.filter(email=new_email).exclude(id=self.id).exists():
            raise ValueError('This email is already in use.')
        self.email = new_email
        self.save(update_fields=['email'])


class Rider(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle_type = models.CharField(
        max_length=50,
        choices=[
            ('bike', 'Bike'),
            ('car', 'Car'),
        ],
        default='bike'
    )
    license_number = models.CharField(max_length=20, unique=True)
    contact_number = models.CharField(max_length=15)
    address = models.TextField()
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.vehicle_type}"

    class Meta:
        verbose_name = 'Rider'
        verbose_name_plural = 'Riders'


class Customer(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    address_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    address_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - Customer"

    def save(self, *args, **kwargs):
        if not self.user.is_staff:
            self.user.is_staff = True
        super().save(*args, **kwargs)

    def get_full_address(self):
        return f"{self.address}, Lat: {self.address_latitude}, Lon: {self.address_longitude}"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def has_valid_address(self):
        """Check if customer has a valid address."""
        return bool(self.address and self.address_latitude and self.address_longitude)

    def update_location(self, latitude, longitude):
        """Update address location information."""
        self.address_latitude = latitude
        self.address_longitude = longitude
        self.save()


@receiver(post_save, sender=Customer)
def create_customer_wallet(sender, instance, created, **kwargs):
    if created:
        CustomerWallet.objects.create(customer=instance)


class RiderWallet(models.Model):
    rider = models.OneToOneField(
        Rider, on_delete=models.CASCADE, related_name='rider_wallet')
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def add_funds(self, amount):
        # Convert Decimal to float for addition
        self.balance = float(self.balance) + float(amount)
        self.balance = Decimal(str(self.balance))  # Convert back to Decimal
        self.save()

    def deduct_funds(self, amount):
        # Convert Decimal to float for subtraction
        self.balance = float(self.balance) - float(amount)
        self.balance = Decimal(str(self.balance))  # Convert back to Decimal
        self.save()

    def __str__(self):
        return f"{self.rider.user.first_name} {self.rider.user.last_name} - Rider Wallet"


class CustomerWallet(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name='customer_wallet')
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        # Convert Decimal to float for addition
        self.balance = float(self.balance) + float(amount)
        self.balance = Decimal(str(self.balance))  # Convert back to Decimal
        self.save()

    def deduct_funds(self, amount):
        # Convert Decimal to float for subtraction
        self.balance = float(self.balance) - float(amount)
        self.balance = Decimal(str(self.balance))  # Convert back to Decimal
        self.save()

    def __str__(self):
        return f"{self.customer.user.first_name} {self.customer.user.last_name} - Customer Wallet"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order {self.id} by {self.user.username}'


class ManualOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )

    UNIT_CHOICES = (
        ('kg', 'KG'),
        ('liter', 'Liter'),
        ('piece', 'Piece'),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='manual_orders',
        null=True,
        blank=True
    )
    rider = models.ForeignKey(
        Rider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    product_image = models.ImageField(
        upload_to='manual_orders/', blank=True, null=True
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    unit = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default='piece'
    )
    order_details = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0
    )
    ride_charges = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0
    )
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    invoice = models.ImageField(upload_to='invoices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    def __str__(self):
        customer_first_name = getattr(self.customer, 'user.first_name', None)
        return f'Manual Order {self.id} by {customer_first_name or "Unknown"}'

    def is_time_expired(self):
        """Check if 20 minutes have passed since the order was placed."""
        time_elapsed = now() - self.created_at
        return time_elapsed >= timedelta(minutes=20)

    def save(self, *args, **kwargs):
        if self.customer and (not self.delivery_latitude or not self.delivery_longitude):
            self.delivery_latitude, self.delivery_longitude = detect_customer_location(
                self.customer)
        super().save(*args, **kwargs)
        if self.delivery_latitude and self.delivery_longitude and not self.rider:
            assign_rider_to_order(self)


def detect_customer_location(customer):
    """Detect customer location if available."""
    if not customer or not hasattr(customer, 'address_latitude'):
        return None, None
    return customer.address_latitude, customer.address_longitude


def assign_rider_to_order(order):
    """Assign the nearest rider to an order."""
    riders = Rider.objects.filter(is_available=True).exclude(
        latitude=None, longitude=None)
    nearest_rider = None
    shortest_distance = float('inf')
    for rider in riders:
        if rider.latitude and rider.longitude:
            distance = calculate_distance(
                order.delivery_latitude, order.delivery_longitude,
                rider.latitude, rider.longitude, order.delivery_longitude,
                float(rider.latitude), float(rider.longitude)
            )
            if distance < shortest_distance:
                shortest_distance = distance
                nearest_rider = rider
                nearest_rider = rider
    if nearest_rider:
        order.rider = nearest_rider
        order.save()
        nearest_rider.is_available = False
        nearest_rider.save()


def get_rider_location(rider):
    return (float(rider.latitude), float(rider.longitude)) if rider.latitude and rider.longitude else None


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two geographic coordinates."""
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


class CompanyWallet(models.Model):
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        # Convert Decimal to float for addition
        self.balance = float(self.balance) + float(amount)
        self.balance = Decimal(str(self.balance))  # Convert back to Decimal
        self.save()

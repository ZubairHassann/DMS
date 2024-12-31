from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from django.dispatch import receiver
from django.db.models.signals import post_save
# from django.contrib.auth.models import User
# from django.contrib.gis.db.models.functions import Distance


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
        related_name='customuser_groups',  # Change related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # Change related_name
        blank=True
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

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
    # user = models.OneToOneField(
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     related_name='rider_profile'
    # )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
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
        max_digits=9, decimal_places=6, null=True, blank=True)  # Latitude
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)  # Longitude
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.vehicle_type}"

    class Meta:
        verbose_name = 'Rider'
        verbose_name_plural = 'Riders'


# class Customer(models.Model):
#     user = models.OneToOneField(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='customer_profile'
#     )
#     address = models.TextField(blank=True, null=True)
#     contact_number = models.CharField(max_length=15, blank=True, null=True)
#     latitude = models.DecimalField(
#         max_digits=9, decimal_places=6, null=True, blank=True)  # Latitude
#     longitude = models.DecimalField(
#         max_digits=9, decimal_places=6, null=True, blank=True)  # Longitude
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"{self.user.first_name} {self.user.last_name} (Customer)"

#     class Meta:
#         verbose_name = 'Customer'
#         verbose_name_plural = 'Customers'
class Customer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    address = models.TextField(max_length=100, null=False, default='None')
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


# Signal to automatically create a wallet when a customer is created
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
        # Ensure the amount is a Decimal
        amount = Decimal(amount)  # This converts amount to a Decimal type
        self.balance += amount
        self.save()


class CustomerWallet(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name='customer_wallet')
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()

    def deduct_funds(self, amount):
        amount = Decimal(amount)
        self.balance -= amount
        self.save()


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )

    # Use your existing User model
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    # cart_items = models.ManyToManyField(CartItem)  # Each order can have multiple cart items
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

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'is_staff': True}, related_name='assigned_orders'
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

    # Latitude and longitude fields to store location without using GeoDjango
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )  # For storing the latitude of delivery location
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )  # For storing the longitude of delivery location

    def __str__(self):
        return f'Manual Order {self.id} by {self.user.username}'

    def is_time_expired(self):
        """Check if 20 minutes have passed since the order was placed."""
        time_elapsed = timezone.now() - self.created_at
        return time_elapsed >= timedelta(minutes=20)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the order first
        # Assign a rider only if not already assigned and location is provided
        if not self.rider and self.delivery_latitude and self.delivery_longitude:
            assign_rider_to_order(self)


def assign_rider_to_order(order):
    """
    Assign the nearest available rider to the given order.
    """
    # Assuming the Rider model now has latitude and longitude fields
    nearest_rider = Rider.objects.filter(is_available=True) \
        .filter(latitude__isnull=False, longitude__isnull=False) \
        .annotate(
            distance=models.ExpressionWrapper(
                models.F('location').distance_from(
                    models.Point(order.delivery_longitude,
                                 order.delivery_latitude)
                ),
                output_field=models.DecimalField()
            )
    ) \
        .order_by('distance') \
        .first()

    if nearest_rider:
        order.rider = nearest_rider.user  # Assign the rider
        order.save()
        nearest_rider.is_available = False  # Mark the rider as unavailable
        nearest_rider.save()


class CompanyWallet(models.Model):
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()

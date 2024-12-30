from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_profile'
    )
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
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} (Customer)"

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'


class RiderWallet(models.Model):
    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rider_wallet')
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()


class CustomerWallet(models.Model):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_wallet')
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


class CompanyWallet(models.Model):
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    )

    # Use your existing User model
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    # The customer placing the order
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={
                              'is_staff': True}, related_name='assigned_orders')  # Rider assigned to the order
    name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    product_image = models.ImageField(
        upload_to='manual_orders/', blank=True, null=True)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default='piece')
    order_details = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    ride_charges = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    # New field for uploading invoice
    invoice = models.ImageField(upload_to='invoices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Manual Order {self.id} by {self.user.username}'

    def is_time_expired(self):
        """Check if 20 minutes have passed since the order was placed."""
        time_elapsed = timezone.now() - self.created_at
        return time_elapsed >= timedelta(minutes=20)
    

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

    # The customer placing the order
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    rider = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={
                              'is_staff': True}, related_name='assigned_orders')  # Rider assigned to the order
    name = models.CharField(max_length=255, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    product_name = models.CharField(max_length=255, blank=True, null=True)
    product_image = models.ImageField(
        upload_to='manual_orders/', blank=True, null=True)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    unit = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default='piece')
    order_details = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    ride_charges = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    paid_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, default=0.0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    # New field for uploading invoice
    invoice = models.ImageField(upload_to='invoices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Manual Order {self.id} by {self.user.username}'

    def is_time_expired(self):
        """Check if 20 minutes have passed since the order was placed."""
        time_elapsed = timezone.now() - self.created_at
        return time_elapsed >= timedelta(minutes=20)


class RiderWallet(models.Model):
    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rider_wallet')
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()


class CustomerWallet(models.Model):
    customer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_wallet')
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


class CompanyWallet(models.Model):
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def add_funds(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()

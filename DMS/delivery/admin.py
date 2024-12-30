from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Rider, Customer, CompanyWallet


class CustomUserAdmin(BaseUserAdmin):

    list_display = ('email', 'first_name', 'last_name',
                    'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_owner')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_owner'),
        }),
    )

    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_type', 'license_number',
                    'contact_number', 'is_available', 'created_at')
    search_fields = ('user__email', 'user__first_name',
                     'user__last_name', 'license_number')
    list_filter = ('vehicle_type', 'is_available', 'created_at')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'contact_number', 'address', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_filter = ('created_at',)


admin.site.register(CustomUser, CustomUserAdmin)

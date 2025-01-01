from rest_framework.permissions import BasePermission
from rest_framework import permissions


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is a superuser
        return request.user.is_superuser


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is a superuser
        return request.user.is_staff


class IsRider(permissions.BasePermission):
    """
    Custom permission to only allow riders to view orders.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_rider

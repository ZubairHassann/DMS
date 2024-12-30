from rest_framework.permissions import BasePermission

class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is a superuser
        return request.user.is_superuser
    

class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is a superuser
        return request.user.is_staff
    
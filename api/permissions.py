"""User permissions."""

from rest_framework.permissions import BasePermission


class IsSSUser(BasePermission):
    '''Allow acces only socio user'''

    def has_permission(self, request, view):
        return request.META.get('HTTP_TOKEN') == 'zzdtco5egt3pu6jjjo4bdt9vwx8mjdmo'
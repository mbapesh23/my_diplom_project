from rest_framework import permissions

class IsSupplier(permissions.BasePermission):
    """
    Разрешает доступ только пользователям, входящим в группу 'Supplier'.
    """
    def has_permission(self, request, view):
        # Суперпользователь проходит всегда
        if request.user and request.user.is_superuser:
            return True
        
        # Проверяем принадлежность к группе
        return request.user.groups.filter(name='Supplier').exists()
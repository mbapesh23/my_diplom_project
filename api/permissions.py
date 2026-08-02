from rest_framework import permissions

class IsSupplier(permissions.BasePermission):
    
    def has_permission(self, request, view):
        if request.user and request.user.is_superuser:
            return True
        
        # Проверка по группе Supplier
        return request.user and request.user.groups.filter(name='Supplier').exists()

    def has_object_permission(self, request, view, obj):
        # Разрешаем доступ поставщику только к его собственным данным
        if isinstance(obj, Shop):
            return obj.user == request.user or request.user.is_superuser
        elif hasattr(obj, 'user'): # Для моделей Contact, Order и других связанных с пользователем
            return obj.user == request.user or request.user.is_superuser
        return False
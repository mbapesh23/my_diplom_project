from rest_framework import permissions


class IsSupplier(permissions.BasePermission):
    
    def has_permission(self, request, view):
        # Суперпользователь всегда проходит
        if request.user and request.user.is_superuser:
            return True
        
        # Проверка ринадлежности к группе по первичному ключу
        return request.user.groups.filter(name='Supplier').exists()

    def has_object_permission(self, request, view, obj):
        # Разрешаем доступ поставщику только к его собственным данным
        if isinstance(obj, Shop):
            return obj.user == request.user or request.user.is_superuser
        return False
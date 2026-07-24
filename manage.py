import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diploma_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Проверьте установлен ли Django."
        ) from exc
    execute_from_command_line(sys.argv)

# Можете проверить при помощи тест файла.
    #  python manage.py test api.tests
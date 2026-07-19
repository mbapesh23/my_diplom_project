import os
import sys
from datetime import datetime
from pathlib import Path

# --- 1. НАСТРОЙКА DJANGO ДЛЯ ЗАПУСКА КАК СКРИПТА ---
PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diploma_backend.settings')
import django
django.setup()

# --- 2. ИМПОРТ МОДЕЛЕЙ ---
from api.models import (
    User, Contact, Shop, Category, Product, 
    ProductInfo, Parameter, ProductParameter,
    Order, OrderItem
)
import yaml
from django.contrib.auth.hashers import make_password
from django.db import transaction


def load_full_data_from_yaml(file_path):
    """
    Основная функция загрузки данных из YAML в БД.
    Адаптирована под структуру prices.yaml пользователя.
    """
    print(f"[INFO] Attempting to open full dataset: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"[FATAL ERROR] File {file_path} not found.")
        return
    except yaml.YAMLError as e:
        print(f"[FATAL ERROR] YAML syntax error: {e}")
        return

    if not isinstance(data, dict):
        print("[FATAL ERROR] Invalid YAML format. Root element must be a dictionary.")
        return

    success_count = 0
    fail_count = 0

    
    # ЭТАП 1: ПОЛЬЗОВАТЕЛИ И КОНТАКТЫ
    
    print("\n--- [1/4] Processing Users & Contacts ---")
    
    for user_data in data.get('users', []):
        username = user_data.get('username')
        email = user_data.get('email')
        
        if not username or not email:
            continue
            
        password_hash = make_password(user_data.get('password'))
        
        try:
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'is_staff': user_data.get('is_staff', False),
                    'password': password_hash,
                    'is_active': True
                }
            )
            status = "Created" if created else "Updated"
            print(f"  -> User '{username}': {status}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to save User '{username}': {e}")
            fail_count += 1

    # Контакты теперь ищем строго по Email, так как он Unique в модели
    for contact_data in data.get('contacts', []):
        email = contact_data.get('email')
        
        try:
            # Находим владельца контакта через связанное поле user__username
            username = contact_data.get('user')
            user_obj = User.objects.get(username=username)
            
            contact_defaults = {k: v for k, v in contact_data.items() if k not in ['user', 'email']}
            contact, created = Contact.objects.update_or_create(
                user=user_obj,
                email=email,
                defaults=contact_defaults
            )
            print(f"  -> Contact ({email}): {'Created' if created else 'Updated'}")
            success_count += 1
        except User.DoesNotExist:
            print(f"  [WARN] Cannot create contact. User '{username}' not found.")
            fail_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to save Contact ({email}): {e}")
            fail_count += 1

    
    # ЭТАП 2: КАТАЛОГ (КАТЕГОРИИ И ПАРАМЕТРЫ)
    
    print("\n--- [2/4] Processing Catalog Structure ---")
    
    shop_name = data.get('store', 'Default Shop')
    shop, _ = Shop.objects.get_or_create(name=shop_name)
    print(f"  -> Shop context set to: {shop.name}")

    category_mapping = {}
    # Важно: в вашем YAML id категории это int (1, 2), приводим к строке для ключа словаря
    for cat_data in data.get('categories', []):
        cid = str(cat_data.get('id')) 
        cname = cat_data.get('name')
        if cid and cname:
            category, created = Category.objects.get_or_create(name=cname)
            category_mapping[cid] = category
            print(f"    * Category [{cid}]: {cname}")

    param_mapping = {}
    for param_data in data.get('parameters', []):
        name = param_data.get('name')
        if name:
            obj, _ = Parameter.objects.get_or_create(name=name)
            param_mapping[name] = obj
            print(f"    * Parameter: {name}")

    
    # ЭТАП 3: ТОВАРЫ И ИНФОРМАЦИЯ О НИХ (PRODUCT INFO)
    
    print("\n--- [3/4] Processing Goods & Prices ---")
    
    for good_data in data.get('goods', []):
        name = good_data.get('name')
        ext_id = good_data.get('id')
        
        if not name or not ext_id:
            print("  [SKIP] Item without name or external ID.")
            continue

        try:
            product, prod_created = Product.objects.update_or_create(
                name=name,
                defaults={
                    'description': f"Model: {good_data.get('model', '')}",
                    'supplier': good_data.get('supplier', '')
                }
            )

            # Категория приходит числом (1 или 2), переводим в строку для поиска в mapping
            cat_id = str(good_data.get('category'))
            category = category_mapping.get(cat_id)
            if category and category not in product.categories.all():
                product.categories.add(category)

            info_defaults = {
                'shop': shop,
                'price': float(good_data.get('price', 0)),
                'price_rrc': float(good_data.get('price_rrc', 0)),
                'quantity': int(good_data.get('quantity', 0)),
                'model': good_data.get('model', ''),
                'name': name
            }

            prod_info, info_created = ProductInfo.objects.update_or_create(
                product=product,
                external_id=ext_id,
                defaults=info_defaults
            )
            
            # Параметры приходят в нижнем регистре ('material', 'color')
            params_dict = good_data.get('parameters', {})
            for p_key, val in params_dict.items():
                # Пробуем найти параметр по точному совпадению регистра
                parameter_obj = param_mapping.get(p_key)
                # Если не нашли (т.к. в Mapping ключи "Материал", "Цвет"), ищем без учета регистра
                if not parameter_obj:
                    for map_name, obj in param_mapping.items():
                        if map_name.lower() == p_key.lower():
                            parameter_obj = obj
                            break
                
                if parameter_obj:
                    ProductParameter.objects.update_or_create(
                        product_info=prod_info,
                        parameter=parameter_obj,
                        defaults={'value': str(val)}
                    )
                    
            s_status = "Created" if info_created else "Updated"
            print(f"  -> Product Info '{name}' ({ext_id}): {s_status}")
            success_count += 1
            
        except Exception as e:
            print(f"  [ERROR] Failed to save Product/Goods '{name}': {e}")
            fail_count += 1

    
    # ЭТАП 4: ЗАКАЗЫ И ПОЗИЦИИ
    
    print("\n--- [4/4] Processing Orders ---")
    
    for order_data in data.get('orders', []):
        username = order_data.get('user')
        contact_email = order_data.get('contact')
        
        try:
            user_obj = User.objects.get(username=username)
            contact_obj = Contact.objects.get(email=contact_email)
            
            items_data = order_data.get('items', [])
            total_amount_calc = sum(float(item['price_at_order']) * int(item['quantity']) for item in items_data)

            needed_ids = [item['product_info_id'] for item in items_data]
            info_map = {pi.external_id: pi for pi in ProductInfo.objects.filter(external_id__in=needed_ids)}

            with transaction.atomic():
                order, order_created = Order.objects.update_or_create(
                    user=user_obj,
                    contact=contact_obj,
                    status=order_data.get('status', 'NEW'),
                    defaults={
                        'total_amount': total_amount_calc,
                        'created_at': datetime.fromisoformat(order_data.get('created_at').replace('Z', '+00:00')) if order_data.get('created_at') else None
                    }
                )
                
                o_status = "Created" if order_created else "Updated"
                print(f"  -> Order #{order.id} for '{username}': {o_status} | Total: {order.total_amount}")
                success_count += 1

                if not order_created:
                    order.items.all().delete()

                for item_data in items_data:
                    prod_info = info_map.get(item_data['product_info_id'])
                    
                    if not prod_info:
                        print(f"    [WARN] ProductInfo ID '{item_data['product_info_id']}' not found. Skipping item.")
                        fail_count += 1
                        continue

                    OrderItem.objects.create(
                        order=order,
                        product_info=prod_info,
                        store=shop,
                        quantity=int(item_data['quantity']),
                        price_at_order=float(item_data['price_at_order'])
                    )
                    
        except (User.DoesNotExist, Contact.DoesNotExist) as e:
            print(f"  [WARN] Skipping Order due to missing dependency: {e}")
            fail_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to process Order block for '{username}': {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"[FINAL SUMMARY] Successfully processed: {success_count}. Errors/Warnings: {fail_count}.")
    print("=" * 60)


if __name__ == '__main__':
    target_file = PROJECT_ROOT / 'media' / 'prices.yaml'
    
    if not target_file.exists():
        print(f"[FATAL] Data file not found at {target_file}")
    else:
        load_full_data_from_yaml(target_file)
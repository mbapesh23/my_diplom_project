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
from django.conf import settings
from django.db.models import Sum, F

def field_exists(model, field_name):
    try:
        return any(f.name == field_name for f in model._meta.get_fields())
    except Exception:
        return False

def load_full_data_from_yaml(file_path):
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
        print("[FATAL ERROR] Invalid YAML format.")
        return

    # === ДИАГНОСТИКА: Выведем сырые данные заказов ===
    print("\n--- [DIAGNOSTIC] RAW ORDERS DATA FROM YAML ---")
    orders_raw = data.get('orders', [])
    print(orders_raw)
    print("--- [END DIAGNOSTIC] ---\n")

    success_count = 0
    fail_count = 0

    # ЭТАП 1: ПОЛЬЗОВАТЕЛИ
    print("\n--- [1/4] Processing Users & Contacts ---")
    owner_username = None
    for user_data in data.get('users', []):
        username = user_data.get('username')
        email = user_data.get('email')
        password_hash = make_password(user_data.get('password'))
        
        if not username or not email:
            continue

        try:
            user_defaults = {
                'email': email,
                'password': password_hash,
                'is_active': True,
            }
            user, created = User.objects.update_or_create(
                username=username,
                defaults=user_defaults
            )
            
            if not owner_username:
                owner_username = username

            status = "Created" if created else "Updated"
            print(f"  -> User '{username}': {status}")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to save User '{username}': {e}")
            fail_count += 1

    # ЭТАП 2: МАГАЗИН, КАТАЛОГ
    print("\n--- [2/4] Processing Catalog Structure & Main Shop ---")
    shop_name = data.get('store', 'Default Marketplace')

    try:
        owner = User.objects.get(username=owner_username)
    except User.DoesNotExist:
        print("[FATAL ERROR] Owner not found in DB. Stopping loader.")
        return

    shop, _ = Shop.objects.get_or_create(
        name=shop_name,
        user=owner
    )
    print(f"  -> Shop '{shop.name}' (Owner: {owner.username}) ready.")

    category_mapping = {}
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

    # ЭТАП 3: ТОВАРЫ
    print("\n--- [3/4] Processing Goods & Prices ---")
    ProductInfo.objects.filter(shop=shop).delete()

    for good_data in data.get('goods', []):
        name = good_data.get('name')
        ext_id = good_data.get('id')
        if not name or not ext_id:
            print("  [SKIP] Item without name or external ID.")
            continue

        try:
            product, prod_created = Product.objects.update_or_create(
                name=name,
                defaults={}
            )

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

            lookup_kwargs = {'product': product, 'shop': shop}
            
            prod_info, info_created = ProductInfo.objects.update_or_create(
                defaults=info_defaults,
                **lookup_kwargs
            )
            
            params_dict = good_data.get('parameters', {})
            for p_key, val in params_dict.items():
                parameter_obj = param_mapping.get(p_key)
                if parameter_obj:
                    ProductParameter.objects.update_or_create(
                        product_info=prod_info,
                        parameter=parameter_obj,
                        defaults={'value': str(val)}
                    )
            
            s_status = "Created" if info_created else "Updated"
            print(f"  -> Product Info '{name}': {s_status}")
            success_count += 1

        except Exception as e:
            print(f"  [ERROR] Failed to save Product/Goods '{name}': {e}")
            fail_count += 1

    # ЭТАП 4: КОНТАКТЫ (Создаем уникальные контакты из заказов ДО самих заказов)
    print("\n--- [4/4] Pre-processing Contacts from Orders ---")
    
    unique_contact_emails = set()
    for order_data in data.get('orders', []):
        contact_email = order_data.get('contact')
        if contact_email:
            unique_contact_emails.add(contact_email)

    # Если emails найдены — создаем контакты
    if unique_contact_emails:
        try:
            buyer_user = User.objects.get(username=owner_username)
            for email in unique_contact_emails:
                contact, created = Contact.objects.update_or_create(
                    user=buyer_user,
                    email=email,
                    defaults={'name': 'Контакт из заказа'}
                )
                print(f"  -> Contact ({email}): {'Created' if created else 'Updated'}")
                success_count += 1
        except User.DoesNotExist:
            print(f"[WARN] Buyer user '{owner_username}' not found for contacts.")
            fail_count += 1
    else:
        print("  [WARN] No contact emails found in orders block of YAML.")

    # ЭТАП 5: ЗАКАЗЫ
    print("\n--- [5/4] Processing Orders ---")
    for order_data in data.get('orders', []):
        username = order_data.get('user')
        contact_email = order_data.get('contact')

        try:
            user_obj = User.objects.get(username=username)
            contact_obj = Contact.objects.get(email=contact_email) 

            items_data = order_data.get('items', [])
            total_amount_calc = sum(
                float(item.get('price_at_order', 0)) * int(item.get('quantity', 1))
                for item in items_data
            )

            with transaction.atomic():
                order_defaults = {
                    'total_amount': total_amount_calc,
                    'status': order_data.get('status', 'NEW')
                }
                
                order, order_created = Order.objects.update_or_create(
                    user=user_obj,
                    contact=contact_obj,
                    defaults=order_defaults
                )

                if not order_created:
                    order.items.all().delete()

                for item_data in items_data:
                    pi_ext_id = item_data.get('product_info_id')
                    
                    prod_info_qs = ProductInfo.objects.filter(product__name=item_data.get('name'), shop=shop)
                    prod_info = prod_info_qs.first()
                    
                    if not prod_info:
                        print(f"    [WARN] ProductInfo for '{item_data.get('name')}' not found. Skipping item.")
                        continue

                    OrderItem.objects.create(
                        order=order,
                        product_info=prod_info,
                        quantity=int(item_data.get('quantity', 1)),
                        price_at_order=float(item_data.get('price_at_order', 0))
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
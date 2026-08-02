import json
import yaml
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from django.db import transaction

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_yaml(request):
    try:
        if isinstance(request.data, dict):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
            
        yaml_url = data.get("url")
        
        if not yaml_url:
            return JsonResponse({"status": "error", "message": "No URL provided"}, status=400)

        validator = URLValidator()
        validator(yaml_url)

        response = requests.get(yaml_url, timeout=15)
        response.raise_for_status()
        stream = response.content
        
        data_yml = yaml.safe_load(stream)
        if not isinstance(data_yml, dict):
            raise ValueError("Корень YAML должен быть словарём")

        with transaction.atomic():  # Вся загрузка атомарна
            shop, _ = Shop.objects.get_or_create(
                user=request.user,
                defaults={'name': data_yml.get('shop')}
            )
            
            for category in data_yml.get('categories', []):
                Category.objects.update_or_create(id=category['id'], defaults={'name': category['name']})

            param_mapping = {}
            for param_data in data_yml.get('parameters', []):
                name = param_data.get('name')
                if name:
                    obj, _ = Parameter.objects.get_or_create(name=name)
                    param_mapping[name] = obj

            cat_mapping = {}
            for cat_data in data_yml.get('categories', []):
                cid = str(cat_data.get('id'))
                cname = cat_data.get('name')
                if cid and cname:
                    obj, _ = Category.objects.get_or_create(name=cname)
                    cat_mapping[cid] = obj

            ProductInfo.objects.filter(shop=shop).delete()

            for item in data_yml.get('goods', []):
                product, _ = Product.objects.update_or_create(name=item['name'])
                
                prod_info_defaults = {
                    'shop': shop,
                    'price': float(item.get('price', 0)),
                    'price_rrc': float(item.get('price_rrc', 0)),
                    'quantity': int(item.get('quantity', 0)),
                    'model': item.get('model', ''),
                    'name': item.get('name'),
                }
                prod_info, info_created = ProductInfo.objects.update_or_create(
                    product=product,
                    external_id=item.get('id'),
                    defaults=prod_info_defaults
                )
                
                params_dict = item.get('parameters', {})
                for p_key, val in params_dict.items():
                    parameter_obj = param_mapping.get(p_key)
                    if parameter_obj:
                        ProductParameter.objects.update_or_create(
                            product_info=prod_info,
                            parameter=parameter_obj,
                            defaults={'value': str(val)}
                        )
                
                cat_id = str(item.get('category'))
                category = cat_mapping.get(cat_id)
                if category and category not in product.categories.all():
                    product.categories.add(category)

        return JsonResponse({'Status': True})

    except KeyError as e:
        return JsonResponse({'Status': False, 'Errors': f'Некорректный формат данных: отсутствует поле {e}'}, status=400)
    except (ValidationError, requests.RequestException, yaml.YAMLError) as e:
        return JsonResponse({'Status': False, 'Errors': str(e)}, status=400)
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Fatal error in upload_yaml: {e}", exc_info=True)
        return JsonResponse({'Status': False, 'Errors': 'Внутренняя ошибка сервера'}, status=500)
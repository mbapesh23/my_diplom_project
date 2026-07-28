import json
import yaml
import requests
from django.http import JsonResponse
# Убран csrf_exempt — сессионная аутентификация DRF защищает от CSRF автоматически
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter


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
            raise ValueError("Корень YAML должен быть словарем")

        #Привязываем магазин к конкретному пользователю-поставщику
        shop, _ = Shop.objects.get_or_create(
            user=request.user,
            defaults={'name': data_yml.get('shop')}
        )
        
        for category in data_yml.get('categories', []):
            cat_obj, _ = Category.objects.update_or_create(
                id=category['id'],
                defaults={'name': category['name']}
            )

        ProductInfo.objects.filter(shop=shop).delete()

        for item in data_yml.get('goods', []):
            product, _ = Product.objects.get_or_create(name=item['name'])
            
            product_info = ProductInfo.objects.create(
                product=product,
                shop=shop,
                external_id=item.get('id'),
                model=item.get('model'),
                name=item.get('name'),
                quantity=item.get('quantity', 0),
                price=item['price'],
                price_rrc=item.get('price_rrc', item['price']),
            )
            
            for name, value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=value
                )

        return JsonResponse({'Status': True})

    except KeyError as e:
        return JsonResponse({'Status': False, 'Errors': f'Некорректный формат данных: отсутствует поле {e}'}, status=400)
    except (ValidationError, requests.RequestException, yaml.YAMLError) as e:
        return JsonResponse({'Status': False, 'Errors': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'Status': False, 'Errors': f'Внутренняя ошибка сервера: {str(e)}'}, status=500)
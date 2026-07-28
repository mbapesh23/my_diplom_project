from api.views import CartViewSet

try:
    instance = CartViewSet()
    print("[SUCCESS] CartViewSet imported and instantiated successfully.")
    
    if hasattr(instance, 'my_cart'):
        print("[SUCCESS] Method 'my_cart' exists in the class.")
    else:
        print("[FATAL ERROR] Method 'my_cart' is MISSING in CartViewSet.")
        
except Exception as e:
    print(f"[FATAL IMPORT ERROR]: {e}")
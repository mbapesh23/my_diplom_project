from django.contrib import admin 
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from .views import index, docs, partner_update

urlpatterns = [ 
    path('', index, name='index'), 
    path('docs/', docs, name='docs'), 
    path('partner/update/', partner_update, name='partner_update'), 
    path('api/', include('api.urls')), 
    path('admin/', admin.site.urls),
    # === ENDPOINTЫ АВТОДОКУМЕНТАЦИИ ===
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularRedocView.as_view(url='/api/schema/'), name='redoc'),

]

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda request: redirect('gestion_ventas:login_view')),
    path('admin/', admin.site.urls),
    path('panaderia/', include('gestion_ventas.urls')),
]


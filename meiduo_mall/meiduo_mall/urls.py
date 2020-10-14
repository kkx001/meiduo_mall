"""meiduo_mall URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('^', include('users.urls', namespace='users')),  # 用户总路由
    re_path('^', include('contents.urls', namespace='contents')),  # 首页
    re_path('^', include('verifications.urls')),  # 验证码
    re_path('^', include('areas.urls', namespace='areas')),  # 省市区三级
    re_path('^', include('goods.urls', namespace='goods')),  # 商品路由
    re_path('^search/', include('haystack.urls')),  # 搜索路由
    re_path('^', include('carts.urls', namespace='carts')),  # 购物车路由
    re_path('^', include('orders.urls', namespace='orders')),  # 订单
    re_path('^', include('payment.urls', namespace='payment')),  # 支付
]

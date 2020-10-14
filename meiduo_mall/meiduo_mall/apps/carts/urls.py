from django.urls import re_path
from . import views

app_name = 'carts'

urlpatterns = [
    re_path('^carts/$', views.CartsView.as_view(), name='info'),  # 购物车页面
    re_path('^carts/selection/$', views.CartsSelectAllView.as_view()),  # 全选
    re_path('^carts/simple/$', views.CartSimpleView.as_view()),  # 小购物车
]

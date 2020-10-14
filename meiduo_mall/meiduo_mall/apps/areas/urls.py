from django.contrib import admin
from django.urls import path, include, re_path
from . import views

app_name = 'areas'

urlpatterns = [
    re_path('^areas/$', views.AreasView.as_view()), #省市区三级联动
]

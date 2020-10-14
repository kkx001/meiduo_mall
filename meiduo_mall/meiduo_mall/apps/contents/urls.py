
from django.urls import re_path
from . import views


app_name = 'contents'


urlpatterns = [

    re_path('^$', views.IndexView.as_view(), name='index')
]

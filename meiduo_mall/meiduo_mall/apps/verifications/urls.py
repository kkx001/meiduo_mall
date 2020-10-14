from django.urls import re_path
from . import views

app_name = 'verifications'

urlpatterns = [
    re_path('^image_codes/(?P<uuid>[\w-]+)/$', views.ImageCodeView.as_view()),  # 图片验证码
    re_path('^sms_codes/(?P<mobile>1[3-9]\d{9})/', views.SMSCodeView.as_view()), #短信验证码
]

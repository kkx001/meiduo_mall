from django.urls import path, include, re_path
from . import views

app_name = 'payment'

urlpatterns = [
    re_path('^payment/(?P<order_id>\d+)/$', views.PaymentView.as_view()),  # 支付请求
    re_path("^payment/status/$", views.PaymentStatusView.as_view()),  # 保存订单支付结果
]

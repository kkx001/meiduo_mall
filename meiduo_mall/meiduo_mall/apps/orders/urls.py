from django.urls import path, include, re_path
from . import views

app_name = 'orders'

urlpatterns = [
    re_path('^orders/settlement/$', views.OrderSettlementView.as_view(), name='settlement'),  # 结算订单
    re_path('^orders/commit/$', views.OrderCommitView.as_view()),  # 提交订单
    re_path('^orders/success/$', views.OrderSuccessView.as_view()),  # 提交订单成功
    re_path('^orders/info/(?P<page_num>\d+)/$', views.UserOrderInfoView.as_view(), name='info'),  # 我的订单
    re_path('^orders/comment/$', views.OrderCommentView.as_view()), #订单评价
    re_path('^comments/(?P<sku_id>\d+)/$', views.GoodsCommentView.as_view()), #评价信息
]

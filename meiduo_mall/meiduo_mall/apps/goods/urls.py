
from django.urls import re_path
from . import views


app_name = 'goods'


urlpatterns = [

    re_path('^list/(?P<category_id>\d+)/(?P<page_num>\d+)/$', views.ListView.as_view(), name='list'), #商品列表页
    re_path('^hot/(?P<category_id>\d+)/$', views.HotGoodsView.as_view()), #热销排行
    re_path('^detail/(?P<sku_id>\d+)/$', views.DetailView.as_view(), name="detail"), #商品详情页
    re_path('^detail/visit/(?P<category_id>\d+)/$', views.DetailVisitView.as_view()), #统计访问量
]

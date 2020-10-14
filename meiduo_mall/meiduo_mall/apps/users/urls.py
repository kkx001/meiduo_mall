from django.contrib import admin
from django.urls import path, include, re_path
from . import views

app_name = 'users'

urlpatterns = [

    re_path("^register/$", views.RegisterView.as_view(), name='register'),  # 注册
    re_path('^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),  # 用户名重复
    re_path('^mobile/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),  # 手机号重复
    re_path('^login/$', views.LoginView.as_view(), name='login'),  # 登陆
    re_path('^logout/$', views.LogoutView.as_view(), name='logout'),  # 登出
    re_path('^info/$', views.UserInfoView.as_view(), name='info'),  # 用户中心
    re_path('^emails/$', views.EmailView.as_view()),  # 添加邮箱
    re_path('^emails/verification/$', views.VerifyEmailView.as_view()),  # 验证邮箱
    re_path('^addresses/$', views.AddressView.as_view(), name="address"),  # 展示用户地址
    re_path('^addresses/create/$', views.AddressCreateView.as_view()),  # 新增用户地址
    re_path('^addresses/(?P<address_id>\d+)/$', views.UpdateDestroyAddressView.as_view()),  # 更新和删除用户地址
    re_path('^addresses/(?P<address_id>\d+)/default/$', views.DefaultAddressView.as_view()),  # 设置默认地址
    re_path('^addresses/(?P<address_id>\d+)/title/$', views.UpdateTitleAddressView.as_view()),  # 设置地址标题
    re_path('^browse_histories/$', views.UserBrowsHistory.as_view()), #用户浏览记录

]

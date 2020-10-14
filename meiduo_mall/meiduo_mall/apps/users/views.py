from django.shortcuts import render, redirect, reverse
from django import http
from django.views import View

import re
from users.models import User
from django.db import DatabaseError
from django.contrib.auth import login, authenticate, logout
from meiduo_mall.utils.response_code import RETCODE
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin
from meiduo_mall.utils.views import LoginRequiredJSONMixin
from celery_tasks.email.tasks import send_verify_email
from users.utils import generate_verify_email_url, check_verify_email_token
from . import constants
from .models import Address
from goods.models import SKU
from carts.utils import merge_carts_cookies_redis

import json

import logging

# 创建日志输出器
logger = logging.getLogger('django')


class UsernameCountView(View):
    def get(self, request, username):
        """
        判断用户名是否重复
        :param request: 用户名
        :param username:
        :return: JSON
        """
        # 实现主体业务逻辑，使用username查询对应的记录的条数，filter返回的是满足条件的结果集
        count = User.objects.filter(username=username).count()

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """

        :param request: 请求对象
        :param mobile: 手机号
        :return: JSON
        """
        # 使用mobile查询对应的记录条数
        count = User.objects.filter(mobile=mobile).count()

        # 返回结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """提供注册页面
        :request: 请求对象
        return :注册页面"""

        return render(request, 'register.html')

    def post(self, request):
        """实现注册的业务逻辑"""

        # 1.接收参数
        username = request.POST.get("username")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        mobile = request.POST.get("mobile")
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get("allow")

        # 校验参数：要保证前后端校验的逻辑相同，不能够让用户越过前端发送请求，要保证后端的安全

        # 校验参数是否完整、齐全
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名111')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 判断手机号是否合法
        if not re.match(r"^1[3-9]\d{9}$", mobile):
            return http.HttpResponseForbidden("请输入正确的手机号")

        # 判断短信验证码是否正确
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)

        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': "短信验证码已失效"})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'register.html', {'sms_code_errmsg': "短信验证码错误"})

        # 判断是否勾选了正确的用户协议
        if allow != 'on':
            return http.HttpResponseForbidden("请勾选用户协议")

        # 保存注册数据，是注册业务的核心
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        # 登入用户，实现状态保持
        login(request, user)

        # 响应注册结果，重定向到首页
        response = redirect(reverse('contents:index'))

        # 为了实现在首页上展示用户名信息，将用户名缓存到cookie中
        response.set_cookie('username', user.username, max_age=3600 * 24 * 7)

        # 重定向到首页
        return response


class LoginView(View):
    """用户名登录"""

    def get(self, request):
        """
        提供登陆界面
        :param request: 请求对象
        :return: 登陆界面
        """
        return render(request, 'login.html')

    def post(self, request):
        """
        实现登陆界面
        :param request: 请求对象
        :return: 登陆结果
        """

        # 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 校验参数
        # 判断参数是否齐全
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9-_]{5,20}$', username):
            return http.HttpResponseForbidden("请输入正确的用户名或手机号")

        # 判断密码是否是8-20个字符
        if not re.match(r"^[a-zA-Z0-9]{8,20}$", password):
            return http.HttpResponseForbidden("密码最少8位，最长20位")

        # 认证登陆用户,判断用户是否存在，如果用户存在，再校验密码是否正确
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})

        # 实现状态保持
        login(request, user)

        # 设置状态保持的周期
        if remembered != 'on':
            # 如果没有记住登陆，状态保持在浏览器会话结束后就销毁
            request.session.set_expiry(0)

        else:
            # 记住用户名,None表示两周后过期
            request.session.set_expiry(None)

        # 响应登陆结果
        # 先取出next
        next = request.GET.get('next')
        if next:
            # 重定向到next
            response = redirect(next)
        else:
            # 重定向到首页
            response = redirect(reverse('contents:index'))

        # 将用户名保存到coojie中，便于在首页中显示用户名信息
        response.set_cookie('username', user.username, max_age=3600 * 24 * 7)

        # 用户登录成功，合并cookie购物车到redis购物车
        response = merge_carts_cookies_redis(request=request, user=user, response=response)

        # 响应登陆结果
        return response


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        """实现退出登录逻辑"""

        # 清理session
        logout(request)

        # 退出登陆重定向到首页
        response = redirect(reverse('contents:index'))

        # 退出时，清除cookie中的username
        response.delete_cookie('username')

        return response


class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self, request):
        """提供个人中心页面"""

        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html', context=context)


class EmailView(LoginRequiredJSONMixin, View):
    """添加邮箱"""

    def put(self, request):
        """实现添加邮箱"""

        # 接收参数
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        # 校验参数
        if not email:
            return http.HttpResponseForbidden("缺少email参数")
        if not re.match(r'[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden("参数email错误")

        # 赋值email字段
        # 将用户名传入的邮箱保存到用户数据库的email字段中
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        # 发送邮箱邮件
        verify_url = generate_verify_email_url(request.user)
        send_verify_email.delay(email, verify_url)  # 在运行时调用delay

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': "OK"})


class VerifyEmailView(View):
    """验证邮箱"""

    def get(self, request):
        # 接收参数
        token = request.GET.get('token')

        # 校验参数
        if not token:
            return http.HttpResponseForbidden("缺少token")

        # 从token中提取用户信息user_id ==> user
        user = check_verify_email_token(token)

        if not user:
            return http.HttpResponseForbidden("无效的token")

        # 将用户的email_active字段设置为true
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮箱失败')

        # 响应结果：重定向到用户中心
        return redirect(reverse('users:info'))


class AddressView(LoginRequiredJSONMixin, View):
    """查询并展示用户收货地址信息"""

    def get(self, request):
        """提供收货地址界面"""
        login_user = request.user
        addresses = Address.objects.filter(user=login_user, is_deleted=False)

        address_list = []
        for address in addresses:
            address_dict = {
                "id": address.id,
                "title": address.title,
                "receiver": address.receiver,
                "province": address.province.name,
                "city": address.city.name,
                "district": address.district.name,
                "place": address.place,
                "mobile": address.mobile,
                "tel": address.tel,
                "email": address.email
            }
            address_list.append(address_dict)

        context = {
            'default_address_id': login_user.default_address_id or '0', # 没有默认地址 None
            "addresses": address_list
        }

        return render(request, 'user_center_site.html', context)


class AddressCreateView(LoginRequiredJSONMixin, View):
    """新增地址"""

    def post(self, request):
        """实现新增地址"""

        # 判断是否超过地址上限
        count = request.user.addresses.count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '超过地址数量上限'})

        # 接受参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden("缺少必传参数")
        # 校验手机号
        if not re.match(r'1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden("手机号格式错误")

        if tel:
            if not re.match(r'(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden("tel参数有误")

        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden("参数email有误")

        # 保存地址信息
        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,  # 标题默认就是收货人
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email,
            )

            # 设置默认地址
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()

        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})

        # 新增地址成功，将新增的地址响应给前端实现局部刷新
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        # 返回响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': "OK", 'address': address_dict})


class UpdateDestroyAddressView(LoginRequiredJSONMixin, View):
    """修改和删除地址"""

    def put(self, request, address_id):
        """更新地址"""
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden("缺少必传参数")

        # 校验手机号
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden("参数mobile有误")
        # 校验固定电话
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden("参数tel错误")

        # 校验邮箱
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden("参数email有误")

        # 使用最新的地址信息覆盖指定的旧的地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '修改地址失败'})

        # 响应新的地址信息给前端渲染
        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': "修改地址成功", "address": address_dict})

    def delete(self, request, address_id):
        """删除地址"""
        try:
            # 查询要删除的地址
            address = Address.objects.get(id=address_id)

            # 将地址逻辑删除设置为true
            address.is_deleted = True
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})

        # 响应删除地址结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class DefaultAddressView(LoginRequiredJSONMixin, View):
    """设置默认地址"""

    def put(self, request, address_id):
        """设置默认地址"""
        try:
            # 接收参数，查询地址
            address = Address.objects.get(id=address_id)

            # 设置地址为默认
            request.user.default_address = address
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})


class UpdateTitleAddressView(LoginRequiredJSONMixin, View):
    """设置地址标题"""

    def put(self, request, address_id):
        """修改地址标题"""

        # 接受参数，地址标题
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')

        #校验参数
        if not title:
            return http.HttpResponseForbidden("缺少title")

        try:
            # 查询地址
            address = Address.objects.get(id=address_id)

            # 设置新的地址标题
            address.title = title
            address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

        # 响应删除地址结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})


class UserBrowsHistory(LoginRequiredJSONMixin, View):
    """用户浏览记录"""

    def get(self, request):
        """查询用户浏览记录"""
        #获取Redis存储的sku_id列表信息
        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        #根据sku_id列表的数据，查询出商品sku信息
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})


    def post(self, request):
        """保存用户浏览记录"""

        #接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        #校验参数
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        #保存用户浏览数据
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id

        #先去重
        pl.lrem('history_%s' % user_id, 0, sku_id)
        #再存储
        pl.lpush('history_%s' % user_id, sku_id)
        #最后截取
        pl.ltrim('history_%s' % user_id, 0, 4)
        #执行管道
        pl.execute()

        #响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


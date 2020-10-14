from django.shortcuts import render

# Create your views here.
from meiduo_mall.utils.views import LoginRequiredMixin, LoginRequiredJSONMixin
from django.views import View
from orders.models import OrderInfo
from django import http
from alipay import AliPay
from django.conf import settings
from meiduo_mall.utils.response_code import RETCODE
import os
from .models import Payment


class PaymentView(LoginRequiredJSONMixin, View):
    """订单支付功能"""

    def get(self, request, order_id):
        # 查询要支付的订单
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单信息错误')

        # 业务处理:使用python sdk调用支付宝的支付接口
        # 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/payment/keys/app_private_key.pem')).read()
        alipy_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/payment/keys/alipay_public_key.pem')).read()

        app_private_key_string == """
                -----BEGIN RSA PRIVATE KEY-----
                base64 encoded content
                -----END RSA PRIVATE KEY-----
            """

        alipy_public_key_string == """
                -----BEGIN PUBLIC KEY-----
                base64 encoded content
                -----END PUBLIC KEY-----
            """

        # 创建支付宝对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipy_public_key_string,
            sign_type="RSA2",  # RSA 或者RSA2
            debug=True  # 默认False
        )

        # 生成登陆支付宝链接
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject='美多商城 %s' % order_id,
            return_url=settings.ALIPAY_RETURN_URL,
        )

        # 响应登陆支付宝链接
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})


class PaymentStatusView(View):
    """保存订单支付结果"""
    def get(self, request):
        #获取前端传入的数据
        query_dict = request.GET
        data = query_dict.dict()
        # 获取并从请求参数中剔除signature
        signature = data.pop('sign')


        #创建支付宝对象
        # 业务处理:使用python sdk调用支付宝的支付接口
        # 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/payment/keys/app_private_key.pem')).read()
        alipy_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/payment/keys/alipay_public_key.pem')).read()

        app_private_key_string == """
                    -----BEGIN RSA PRIVATE KEY-----
                    base64 encoded content
                    -----END RSA PRIVATE KEY-----
                """

        alipy_public_key_string == """
                        -----BEGIN PUBLIC KEY-----
                        base64 encoded content
                        -----END PUBLIC KEY-----
                    """

        # 创建支付宝对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipy_public_key_string,
            sign_type="RSA2",  # RSA 或者RSA2
            debug=True  # 默认False
        )

        # 校验这个重定向是否是alipay重定向过来的
        success = alipay.verify(data, signature)

        if success:
            #读取order_id
            order_id = data.get('out_trade_no')
            #读取支付宝流水号
            trade_id = data.get('trade_no')
            #保存Payment模型类数据
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_id
            )

            #修改订单状态为待评价
            OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])

            #响应trade_id
            context={
                'trade_id': trade_id
            }

            return render(request, 'pay_success.html', context)
        else:
            #订单支付失败
            return http.HttpResponseForbidden('非法请求')
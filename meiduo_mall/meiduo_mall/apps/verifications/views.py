from django.shortcuts import render

from django.views import View
from .libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from . import constants
from django import http
from django_redis import get_redis_connection
from meiduo_mall.utils.response_code import RETCODE
from verifications.libs.yuntongxun.sms import CCP

from celery_tasks.sms.tasks import send_sms_code


import logging, random

#创建日志输出器
logger = logging.getLogger('django')


class ImageCodeView(View):
    """图形验证码"""

    def get(self, request, uuid):
        """

        :param request: 请求对象
        :param uuid: 唯一标识图形验证码所属用户的id
        :return: image/jpg
        """

        #生成图片验证码
        text, image = captcha.generate_captcha()

        #保存图片验证码
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        #响应图片验证码
        return http.HttpResponse(image, content_type='/image/jpg')


class SMSCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):
        """

        :param request: 请求对象
        :param mobile: 手机号
        :return: JSON
        """

        #接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        #校验参数
        if not all([image_code_client, uuid]):
            return http.JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg':'缺少必传参数'})

        #创建连接到redis
        redis_conn = get_redis_connection('verify_code')

        #判断用户是否频繁发送短信验证码
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '短信验证码发送过于频繁'})

        #提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            #图形验证码过期或不存在
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'ermsg': '图形验证码失效'})

        #删除图形验证码，避免恶意测试验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.error(e)

        #对比图形验证码
        image_code_server = image_code_server.decode() #bytes转成字符
        if image_code_client.lower() != image_code_server.lower(): #转化为小写进行比较
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '验证码错误'})

        #生成短信验证码：生成6位数的短信验证码
        sms_code = '%06d' %random.randint(0, 999999)
        logger.info(sms_code)


        # #保存短信验证码
        # redis_conn.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # #重新写入send_flag
        # redis_conn.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        #创建redis管道
        pl = redis_conn.pipeline()
        #将redis请求添加到队列中
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        #执行请求
        pl.execute()


        #发送短信验证码
        # ccp = CCP()
        # ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60], constants.SEND_SMS_TEMPLATE_ID)

        send_sms_code.delay(mobile, sms_code)

        #响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功', })

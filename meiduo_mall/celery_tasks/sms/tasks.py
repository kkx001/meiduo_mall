# *_*coding:utf-8 *_*

from celery_tasks.sms.yuntongxun.ccp_sms import CCP

from . import constants

from celery_tasks.main import celery_app


# 使用装饰器异步任务，保证celery识别任务

@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code):
    """
    发送短信异步任务
    :param mobile: 手机号
    :param sms:  短信验证码
    :param sms_code:
    :return: 成功：0、 失败： -1
    """
    ccp = CCP()
    send_ret = ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60],
                                     constants.SEND_SMS_TEMPLATE_ID)

    return send_ret

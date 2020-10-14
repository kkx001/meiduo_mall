# *_*coding:utf-8 *_*

from django.core.mail import send_mail
from django.conf import settings
from celery_tasks.main import celery_app



@celery_app.task(bind=True, name='send_verify_email', retry_backoff=3)
def send_verify_email(self, to_mail, verify_url):
    """定义发送邮件验证任务"""

    # send_mail('标题', '普通邮件正文', '发件人', '收件人列表', '富文本邮件正文(html)')
    subject = "美多商城邮箱验证"
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用美多商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s</a></p>' % (to_mail, verify_url, verify_url)

    try:
        send_mail(subject, '', settings.EMAIL_FROM, [to_mail], html_message=html_message)
    except Exception as e:
        #触发错误重试，最多3次
        raise self.retry(exc=e, max_retries=3)

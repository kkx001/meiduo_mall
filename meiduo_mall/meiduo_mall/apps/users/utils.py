# *_*coding:utf-8 *_*

# 多账号登陆
from django.contrib.auth.backends import ModelBackend
import re
# from users.models import User
from .models import User

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from . import constants
from itsdangerous import BadData


def get_user_by_account(account):
    """
    通过账号获取用户
    :param account: 用户名或者手机号
    :return: user
    """

    try:
        if re.match(r'^1[3-9]\d{9}$', account):
            # ===>acount 为手机号
            user = User.objects.get(mobile=account)
        else:
            # ====>account 为用户名
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileBackend(ModelBackend):
    """自定义用户认证后端"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        重写认证方法，实现多账号登陆
        :param request: 请求对象
        :param username: 用户名
        :param password: 密码
        :param kwargs: 其他参数
        :return: user
        """

        # 根据传入的username获取user对象，username可以是手机号也可以是用户名
        user = get_user_by_account(username)

        # 校验user是否存在，并校验密码是否正确
        if user and user.check_password(password):
            return user


def generate_verify_email_url(user):
    """
    生成邮箱激活链接
    :param user: 当前登陆用户
    :return: 'http://www.meiduo.site:8000/emails/verification/?token='
    """
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    data = {'user_id': user.id, 'email': user.email}
    token = s.dumps(data)

    return settings.EMAIL_VERIFY_URL + '?token=' + token.decode()


def check_verify_email_token(token):
    """
    反序列化，验证token，获取到user
    :param token: 序列化后的用户信息
    :return: user
    """
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    try:
        data = s.loads(token)
    except BadData:
        return None
    else:
        #从data取出user_id和email
        user_id = data.get('user_id')
        email = data.get('email')

        try:
            user = User.objects.get(id=user_id, email=email)
        except User.DoesNotExist:
            return None
        else:
            return user
# *_*coding:utf-8 *_*
from django_redis import get_redis_connection
import base64, pickle


def merge_carts_cookies_redis(request, user, response):
    """
    登录后合并cookie购物车数据到Redis
    :param request: 本次请求对象，获取cookie中的数据
    :param user: 登录用户信息，获取user_id
    :param response: 本次响应对象，清除cookie中的数据
    :return: response
    """

    # 获取cookie中的购物车数据
    cookie_cart_str = request.COOKIES.get('carts')

    #cookie中没有数据就响应结果
    if not cookie_cart_str:
        return response
    cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart_str.encode()))

    new_cart_dict = {}
    new_cart_selected_add = []
    new_cart_selected_remove = []

    #同步cookie中购物车数据
    for sku_id, cooki_dict in cookie_cart_dict.items():
        new_cart_dict[sku_id] = cooki_dict['count']

        if cooki_dict['selected']:
            new_cart_selected_add.append(sku_id)
        else:
            new_cart_selected_remove.append(sku_id)

    #将new_cart_dict 写入redis数据库
    redis_conn = get_redis_connection('carts')
    pl = redis_conn.pipeline()
    pl.hmset('carts_%s' % user.id, new_cart_dict)

    # 将勾选状态同步到Redis数据库
    if new_cart_selected_add:
        pl.sadd('selected_%s' % user.id, *new_cart_selected_add)
    if new_cart_selected_remove:
        pl.srem('selected_%s' % user.id, *new_cart_selected_remove)

    pl.execute()

    #清除cookie
    response.delete_cookie('carts')

    return response

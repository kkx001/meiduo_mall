from django.shortcuts import render
from django.views import View
# Create your views here.
import json, pickle, base64
from django import http
from goods.models import SKU
from django_redis import get_redis_connection
from meiduo_mall.utils.response_code import RETCODE
from . import constants


class CartsView(View):
    """购物车管理"""

    def get(self, request):
        """展示购物车"""
        user = request.user

        if user.is_authenticated:
            # 用户已经登陆

            # 查询redis购物车
            redis_conn = get_redis_connection('carts')

            # 查询redis购物车中的数据
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)

            # 获取redis中的选中状态
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 将redis中的数据构造成cookie中的格式一致
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            # 用户没有登陆, 查询cookie购物车
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                # 将cart_str转成bytes，再转成base64的bytes， 最后转成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

        # 构造购物车渲染数据
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        cart_skus = []
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'selected': str(cart_dict.get(sku.id).get('selected')),  # 将True转'True'
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount': str(sku.price * cart_dict.get(sku.id).get('count')),
            })
        context = {
            'cart_skus': cart_skus
        }
        return render(request, 'cart.html', context)

    def post(self, request):
        """添加购物车"""
        # 接收和校验参数
        # 判断用户是否登陆

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('参数不完整')

        # 判断sku_id是否存在
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')
        # 判断count是否为数字
        try:
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden("参数count有误")

        # 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登陆
        user = request.user

        if user.is_authenticated:
            # 用户已经登陆
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 新增购物车数据
            pl.hincrby("carts_%s" % user.id, sku_id, count)

            # 新增选中的状态
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)

            # 执行管道
            pl.execute()

            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
        else:
            # 用户没有登陆,操作cookie购物车
            cart_str = request.COOKIES.get('carts')
            # 如果用户操作过cookie购物车
            if cart_str:
                # 将cart_str转化为bytes，再将bytes转成base64的bytes， 最后将bytes转成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 用户没有操作过cookie购物车
                cart_dict = {}

            # 判断要加入购物车的商品是否已经在购物车中，如果有相同商品，累加，没有，则直接赋值
            if sku_id in cart_dict:
                # 累加求和
                origin_count = cart_dict[sku_id]['count']
                count += origin_count

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 将字典转化为bytes，再将bytes转化为base64的bytes，最后将bytes转化为字符串
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 创建响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})

            # 响应结果并将购物车数据写入到cookie中
            response.set_cookie('carts', cookie_cart_str, max_age=constants.CARTS_COOKIE_EXPIRES)

            return response

    def put(self, request):
        """修改购物车"""

        # 接受参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少参数')

        # 判断sku_id是否存在
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("商品sku_id不存在")

        # 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden("参数count有误")

        # 判断selected是否为bool类型
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登陆
        user = request.user
        if user.is_authenticated:
            # 已登陆
            # 修改redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 因为接口设计为幂等的，直接覆盖
            pl.hset('carts_%s' % user.id, sku_id, count)
            # 是否被选中
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)

            pl.execute()

            # 创建响应的对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count
            }
            return http.JsonResponse({'code': RETCODE.Ok, 'errmsg': '修改购物车成功', 'cart_sku':cart_sku})
        else:
            # 用户未登录，修改cookie购物车
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                # 将cart_str转成bytes,再将bytes转成base64的bytes,最后将bytes转字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            # 因为接口设计为幂等的，直接覆盖
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 创建响应对象
            cart_sku = {
                'id': sku_id,
                'count': count,
                'selected': selected,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price,
                'amount': sku.price * count,
            }

            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})

            # 响应结果并将购物车数据写入到cookie
            response.set_cookie('carts', cookie_cart_str, max_age=constants.CARTS_COOKIE_EXPIRES)

            return response

    def delete(self, request):
        """删除购物车"""

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 判断sku_id是否存在
        try:
            SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden("商品不存在")

        # 判断用户是否登录
        user = request.user

        if user is not None and user.is_authenticated:
            # 用户已登录，删除redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # 删除键，就等价于删除整条数据
            pl.hdel('carts_%s' % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

            # 删除结束后，没有响应的数据，只需要响应状态码即可
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})
        else:
            # 用户未登录，删除cookie购物车
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                # 将cart_str转成bytes,再将bytes转成base64的bytes,最后将bytes转字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            # 创建响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})

            if sku_id in cart_dict:
                del cart_dict[sku_id]

                # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
                cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).deocde()

                # 响应结果并将购物车数据写入到cookie
                response.set_cookie('carts', cookie_cart_str, max_age=constants.CARTS_COOKIE_EXPIRES)

            return response


class CartSimpleView(View):
    """商品页面右上角购物车"""

    def get(self, request):
        # 判断用户是否登录
        user = request.user

        if user.is_authenticated:
            # 用户已登录，查询Redis购物车
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 将redis中的两个数据统一格式，跟cookie中的格式一致，方便统一查询
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }

        else:
            # 用户未登录，查询cookie购物车
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

            else:
                cart_dict = {}
            # 构造简单购物车JSON数据
            cart_skus = []
            sku_ids = cart_dict.keys()
            skus = SKU.objects.filter(id__in=sku_ids)

            for sku in skus:
                cart_skus.append({
                    'id': sku.id,
                    'name': sku.name,
                    'count': cart_dict.get(sku.id).get('count'),
                    'default_image_url': sku.default_image.url
                })

            # 返回响应
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_skus': cart_skus})


class CartsSelectAllView(View):
    """全选购物车"""

    def put(self, request):
        # 接受参数
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)

        # 校验参数
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')

            # 获取所有的记录 {b'3': b'1', b'5': b'2'}
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)

            # 获取字典中所有的key [b'3', b'5']
            redis_sku_ids = redis_cart.keys()

            # 判断用户是否全选
            if selected:
                # 全选
                redis_conn.sadd('selected_%s' % user.id, *redis_sku_ids)
            else:
                # 取消全选
                redis_conn.srem('selected_%s' % user.id, *redis_sku_ids)

            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        else:
            # 用户未登录，操作cookie购物车
            # 获取cookie中的购物车数据，并且判断是否有购物车数据
            cart_str = request.COOKIES.get('carts')

            # 构造响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'Ok'})

            if cart_str:
                # 将 cart_str转成bytes类型的字符串
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))

                # 遍历所有的购物车记录
                for sku_id in cart_dict:
                    cart_dict[sku_id]['selected'] = selected

                cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 重写将购物车数据写入到cookie
                response.set_cookie('carts', cookie_cart_str)

            return response

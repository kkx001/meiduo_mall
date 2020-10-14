from django.shortcuts import render
from django.views import View
from django import http
from .utils import get_breadcrumb
from contents.utils import get_categories
from django.core.paginator import Paginator, EmptyPage
from . import constants
from .models import SKU, GoodsCategory, GoodsVisitCount
from django.utils import timezone
import datetime
import logging
from meiduo_mall.utils.response_code import RETCODE


logger = logging.getLogger('django')

class ListView(View):
    """商品列表"""

    def get(self, request, category_id, page_num):
        """查询并渲染商品列表"""

        # 判断category_id是否正确
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('GoodsCategory does not exist')

        # 接收sort参数，如果用户不传，就是默认的排序方式
        sort = request.GET.get('sort', 'default')

        # 查询商品频道分类
        categories = get_categories()

        # 查询面包屑导航
        breadcrumb = get_breadcrumb(category)

        # 按照排序规则查询该分类商品SKU信息
        if sort == 'price':
            # 按照价格排序
            sort_field = 'price'
        elif sort == 'hot':
            # 按照销量由高到低排序
            sort_field = '-sales'
        else:
            # 'price' 和'sales'以外的所有排序方式都归为default
            sort = 'default'
            sort_field = 'create_time'

        skus = SKU.objects.filter(category=category, is_launched=True).order_by(sort_field)

        # 创建每页商品数据
        paginator = Paginator(skus, constants.GOODS_LIST_LIMIT)

        # 获取每页的商品数据
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            return http.HttpResponseNotFound('empty page')

        # 获取列表页总数
        total_page = paginator.num_pages

        # 渲染页面
        context = {
            'categories': categories,  # 频道分类
            'breadcrumb': breadcrumb,  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后的数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }
        return render(request, 'list.html', context)


class HotGoodsView(View):
    """商品销量排行"""

    def get(self,request, category_id):
        """提供商品热销排行JSON数据"""
        #根据销量排序
        skus = SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[:2]

        #序列化
        hot_skus = []
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image.url,
                'name': sku.name,
                'price': sku.price
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})


class DetailView(View):
    """商品详情页"""

    def get(self, request, sku_id):
        """提供商品详情页"""

        #接受和校验参数
        try:
            #查询sku
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')

        #查询商品频道分类
        categories = get_categories()

        #查询面包屑导航
        breadcrumb = get_breadcrumb(sku.category)

        #构建当前商品的规格键
        sku_specs = sku.specs.order_by('spec_id')
        sku_key = []
        for spec in sku_specs:
            sku_key.append(spec.option.id)

        #获取当前商品所有的SKU
        skus = sku.spu.sku_set.all()

        #构建不同规则参数（选项）的sku字典
        spec_sku_map = {}
        for s in skus:
            #获取sku的规格参数
            s_specs = s.specs.order_by('spec_id')
            #用于形成规格参数-sku字典的键
            key = []
            for spec in s_specs:
                key.append(spec.option.id)

            #向规格参数-sku字典添加记录
            spec_sku_map[tuple(key)] = s.id

        #获取当前商品的规格信息
        goods_specs = sku.spu.specs.order_by('id')
        #如果当前sku的规格信息不完整，则不再继续
        if len(sku_key) < len(goods_specs):
            return

        for index, spec in enumerate(goods_specs):
            #复制当前sku的规格键
            key = sku_key[:]
            #该规格的选项
            spec_options = spec.options.all()
            for option in spec_options:
                #在规格参数sku字典中查找符合当前规格的sku
                key[index] = option.id
                option.sku_id = spec_sku_map.get(tuple(key))
            spec.spec_options = spec_options



        #渲染页面
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'specs': goods_specs
        }
        return render(request, 'detail.html', context)


class DetailVisitView(View):
    """详情页分类商品访问量"""

    def post(self, request, category_id):
        """记录分类商品访问量"""

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseForbidden('缺少必传参数')

        #获取今天的日期
        t = timezone.localtime()
        today_str = "%d-%02d-%02d" % (t.year, t.month, t.day)
        today_date = datetime.datetime.strptime(today_str, "%Y-%m-%d")

        try:
            #查询今天该类别的商品的访问量
            counts_data = GoodsVisitCount.objects.get(date=today_date, category=category)
        except GoodsVisitCount.DoesNotExist:
            # 如果该类别的商品在今天没有过访问记录，就新建一个访问记录
            counts_data = GoodsVisitCount()

        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError("服务器异常")

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

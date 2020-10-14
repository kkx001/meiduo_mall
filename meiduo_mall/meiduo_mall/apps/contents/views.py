from django.shortcuts import render

# Create your views here.
from django.views import View
from collections import OrderedDict
from goods.models import GoodsChannel
from .utils import get_categories
from .models import ContentCategory



class IndexView(View):
    """首页广告"""

    def get(self, request):
        """提供首页广告页面"""

        #查询商品频道和分类
        # categories = OrderedDict()
        categories = get_categories()
        channels = GoodsChannel.objects.order_by('group_id', 'sequence')


        for channel in channels:
            group_id = channel.group_id  #当前组

            if group_id not in categories:
                categories[group_id] = {'channel': [], 'sub_cats': []}

            cat1 = channel.category  #当前类别的频道

            #追加当前频道
            categories[group_id]['channels'].append({
                'id': cat1.id,
                'name': cat1.name,
                'url': channel.url
            })

            #构建当前类的子类别
            for cat2 in cat1.subs.all():
                cat2.sub_cats = []
                for cat3 in cat2.subs.all():
                    cat2.sub_cats.append(cat3)
                categories[group_id]['sub_cats'].append(cat2)

            #广告数据
            contents = {}
            content_categories = ContentCategory.objects.all()
            for cat in content_categories:
                contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

            #渲染上下文
            context = {
                'categories': categories,
                'contents': contents,
            }

            return render(request, 'index.html', context)

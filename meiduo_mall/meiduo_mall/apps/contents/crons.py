# *_*coding:utf-8 *_*
import time
from .utils import get_categories
from .models import ContentCategory
from django.template import loader
import os
from django.conf import settings


def generate_static_index_html():
    """生成静态的html文件"""

    print('%s: generate_static_index_html' % time.ctime())

    #获取商品和分类
    categories = get_categories()

    #广告内容
    contents = {}
    content_categories = ContentCategory.objects.all()
    for cat in content_categories:
        contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

    #渲染模版
    context = {
        'categories': categories,
        'contents': contents
    }

    #获取首页模版文件
    template = loader.get_template('index.html')

    #渲染首页html字符串
    html_text = template.render(context)

    #将首页html字符串写入到指定目录，命名'index.html'
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_text)
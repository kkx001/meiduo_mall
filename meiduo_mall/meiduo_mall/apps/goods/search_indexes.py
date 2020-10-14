# *_*coding:utf-8 *_*

from haystack import indexes
from .models import SKU


# 指定对于某个类的某些数据建立索引
# 索引类名格式:模型类名+Index
class SKUIndex(indexes.SearchIndex, indexes.Indexable):
    """SKU索引数据模型类"""
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        """返回建立索引的模型类"""
        return SKU

    def index_queryset(self, using=None):
        """返回要建立索引的数据查询集"""
        return self.get_model().objects.filter(is_launched=True)
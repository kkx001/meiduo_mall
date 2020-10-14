# *_*coding:utf-8 *_*

from django.db import models

class BaseModel(models.Model):
    """为模型类补充字段"""
    create_time = models.DateField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateField(auto_now=True, verbose_name="更新时间")

    class Meta:
        abstract = True # 说明是抽象模型类, 用于继承使用，数据库迁移时不会创建BaseModel的表
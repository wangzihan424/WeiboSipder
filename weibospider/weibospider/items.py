# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


BaseinfoMap={
    'NickName': '昵称',
    'Gender': '性别',
    'Location': '地区',
    'BriefIntroduction': '简介',
    'Birthday': '生日',
    'Talente': '达人',
    'Authentication': '认证',
    'AuthenticationInfo': '认证信息',
    'Url': '互联网'
}
class BaseInfoItem(Item):
    """ 个人信息 """
    Id = Field()  # 用户ID

    NickName = Field()  # 昵称:
    Gender = Field()  # 性别
    Location = Field()  #地区
    BriefIntroduction = Field()  # 简介
    Birthday = Field()  # 生日
    Talente = Field()   #达人
    Authentication = Field()  # 认证
    AuthenticationInfo = Field()  # 认证信息
    Url = Field()             #
    Tweets = Field()  # 微博数
    Follows = Field()  # 关注数
    Fans = Field()  # 粉丝数

    Viplevel = Field()  # 会员等级


class TweetsItem(Item):
    """ 微博信息 """
    id = Field()  # 微博ID
    Id = Field()  # 用户ID
    IsTransfer = Field()   # 是否为转发
    TransferReason = Field()  # 转发理由
    Content = Field()  # 微博内容
    ImageUrl = Field()  # 图片Url列表  josn格式存储
    Like = Field()  # 点赞数
    Transfer = Field()  # 转载数
    Comment = Field()  # 评论数
    PubTime = Field()  # 发表时间
    Tools = Field()  # 发表工具/平台
    Co_oridinates = Field()  # 定位坐标
    ImageUrl = Field()   #图片列表


class TweetsInfoItem(Item):
    Tweets = Field()  # 微博数
    Follows = Field()  # 关注数
    Fans = Field()  # 粉丝数








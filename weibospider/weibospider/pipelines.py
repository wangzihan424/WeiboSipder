from weibospider.items import TweetsItem,BaseInfoItem
import logging

import MySQLdb
from twisted.enterprise import adbapi
import MySQLdb.cursors

import pymongo


class MongoPipeline(object):
    userinfo = 'users'
    Tweets = 'tweets'

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, BaseInfoItem):
            self.db[self.userinfo].insert(dict(item))
        if isinstance(item, TweetsItem):
            self.db[self.Tweets].insert(dict(item))



class MysqlPipeline(object):
    def __init__(self,settings):
        self.conn = MySQLdb.connect(settings.get('MYSQL_HOST'), settings.get('MYSQL_USER'), settings.get('MYSQL_PASSWORD'),
                                    settings.get('MYSQL_DBNAME'), charset="utf8mb4", use_unicode=True)
        self.cursor = self.conn.cursor()

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    def close_spider(self, spider):
        self.cursor.close()
        self.conn.close()

    def process_item(self, item, spider):
        sql = ''
        if isinstance(item, BaseInfoItem):
            for key in BaseInfoItem.fields:
                if item.get(key)==None:
                    item[key]=''
            sql, params = self.insert_base_info(item)
        elif isinstance(item, TweetsItem):
            for key in TweetsItem.fields:
                if item.get(key)==None:
                    item[key]=''
            if item['IsTransfer'] == 0 and item['ImageUrl']:
                if len(item['ImageUrl']) > 0:
                    if 'bmiddle' in item['ImageUrl']:
                        sql, params = self.insert_tweets(item)
        try:
            if sql:
                self.cursor.execute(sql, params)
                self.conn.commit()
        except Exception as e:
            logging.info(e)
            self.conn.rollback()


    def insert_base_info(self,item):
        insert_sql = '''
                      insert into weibo_userinfo(ID, NickName,Gender,Location,BriefIntroduction,Birthday,Tweets,Follows,Fans,Viplevel,Talente,Authentication,AuthenticationInfo,Url)
                      VALUES (%s, %s, %s, %s,  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
        params = (
        item['Id'], item['NickName'], item['Gender'], item['Location'], item['BriefIntroduction'], item['Birthday'],
        item['Tweets'], item['Follows'], item['Fans'], item['Viplevel'], item['Talente'], item['Authentication'],
        item['AuthenticationInfo'], item['Url'])
        return insert_sql,params



    def insert_tweets(self, item):
        insert_sql = '''
                insert into weibo_tweets(wbid,ID, IsTransfer, Content, Likes,Transfer,Comment,PubTime,Tools,Co_oridinates, ImageUrl)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params=(item['id'],item['Id'],item['IsTransfer'],item['Content'],item['Like'],item['Transfer'],item['Comment'],item['PubTime'],item['Tools'],item['Co_oridinates'],item['ImageUrl'])
        return insert_sql, params






class MysqlTwistedPipline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        dbparms = dict(
            host = settings["MYSQL_HOST"],
            db = settings["MYSQL_DBNAME"],
            user = settings["MYSQL_USER"],
            passwd = settings["MYSQL_PASSWORD"],
            charset='utf8mb4',
            cursorclass=MySQLdb.cursors.DictCursor,
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool("MySQLdb", **dbparms)
        return cls(dbpool)

    def close_spider(self, spider):
        self.dbpool.close()

    def process_item(self, item, spider):
        #使用twisted将mysql插入变成异步执行
        if isinstance(item, BaseInfoItem):
            for key in BaseInfoItem.fields:
                if item.get(key)==None:
                    item[key]=''
            query = self.dbpool.runInteraction(self.insert_base_info, item)
            query.addErrback(self.handle_error, item)
        elif isinstance(item, TweetsItem):
            for key in TweetsItem.fields:
                if item.get(key)==None:
                    item[key]=''
            query = self.dbpool.runInteraction(self.insert_tweets, item)
            query.addErrback(self.handle_error, item)
        # elif isinstance(item, TweetsInfoItem):
        #     query = self.dbpool.runInteraction(self.update_tweets_info, item)
        #     query.addErrback(self.handle_error, item) #处理异常

    def handle_error(self, failure, item):
        # 处理异步插入的异常
        logging.debug(failure)


    def insert_base_info(self, cursor, item):
        insert_sql='''
              insert into userinfo(ID, 昵称,性别,地区,简介,生日,微博数,关注数,粉丝数,会员等级,达人,认证,认证信息,Url)
              VALUES (%s, %s, %s, %s,  %s, %s, %s,%s, %s, %s, %s, %s, %s, %s)
        '''
        params = (item['Id'], item['NickName'], item['Gender'], item['Location'], item['BriefIntroduction'], item['Birthday'],
                  item['Tweets'],item['Follows'],item['Fans'],item['Viplevel'], item['Talente'], item['Authentication'],
                  item['AuthenticationInfo'], item['Url'])
        cursor.execute(insert_sql, params)


    def insert_tweets(self, cursor, item):
        insert_sql = '''
                insert into tweets(wbid,ID, IsTransfer, Content, Likes,Transfer,Comment,PubTime,Tools,Co_oridinates )
                VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params=(item['id'],item['Id'],item['IsTransfer'],item['Content'],item['Like'],item['Transfer'],item['Comment'],item['PubTime'],item['Tools'],item['Co_oridinates'])
        cursor.execute(insert_sql, params)


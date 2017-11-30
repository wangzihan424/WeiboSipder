# -*- coding: utf-8 -*-
import json
import os
import random,time
import redis
from weibospider.user_agents import agents
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from weibospider import cookies
from weibospider.cookies import CookiesManager
from scrapy.exceptions import IgnoreRequest
from scrapy.utils.response import response_status_message
import logging

class UserAgentMiddleware(object):
    """ 换User-Agent """
    def process_request(self, request, spider):
        agent = random.choice(agents)
        request.headers["User-Agent"] = agent
        # request.meta['proxy']="http://54.223.206.129:33862"



class CookiesMiddleware(RetryMiddleware):
    """ 维护Cookie """

    def __init__(self, settings):
        RetryMiddleware.__init__(self, settings)
        self.rconn = redis.Redis(settings.get('REDIS_HOST', 'localhsot'), settings.get('REDIS_PORT', 6379))
        self.cookiemanager=CookiesManager()
        self.cookiemanager.init_all_cookies(self.rconn)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        hkey='weibo:cookie'
        accountlist = self.rconn.hkeys(hkey)
        account = random.choice(accountlist)
        cookies = json.loads(self.rconn.hget(hkey, account).decode(encoding='utf-8'))
        request.cookies = cookies
        request.meta["account"] = account

    def process_response(self, request, response, spider):
        if response.status in [300, 301, 302, 303]:
            try:
                redirect_url = response.headers["location"]
                if "login.weibo" in redirect_url or "login.sina" in redirect_url:  # Cookie失效
                    logging.info("One Cookie going to update...")
                    self.cookiemanager.updateCookie(request.meta['account'],self.rconn)
                elif "weibo.cn/security" in redirect_url:  # 账号被限
                    logging.info("One Account is locked! Remove it!")
                    self.cookiemanager.removeCookie(request.meta["account"], self.rconn)
                elif "weibo.cn/pub" in redirect_url:
                    logging.info("Redirect to 'http://weibo.cn/pub'!( Account:%s )" % request.meta["account"].split("-")[0])
                reason = response_status_message(response.status)
                return self._retry(request, reason, spider) or response  # 重试
            except Exception as e:
                raise IgnoreRequest
        elif response.status in [403, 414]:
            logging.info("%s! Stopping..." % response.status)
            time.sleep(60)
            
        else:
            return response


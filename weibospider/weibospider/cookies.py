import json
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from weibospider.config import *
import redis
import os
import logging
from weibospider.yzm import YZM

from weibospider.verify import Yundama
import requests
import sys

sys.path.append(os.path.abspath(__file__))
class CookiesManager(object):
    '''
    登陆config中所有账号,获取cookie并存入Redis
    维护cookie
    '''
    def __init__(self,browser_type=DEFAULT_BROWSER,YdmAdmin=YdmAdmin,YdmRoot=YdmRoot):
        self.browser_type=browser_type
        # self.ydm=Yundama(YdmAdmin,YdmRoot)


    def _init_browser(self):
        '''
        根据self.browser_type初始化一个webdriver对象引用并返回
        指定了游览器驱动的绝对路径
        '''
        if self.browser_type == 'PhantomJS':
            dcap = DesiredCapabilities.PHANTOMJS.copy()
            dcap["phantomjs.page.settings.userAgent"] = (
                "Mozilla/5.0 (Linux; U; Android 2.3.6; en-us; Nexus S Build/GRK39F) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1"
            )
            # dcap["phantomjs.page.settings.loadImages"] = False
            browser = webdriver.PhantomJS(
                executable_path='C:\Python35\Scripts\phantomjs.exe',
                desired_capabilities=dcap)
            # browser.viewportSize = {'width': 1024, 'height': 800}
            browser.set_window_size(1400, 500)
            return browser
        elif self.browser_type == 'Chrome':
            browser = webdriver.Chrome(executable_path='C:\Program Files (x86)\chromedriver\chromedriver.exe')
            # browser.set_window_size(1400, 500)
            return browser
        else:
            logging.info('brwoser type error')
            return None

    def _is_login(self,driver):
        '''
        检测是否登陆成功
        :Return  True if success else Flase
        '''
        browser=driver
        n = 13
        while n > 0:
            if "我的首页" in browser.title:
                print('Successed login')
                return True
            else:
                time.sleep(0.5)
                n-=1
        logging.info('didn\'t login')
        return False

    def __read_account_from_weibotxt(self):
        '''
        :return: dict  username as Keys and password as Values
        '''
        weibo = {}
        with open('.\weibospider\weibo.txt', 'r') as f:
            for line in f.readlines():
                if len(line) > 1:
                    line = line.split('----')
                    weibo[line[0]] = line[1].replace('\n', '')
            return weibo

    def get_cookie_from_weibo(self, username, password, driver):
        '''
        需传入一个Browser引用
        登陆     获取cookie
        返回Cookie  以便存入Redis
        :return: json(cookies_dict)
        '''
        print('Generating Cookies of', username)
        browser=driver
        browser.delete_all_cookies()
        browser.get('https://passport.weibo.cn/signin/login?entry=mweibo&r=http%3A%2F%2Fweibo.cn%2F&backTitle=%CE%A2%B2%A9&vt=')
        wait = WebDriverWait(browser, 13)
        try:
            admin=wait.until(EC.presence_of_element_located((By.ID, "loginName")))
            root = wait.until(EC.presence_of_element_located((By.ID, "loginPassword")))
            submit = wait.until(EC.element_to_be_clickable((By.ID, "loginAction")))
            admin.clear()
            admin.send_keys(str(username))
            root.send_keys(str(password))
            submit.click()
            # time.sleep(0.3)
            try:                                             #看看有没有验证码,找到验证码了就识别后再次提交
                Yzm=YZM(browser)
                if not Yzm.verify():
                    pass

            except Exception as e:
                print(e)
            if self._is_login(browser):                   # islogin , get cookie then
                cookies_dict = {}
                for cookie in browser.get_cookies():
                    cookies_dict[cookie.get('name')] = cookie.get('value')
                return json.dumps(cookies_dict)
            else:
                return False

        except Exception as e:
            logging.info(e)

    def init_all_cookies(self,rconn):
        '''
        登陆weibo.txt中所有账号，并将cookie以散列结构(HSET KEY Filed value)存入Rdies   weibo:cookie as KEY username-password as Filed
        :Param rconn 一个Rdies连接实例
        :return: Bool
        '''
        time.clock()
        browser=self._init_browser()           #初始化一个公用browser对象，登陆所有账号后关闭
        if not isinstance(rconn ,type(redis.Redis())):
            logging.info('rconn 不是一个Redis连接实例')
            return False
        weibo=self.__read_account_from_weibotxt()
        for account in weibo.items():
            username,password=account
            hkey = 'weibo:cookie'
            account=username+'-'+password
            if rconn.hexists(hkey,account):         #账号已经登陆,cookie存在于redis,则不获取
                continue
            cookies=self.get_cookie_from_weibo(username, password,browser)
            if not cookies:         #获取失败，重试一次，再失败就跳过
                cookies=self.get_cookie_from_weibo(username, password,browser)
                if not cookies:
                    print('登陆失败:{}'.format(username))
                    continue
            rconn.hset(hkey,account,cookies)
            print('{}存入Redis成功'.format(account))
        print('所有账号登陆完成,耗时{:.2f}'.format(time.clock()))
        browser.quit()
        return True

    def updateCookie(self, account, rconn):
        """
        更新一个账号的Cookie
        :Param  account 'username-password'
        """
        username = account.split("-")[0]
        password = account.split("-")[1]
        browser = self._init_browser()
        cookies = self.get_cookie_from_weibo(username,password,browser)     #更新cookie 会新初始化一个browser实例 并在登陆后关闭游览器
        browser.quit()
        if cookies:
            logging.info("updated cookie of %s " % account)
            hkey = 'weibo:cookie'
            rconn.set(hkey,account,cookies)
        else:
            logging.info('updated cookie of %s failed, Removing ' % account)
            self.removeCookie(account, rconn)

    def removeCookie(self,account, rconn):
        """ 删除某个账号的Cookie """
        hkey = 'weibo:cookie'
        rconn.hdel(hkey,account)
        cookietotal = rconn.hlen(hkey,account)
        logging.info("The num of the cookies left  %s" % cookietotal)
        if cookietotal == 0:
            logging.info('no cookie left,system pause')
            os.system("pause")

if __name__ == '__main__':
    t=time.time()
    ck=CookiesManager()
    ck.init_all_cookies(redis.Redis())
    print('total{:.2f}'.format(time.time()-t))
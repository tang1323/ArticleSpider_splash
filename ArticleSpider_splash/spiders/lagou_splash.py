# -*- coding: utf-8 -*-
from datetime import datetime
import json
import redis
import scrapy
import requests
import os
import time
import pickle
from scrapy_splash import SplashRequest     # yield用这个
from scrapy_splash import SplashTextResponse, SplashJsonResponse, SplashResponse
from scrapy.http import HtmlResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from ArticleSpider_splash.settings import BASE_DIR   # 在settings已经定位好了项目的根目录
from scrapy import Selector

import urllib.request
from ArticleSpider_splash.items import LagouJobItemLoader, LagouJobItem
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from ArticleSpider_splash.tools.common import get_md5


class LagouCookiePoolSpider(CrawlSpider):
    name = 'lagou_splash'
    allowed_domains = ['www.lagou.com']
    start_urls = ['http://www.lagou.com/']

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36 Edg/80.0.361.111',
        'origin': 'https://www.lagou.com',
        'referer': 'https://www.lagou.com/',
    }

    # 需要登录 的就要cookies_enabled设置为True，在第一个start_url中把cookies带过去给requests, 在下一个requests也会把cookies带上去
    # DOWNLOAD_DELAY:10 每10秒爬取一个
    custom_settings = {
        "COOKIES_ENABLED": False,
        "AUTOTHROTTLE_ENABLED": True,
        "DOWNLOAD_DELAY": 12
    }

    def __init__(self, *a, **kw):
        # 全局初始化redis连接，这样就不必要重复的代码了，因为有多处要连接redis，所以这样做
        # decode_responses=True加进来的作用是从redis拿cookies就不再是bytes类型
        self.redis_cli = redis.Redis("127.0.0.1", 6379, decode_responses=True)
        super().__init__(*a, **kw)

    # 这个是爬虫规则，可以自己自定义
    # 就是设置了一个Rule,它如果匹配这样的url，那它就会去爬取
    rules = (
        # 点进LinkExtractor，有个allow=()，如果这里的allow是符合这样的url我就callback到parse_item提取
        # allow=http://www.lagou.com/jobs/， 这里就不这么写了，前面已经有allowed_domains = ['www.lagou.com']
        # 它会自己urljoin起来
        # follow=True意思是比如这个页面详情有相似职位，它也会深入获取获取
        # Rule(LinkExtractor(allow=r'jobs/\d+.html*'), callback='parse_item', follow=True),
        # process_request='use_splash'这个要给splash进一步处理
        Rule(LinkExtractor(allow=r'jobs/\d+.html*'), process_request='use_splash', callback='parse_item', follow=True),

        # 随便点进一个java的招聘，http://www.lagou.com/后面跟有guangzhou-zhaopin/这个的都可以爬取，无所谓
        # follow=True意思是比如这个页面详情有相似职位，它也会深入获取获取
        Rule(LinkExtractor(allow=("guangzhou-zhaopin/.*")), follow=True),

        # 点进公司也有一招聘职位，匹配gongsi/j这样的模式它就会去爬取，
        # follow=True意思是比如这个页面详情有相似职位，它也会深入获取获取
        Rule(LinkExtractor(allow=("gongsi/j\.*.html")), process_request='use_splash', callback='parse_item', follow=True),
    )

    def start_requests(self):
        return [scrapy.Request('https://www.lagou.com/', callback=self.login_cookie)]

    def login_cookie(self, response):
        for url in self.start_urls:
            # 从redis中随机获取一个cookie并设置给request
            cookie_str = self.redis_cli.srandmember("lagou:cookies")
            # scrapy中只认识cookie为dict类型，所以用loads做，在redis中是字符串，现在转换成字典类型
            cookie_dict = json.loads(cookie_str)
            yield SplashRequest(url, cookies=cookie_dict, dont_filter=True)

    # 如果要用splash，就要重载这个方法，因为crawlspider会检测返回来的网页是什么类型，
    # 经过splash后返回回来的是SplashTextResponse类型，所以这里要重载一下
    def _requests_to_follow(self, response):
        if not isinstance(response, (HtmlResponse, SplashJsonResponse, SplashTextResponse)):
            return
        seen = set()
        for n, rule in enumerate(self._rules):
            links = [lnk for lnk in rule.link_extractor.extract_links(response)
                     if lnk not in seen]
            if links and rule.process_links:
                links = rule.process_links(links)
            for link in links:
                seen.add(link)
                req = self._build_request(n, link)
                yield rule._process_request(req, response)

    def use_splash(self, request):
        request.meta.update(splash={
            'args': {
                'wait': 1,
            },
            'endpoint': 'render.html',
        })
        return request

    def parse_item(self, response):
        """解析拉勾网的职位"""

        # 实例化一个对象， LagouJobItem是拉勾的item
        # LagouJobItemLoader是自定义的一个给lagou的item
        # Lg = LagouJobItem()
        item_loader = LagouJobItemLoader(item=LagouJobItem(), response=response)

        # print(response.text)
        item_loader.add_css("title", ".job-name::attr(title)")
        item_loader.add_value("url", response.url)
        item_loader.add_value("url_object_id", get_md5(response.url))
        item_loader.add_css("salary", ".job_request .salary::text")
        item_loader.add_xpath("job_city", "//*[@class='job_request']//span[2]/text()")
        item_loader.add_xpath("work_years", "//*[@class='job_request']//span[3]/text()")
        item_loader.add_xpath("degree_need", "//*[@class='job_request']//span[4]/text()")
        item_loader.add_xpath("job_type", "//*[@class='job_request']//span[5]/text()")

        item_loader.add_css("tags", '.position-label li::text')
        item_loader.add_css("publish_time", ".publish_time::text")
        item_loader.add_css("job_advantage", ".job-advantage p::text")
        item_loader.add_css("job_desc", ".job_bt div")
        item_loader.add_css("job_addr", ".work_addr")   # 获取的字段里面包含了一段html，所以不能用::text,我们在itemloader里去除不必要的html
        item_loader.add_css("company_name", "#job_company dt a img::attr(alt)")
        item_loader.add_css("company_url", "#job_company dt a::attr(href)")
        item_loader.add_value("crawl_time", datetime.now())

        job_item = item_loader.load_item()

        return job_item


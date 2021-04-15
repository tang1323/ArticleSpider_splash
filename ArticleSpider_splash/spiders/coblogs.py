# -*- coding: utf-8 -*-
import re
import scrapy
import datetime
from scrapy.http import Request
from urllib import parse
from scrapy_splash import SplashRequest

from ArticleSpider_splash.items import CnblogsArticleItem, ArticleItemLoader
from ArticleSpider_splash.tools.common import get_md5
# 分布式爬虫的步骤
# -----1导入分布式爬虫类
from scrapy_redis.spiders import RedisSpider


# -----2 继承分布式爬虫类
class CnblogsSpider(RedisSpider):
    name = 'cnblogs_splash'
    # -----3注销：start_urls和allowed_domains
    # # 允许修改的域
    # allowed_domains = ['www.cnblogs.com']
    # start_urls = ['https://www.cnblogs.com/']

    # ----4 设置redis-key,这个key 随意设置，但是所有爬虫都要从这个key找起始url，也是往里放数据，也从里面取
    # 在redis中输入lpush cnblogs:start_urls https://www.cnblogs.com/
    redis_key = 'cnblogs:start_urls'

    # ----5 设置__init__
    def __init__(self, *args, **kwargs):
        # 在初始化的时候是获取domain参数，如果没有则为空字符串。
        domain = kwargs.pop('domain', '')

        # 我们在domain是可能有多个允许的域，所以用domain.split(',')， 用逗号隔开
        # ['www.jd.com', 'list.jd.com', 'p.3.cn']就是这样的域
        # filter要转换成一个列表
        self.allowed_domains = list(filter(None, domain.split(',')))
        super(CnblogsSpider, self).__init__(*args, **kwargs)

    # 需要登录 的就要cookies_enabled设置为True,在第一个start_url中把cookies带过去给requests, 在下一个requests也会把cookies带上去
    # DOWNLOAD_DELAY下载速度10秒一次
    custom_settings = {
        "COOKIES_ENABLED": True,
        "DOWNLOAD_DELAY": 2
    }

    def parse(self, response):
        """
        1. 获取文章列表中的文章url并交给scrapy下载并进行解析
        2. 获取下一页的url并交给scrapy进行下载，下载完成后交给parse

        :param response:
        :return:
        """

        # extract_first 提取list中第一个元素，若为空list，则返回默认值

        post_nodes = response.css('.post-item .post-item-text')  # 是id就用#,是class就用.,这是获取页面的所有链接
        for post_node in post_nodes:    # 一个一个解析出来
            # 解析出图片url
            image_url = post_node.css('.post-item-text .post-item-summary img::attr(src)').extract_first("")
            # 帮图片的url加上//
            if image_url.startswith("//"):
                image_url = "https:"+image_url
            # print(image_url)

            # 解析出文章的url
            post_url = post_node.css('.post-item-text a::attr(href)').extract_first("")
            # print(post_url)

            # 拿到post_url就要交给request，不要全部拿到才交给request
            yield SplashRequest(url=parse.urljoin(response.url, post_url), meta={"front_image_url": image_url}, callback=self.parse_detail)

        # 提取下一页并交给scrapy进行下载
        next_url = response.css('div.pager a:last-child::text').extract_first("")
        yield SplashRequest(url=parse.urljoin(response.url, next_url), callback=self.parse)
        if next_url == ">":
            next_url = response.css('div.pager a:last-child::attr(href)').extract_first("")
            # 拿到下一页的url又交给callback=self.parse函数获取post_url
            # 这里要用yield生成器来做
            """
            是可以停止的函数，它只会运行到第一个yield
            不像其他函数那样，会从上向下运行完
            所以它会停止。当它再次运行时，会接着从下一个yield的地方再次取数据运行
            或者调用它，用next()去获取
            scrapy是异步io框架，没有多线程，没有引入消息队列
            scrapy是单线程高并发异步io框架
            """
            yield SplashRequest(url=parse.urljoin(response.url, next_url), callback=self.parse, dont_filter=True)

    def parse_detail(self, response):
        match_re = re.match(".*?(\d+)", response.url)
        if match_re:
            item_loader = ArticleItemLoader(item=CnblogsArticleItem(), response=response)
            item_loader.add_css("title", "#cb_post_title_url span::text")
            item_loader.add_css("content", "#cnblogs_post_body")
            item_loader.add_css("create_date", "#post-date ::text")
            item_loader.add_css("tags", ".postDesc a::text")
            item_loader.add_value("comment_nums", "#post_comment_count ::text")
            item_loader.add_value("praise_nums", "#post_view_count ::text")
            item_loader.add_value("fav_nums", "#post_view_count ::text")
            item_loader.add_value("url", response.url)
            if response.meta.get("front_image_url", []):
                item_loader.add_value("front_image_url", response.meta.get("front_image_url", []))
            item_loader.add_value("url_object_id", get_md5(response.url))

            article_item = item_loader.load_item()

            yield article_item















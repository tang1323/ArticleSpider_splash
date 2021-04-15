# -*- coding: utf-8 -*-
import sys
import os
from ArticleSpider_splash.tools.dupefilter_redis_splash import SplashAwareDupeFilter
# Scrapy settings for ArticleSpider project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'ArticleSpider_splash'

SPIDER_MODULES = ['ArticleSpider_splash.spiders']
NEWSPIDER_MODULE = 'ArticleSpider_splash.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'ArticleSpider (+http://www.yourdomain.com)'

# Obey robots.txt rules
# 默认是true，这样有些数据就爬不到，要改成False
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs


# 这个参数是0.5秒到1.5秒的一个随机时间乘于DOWNLOAD_DELAY，也就是在15秒左右爬取一次
# RANDOMIZE_DOWNLOAD_DELAY = True

# 这个是限速10爬取一次
# DOWNLOAD_DELAY = 10


# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# 设置COOKIES_ENABLED为True有什么用呢
"""
在源码里scrapy/downloadermiddlewares/cookies中说明如果设置为True的话
那以后的每个request的url都会带上我们的cookies

for url in self.start_urls:
    yield scrapy.Request(url, dont_filter=True, cookie=cookie_dict)
中是第一次把cookies带过去，如果COOKIES_ENABLED设置为True，
那以后的每个request的url都会带上我们的cookies
"""
# 我们在spider里有custom_settings，会优先使用这个,
# 在第一个start_url中把cookies带过去给requests, 在下一个requests也会把cookies带上去
# COOKIES_ENABLED = True

# 这个是可以运行时候可以看得到我们的cookies信息
COOKIES_DEBUG = False



# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    # 这是splash的配置
    'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
    # 'ArticleSpider.middlewares.ArticlespiderSpiderMiddleware': 543,
}


# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html

# 后面的543 是优先级，数字越小优先级越高
DOWNLOADER_MIDDLEWARES = {
    # 这两个是splash配置，这两个要比中间件先执行，所以随机更换user-agent先后执行
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    'ArticleSpider_splash.middlewares.RandomUsrAgentMiddlware': 811,# 这是更换user_agent的
    # 'ArticleSpider.middlewares.RandomProxyMiddleware':544,  # 这是更换ip的
    # 'ArticleSpider.middlewares.RandomProxy':544,  # 这是更换ip的
    # 'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html

# 后面的1，2是什么，#数字越小，优先级越高
# 这是百度上查的，每个pipeline后面有一个数值, 这个数值的范围是0-1000, 这个数值确定了他们的运行顺序(即优先级), 数字越小越优先执行.
ITEM_PIPELINES = {

    # 数据存入redis的管道
    'scrapy_redis.pipelines.RedisPipeline': 40,
    # 这个是自动下载图片，还得写一个IMAGES_STORE。（还有一个下载文件的没写进来，看网页有没有文件要下载）
    # 'scrapy.pipelines.images.ImagesPipeline':289,
    # 先处理文件图片优先级高一些
    # 'ArticleSpider.pipelines.ArticleImagePipeline': 1,

    # 'ArticleSpider.pipelines.JsonWithEncodingPipeline':2,# 两种写入json方式，JsonExporterPipleline是最好的，根据个人需要
    # 'ArticleSpider.pipelines.JsonExporterPipleline': 3,

    # 'ArticleSpider.pipelines.MysqlPipeline':4,# 这是同步插入数据库
    'ArticleSpider_splash.pipelines.MysqlTwistedPipline': 50,# 这是异步插入数据库
    # 'ArticleSpider.pipelines.ArticlespiderPipeline':300,


    # 'ArticleSpider.pipelines.ElasticsearchPipline': 1,

}
# splash配置
SPLASH_URL = 'http://192.168.99.100:8050'
# 这是splash的配置
# DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'

# 去重过滤器
# DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
# DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter" # 指纹生成以及去重类
DUPEFILTER_CLASS = 'tools.dupefilter_redis_splash.SplashAwareDupeFilter' # 混合去重类的位置

# scrapy_redis断点续爬
SCHEDULER = "scrapy_redis.scheduler.Scheduler" # 调度器类
SCHEDULER_PERSIST = True # 持久化请求队列和指纹集合, scrapy_redis和scrapy_splash混用使用splash的DupeFilter!
REDIS_URL = "redis://127.0.0.1:6379" # redis的url


# 这是scrapy下载图片的设置
# 要指定下载front_image_url这个字段，IMAGES_URLS_FIELD是固定的
IMAGES_URLS_FIELD = "front_image_url"
project_dir = os.path.abspath(os.path.dirname(__file__))# os.path.dirname是当前的这个文件的路径，就是settings这个文件夹，os.path.abspath是上一节目录的路径，就是ArticleSpider文件
IMAGES_STORE = os.path.join(project_dir, 'images')# 下载图片的放在哪里


import sys
# 这个是在创建lagou的时候会出现的一个ImportError错误：No nodule named utils，加上这个动态路径就能解决
BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'ArticleSpider_splash'))

# USER_AGENT这个值在downloadermiddlewares有，如果在settings没有这个值，就会使用scrapy的用户代理，所以这是一定要的写在这里的
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3080.5 Safari/537.36"

# 一个随机的user-Agent设置为随机，可以在middlewares中配置
RANDOM_UA_TYPE = "random"



# IMAGES_MIN_HEIGHT = 100 # 下载的图片必须是100*100
# IMAGES_MIN_WIDTH = 100


# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# 连接mysql数据库
MYSQL_HOST = "localhost"
MYSQL_DBNAME = "article_spider"
MYSQL_USER = "tangming"
MYSQL_PASSWORD = "130796"


SQL_DATETIME_FORMAT = "%Y-%M-%D %h:%M:%S"
SQL_DATE_FORMAT = "%Y-%M-%D"





# 代理ip
# PROXIES = [
#     {'ip_port': '115.223.213.94:9000', 'user_passwd': ''},
#     {'ip_port': '60.214.155.243:53281', 'user_passwd': ''},
#     {'ip_port': '121.232.146.162:9000', 'user_passwd': ''},
#     {'ip_port': '113.116.146.178:9000', 'user_passwd': ''},
# ]


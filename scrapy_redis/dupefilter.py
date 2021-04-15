import logging
import time

from scrapy.dupefilters import BaseDupeFilter
from scrapy.utils.request import request_fingerprint

from . import defaults
from .connection import get_redis_from_settings
from ArticleSpider_splash.tools.bloomfilter import PyBloomFilter, conn

logger = logging.getLogger(__name__)


# TODO: Rename class to RedisDupeFilter.
# 这个类也是继承scrapy下的dupefilters的但是在这里它加了一些server,key
class RFPDupeFilter(BaseDupeFilter):
    """Redis-based request duplicates filter.

    This class can also be used with default Scrapy's scheduler.

    """

    logger = logger

    def __init__(self, server, key, debug=False):
        """Initialize the duplicates filter.

        Parameters
        ----------
        server : redis.StrictRedis
            The redis server instance.
        key : str
            Redis key Where to store fingerprints.
        debug : bool, optional
            Whether to log filtered requests.

        """
        self.server = server
        self.key = key
        self.debug = debug
        self.logdupes = True
        # 全局的bloomfilter对象bf,我们不可能每次生成request_seen()，的时候就去生成一个bf对象
        # 所以设置一个全局的对象bf，
        # key=key是这个RFPDupeFilter初始化的key
        self.bf = PyBloomFilter(conn=conn, key=key)

    @classmethod
    def from_settings(cls, settings):
        """Returns an instance from given settings.

        This uses by default the key ``dupefilter:<timestamp>``. When using the
        ``scrapy_redis.scheduler.Scheduler`` class, this method is not used as
        it needs to pass the spider name in the key.

        Parameters
        ----------
        settings : scrapy.settings.Settings

        Returns
        -------
        RFPDupeFilter
            A RFPDupeFilter instance.


        """
        # 这个server就是调用了connections文件中的get_redis_from_settings函数
        # server初始化就连接到了redis了
        # 它其实是一个set去重
        server = get_redis_from_settings(settings)

        # XXX: This creates one-time key. needed to support to use this
        # class as standalone dupefilter with scrapy's default scheduler
        # if scrapy passes spider on open() method this wouldn't be needed
        # TODO: Use SCRAPY_JOB env as default and fallback to timestamp.
        key = defaults.DUPEFILTER_KEY % {'timestamp': int(time.time())}
        # DUPEFILTER_DEBUG是在settings下的，而这是在这里打印我们的过滤信息
        debug = settings.getbool('DUPEFILTER_DEBUG')
        return cls(server, key=key, debug=debug)

    @classmethod
    def from_crawler(cls, crawler):
        """Returns instance from crawler.

        Parameters
        ----------
        crawler : scrapy.crawler.Crawler

        Returns
        -------
        RFPDupeFilter
            Instance of RFPDupeFilter.

        """
        return cls.from_settings(crawler.settings)

    def request_seen(self, request):
        """Returns True if request was already seen.

        Parameters
        ----------
        request : scrapy.http.Request

        Returns
        -------
        bool

        """
        fp = self.request_fingerprint(request)

        if self.bf.is_exist(fp):    # 如果存在在里面了，那就不要再放进redis了，返回True
            return True
        else:
            self.bf.add(fp)     # 如果不存在，那就放进redis中，但用的策略是bloomfilter，己放的url是用bf集合管理
            return False    # 如果不存在，同时返回False
        # This returns the number of values added, zero if already exists.
        # self.key就是变量的名称，fp就是requests的一个指纹，这个指纹会加入到这个key里面

        # added = self.server.sadd(self.key, fp)
        # 如果等于0，那就入库失败，那就说明己经存在了，也就是说request_seen等于True了
        # return added == 0

    def request_fingerprint(self, request):
        """Returns a fingerprint for a given request.

        Parameters
        ----------
        request : scrapy.http.Request

        Returns
        -------
        str

        """
        # 点进这里就有指纹去重哈希
        return request_fingerprint(request)

    @classmethod
    def from_spider(cls, spider):
        settings = spider.settings
        server = get_redis_from_settings(settings)
        dupefilter_key = settings.get("SCHEDULER_DUPEFILTER_KEY", defaults.SCHEDULER_DUPEFILTER_KEY)
        key = dupefilter_key % {'spider': spider.name}
        debug = settings.getbool('DUPEFILTER_DEBUG')
        return cls(server, key=key, debug=debug)

    def close(self, reason=''):
        """Delete data on close. Called by Scrapy's scheduler.

        Parameters
        ----------
        reason : str, optional

        """
        self.clear()

    def clear(self):
        """Clears fingerprints data."""
        self.server.delete(self.key)

    def log(self, request, spider):
        """Logs given request.

        Parameters
        ----------
        request : scrapy.http.Request
        spider : scrapy.spiders.Spider

        """
        if self.debug:
            msg = "Filtered duplicate request: %(request)s"
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
        elif self.logdupes:
            msg = ("Filtered duplicate request %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
            self.logdupes = False

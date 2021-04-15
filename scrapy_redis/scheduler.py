import importlib
import six

from scrapy.utils.misc import load_object

from . import connection, defaults

"""
这是调度器
是比较核心的一个文件
在scrapy/core/scheduler有两个比较重要的函数
"""


# TODO: add SCRAPY_JOB support.
class Scheduler(object):
    """Redis-based scheduler

    Settings
    --------
    SCHEDULER_PERSIST : bool (default: False)
        Whether to persist or clear redis queue.
    SCHEDULER_FLUSH_ON_START : bool (default: False)
        Whether to flush redis queue on start.
    SCHEDULER_IDLE_BEFORE_CLOSE : int (default: 0)
        How many seconds to wait before closing if no message is received.
    SCHEDULER_QUEUE_KEY : str
        Scheduler redis key.
    SCHEDULER_QUEUE_CLASS : str
        Scheduler queue class.
    SCHEDULER_DUPEFILTER_KEY : str
        Scheduler dupefilter redis key.
    SCHEDULER_DUPEFILTER_CLASS : str
        Scheduler dupefilter class.
    SCHEDULER_SERIALIZER : str
        Scheduler serializer.

    """

    # flush_on_start当我们启动时，会清除这个队列的所有数据
    def __init__(self, server,
                 persist=False,
                 flush_on_start=False,
                 queue_key=defaults.SCHEDULER_QUEUE_KEY,
                 queue_cls=defaults.SCHEDULER_QUEUE_CLASS,
                 dupefilter_key=defaults.SCHEDULER_DUPEFILTER_KEY,
                 dupefilter_cls=defaults.SCHEDULER_DUPEFILTER_CLASS,
                 idle_before_close=0,
                 serializer=None):
        """Initialize scheduler.

        Parameters
        ----------
        server : Redis
            The redis server instance.
        persist : bool
            Whether to flush requests when closing. Default is False.
        flush_on_start : bool
            Whether to flush requests on start. Default is False.
        queue_key : str
            Requests queue key.
        queue_cls : str
            Importable path to the queue class.
        dupefilter_key : str
            Duplicates filter key.
        dupefilter_cls : str
            Importable path to the dupefilter class.
        idle_before_close : int
            Timeout before giving up.

        """
        if idle_before_close < 0:
            raise TypeError("idle_before_close cannot be negative")

        self.server = server
        self.persist = persist
        self.flush_on_start = flush_on_start
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.dupefilter_cls = dupefilter_cls
        self.dupefilter_key = dupefilter_key
        self.idle_before_close = idle_before_close
        self.serializer = serializer
        self.stats = None

    def __len__(self):
        return len(self.queue)

    # 这是我们的一个入口
    @classmethod
    def from_settings(cls, settings):
        kwargs = {
            'persist': settings.getbool('SCHEDULER_PERSIST'),
            'flush_on_start': settings.getbool('SCHEDULER_FLUSH_ON_START'),
            'idle_before_close': settings.getint('SCHEDULER_IDLE_BEFORE_CLOSE'),
        }

        # If these values are missing, it means we want to use the defaults.
        optional = {
            # TODO: Use custom prefixes for this settings to note that are
            # specific to scrapy-redis.
            'queue_key': 'SCHEDULER_QUEUE_KEY',

            # SCHEDULER_QUEUE_CLASS在defaults中也是调用的PriorityQueue队列
            'queue_cls': 'SCHEDULER_QUEUE_CLASS',
            # SCHEDULER_DUPEFILTER_KEY是一个去重
            'dupefilter_key': 'SCHEDULER_DUPEFILTER_KEY',
            # We use the default setting name to keep compatibility.
            'dupefilter_cls': 'DUPEFILTER_CLASS',
            'serializer': 'SCHEDULER_SERIALIZER',
        }
        for name, setting_name in optional.items():
            val = settings.get(setting_name)
            if val:
                kwargs[name] = val

        # Support serializer as a path to a module.
        if isinstance(kwargs.get('serializer'), six.string_types):
            kwargs['serializer'] = importlib.import_module(kwargs['serializer'])

        server = connection.from_settings(settings)
        # Ensure the connection is working.
        server.ping()

        return cls(server=server, **kwargs)

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls.from_settings(crawler.settings)
        # FIXME: for now, stats are only supported from this constructor
        instance.stats = crawler.stats
        return instance

    def open(self, spider):
        self.spider = spider

        try:
            self.queue = load_object(self.queue_cls)(
                server=self.server,
                spider=spider,
                key=self.queue_key % {'spider': spider.name},
                serializer=self.serializer,
            )
        except TypeError as e:
            raise ValueError("Failed to instantiate queue class '%s': %s",
                             self.queue_cls, e)

        self.df = load_object(self.dupefilter_cls).from_spider(spider)

        # # flush_on_start当我们启动时，会清除这个队列的所有数据
        if self.flush_on_start:
            # 点进flush()就会看到self.queue.clear()，清除队列
            self.flush()
        # notice if there are requests already in the queue to resume the crawl
        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.flush()

    def flush(self):
        self.df.clear()
        self.queue.clear()

    # 这是很重要的两个函数
    def enqueue_request(self, request):
        """
        增量爬取的一个源码
        :param request:
        :return:
        """
        # 通信，从redis中获取url并放入到队列中
        # import redis
        # import json
        # import scrapy
        # # 每次都有url放到queue的时候。我自己加入一段逻辑，先从这个queue上获取 这个url
        # rd = redis.Redis("127.0.0.1", decode_responses=True)
        #
        # # 先检查指定的redis队列是否有url，先做一个while，检查是否为空的方法rd.llen(),是一个列表类型
        # list_name = "cnblogs:new_urls"
        # while rd.llen(list_name):   # 1.得到url，，，，，，，，重点：：：：这是放入
        #     # 先做成一个字符串，再反序列化回来，再做一个json，就能得到 一个url和优先级
        #     data = json.loads(rd.lpop(list_name))   # 2.得到优先级
        #     callback_func = getattr(self.spider, data[2])
        #     req = scrapy.Request(url=data[0], dont_filter=False, callback=callback_func, priority=data[1])# 3.再做一个callback，根据自己的需求回调到哪一个函数，是parse还是parse_detail
        #
        #     # 再放到一个队列中，用push()方法，我们用的是默认PriorityQueue队列
        #     # 其实每个Queue都有push()方法，但我们默认的是PriorityQueue队列
        #     self.queue.push(req)
        """
        增量爬取的结束
        """
        if not request.dont_filter and self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        self.queue.push(request)
        return True

    # 这是很重要的两个函数， 这是获取下一个request方法
    def next_request(self):

        # 设置queue的队列优先就可以完成增量爬取self.queue.pop，在enqueue_request改动
        block_pop_timeout = self.idle_before_close

        # 这是用的pop方法，也就是出队，
        # 其实每个Queue都有pop()方法，但我们默认的是PriorityQueue队列方法
        request = self.queue.pop(block_pop_timeout)
        if request and self.stats:  # 重点：：：这是出来的url
            # scheduler/dequeued/redis这是中间状态
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0



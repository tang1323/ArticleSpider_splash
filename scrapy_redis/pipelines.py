from scrapy.utils.misc import load_object
from scrapy.utils.serialize import ScrapyJSONEncoder
from twisted.internet.threads import deferToThread

from . import connection, defaults


default_serialize = ScrapyJSONEncoder().encode


# 在settings中ITEM_PIPELINES己经配置好了
class RedisPipeline(object):
    """
    是将我们的item放到redis中，但是要在settings里面配置

    """
    """Pushes serialized item into a redis list/queue

    Settings
    --------
    REDIS_ITEMS_KEY : str
        Redis key where to store items.
    REDIS_ITEMS_SERIALIZER : str
        Object path to serializer function.

    """

    def __init__(self, server,
                 key=defaults.PIPELINE_KEY,
                 serialize_func=default_serialize):
        # default_serialize的作用就是将我们传过来的item进行一个序列化才放到我们的redis中
        # redis放的是字符串或者是数字之类有东西 ， 如果放的是类就好不保存
        # 所以必须做一个序列化
        """Initialize pipeline.

        Parameters
        ----------
        server : StrictRedis
            Redis client instance.
        key : str
            Redis key where to store items.
        serialize_func : callable
            Items serializer function.

        """
        self.server = server
        self.key = key
        self.serialize = serialize_func

    # 这是入口， from_settings是被from_crawler调用的
    # from_settings()是在connection中
    @classmethod
    def from_settings(cls, settings):
        params = {
            'server': connection.from_settings(settings),
        }
        # 这里是不同的spider是放在不同的变量的
        if settings.get('REDIS_ITEMS_KEY'):
            params['key'] = settings['REDIS_ITEMS_KEY']
        if settings.get('REDIS_ITEMS_SERIALIZER'):
            params['serialize_func'] = load_object(
                settings['REDIS_ITEMS_SERIALIZER']
            )

        # 这个是上面的if设置的，
        # 如果不设置他会自己有默认的serialize_func=default_serialize，在30行
        return cls(**params)

    # from_settings是被from_crawler调用的
    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings)

    # 这是pipelines重要的函数
    # deferToThread是异步的操作，而且是将item传到_process_item来做寿
    def process_item(self, item, spider):
        """
        我们每个item保存到redis中肯定要生成对应变量名
        """
        return deferToThread(self._process_item, item, spider)

    # _process_item是异步化的，是放到另一个线程来做
    # 为什么这个函数不直接放在process_item， 因为是为了高效
    def _process_item(self, item, spider):
        # 将每一个item生成一个变量名
        key = self.item_key(item, spider)

        # 然后这里将item做序列化成一个data
        data = self.serialize(item)
        # rpush就是放在队列顺序中的队尾，也就是在队列的队尾插入数据
        self.server.rpush(key, data)
        return item

    def item_key(self, item, spider):
        """Returns redis key based on given spider.

        Override this function to use a different key depending on the item
        and/or spider.

        """
        return self.key % {'spider': spider.name}

from scrapy.utils.reqser import request_to_dict, request_from_dict

from . import picklecompat


"""
这个文件和调度器(scheduler)一起用的
"""


class Base(object):
    """Per-spider base queue class"""

    def __init__(self, server, spider, key, serializer=None):
        """Initialize per-spider redis queue.

        Parameters
        ----------
        server : StrictRedis
            Redis client instance.
        spider : Spider
            Scrapy spider instance.
        key: str
            Redis key where to put and get messages.
        serializer : object
            Serializer object with ``loads`` and ``dumps`` methods.

        """
        if serializer is None:
            # Backward compatibility.
            # TODO: deprecate pickle.
            serializer = picklecompat
        if not hasattr(serializer, 'loads'):
            raise TypeError("serializer does not implement 'loads' function: %r"
                            % serializer)
        if not hasattr(serializer, 'dumps'):
            raise TypeError("serializer '%s' does not implement 'dumps' function: %r"
                            % serializer)

        self.server = server
        self.spider = spider
        self.key = key % {'spider': spider.name}
        self.serializer = serializer

    def _encode_request(self, request):
        """Encode a request object"""
        obj = request_to_dict(request, self.spider)
        return self.serializer.dumps(obj)

    def _decode_request(self, encoded_request):
        """Decode an request previously encoded"""
        obj = self.serializer.loads(encoded_request)
        return request_from_dict(obj, self.spider)

    def __len__(self):
        """Return the length of the queue"""
        raise NotImplementedError

    def push(self, request):
        """Push a request"""
        raise NotImplementedError

    def pop(self, timeout=0):
        """Pop a request"""
        raise NotImplementedError

    def clear(self):
        """Clear queue/stack"""
        self.server.delete(self.key)


# first in first out翻译过来就是先进先出队列，也就是有序的队列
# 也就是在队尾插入数据,用rpush在队尾插入数据， 理应是用rpush插入队尾的
# 那在这里用的是lpush是有问题么
class FifoQueue(Base):
    """Per-spider FIFO queue"""

    def __len__(self):
        """Return the length of the queue"""
        return self.server.llen(self.key)

    # 来一个数据就在队头插入数据
    def push(self, request):
        """Push a request"""
        # 这里的lpush是在队头插入数据的，理应是用rpush插入队尾的
        # 但是在pop做了逻辑是从队尾拿数据的所以也是正确的
        self.server.lpush(self.key, self._encode_request(request))

    # 取数据在队尾取
    def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            # brpop这里是在队尾取的数据，也是和队列同一样的先进先出的策略
            data = self.server.brpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = self.server.rpop(self.key)
        if data:
            return self._decode_request(data)


# 关键是这个Queue，默认也是使用这个Queue，在default.py中就有这个设置
class PriorityQueue(Base):
    """Per-spider priority queue abstraction using redis' sorted set"""

    def __len__(self):
        """Return the length of the queue"""
        # zcard是有序的集合
        return self.server.zcard(self.key)

    # 插入数据
    def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        # score分数,是可以在我们的request设置优先级的，数字越大优先级越高
        score = -request.priority
        # We don't use zadd method as the order of arguments change depending on
        # whether the class is Redis or StrictRedis, and the option of using
        # kwargs only accepts strings, not bytes.
        self.server.execute_command('ZADD', self.key, score, data)

    # 取出数据
    def pop(self, timeout=0):
        """
        Pop a request
        timeout not support in this queue class
        """
        # use atomic range/remove using multi/exec
        pipe = self.server.pipeline()
        pipe.multi()
        # 0, 0就是从第一个取数据
        pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
        results, count = pipe.execute()
        if results:
            return self._decode_request(results[0])


# last in first out后进先出，也就是我们的栈
class LifoQueue(Base):
    """Per-spider LIFO queue."""

    def __len__(self):
        """Return the length of the stack"""
        return self.server.llen(self.key)

    # 有数据就在队头插入数据
    def push(self, request):
        """Push a request"""
        # 所以这里用的是lpush
        self.server.lpush(self.key, self._encode_request(request))

    # 取数据
    def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            # blpop的意思是从左边取数据，也就是在队头取数据
            data = self.server.blpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = self.server.lpop(self.key)

        if data:
            return self._decode_request(data)


# TODO: Deprecate the use of these names.
SpiderQueue = FifoQueue
SpiderStack = LifoQueue
SpiderPriorityQueue = PriorityQueue











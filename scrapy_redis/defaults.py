import redis


# For standalone use.
# 这个实际是用来保存我们访问过的requests
DUPEFILTER_KEY = 'dupefilter:%(timestamp)s'

# 它实际上是根据我们的每个spider的items都有一个队列
PIPELINE_KEY = '%(spider)s:items'

# 这个是用了redis.py的模块，这个在github上搜索就有了，就是用这个做驱动的
REDIS_CLS = redis.StrictRedis
# 连接redis的一个编码
REDIS_ENCODING = 'utf-8'
# Sane connection defaults.
# 这个是就redis.py的一些参数
REDIS_PARAMS = {
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
    'retry_on_timeout': True,
    'encoding': REDIS_ENCODING,
}

# 这个就是requests的一个队列
SCHEDULER_QUEUE_KEY = '%(spider)s:requests'
# 这个就是我们使用哪一种的队列类型，在scrapy-redis有三种队列,在queue.py文件中你就会看到
SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.PriorityQueue'
# 是用来保存的去重它的一个key,  我们可以理解为变量名
SCHEDULER_DUPEFILTER_KEY = '%(spider)s:dupefilter'
SCHEDULER_DUPEFILTER_CLASS = 'scrapy_redis.dupefilter.RFPDupeFilter'

START_URLS_KEY = '%(name)s:start_urls'
START_URLS_AS_SET = False
START_URLS_AS_ZSET = False

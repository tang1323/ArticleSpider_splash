from __future__ import absolute_import
from copy import deepcopy
from scrapy.utils.request import request_fingerprint
from scrapy.utils.url import canonicalize_url
from scrapy_splash.utils import dict_hash
from scrapy_redis.dupefilter import RFPDupeFilter


def splash_request_fingerprint(request, include_headers=None):
    """ Request fingerprint which takes 'splash' meta key into account """
    # 生成指纹
    fp = request_fingerprint(request, include_headers=include_headers)

    # 实现了splash的渲染功能代码
    if 'splash' not in request.meta:
        return fp

    splash_options = deepcopy(request.meta['splash'])
    args = splash_options.setdefault('args', {})

    if 'url' in args:
        args['url'] = canonicalize_url(args['url'], keep_fragments=True)

    return dict_hash(splash_options, fp)


# 实现了scrapy_redis的指纹去重功能
# 又完成了scrapy_splash渲染功能
class SplashAwareDupeFilter(RFPDupeFilter):
    """
    DupeFilter that takes 'splash' meta key in account.
    It should be used with SplashMiddleware.
    """
    def request_fingerprint(self, request):
        return splash_request_fingerprint(request)

import requests
from scrapy.selector import Selector
import MySQLdb

conn = MySQLdb.connect(host="127.0.0.1", user="tangming", passwd="130796", db="article_spider", charset="utf8")
cursor = conn.cursor()

# 需要登录 的就要cookies_enabled设置为True
custom_settings = {
    "COOKIES_ENABLED": False,
    "DOWNLOAD_DELAY":10

}


def crawl_ips():
    # 爬取快代理免费ip代理
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36 Edg/80.0.361.111"}


    for i in range(3586):# 有3586页的ip，做一个遍历
        re = requests.get("https://www.kuaidaili.com/free/inha/{}/".format(i), headers=headers)



        selector = Selector(text=re.text)
        all_trs = selector.css("#list tr")



        ip_list = []
        for tr in all_trs[1:]:
            speed_str = tr.css('td:nth-child(6)::text').extract()
            if speed_str:
                str = ''.join(speed_str)
                speed = float(str.split("秒")[0]) #要将列表转换成字符串才能split
            all_texts = tr.css("td::text").extract()

            ip = all_texts[0]
            port = all_texts[1]
            proxy_type = all_texts[3]

            ip_list.append((ip, port, proxy_type, speed))
            print("{},{},{}".format(ip, port, proxy_type))


        for ip_info in ip_list:
            cursor.execute(
                "insert proxy_ip(ip, port, speed, proxy_type) VALUES('{0}', '{1}', '{2}', 'HTTP')".format(
                    ip_info[0], ip_info[1], ip_info[3]
                )
            )
            conn.commit()


class GetIP(object):

    #删除不可用的ip的myslq语句
    def delete_ip(self, ip):

        #从数据库删除 无效的ip的mysql语句
        delete_sql = """
                delete from proxy_ip where ip='{0}'
        
        """.format(ip)
        cursor.execute(delete_sql)
        conn.commit()
        return True

    # 判断ip是否可用
    def judge_ip(self, ip, port):
        http_url = "https://www.lagou.com"
        proxy_url = "http://{0}:{1}".format(ip, port)
        try:
            proxy_dict = {
                "http":proxy_url,
            }
            response = requests.get(http_url,proxies=proxy_dict)
        except:
            print("不可用,即将删除。。。。。")
            self.delete_ip(ip)#删除不可用ip
            return  False
        else:
            # status_code是服务返回来的一个状态码
            code = response.status_code
            if code >=200 and code <300:
                print("有效ip")
                # print("{},{}".format(ip, port))
                return True
            else:
                print("不可用,即将删除。")
                self.delete_ip(ip)  # 删除不可用ip
                return False


    # 随机获取一个在数据库的一个ip
    def get_random_ip(self):

        # 这是随机获取ip的mysql语句
        random_sql = """
                select ip, port from proxy_ip
                order by rand()
                limit 1
              """
        result = cursor.execute(random_sql)
        for ip_info in cursor.fetchall():
            ip = ip_info[0]
            port = ip_info[1]

            judge_re = self.judge_ip(ip, port)# 把要用的ip送去judge_ip函数检查一下
            if judge_re:
                return "http://{0}:{1}".format(ip, port)
            else:
                return self.get_random_ip()



if __name__ == "__main__":
    # get_ip = GetIP()
    # get_ip.get_random_ip()
    crawl_ips()












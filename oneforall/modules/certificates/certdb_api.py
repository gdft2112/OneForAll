# coding=utf-8
import time
import queue
import config
from common.query import Query
from common import utils
from config import logger


class CertDBAPI(Query):
    def __init__(self, domain):
        Query.__init__(self)
        self.domain = domain
        self.module = 'Certificate'
        self.source = 'CertDBQuery'
        self.addr = 'https://api.spyse.com/v1/subdomains'
        self.token = config.certdb_api_token

    def query(self):
        """
        向接口查询子域并做子域匹配
        """
        page_num = 1
        while True:
            time.sleep(self.delay)
            self.header = self.get_header()
            self.proxy = self.get_proxy(self.source)
            params = {'domain': self.domain, 'api_token': self.token, 'page': page_num}
            resp = self.get(self.addr, params)
            if not resp:
                return
            resp_json = resp.json()
            subdomains_find = utils.match_subdomain(self.domain, str(resp_json))
            self.subdomains = self.subdomains.union(subdomains_find)  # 合并搜索子域名搜索结果
            page_num += 1
            if resp_json.get('count') < 30:  # 默认每次查询最多返回30条 当前条数小于30条说明已经查完
                break

    def run(self, rx_queue):
        """
        类执行入口
        """
        if not self.token:
            logger.log('ERROR', f'{self.source}模块API配置错误')
            logger.log('ALERT', f'不执行{self.source}模块')
            return
        logger.log('DEBUG', f'开始执行{self.source}模块查询{self.domain}的子域')
        start = time.time()
        self.query()
        end = time.time()
        self.elapsed = round(end - start, 1)
        self.save_json()
        self.gen_result()
        self.save_db()
        rx_queue.put(self.results)
        logger.log('DEBUG', f'结束执行{self.source}模块查询{self.domain}的子域')


def do(domain, rx_queue):   # 统一入口名字 方便多线程调用
    """
    类统一调用入口

    :param str domain: 域名
    :param rx_queue: 结果集队列
    """
    query = CertDBAPI(domain)
    query.run(rx_queue)
    logger.log('INFOR', f'{query.source}模块耗时{query.elapsed}秒发现{query.domain}的子域{len(query.subdomains)}个')
    logger.log('DEBUG', f'{query.source}模块发现{query.domain}的子域 {query.subdomains}')


if __name__ == '__main__':
    result_queue = queue.Queue()
    do('owasp.org', result_queue)
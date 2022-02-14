import requests
import json
import math
import time
import os
import re
from util.danteng_lib import save_json, load_json

BASE_URL = r'https://poe.game.qq.com/trade/search'
LIST_API_URL = r'https://poe.game.qq.com/api/trade/search'
EXCHANGE_API_URL = r'https://poe.game.qq.com/api/trade/exchange'
TRADE_API_URL = r'https://poe.game.qq.com/api/trade/fetch'
DATA_BASE_URL = r'https://poe.game.qq.com/api/trade/data'

DATA_BASE_PATH = 'data'

QUERY_NUMBER_PRE_PAGE = 10
SLEEP_TIME = 3
RETRY_TIME = 5
MAX_EXCHANGE_NUMBER = 50


class PoeTradeCN:
    def __init__(self, league_name, **kwargs):
        self._league_name = league_name
        self._trade_data = {}
        self._cookies = {'POESESSID': '483d3b716faceccc22ea4fd3b6c38375'}
        # self._cookies = {'POESESSID': kwargs.get('POESESSID')}
        self._sleep_time = int(kwargs.get('sleep_time')) if kwargs.get('sleep_time') else SLEEP_TIME
        self._retry_time = int(kwargs.get('retry_time')) if kwargs.get('retry_time') else RETRY_TIME
        self._query_number_per_page = int(kwargs.get('query_number_per_page')) if kwargs.get('query_number_per_page') else QUERY_NUMBER_PRE_PAGE
        self.init_data()

    # 初始化基本数据
    def init_data(self):
        for data_type in ['items', 'stats', 'static']:
            data_json_path = os.path.join(DATA_BASE_PATH, f'{data_type}.json')
            if not os.path.exists(data_json_path):
                data_url = f'{DATA_BASE_URL}/{data_type}'
                count = 0
                while True:
                    try:
                        response = requests.get(data_url, cookies=self._cookies, timeout=30)
                        if response.status_code == 200:
                            time.sleep(self._retry_time)
                            break
                        else:
                            count += 1
                            self._log(
                                f'获取基本数据[{data_type}]时，网络出错（{response.status_code}）（第{count}次），{self._retry_time}秒后重试！')
                            time.sleep(self._retry_time)
                    except Exception as e:  # 超时重新下载
                        count += 1
                        self._log(f'获取基本数据[{data_type}]时出错（第{count}次），{self._retry_time}秒后重试！')
                        time.sleep(self._retry_time)
                save_json(json.loads(response.text)['result'], data_json_path)

    def _log(self, string):
        print(f'[{self._league_name}] {string}')

    # 根据一个filter从网页市集获得数据
    def query_data(self, filter_json):
        list_data = self._query_list(filter_json)
        old_length = len(self._trade_data)
        auto_combi_text = f'[{filter_json["current"]}/{filter_json["total"]}]({"%.2f%%" % (filter_json["current"]/filter_json["total"]*100)})' if filter_json.get('auto_combi') else ''
        # TODO
        # Traceback (most recent call last):
        #   File "poe_market.py", line 379, in <module>
        #   File "poe_market.py", line 49, in run
        #   File "poe_market.py", line 68, in save_filter_result
        #   File "poe_market.py", line 155, in query_goods_data
        #   File "poemarket.py", line 40, in query_data
        # KeyError: 'id'
        # [26068] Failed to execute script poe_market
        if list_data["total"] == 0:
            self._log(f'获取到列表[{list_data["id"]}]{auto_combi_text}，此列表没有符合条件的数据')
        else:
            self._log(f'获取到列表[{list_data["id"]}]{auto_combi_text}，符合条件的数据{list_data["total"]}条，正在请求其中的{len(list_data["result"])}条')
            time.sleep(self._sleep_time)

            self._trade_data.update(self._query_item_data(list_data))
        self._log(f'获取完列表[{list_data["id"]}]{auto_combi_text}，目前总数据{len(self._trade_data)}（+{len(self._trade_data)-old_length}）')
        print('')

    # 获取列表获取列表
    def _query_list(self, filter_json):
        count = 0
        while True:
            try:
                response = requests.post(f'{LIST_API_URL}/{self._league_name}', json=filter_json, cookies=self._cookies, timeout=45)
                if response.status_code == 200:
                    time.sleep(self._retry_time)
                    break
                else:
                    count += 1
                    self._log(f'获取列表[{filter_json["name"]}]时，网络出错（{response.status_code}）（第{count}次），{self._retry_time}秒后重试！')
                    time.sleep(self._retry_time)
            except Exception as e:  # 超时重新下载
                count += 1
                self._log(f'获取列表[{filter_json["name"]}]时出错（第{count}次），{self._retry_time}秒后重试！')
                time.sleep(self._retry_time)
        return json.loads(response.text)

    # 获取项目
    def _query_item_data(self, list_data):
        query_times = math.ceil(len(list_data['result']) / self._query_number_per_page)
        item_data = {}
        count = 0
        count_500 = 0
        for i in range(query_times):
            self._log(f'正在获取列表[{list_data["id"]}]物品数据：{i+1}/{query_times}组')
            query_url = f'{TRADE_API_URL}/{",".join(list_data["result"][i * self._query_number_per_page:(i + 1) * self._query_number_per_page])}?query={list_data["id"]}'
            while True:
                try:
                    response_item_data = requests.get(query_url, cookies=self._cookies, timeout=30)
                    if response_item_data.status_code == 200:
                        time.sleep(self._sleep_time)
                        break
                    if response_item_data.status_code == 500:
                        count_500 += 1
                        if count_500 < 5:
                            self._log(f'获取列表[{list_data["id"]}]的物品数据时，获取数据失败（{response_item_data.status_code}）（第{count_500}次），{self._retry_time}秒后重试！')
                            time.sleep(self._retry_time)
                            break
                        else:
                            self._log(
                                f'获取列表[{list_data["id"]}]的物品数据时，获取数据失败（{response_item_data.status_code}）（第{count_500}次），超出数量限制，跳过该数据！')
                    else:
                        count += 1
                        self._log(f'获取列表[{list_data["id"]}]的物品数据时，网络出错（{response_item_data.status_code}）（第{count}次），{self._retry_time}秒后重试！')
                        time.sleep(self._retry_time)
                except Exception as e:  # 超时重新下载
                    count += 1
                    self._log(f'获取列表[{list_data["id"]}]的物品数据时出错（第{count}次），{self._retry_time}秒后重试！')
                    time.sleep(self._retry_time)
            if response_item_data.status_code == 500:
                continue
            for item_info in json.loads(response_item_data.text)['result']:
                if item_info:
                    item_data[item_info['id']] = item_info
        return item_data

    # 获取地图价格数据
    def _query_exchange_map_data(self):
        static_data = get_data('static')
        for static_category in static_data:
            if static_category['id'][:4] == 'Maps':
                self._log(f'开始处理[{static_category["label"]}]中的物品类型')
                for entry in static_category['entries']:
                    query_name = f'[{static_category["label"]}][{entry["text"]}]'
                    self._log(f'开始请求{query_name}的数据列表')
                    query_url = f'{EXCHANGE_API_URL}/{self._league_name}'
                    query_json = {
                        'exchange': {
                            'status': {
                                'option': 'any',
                            },
                            'have': [],
                            'want': [
                                entry['id']
                            ]
                        }
                    }
                    entry_data = self._post(query_url, query_json, query_name)
                    if len(entry_data["result"]) > MAX_EXCHANGE_NUMBER:
                        entry_data['result'] = entry_data['result'][:MAX_EXCHANGE_NUMBER]

                    self._log(f'获取到列表{query_name}，总计数据{(entry_data["total"])}条，正在请求其中的{len(entry_data["result"])}条')
                    item_data = self._query_item_data(entry_data)
                    z = 1
        z = 1

    # 请求
    def _post(self, url, json_data, name):
        count = 0
        while True:
            try:
                response = requests.post(url, json=json_data, cookies=self._cookies, timeout=45)
                time.sleep(self._sleep_time)
                if response.status_code == 200:
                    time.sleep(self._retry_time)
                    break
                else:
                    count += 1
                    self._log(f'获取{name}时，网络出错（{response.status_code}）（第{count}次），{self._retry_time}秒后重试！')
                    time.sleep(self._retry_time)
            except Exception as e:  # 超时重新下载
                count += 1
                self._log(f'获取{name}时出错（第{count}次），{self._retry_time}秒后重试！')
                time.sleep(self._retry_time)
        return json.loads(response.text)

    # 请求
    def _get_code_html(self, code):
        url = f'{BASE_URL}/{self._league_name}/{code}'
        count = 0
        while True:
            try:
                response = requests.get(url, cookies=self._cookies, timeout=45)
                time.sleep(self._sleep_time)
                if response.status_code == 200:
                    time.sleep(self._retry_time)
                    break
                else:
                    count += 1
                    self._log(f'获取{url}时，网络出错（{response.status_code}）（第{count}次），{self._retry_time}秒后重试！')
                    time.sleep(self._retry_time)
            except Exception as e:  # 超时重新下载
                count += 1
                self._log(f'获取{url}时出错（第{count}次），{self._retry_time}秒后重试！')
                time.sleep(self._retry_time)
        return response.text

    # 获取总数据
    def get_result(self):
        return self._trade_data

    # 根据code获得配置
    def query_config_from_code(self, code):
        html = self._get_code_html(code)

        find = re.findall(r'require\(\["main"], function\(\)\{require\(\["trade"], function\(t\)\{    t\((.*?)\);}\);}\);', html)
        if find:
            data_json = json.loads(find[0])
        else:
            print(f'查找[{code}]数据失败，请检查')
            return None

        # 整理数据
        result = {
            'query': data_json['state'],
            'sort': {
                'price': 'asc'
            }
        }
        result['query']['status'] = dict(option=result['query']['status'])
        return result


def get_data(data_type):
    data_json_path = os.path.join(DATA_BASE_PATH, f'{data_type}.json')
    # if not os.path.exists(data_json_path):
    #     init_data()
    return load_json(data_json_path)



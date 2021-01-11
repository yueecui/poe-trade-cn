import re
import os
import sys
from danteng_lib import save_json, load_json, save_to_csv
from PoeTradeCN import PoeTradeCN, EXCHANGE_MAP
from SaveToExcel import save_to_excel
from itertools import combinations


from config import load_config

FILTER_BASE_PATH = r'filter'
CACHE_PATH = r'Temp\temp.json'
CONFIG_PATH = r'config.ini'

DATA_BASE_URL = r'https://poe.game.qq.com/api/trade/data'


def run():
    cfg = load_config()

    filter_name_list = sys.argv[1:]

    # 下载数据
    if len(filter_name_list) == 0:
        filter_name_list = os.listdir(FILTER_BASE_PATH)

    for filter_name in filter_name_list:
        if filter_name in EXCHANGE_MAP:
            save_exchange_result(filter_name, cfg)
        else:
            save_filter_result(filter_name, cfg)


def save_filter_result(filter_name, cfg):
    print('===================================================')
    print(f'=  开始检索过滤组【{filter_name}】')
    print('===================================================')

    filter_path = os.path.join(FILTER_BASE_PATH, filter_name)
    if not os.path.exists(filter_path) or not os.path.isdir(filter_path):
        print('')
        print(f'过滤组【{filter_name}】目录不存在，请检查')
        print('')
        return False
    z = 1
    if cfg['load_cache']:
        goods_data = load_json(CACHE_PATH)
        goods_data.update(load_filter_config(filter_path))
    else:
        goods_data = query_goods_data(cfg, filter_path)

    if cfg['save_cache']:
        save_json(goods_data, CACHE_PATH)

    # 添加配置字段
    goods_data['config'] = {
        'split_mods': cfg['split_mods']
    }

    # 保存数据
    # 超过1000条用csv
    if cfg['file_type'] == 'xlsx':
        try:
            goods_data_save_to_table(goods_data, filter_name, 'xlsx')
        except Exception as e:
            print('')
            print('★ 保存成Excel时出错，尝试改用CSV输出')
            print('')
            goods_data_save_to_table(goods_data, filter_name, 'csv')
    else:
        goods_data_save_to_table(goods_data, filter_name, 'csv')

    print(f'◆过滤器【{filter_name}】内容保存完毕')
    print('')
    return True


def load_filter_config(filter_path):
    temp_data = {}

    for suffix in ['json', 'txt']:
        file_path = os.path.join(filter_path, f'config.{suffix}')
        if os.path.exists(file_path):
            temp_data.update(load_json(file_path))
            break

    return temp_data


def query_goods_data(cfg, filter_path):
    poe = PoeTradeCN(cfg['league'], sleep_time=cfg['sleep_time'], retry_time=cfg['retry_time'],
                     query_number_per_page=cfg['query_number_per_page'])

    goods_data = {
        'output_filter': [],
        'goods': {},
    }
    goods_data.update(load_filter_config(filter_path))

    for filename in os.listdir(filter_path):
        if os.path.splitext(filename)[1] not in ['.json', '.txt']:
            continue
        else:
            filter_name = os.path.splitext(filename)[0]
        if filter_name[0] == '!':
            auto_mode = 1
            filter_name = filter_name[1:]
        elif filter_name[0] == '@':
            auto_mode = 2
            filter_name = filter_name[1:]
        else:
            auto_mode = 0

        file_path = os.path.join(filter_path, filename)
        if filter_name == 'config':
            continue
        else:
            print('')
            print(f'已读取{"[自动组合]" if auto_mode > 0 else ""}[{filter_name}]过滤器，正在尝试请求数据')
            filter_json = load_json(file_path)
            filter_json['name'] = filter_name
            if auto_mode == 1:
                # 遍历第一组过滤中的每个单选项
                filter_list = filter_json['query']['stats'][0]['filters']
                total = len(filter_list)
                filter_json.update({
                    'auto_combi': True,
                    'total': total,
                    'current': 0,
                })
                for round_index in range(len(filter_list)):
                    for f_index in range(len(filter_list)):
                        if f_index == round_index:
                            filter_list[f_index]['disabled'] = False
                        else:
                            filter_list[f_index]['disabled'] = True
                    filter_json['current'] += 1
                    poe.query_data(filter_json)
            elif auto_mode == 2:
                # 遍历所有组合
                filter_list = filter_json['query']['stats'][0]['filters']
                combi = list(combinations(range(len(filter_list)), 2))
                total = len(combi)
                filter_json.update({
                    'auto_combi': True,
                    'total': total,
                    'current': 0,
                })
                for enable_list in combi:
                    for f_index in range(len(filter_list)):
                        if f_index in enable_list:
                            filter_list[f_index]['disabled'] = False
                        else:
                            filter_list[f_index]['disabled'] = True
                    filter_json['current'] += 1
                    poe.query_data(filter_json)
            else:
                poe.query_data(filter_json)

    goods_data['goods'] = poe.get_result()

    return goods_data


def goods_data_save_to_table(goods_data, filter_name, file_format):
    headers = {
        filter_name: []
    }
    contents = {
        filter_name: {}
    }
    output_filter = goods_data['output_filter']

    # 通过type=filter添加的header
    extra_header = []

    # 整理数据内容
    properties_list = []
    has_enchant = False
    has_implicit = False
    has_crafted = False
    has_dps = False
    for goods_hash, goods_info in goods_data['goods'].items():
        temp_goods_info = {
            'name': goods_info['item']['name'],
            'basetype': goods_info['item']['typeLine'],
            'ilvl': goods_info['item']['ilvl'],
            'currency': goods_info['listing']['price']['currency'] if goods_info['listing']['price'] else 'none',
            'amount': goods_info['listing']['price']['amount'] if goods_info['listing']['price'] else 0,
            'note': goods_info['item']['note'] if 'note' in goods_info['item'] else '',
            'seller': goods_info['listing']['account']['lastCharacterName'],
            'whisper': goods_info['listing']['whisper'] if goods_info['listing'].get('whisper') else '',
            'influences': '/'.join(list(goods_info['item'].get('influences').keys())) if goods_info['item'].get('influences') else ''
        }

        if 'properties' in goods_info['item']:
            for properties_info in goods_info['item']['properties']:
                if len(properties_info['values']) > 0:
                    if properties_info['name'] not in properties_list:
                        properties_list.append(properties_info['name'])
                    temp_goods_info[properties_info['name']] = properties_info['values'][0][0]

        if 'enchantMods' in goods_info['item']:
            has_enchant = True
            temp_goods_info['enchant'] = '\r\n'.join(goods_info['item']['enchantMods'])

        if 'implicitMods' in goods_info['item']:
            has_implicit = True
            temp_goods_info['implicit'] = '\r\n'.join(goods_info['item']['implicitMods'])

        if goods_info['item'].get('corrupted'):
            temp_goods_info['corrupted'] = '是'
        else:
            temp_goods_info['corrupted'] = '否'

        if 'explicitMods' in goods_info['item']:
            temp_goods_info['explicit'] = '\r\n'.join(goods_info['item']['explicitMods'])

        if 'craftedMods' in goods_info['item']:
            has_crafted = True
            temp_goods_info['crafted'] = '\r\n'.join(goods_info['item']['craftedMods'])

        # found_mod = []
        for mod_type in ['enchantMods', 'implicitMods', 'explicitMods']:
            if mod_type not in goods_info['item']:
                continue
            for mod_str in goods_info['item'][mod_type]:
                for filter_info in output_filter:
                    find = re.findall(filter_info['regex'], mod_str, re.S)
                    if find:
                        filter_type = filter_info.get('type') if filter_info.get('type') else 'sum'
                        if filter_type in ['overwrite', 'str']:
                            temp_goods_info[filter_info['name']] = find[0]
                        elif filter_type == 'filter':
                            ignore_list = filter_info.get('ignore') if filter_info.get('ignore') else []
                            if find[0] not in ignore_list:
                                if find[0] not in extra_header:
                                    extra_header.append(find[0])
                                if find[0] not in temp_goods_info:
                                    temp_goods_info[find[0]] = 0
                                temp_goods_info[find[0]] = temp_goods_info[find[0]] + 1
                        else:
                            if filter_info['name'] not in temp_goods_info:
                                temp_goods_info[filter_info['name']] = 0
                            temp_goods_info[filter_info['name']] = temp_goods_info[filter_info['name']] + int(find[0])
                    # found_mod.append(mod_str)
        # temp_goods_info['other'] = '\r\n'.join(list(set(goods_info['item']['explicitMods']).difference(set(found_mod))))

        if goods_data['config']['split_mods']:
            prefix_mod_str_list = []
            suffix_mod_str_list = []
            if goods_info['item']['extended']['mods'].get('explicit'):
                for mod_info in goods_info['item']['extended']['mods']['explicit']:
                    if mod_info['name'] == '' and mod_info['tier'] == '':
                        continue
                    if mod_info['tier'][0] == 'P':
                        prefix_mod_str_list.append(f'{mod_info["name"]}({mod_info["tier"]})')
                    elif mod_info['tier'][0] == 'S':
                        suffix_mod_str_list.append(f'{mod_info["name"]}({mod_info["tier"]})')
                    else:
                        raise Exception(f'出现预料外的词缀阶级：{mod_info["tier"]}')
            temp_goods_info['prefix_mods'] = '\r\n'.join(prefix_mod_str_list)
            temp_goods_info['suffix_mods'] = '\r\n'.join(suffix_mod_str_list)
        else:
            mod_str_list = []
            if goods_info['item']['extended']['mods'].get('explicit'):
                for mod_info in goods_info['item']['extended']['mods']['explicit']:
                    if mod_info['name'] == '' and mod_info['tier'] == '':
                        continue
                    mod_str_list.append(f'{mod_info["name"]}({mod_info["tier"]})')
            temp_goods_info['mods'] = '\r\n'.join(mod_str_list)

        if goods_info['item']['extended'].get('dps'):
            has_dps = True
            for key in ['dps', 'pdps', 'edps']:
                if goods_info['item']['extended'].get(key):
                    temp_goods_info[key] = goods_info['item']['extended'][key]

        contents[filter_name][goods_info['id']] = temp_goods_info

    # 表头补充
    headers[filter_name].extend(['name', 'basetype', 'ilvl'])
    properties_list.sort()
    for filter_info in output_filter:
        if filter_info['name'] not in headers[filter_name] and filter_info.get('type') != 'filter':
            headers[filter_name].append(filter_info['name'])
    for header_name in extra_header:
        if header_name not in headers[filter_name]:
            headers[filter_name].append(header_name)
    for properties in properties_list:
        headers[filter_name].append(properties)
    if has_dps:
        headers[filter_name].extend(['dps', 'pdps', 'edps'])
    if has_enchant:
        headers[filter_name].append('enchant')
    if has_implicit:
        headers[filter_name].append('implicit')
    headers[filter_name].append('explicit')
    if goods_data['config']['split_mods']:
        headers[filter_name].extend(['prefix_mods', 'suffix_mods'])
    else:
        headers[filter_name].append('mods')
    if has_crafted:
        headers[filter_name].append('crafted')
    headers[filter_name].extend(['influences', 'corrupted', 'currency', 'amount', 'note', 'seller', 'whisper'])

    save_path = f'{filter_name}.{file_format}'
    if file_format == 'csv':
        save_to_csv(contents[filter_name], headers[filter_name], save_path)
    elif file_format == 'xlsx':
        save_to_excel(headers, contents, save_path)


def save_exchange_result(exchange_type, cfg):
    print('===================================================')
    print(f'=  开始整理兑换列表【{exchange_type}】')
    print('===================================================')

    if cfg['GENERAL'].get('load_cache') == '1':
        goods_data = load_json(CACHE_PATH)
    else:
        goods_data = query_exchange_data(cfg['GENERAL']['league'], exchange_type)

    if cfg['GENERAL'].get('save_cache') == '1':
        save_json(goods_data, CACHE_PATH)

    # 保存数据
    # # 超过1000条用csv
    # if cfg['GENERAL'].get('file_type') == 'xlsx':
    #     try:
    #         goods_data_save_to_table(goods_data, filter_name, 'xlsx')
    #     except Exception as e:
    #         print('')
    #         print('★ 保存成Excel时出错，尝试改用CSV输出')
    #         print('')
    #         goods_data_save_to_table(goods_data, filter_name, 'csv')
    # else:
    #     goods_data_save_to_table(goods_data, filter_name, 'csv')
    #
    # print(f'◆过滤器【{filter_name}】内容保存完毕')
    # print('')
    return True


def query_exchange_data(league_name, exchange_type):
    poe = PoeTradeCN(league_name)

    exchange_data = {
        'exchange': None
    }

    poe.query_exchange_data(exchange_type)

    exchange_data['exchange'] = poe.get_result()

    return exchange_data


if __name__ == '__main__':
    run()

import re
import os
import sys
import time
from util.danteng_lib import save_json, load_json, save_to_csv
from util.SaveToExcel import save_to_excel

from module import read_app_config, query_goods_data, TradeConfig


CACHE_PATH = r'Temp\temp.json'
CONFIG_PATH = r'config.ini'

DATA_BASE_URL = r'https://poe.game.qq.com/api/trade/data'


def run():
    cfg = read_app_config()

    filter_name_list = sys.argv[1:]

    # 下载数据
    if len(filter_name_list) == 0:
        filter_name_list = os.listdir(cfg['filter_path'])

    for filter_name in filter_name_list:
        (file_name, file_type) = os.path.splitext(filter_name)
        if file_type == '':
            file_type = '.xlsx'

        filter_file_path = os.path.join(cfg['filter_path'], f'{file_name}{file_type}')

        if file_type != '.xlsx' or os.path.isdir(filter_file_path) or not os.path.exists(filter_file_path):
            continue

        print('===================================================')
        print(f'=  开始检索过滤组【{file_name}】')
        print('===================================================')

        trade_config = TradeConfig(filter_file_path)
        if not trade_config.is_ready():
            continue

        # 尝试加载缓存
        data_cache_path = os.path.join(cfg['cache_path'], f'{file_name}.json')
        data_cache = load_json(data_cache_path)
        timestamp = int(time.time())
        if not (data_cache is None) and (data_cache.get('time') or 0) + cfg['cache_time'] > timestamp:
            minute = int((timestamp - data_cache.get('time')) / 60)
            print(f'读取了{"1分钟内" if minute == 0 else f"{minute}分钟前"}的缓存...')
            goods_data = data_cache['goods']
        else:
            goods_data = query_goods_data(cfg, trade_config)
            save_json({
                'time': timestamp,
                'goods': goods_data
            }, data_cache_path)

        save_filter_result(filter_name, cfg)


def save_filter_result(filter_name, cfg):
    print('===================================================')
    print(f'=  开始检索过滤组【{filter_name}】')
    print('===================================================')

    filter_path = os.path.join(cfg['filter_path'], filter_name)
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


if __name__ == '__main__':
    run()

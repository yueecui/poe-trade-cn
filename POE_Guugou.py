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
        generate_bat(cfg)
    else:
        find_trade_info(cfg, filter_name_list)


# 生成执行用的BAT
def generate_bat(cfg):
    root_file_list = os.listdir()
    for bat_name in root_file_list:
        (file_name, file_type) = os.path.splitext(bat_name)
        bat_file_path = os.path.join(bat_name)
        if file_type == '.bat' and (not os.path.isdir(bat_file_path)) and os.path.exists(bat_file_path):
            os.remove(bat_file_path)

    filter_name_list = os.listdir(cfg['filter_path'])
    exe_name = os.path.split(sys.argv[0])[1]
    count = 0
    for filter_name in filter_name_list:
        (file_name, file_type) = os.path.splitext(filter_name)
        filter_file_path = os.path.join(cfg['filter_path'], filter_name)
        if file_type != '.xlsx' or os.path.isdir(filter_file_path) or not os.path.exists(filter_file_path):
            continue
        bat_file_path = os.path.join(f'run_{file_name}.bat')
        with open(bat_file_path, 'w') as f:
            f.write(f'@{exe_name} "{file_name}"\n@pause')
        count += 1

    if count > 0:
        print(f'生成可执行bat文件完成！共生成{count}个')
    else:
        print(f'没有在{cfg["filter_path"]}目录中找到可用的过滤器，请先配置过滤器文件')


def find_trade_info(cfg, filter_name_list):
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
                'time': int(time.time()),
                'goods': goods_data
            }, data_cache_path)

        data = {
            'name': file_name,
            'split_mods': cfg['split_mods'],
            'file_type': cfg['file_type'],
            'goods': goods_data
        }

        save_result(data, trade_config)


def save_result(data, trade_config):
    # 保存数据
    # 超过1000条用csv
    if data['file_type'] == 'xlsx':
        try:
            goods_data_save_to_table(data, trade_config, 'xlsx')
        except Exception as e:
            print('')
            print('★ 保存成Excel时出错，尝试改用CSV输出')
            print('')
            goods_data_save_to_table(data, trade_config, 'csv')
    else:
        goods_data_save_to_table(data, trade_config, 'csv')

    print(f'◆过滤器【{data["name"]}】内容保存完毕')
    print('')
    return True


def goods_data_save_to_table(data, trade_config, file_format):
    filter_name = data["name"]
    headers = {
        filter_name: []
    }
    contents = {
        filter_name: {}
    }
    header_config = trade_config.get_header_config()

    # 通过过滤器添加的header
    filter_header = []
    # 通过type=filter添加的header
    extra_header = []

    # 整理数据内容
    properties_list = []
    has_enchant = False
    has_implicit = False
    has_crafted = False
    has_dps = False
    for goods_hash, goods_info in data['goods'].items():
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

        pob = [
            goods_info['item']['name'],
            goods_info['item']['typeLine'],
        ]

        if 'properties' in goods_info['item']:
            for properties_info in goods_info['item']['properties']:
                if len(properties_info['values']) > 0:
                    if properties_info['name'] not in properties_list:
                        properties_list.append(properties_info['name'])
                    temp_goods_info[properties_info['name']] = properties_info['values'][0][0]

        if 'enchantMods' in goods_info['item']:
            has_enchant = True
            temp_goods_info['enchant'] = '\r\n'.join(goods_info['item']['enchantMods'])
            pob.extend([f'{text} (enchant)' for text in goods_info['item']['enchantMods']])

        if 'implicitMods' in goods_info['item']:
            has_implicit = True
            temp_goods_info['implicit'] = '\r\n'.join(goods_info['item']['implicitMods'])
            pob.extend([f'{text} (implicit)' for text in goods_info['item']['implicitMods']])

        if goods_info['item'].get('corrupted'):
            temp_goods_info['corrupted'] = '是'
        else:
            temp_goods_info['corrupted'] = '否'

        if 'explicitMods' in goods_info['item']:
            temp_goods_info['explicit'] = '\r\n'.join(goods_info['item']['explicitMods'])
            pob.extend(goods_info['item']['explicitMods'])

        if 'craftedMods' in goods_info['item']:
            has_crafted = True
            temp_goods_info['crafted'] = '\r\n'.join(goods_info['item']['craftedMods'])
            pob.extend([f'{text} (crafted)' for text in goods_info['item']['craftedMods']])

        # found_mod = []
        for mod_type in ['enchantMods', 'implicitMods', 'explicitMods']:
            if mod_type not in goods_info['item']:
                continue
            for mod_str in goods_info['item'][mod_type]:
                for header, filter_group in header_config.items():
                    for filter_set in filter_group:
                        # 记录header
                        if filter_set['模式'] < 2:
                            if header not in filter_header:
                                filter_header.append(header)

                        find = re.findall(filter_set['正则表达式'], mod_str, re.S)
                        if find:
                            # 覆盖数值模式
                            if filter_set['模式'] == 1:
                                temp_goods_info[header] = find[0]
                            # 计数模式（珠宝附带技能）
                            elif filter_set['模式'] == 2 or filter_set['模式'] == 3:
                                if (filter_set['模式'] == 2 and find[0] not in filter_set['列表']) or (filter_set['模式'] == 3 and find[0] in filter_set['列表']):
                                    if find[0] not in extra_header:
                                        extra_header.append(find[0])
                                    if find[0] not in temp_goods_info:
                                        temp_goods_info[find[0]] = 0
                                    temp_goods_info[find[0]] = temp_goods_info[find[0]] + 1
                            # 默认：累加模式
                            else:
                                if header not in temp_goods_info:
                                    temp_goods_info[header] = 0
                                temp_goods_info[header] = temp_goods_info[header] + int(find[0])

        # 前后缀分开显示
        if data['split_mods']:
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

        temp_goods_info['pob'] = '\r\n'.join(pob)
        contents[filter_name][goods_info['id']] = temp_goods_info

    # 表头补充
    headers[filter_name].extend(['name', 'basetype', 'ilvl'])
    properties_list.sort()
    for header_name in filter_header:
        if header_name not in headers[filter_name]:
            headers[filter_name].append(header_name)
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
    if data['split_mods']:
        headers[filter_name].extend(['prefix_mods', 'suffix_mods'])
    else:
        headers[filter_name].append('mods')
    if has_crafted:
        headers[filter_name].append('crafted')
    headers[filter_name].extend(['influences', 'corrupted', 'currency', 'amount', 'note', 'seller', 'whisper', 'pob'])

    save_path = f'result_{filter_name}.{file_format}'
    if file_format == 'csv':
        save_to_csv(contents[filter_name], headers[filter_name], save_path)
    elif file_format == 'xlsx':
        save_to_excel(headers, contents, save_path)


if __name__ == '__main__':
    run()

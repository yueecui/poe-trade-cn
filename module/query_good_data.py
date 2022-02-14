import os
import json
from itertools import combinations
from danteng_lib import save_json, load_json
from .PoeTradeCN import PoeTradeCN


def query_goods_data(cfg, trade_config):
    poe_trade = PoeTradeCN(cfg['league'], **cfg)

    index = 0
    for config in trade_config:
        index += 1
        print('')
        print('===================================================')
        print(f'=  开始查询【{config["名称"]}】（{index}/{len(trade_config)}）')
        print('===================================================')
        if not config['启用']:
            print('条件未启用，跳过')
            print('')
            continue
        filter_json = read_trade_config_json(poe_trade, cfg, config)
        auto_mode = config['模式']
        filter_json['name'] = config['名称']

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
                poe_trade.query_data(filter_json)
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
                poe_trade.query_data(filter_json)
        else:
            poe_trade.query_data(filter_json)

    return poe_trade.get_result()


def read_trade_config_json(poe_trade, cfg, trade_config):
    config_json_path = os.path.join(cfg['cache_path'], f'{trade_config["代码"]}.json')
    config = None
    if os.path.exists(config_json_path) and os.path.getsize(config_json_path) > 0:
        try:
            config = load_json(config_json_path)
        except json.decoder.JSONDecodeError:
            pass
    if config is None:
        config = poe_trade.query_config_from_code(trade_config['代码'])
        save_json(config, config_json_path)
    return config

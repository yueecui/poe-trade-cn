from util.danteng_excel import read_all_sheets_from_xlsx


class TradeConfig:
    def __init__(self, filter_file_path):
        self._config = None

        self.read_trade_config(filter_file_path)

    def read_trade_config(self, filter_file_path):
        file_content = read_all_sheets_from_xlsx(filter_file_path)
        query_setting = file_content.get('抓取设置') or file_content.get('Sheet1') or None
        header_setting = file_content.get('提取设置') or file_content.get('Sheet2') or None

        if query_setting is None:
            print('抓取设置读取出错！请保证抓取设置配置于《抓取设置》工作簿中！')
            return
        if header_setting is None:
            print('提取设置读取出错！请保证抓取设置配置于《提取设置》工作簿中！')
            return

        # 修正数据
        for name, group in query_setting['data'].items():
            for config in group:
                config['名称'] = name
                config['模式'] = config.get('模式') or 0
                if type(config['模式']) != int or config['模式'] > 2:
                    config['模式'] = 0
                flag = config.get('启用')
                if flag and type(flag) == str:
                    flag = flag.lower() in ['1', '是', 'yes', 'true']
                config['启用'] = bool(flag)

        trade_config = {
            'query': query_setting['data'],
            'header': header_setting['data']
        }

        self._config = trade_config

    def is_ready(self):
        return not (self._config is None)

    def __iter__(self):
        for _, group in self._config['query'].items():
            for config in group:
                yield config

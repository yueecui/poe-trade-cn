
def load_config():
    error_check_list = {
        'GENERAL': [
            {'n': 'league', 't': 'exists'},
            {'n': 'save_cache', 't': 'check_value', 'd': '0'},
            {'n': 'load_cache', 't': 'check_value', 'd': '0'},
            {'n': 'sleep_time', 't': 'check_value', 'd': '10'},
            {'n': 'file_type', 't': 'check_value', 'd': 'xlsx'},
        ],
        'GNILHPROM': [
            {'n': 'split_mods', 't': 'check_value', 'd': '0'},
        ]
    }

    # 读取配置文件
    return config_loader(CONFIG_PATH, error_check_list)
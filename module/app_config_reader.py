from config import CONFIG_PATH
import configparser


def open_cfg():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(CONFIG_PATH, encoding='GBK')
    except UnicodeDecodeError:
        cfg.read(CONFIG_PATH, encoding='UTF-8')

    return cfg


def read_app_config():
    cfg = open_cfg()

    result_config = {
        'league': cfg.get('GENERAL', 'league', fallback=''),
        'POESESSID': cfg.get('GENERAL', 'POESESSID', fallback=''),
        'file_type': cfg.get('GENERAL', 'file_type', fallback='xlsx'),
        'cache_time': cfg.getint('GENERAL', 'cache_minute', fallback=10),
        'split_mods': cfg.getboolean('GENERAL', 'split_mods', fallback=False),

        'filter_path': cfg.get('PATH', 'FILTER', fallback='filter'),
        'cache_path': cfg.get('PATH', 'CACHE', fallback='cache'),

        'sleep_time': cfg.getint('PARAMS', 'sleep_time', fallback=3),
        'retry_time': cfg.getint('PARAMS', 'retry_time', fallback=5),
        'query_number_per_page': cfg.getint('PARAMS', 'query_number_per_page', fallback=10),
    }

    # 换算成毫秒
    result_config['cache_time'] = result_config['cache_time'] * 60

    if result_config['file_type'] != 'csv':
        result_config['file_type'] = 'xlsx'

    return result_config

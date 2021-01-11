import configparser

CONFIG_PATH = r'config.ini'


def open_cfg():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(CONFIG_PATH, encoding='GBK')
    except UnicodeDecodeError:
        cfg.read(CONFIG_PATH, encoding='UTF-8')

    return cfg


def load_config():
    cfg = open_cfg()

    result_config = {
        'league': cfg.get('GENERAL', 'league', fallback=''),
        'file_type': cfg.get('GENERAL', 'file_type', fallback='xlsx'),
        'save_cache': cfg.getboolean('GENERAL', 'save_cache', fallback=True),
        'load_cache': cfg.getboolean('GENERAL', 'load_cache', fallback=False),
        'split_mods': cfg.getboolean('GENERAL', 'split_mods', fallback=False),

        'sleep_time': cfg.getint('PARAMS', 'sleep_time', fallback=3),
        'retry_time': cfg.getint('PARAMS', 'retry_time', fallback=5),
        'query_number_per_page': cfg.getint('PARAMS', 'query_number_per_page', fallback=10),
    }

    if result_config['file_type'] != 'csv':
        result_config['file_type'] = 'xlsx'

    return result_config

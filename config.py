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
        'sleep_time': cfg.getint('GENERAL', 'sleep_time', fallback=10),
        'file_type': cfg.get('GENERAL', 'file_type', fallback='xlsx'),
        'save_cache': cfg.getboolean('GENERAL', 'save_cache', fallback=True),
        'load_cache': cfg.getboolean('GENERAL', 'load_cache', fallback=False),
        'split_mods': cfg.getboolean('GENERAL', 'split_mods', fallback=False),
    }

    if result_config['file_type'] != 'csv':
        result_config['file_type'] = 'xlsx'

    return result_config

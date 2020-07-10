# encoding=utf-8

import sys
from config import load_config


def run():
    config = load_config()
    filter_name_list = sys.argv[1:]


if __name__ == '__main__':
    run()

import os
import pickle
import json
# import msgpack
import sys
from collections import OrderedDict
from time import strftime, localtime


# 带时间的log
def log(string, error_string=''):
    _str = '%s %s' % (strftime("[%H:%M:%S]", localtime()), string)
    try:
        print('%s %s' % (strftime("[%H:%M:%S]", localtime()), string))
    except:
        print('%s %s' % (strftime("[%H:%M:%S]", localtime())
                         , error_string if error_string == '' else '字符串中有无法显示的字符。'))
    return _str


# dump数据到文件
def save_obj(obj, path):
    check_folder(path, mode=1)
    with open(path, 'wb') as f:
        pickle.dump(obj, f)
    return True


# 从文件读取dump出来的数据
def load_obj(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        return None


# 转json
def save_json(obj, path, indent=4):
    check_folder(path, mode=1)
    with open(path, 'w', encoding='UTF-8') as f:
        if indent > 0:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'), indent=indent)
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    return True


# 从文件读取dump出来的数据
def load_json(path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        file_text, result = read_file(path)
        if result:
            version_info = sys.version_info
            if version_info[0] == 3 and version_info[1] >= 7:
                return json.loads(file_text)
            else:
                return json.loads(file_text, object_pairs_hook=OrderedDict)
        else:
            return None
    else:
        return None


# # 转msgpack
# def save_msgpack(obj, path):
#     check_folder(path, mode=1)
#     with open(path, 'wb') as f:
#         msgpack.pack(obj, f)
#     return True
#
#
# # 从文件读取msgpack出来的数据
# def load_msgpack(path):
#     if os.path.exists(path) and os.path.getsize(path) > 0:
#         with open(path, 'rb') as f:
#             version_info = sys.version_info
#             if version_info[0] == 3 and version_info[1] >= 7:
#                 return msgpack.unpack(f, parse=False)
#             else:
#                 return msgpack.unpack(f, parse=False, object_pairs_hook=OrderedDict)
#     else:
#         return None


# 检查所有层级目录是否存在，不存在则创建
# mode:
# 0:会将最右边的那层视为目录
# 1:最右边的那层被视为一个文件名
def check_folder(file_path, mode=0):
    if mode == 1:
        file_path = os.path.split(file_path)[0]

    if not os.path.exists(file_path):
        try:
            os.makedirs(file_path)
        except:
            pass

    # file_path = file_path.replace('\\', '/')
    #
    # path_split = file_path.split('/')
    # path = ''
    # if len(path_split) > mode:
    #     for i in range(len(path_split) - mode):
    #         path = os.path.join(path, path_split[i])
    #         if path == '':
    #             continue
    #
    #         if not os.path.exists(path):
    #             os.mkdir(path)


def get_root(file_path=None):
    if file_path is None:
        file_path = '..'
    me = os.path.abspath(file_path)
    drive, path = os.path.splitdrive(me)
    if not drive:
        return os.path.split(path)[0]
    else:
        return drive


# 自动识别编码读取
# 说明：UTF兼容ISO8859-1和ASCII，GB18030兼容GBK，GBK兼容GB2312，GB2312兼容ASCII
CODES = ['UTF-8', 'GB18030', 'UTF-16', 'BIG5']
# UTF-8 BOM前缀字节
UTF_8_BOM = b'\xef\xbb\xbf'


def read_file(file_path):
    result = False
    file_text = ''
    coding = ''
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'rb') as f:
            b = f.read()
            # 遍历编码类型
            for code in CODES:
                try:
                    b.decode(encoding=code)
                    if code == 'UTF-8' and b.startswith(UTF_8_BOM):
                        coding = 'UTF-8-SIG'
                    else:
                        coding = code
                    break
                except Exception:
                    continue
        if coding != '':
            with open(file_path, 'r', encoding=coding) as f:
                file_text = f.read()
                result = True
    return file_text, result


def encode_to_7bit(value):
    """
    Encode unsigned int to 7-bit str data
    """
    data = []
    number = abs(value)
    while number >= 0x80:
        data.append((number | 0x80) & 0xff)
        number >>= 7
    data.append(number & 0xff)
    return ''.join(chr(char) for char in data)


def decode_from_7bit(data):
    """
    Decode 7-bit encoded int from str data
    """
    result = 0
    for index, char in enumerate(data):
        byte_value = ord(char)
        result |= (byte_value & 0x7f) << (7 * index)
        if byte_value & 0x80 == 0:
            break
    return result


def read_7bit_encoded_int(file_handle, max_length=-1):
    """
    读取文件流中的下一个7bit数字
    :param file_handle: 文件句柄
    :return: 数字
    """
    b = ord(file_handle.read(1))
    length = 0
    num = 0
    count = 0
    while True:
        num |= b & 0x7f << length
        length += 7
        count += 1
        if b & 0x80 == 0:
            break
        if count == max_length > 0:
            raise Exception('d刦7bit时，超出最大位数')
    return num


# 将目标结构体变为一个结构描述
def get_struct(obj):
    obj_type = type(obj)
    if obj_type not in [dict, OrderedDict]:
        return get_type_str(obj_type)
    return get_struct_one_tier(obj)


# 获得目标一层的结构描述
def get_struct_one_tier(obj):
    temp_struct = new_ordered_dict()
    for k, v in obj.items():
        if type(v) in [dict, OrderedDict]:
            temp_struct[k] = get_struct_one_tier(v)
        else:
            temp_struct[k] = get_type_str(type(v))
    return temp_struct


# 去掉 <class ' '>
def get_type_str(obj_type):
    return str(obj_type)[8:-2]


def update_struct(base_struct, plus_struct):
    for k, v in plus_struct.items():
        if k not in base_struct:
            base_struct[k] = v
        elif type(v) in [dict, OrderedDict]:
            base_struct[k] = update_struct(base_struct[k], v)

    return base_struct


# 保存成csv
def save_to_csv(datas, headers, filename):
    import unicodecsv
    with open(filename, 'wb') as f:
        writer = unicodecsv.writer(f)
        writer.writerow(headers)
        if type(datas) == list:
            for data in datas:
                line = []
                for header in headers:
                    line.append(data[header] if header in data else '')
                writer.writerow(line)
        elif type(datas) in [dict, OrderedDict]:
            for key in datas:
                data = datas[key]
                line = []
                for header in headers:
                    line.append(data[header] if header in data else '')
                writer.writerow(line)

    with open(filename, 'r', encoding='UTF-8') as f:
        temp_file_content = f.read()
    with open(filename, 'w', encoding='utf_8_sig') as f:
        f.write(temp_file_content)


# 根据版本获得一个有序字典
def new_ordered_dict():
    version_info = sys.version_info
    if version_info[0] == 3 and version_info[1] >= 7:
        return {}
    else:
        return OrderedDict()

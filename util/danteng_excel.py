import os
import xlrd
from util.danteng_lib import log, new_ordered_dict


# 获取一个工作表的数据（旧版，为了兼容以前写的内容而保留）
def read_sheet_from_xlsx(xls_path, sheet_name='', sheet_index=-1, mode=list()):
    if type(mode) == str:
        mode = [mode]

    result_data = new_ordered_dict()
    if not os.path.exists(xls_path):
        log('[ %s ] 文件不存在！' % xls_path)
        return False

    # 打开工作薄
    try:
        data_wb = xlrd.open_workbook(xls_path)
    except xlrd.biffh.XLRDError as e:
        log('[ %s ] 文件打开失败！错误：' + str(e) % xls_path)
        return False

    # 打开工作表
    try:
        if sheet_index > -1:
            data_ws = data_wb.sheet_by_index(sheet_index)
        elif sheet_name != '':
            data_ws = data_wb.sheet_by_name(sheet_name)
        else:
            data_ws = data_wb.sheet_by_index(0)
        sheet_name = data_ws.name
    except xlrd.biffh.XLRDError as e:
        print(e)
        return False

    # 读取数据
    try:
        result_data[sheet_name] = _read_sheet_data(data_ws, mode)
    except Exception as e:
        log('读取EXCEL文件发生错误，请检查工作薄中的格式是否符合规范。（%s）' % e)

    return result_data


# 获取一个工作表的数据（新版）
def read_one_sheet_from_xlsx(xls_path, sheet_name='', sheet_index=-1, mode=list()):
    if type(mode) == str:
        mode = [mode]

    if not os.path.exists(xls_path):
        log('[ %s ] 文件不存在！' % xls_path)
        return False

    # 打开工作薄
    try:
        data_wb = xlrd.open_workbook(xls_path)
    except xlrd.biffh.XLRDError as e:
        log('[ %s ] 文件打开失败！错误：' + str(e) % xls_path)
        return False

    # 打开工作表
    try:
        if sheet_index > -1:
            data_ws = data_wb.sheet_by_index(sheet_index)
        elif sheet_name != '':
            data_ws = data_wb.sheet_by_name(sheet_name)
        else:
            data_ws = data_wb.sheet_by_index(0)
    except xlrd.biffh.XLRDError as e:
        print(e)
        return False

    # 读取数据
    try:
        result_data = _read_sheet_data(data_ws, mode)
        return result_data
    except Exception as e:
        raise Exception('读取EXCEL文件发生错误，请检查工作薄中的格式是否符合规范。（%s）' % e)


# 获取全部工作表的数据
def read_all_sheets_from_xlsx(xls_path, mode=list()):
    if type(mode) == str:
        mode = [mode]

    result_data = new_ordered_dict()
    if not os.path.exists(xls_path):
        log('[ %s ] 文件不存在！' % xls_path)
        return False

    # 打开工作薄
    try:
        data_wb = xlrd.open_workbook(xls_path)
    except xlrd.biffh.XLRDError as e:
        log('[ %s ] 文件打开失败！错误：' + str(e) % xls_path)
        return False

    # 打开工作表
    sheet_names = data_wb.sheet_names()

    # 读取数据
    try:
        for sheet_name in sheet_names:
            data_ws = data_wb.sheet_by_name(sheet_name)
            result_data[sheet_name] = _read_sheet_data(data_ws, mode)
    except Exception as e:
        log('读取EXCEL文件发生错误，请检查工作薄中的格式是否符合规范。（%s）' % e)

    return result_data


# 读取一个工作表的数据（内部调用）
# mode类型
# noheader：没有表头，第一行也是数据
# onlyheader：只要表头
# simple：每个key只对应一行数据（当第一列key出现重复时，只有最后一条有效）
# dict：返回有序字典，key为第一列，内容为其他数据，所以也会默认simple
def _read_sheet_data(data_ws, mode=list()):
    temp_header = []  # 读取记录用的header
    result_header = []  # 最终输出时用的header列表，会去掉符号和跳过的内容
    sheet_data = new_ordered_dict()  # 数据存储用
    a1_value = ''

    # 获取header
    if 'noheader' in mode:
        # 无header，用列号作为header
        for i in range(0, data_ws.ncols):
            temp_header.append(i)
            result_header.append(i)
    else:
        # 正常的有header情况
        for i in range(0, data_ws.ncols):
            header = data_ws.cell_value(0, i)
            header_type = data_ws.cell_type(0, i)

            if header_type == xlrd.XL_CELL_NUMBER:
                if header % 1 == 0.0:
                    header = int(header)
            temp_header.append(header)

            if i == 0:
                a1_value = str(header)
            elif header != '' and str(header)[0] != '!' and i > 0:
                if str(header)[0] == '#':
                    result_header.append(header[1:])
                else:
                    result_header.append(header)

    # 如果只获取头
    if 'onlyheader' in mode and 'noheader' not in mode:
        return {'data': sheet_data, 'header': result_header, 'a1': a1_value}

    # 获取数据
    if 'noheader' in mode:
        start_row = 0
    else:
        start_row = 1
    for i in range(start_row, data_ws.nrows):
        # 按第一列生成索引（条目标题）
        data_title = data_ws.cell_value(i, 0)
        data_title_type = data_ws.cell_type(i, 0)
        if data_title == '':
            continue
        if str(data_title)[0] == '!':
            continue
        data_title = _sheet_value_check(data_title, data_title_type, data_title)

        # 初始化
        if 'simple' not in mode and 'dict' not in mode:
            if data_title not in sheet_data:
                sheet_data[data_title] = []

        try:
            # 读取每一行数据
            row_data = new_ordered_dict()
            for j in range(1, len(temp_header)):
                header = str(temp_header[j])
                if len(header) == 0:
                    continue
                if header[0] == '!':
                    continue
                if header[0] == '#':
                    header_output = header[1:]
                else:
                    header_output = temp_header[j]
                row_data[header_output] = _sheet_value_check(data_ws.cell_value(i, j), data_ws.cell_type(i, j), header)
        except:
            print('Excel数据读取失败，请检查')

        if 'simple' in mode or 'dict' in mode:
            sheet_data[data_title] = row_data
        else:
            sheet_data[data_title].append(row_data)

    if 'dict' in mode:
        result_dict = new_ordered_dict()

        for data_key, data_info in sheet_data.items():
            temp_dict_item = new_ordered_dict()
            temp_dict_item[a1_value] = data_key
            temp_dict_item.update(data_info)
            result_dict[data_key] = temp_dict_item

        return result_dict
    else:
        return {'data': sheet_data, 'header': result_header, 'a1': a1_value}


# 检查单元格值是否合法
# 整数会转成int
# 日期会转成英文或是中文日期

def _sheet_value_check(cell_value, cell_type, header=''):
    if cell_type == xlrd.XL_CELL_NUMBER:
        if cell_value % 1 == 0.0:
            cell_value = int(cell_value)
    elif cell_type == xlrd.XL_CELL_BOOLEAN:
        if cell_value == 1:
            cell_value = True
        else:
            cell_value = False
    elif cell_type == xlrd.XL_CELL_DATE:
        if cell_value < 61:
            date_tuple = xlrd.xldate_as_tuple(cell_value, 1)
            date_year = date_tuple[0] - 4
            date_day = date_tuple[2] - 1
            if date_day == 0:
                date_day = 31
                date_month = 1
            else:
                date_month = date_tuple[1]
            if header != '':
                if header[0] == '#':
                    cell_value = '%d月%d日' % (date_month, date_day)
                else:
                    cell_value = '%4d-%02d-%02d' % (date_year, date_month, date_day)
        else:
            date_tuple = xlrd.xldate_as_tuple(cell_value, 0)
            if header != '':
                if header[0] == '#':
                    cell_value = '%d月%d日' % (date_tuple[1], date_tuple[2])
                else:
                    cell_value = '%4d-%02d-%02d' % (date_tuple[0], date_tuple[1], date_tuple[2])

    return cell_value


# 用于读取补充数据
def read_additional_data_from_excel(excel_path, sheet_list=list(), use_list_type_list=list()):
    excel_data = read_all_sheets_from_xlsx(excel_path)

    if len(sheet_list) == 0:
        sheet_list = list(excel_data.keys())

    result_data = new_ordered_dict()

    # 普通数据
    for sheet_name in sheet_list:
        result_data[sheet_name] = new_ordered_dict()
        for package_id, package_list_info in excel_data[sheet_name]['data'].items():
            if sheet_name in use_list_type_list:
                result_data[sheet_name][package_id] = []
            for package_info in package_list_info:
                for package_info_key, package_info_value in package_info.items():
                    try:
                        if type(package_info_value) == str:
                            package_info[package_info_key] = eval(package_info_value)
                    except SyntaxError:
                        package_info[package_info_key] = package_info_value
                    except NameError:
                        continue
                if sheet_name in use_list_type_list:
                    result_data[sheet_name][package_id].append(package_info)
                else:
                    result_data[sheet_name][package_id] = package_info.copy()

    return result_data

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Description: 下载PeMS数据，一次下载一周的数据，将下载的周数据进行合并

import time
import os
import numpy as np
import pandas as pd
import requests
import csv
import argparse
import math


def get_vds_list(filename):
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        vds_list = [int(row[0]) for row in reader]
    return vds_list


def time_2_timestamp(input, lags=True):
    """默认True: 时间转化为时间戳, 包含时差计算"""
    if lags:
        timeArray = time.strptime(input, "%Y-%m-%d %H:%M")
        # 转换成时间戳
        return int(time.mktime(timeArray) + 8 * 60 * 60)  # 时差计算
    else:
        time_local = time.localtime(input - 8 * 60 * 60)
        return time.strftime("%Y-%m-%d %H:%M", time_local)


def get_session():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
        'Referer': 'https://pems.dot.ca.gov/',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {"redirect": "", "username": "用户名",
            "password": "密码", "login": "Login"}
    requests.packages.urllib3.disable_warnings()
    session = requests.session()
    session.keep_alive = False
    url_login = 'https://pems.dot.ca.gov'
    session.post(url_login, headers=headers, data=data, verify=False)
    return session


def get_url(vds, begin):
    str_begin = time_2_timestamp(begin, False)
    s_begin = str_begin[5:7] + '%2F' + str_begin[8:10] + '%2F' + str_begin[:4] + '+00%3A00'
    end = begin + 60 * 60 * 24 * 7 - 60
    str_end = time_2_timestamp(end, False)
    s_end = str_end[5:7] + '%2F' + str_end[8:10] + '%2F' + str_end[:4] + '+23%3A59'
    url = 'https://pems.dot.ca.gov/?report_form=1&dnode=VDS&content=loops&export=xls&station_id=' \
          + str(vds) + '&s_time_id=' + str(begin) + '&s_time_id_f=' + str(s_begin) + '&e_time_id=' + str(end) \
          + '&e_time_id_f=' + str(s_end) + '&tod=all&tod_from=0&tod_to=0&dow_0=on&dow_1=on&dow_2=on&dow_3=on' \
          '&dow_4=on&dow_5=on&dow_6=on&holidays=on&q=speed&q2=flow&gn=5min&agg=on'
    # 第一维：speed 第二维：flow  5 min
    print('获取url: vds[%s] %s --- %s' % (str(vds), str_begin, str_end))
    return url


def download(session, save_path, vds, start_stamp, end_stamp):
    i = 0
    for begin in range(start_stamp, end_stamp, 60 * 60 * 24 * 7):
        i += 1
        file_path = save_path + '\\' + str(i) + '.xlsx'
        if os.path.exists(file_path) and os.path.getsize(file_path) > 50000:
            print(str(i) + '.xlsx' + '已存在')
        else:
            url = get_url(vds, begin)
            #下载数据
            response = session.get(url, verify=False)
            with open(file_path, 'wb') as f:
                f.write(response.content)
                print(str(i) + '.xlsx' + '下载成功')
        if i % 8 == 0:
            time.sleep(5) #每下载8个休息五秒


def combine_download_data(vds, path, num):
    df = pd.read_excel(path + '\\1.xlsx', index_col=None)
    dfs = df.values
    headers = df.columns
    for i in range(2, num + 1):
        df = pd.read_excel(path + '\\' + str(i) + '.xlsx', index_col=None).values
        dfs = np.row_stack((dfs, df))
    dfs = pd.DataFrame(data=dfs, columns=headers)
    #pd.DataFrame(dfs).to_csv(path + '\\' + str(vds) + '_combine.csv', index=None, header=headers)
    print(str(vds)+' 合并文件保存成功')
    return dfs

def gen_time_df(start_time, end_time):
    time_indexs = pd.date_range(start=start_time, end=end_time, freq='5min')
    time_df = pd.DataFrame(data=time_indexs, columns=['5 Minutes'])
    return time_df

def handle_missing_data(vds, vds_df, time_df, path, fill_value):
    #vds_df['5 Minutes'] = pd.to_datetime(vds_df['5 Minutes'])
    df = pd.merge(time_df, vds_df, on='5 Minutes', how='left', sort=True)
    pd.DataFrame(df).to_csv(path + '\\' + str(vds) + '_combine_nan.csv', index=None)
    if fill_value.isdigit():
        df = df.fillna(float(fill_value))
    else:
        #以线性插值进行填充
        df = df.interpolate()
    #pd.DataFrame(df).to_csv(path + '\\' + str(vds) + '_combine_'+fill_value+'.csv', index=None)
    print(str(vds) + ' 缺失值补全')
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #下载数据的时间跨度
    parser.add_argument('-s', '--start_time', default='2017-01-01')
    parser.add_argument('-e', '--end_time', default='2017-06-30')
    parser.add_argument('-f', '--fill_value', default='0')
    args = parser.parse_args()
    path = r'download'  # 文件保存路径
    #vds_list = [400001, 400017]
    vds_list = get_vds_list('graph_sensor_locations_bay.csv') # 需要下载的VDS列表
    start_time, end_time = args.start_time+' 00:00', args.end_time+' 23:59'  # 数据下载开始时间和结束时间，每次下载一周，无数据则下载为空文件
    time_df = gen_time_df(start_time, end_time)
    start_stamp, end_stamp = time_2_timestamp(start_time), time_2_timestamp(end_time) #时间转化为时间戳
    num = math.ceil((end_stamp-start_stamp) / (60 * 60 * 24 * 7))
    save_path = path + '\\' + start_time[2:10] + '_' + end_time[2:10]
    session = get_session()
    speed_df = pd.DataFrame(index=time_df.values[:, 0])
    flow_df = pd.DataFrame(index=time_df.values[:, 0])
    for vds in vds_list:
        save_paths = save_path + '\\' + str(vds)  # 创建文件保存路径
        if not os.path.exists(save_paths):
            os.makedirs(save_paths)
        print('开始下载：%s   %s---%s' % (str(vds), start_time, end_time))
        download(session, save_paths, vds, start_stamp, end_stamp)  # 下载文件
        vds_df = combine_download_data(vds, save_paths, num)  # 将单个VDS下载文件进行合
        df = handle_missing_data(vds, vds_df, time_df, save_paths, args.fill_value)
        speed_df[vds] = df.values[:, 1]
        flow_df[vds] = df.values[:, 2]
    pd.DataFrame(speed_df).to_csv(path+'\\'+'pems_bay_speed_'+args.fill_value+'.csv')
    pd.DataFrame(flow_df).to_csv(path+'\\'+'pems_bay_flow_'+args.fill_value+'.csv')
    store = pd.HDFStore(path+'\\'+'pems-bay_'+args.fill_value+'.h5')
    store['speed'] = speed_df
    store['flow'] = flow_df
    store.close()



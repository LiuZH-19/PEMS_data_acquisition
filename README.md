# 代码说明

该代码用于从[PEMS](https://pems.dot.ca.gov/)上自动下载VDS的数据集（需要FQ，挂全局代理）。

在运行此代码前，需在[PEMS](https://pems.dot.ca.gov/)网站上注册账号，并更改代码`get_session()`函数中`data`中登录PEMS系统的用户名和密码：

```
  data = {"redirect": "", "username": "用户名",
            "password": "密码", "login": "Login"}
```

同时可自行更改：

- 文件保存地址： `path`。
- 需要下载的VDS列表：`vds_list`。代码中使用的VDS列表为DCRNN论文中用到的VDS列表。

代码运行如下：

```
python crawl_data.py -s 2017-01-01  -e  2017-02-02  -f 0
```

命令行参数说明：

```python
parser.add_argument('-s', '--start_time', default='2017-01-01')
parser.add_argument('-e', '--end_time', default='2017-06-30')
parser.add_argument('-f', '--fill_value', default='0')
```

`-s`: 下载数据的开始时间。

`-e`: 下载数据的结束时间。时间跨度默认为DCRNN所用PEMS-BAY的时间跨度。

`-f`: 由于下载的数据中有时会出现缺失的时刻，故对缺失值进行填充。若`args.fill_value`为数字，则以该数字进行填充；否则以线性插值进行填充。



# 生成文件

pems-bay-*为原始数据

PEMS-BAY-*文件夹：以DCRNN方式划分的训练集、测试集、验证集

## pems-bay-*.h5

读取该文件

```
store = pd.HDFStore('pems-bay.h5')
speed_df = store['speed']
flow_df = store['flow']
```

其中speed_df 和 flow_df 的格式相同，flow_df的内容如下所示：

|               | 400001 | 400017 | 400030 | 其他sensor |
| ------------- | ------ | ------ | ------ | ---------- |
| 2017/1/1 0:00 | 84     | 102    | 79     | …          |
| 2017/1/1 0:05 | 81     | 97     | 79     | …          |
| 2017/1/1 0:10 | 93     | 92     | 76     | …          |
| 2017/1/1 0:15 | 83     | 97     | 76     | …          |
| 2017/1/1 0:20 | 84     | 87     | 65     | …          |
|               | …      | …      | …      | …          |

**注意**：

- pems-bay-zero.h5文件中的缺失值以0进行填充
- pems-bay-interpolate.h5文件中的缺失值以线性插值的方式进行填充

## 训练集、验证集、测试集的生成

运行代码：(该代码根据DCRNN的代码进行修改)

```
mkdir -p data/PEMS-BAY
python generate_training_data.py --output_dir=data/PEMS-BAY --traffic_df_filename=download/pems-bay_0.h5
```

eg:按DCRNN的时间跨度下载的数据集划分如下：

- train x:  (36465, 12, 325, 10) y: (36465, 12, 325, 10)

- val x:  (5209, 12, 325, 10) y: (5209, 12, 325, 10)

- test x:  (10419, 12, 325, 10) y: (10419, 12, 325, 10)

  (num_samples, input_length, num_nodes, input_dim)

  共有10维，分别为speed、flow、time_in_day、day_in_week（7维）。可设置如下代码中的值为True/False，选择是否加入该维度。

  ```python
  x, y = generate_graph_seq2seq_io_data(
          speed_df,
          flow_df,
          x_offsets=x_offsets,
          y_offsets=y_offsets,
          add_speed=True,
          add_flow=True,
          add_time_in_day=True,
          add_day_in_week=True,
      )
  ```

  

  比如 `x_test[0, :, 0, :]` 如下：

  ```txt
  [[ 70.6        239.           0.74305556   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 71.7        216.           0.74652778   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 70.7        240.           0.75         0.           0.
      0.           1.           0.           0.           0.        ]
   [ 71.1        185.           0.75347222   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 70.4        221.           0.75694444   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 70.9        206.           0.76041667   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 71.5        219.           0.76388889   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 72.4        220.           0.76736111   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 71.6        181.           0.77083333   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 71.3        175.           0.77430556   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 73.1        224.           0.77777778   0.           0.
      0.           1.           0.           0.           0.        ]
   [ 73.1        215.           0.78125      0.           0.
      0.           1.           0.           0.           0.        ]]
  ```

  



  
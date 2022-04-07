import dash
from dash import dcc
from dash import Dash, html, dash_table
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from pymongo import MongoClient
from warnings import simplefilter
import numpy as np
import pandas as pd
from plotly.colors import n_colors

import plotly.express as px
import datetime
from datetime import date
from plotly.subplots import make_subplots

# 列印用
desired_width = 320
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 20)

# 取消 future warning
simplefilter(action='ignore', category=FutureWarning)

# 引入密碼
path = "mongodb_password"
with open(path) as f:
    word = f.readline().split(',')
    account = word[0]
    password = word[1]


# Build Function
def read_AccountSummary(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': "AccountSummary"}]})
    AccountSummary = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        AccountSummary = pd.concat([AccountSummary, data], axis=0, ignore_index=True)
    return AccountSummary


def read_Portfolio(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': "Portfolio"}]})
    Portfolio = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)
    return Portfolio


def ib_data_process(download_date):
    AccountSummary = read_AccountSummary(download_date)
    AccountSummary = AccountSummary.pivot(index="Account", columns="tag",
                                          values='value')

    Portfolio = read_Portfolio(download_date)

    # 帳戶資料新增持倉
    for account in AccountSummary.index:
        secType_filt = {"StockValue": (Portfolio["Account"] == account) & (Portfolio["secType"] == "STK"),
                        "BondValue": (Portfolio["Account"] == account) & (Portfolio["secType"] == "BOND"),
                        "OPTValue": (Portfolio["Account"] == account) & (Portfolio["secType"] == "OPT"),
                        "FUTValue": (Portfolio["Account"] == account) & (Portfolio["secType"] == "FUT"),
                        }
        for filt in secType_filt.keys():
            AccountSummary.loc[account, filt] = Portfolio[secType_filt.get(filt)]['marketValue'].sum()

    # 投資組合資產分類
    Portfolio_STK = Portfolio[Portfolio["secType"] == "STK"][[
        'Account', 'symbol', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_BOND = Portfolio[Portfolio["secType"] == "BOND"][[
        'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_OPT = Portfolio[Portfolio["secType"] == "OPT"][[
        'Account', 'symbol', 'right', 'strike', 'lastTradeDate', 'position', 'marketPrice', 'marketValue',
        'averageCost', 'unrealizedPNL']]
    Portfolio_FUT = Portfolio[Portfolio["secType"] == "FUT"][[
        'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]

    data_dict = {"AccountSummary": AccountSummary,
                 "Portfolio_STK": Portfolio_STK,
                 "Portfolio_BOND": Portfolio_BOND,
                 "Portfolio_OPT": Portfolio_OPT,
                 "Portfolio_FUT": Portfolio_FUT}
    return data_dict


if __name__ == "__main__":
    # mongodb connection
    CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
    client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
    db = client.getdata
    collection = db.ib
    db_date = collection.distinct("date")
    download_date = db_date[-10:]
    for date in download_date:
        data = {date: ib_data_process(date)}

    print(data['data'])

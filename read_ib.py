import pprint
import time
import pandas as pd
import numpy as np
from finvizfinance.quote import finvizfinance
from finvizfinance.insider import Insider
from finvizfinance.news import News
from finvizfinance.screener.overview import Overview
from pymongo import MongoClient
from warnings import simplefilter

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

# mongodb connection
CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)

db = client.getdata
collection = db.ib

download_date = '2022/04/06'

account_data = collection.find_one({'$and': [{'date': download_date}, {'tag': "AccountSummary"}]})
AccountSummary = pd.DataFrame(account_data['data'])
AccountSummary = AccountSummary.dropna()
print(AccountSummary)

portfolio_data = collection.find_one({'$and': [{'date': download_date}, {'tag': "Portfolio"}]})
Portfolio = pd.DataFrame(portfolio_data['data'])
Portfolio = Portfolio.dropna()
print(Portfolio)

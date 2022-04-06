from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import *
from ibapi.contract import *
import os
import pandas as pd
import pprint
import datetime
import time
import numpy as np
from pymongo import MongoClient
from warnings import simplefilter
import json
import sys

# 列印用
desired_width = 320
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 10)

# 取消 future warning
simplefilter(action='ignore', category=FutureWarning)


# 管理帳號列表物件
class AccountList(EClient, EWrapper):
    accountslist = []

    def __init__(self):
        EClient.__init__(self, self)

    def managedAccounts(self, accountsList: str):
        self.reqManagedAccts()
        super().managedAccounts(accountsList)
        self.accountslist = accountsList.split(',')
        for i in self.accountslist:
            if '' in self.accountslist:
                self.accountslist.remove('')
        return accountsList

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        print("Error: ", reqId, "", errorCode, "", errorString)


# 下載管理帳號列表
def downloadlist():
    app = AccountList()
    app.connect("127.0.0.1", 7496, 123)
    app.run()
    return app.accountslist


# 帳號概況
class AccountSummary(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.reqId = 9002
        self.group = "All"
        self.tag = "NetLiquidation"
        self.accsum = []

    def nextValidId(self, orderId: int):
        self.reqAccountSummary(self.reqId, self.group, self.tag)

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        self.accsum.append((account, tag, value, currency))

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        print("Error: ", reqId, "", errorCode, "", errorString)

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(self.reqId)
        self.cancelAccountSummary(self.reqId)
        print("AccountSummaryEnd. ReqId:", self.reqId)
        self.disconnect()


# 下載帳號概況
def downloadAccountSummary():
    columns = ['Account', 'tag', 'value', 'currency']
    app = AccountSummary()
    app.connect("127.0.0.1", 7496, 123)
    app.run()
    data = pd.DataFrame(app.accsum, columns=columns)
    accsum = data.set_index('Account').sort_index()
    return accsum


# 投資組合
class Portfolio(EClient, EWrapper):

    def __init__(self, accountcode):
        EClient.__init__(self, self)
        self.accountcode = accountcode
        self.portfolio = []
        self.accountslist = []

    def nextValidId(self, orderId: int):
        self.reqAccountUpdates(True, self.accountcode)

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        print("Error: ", reqId, "", errorCode, "", errorString)

    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float,
                        marketValue: float, averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        self.portfolio.append(
            (contract.symbol, contract.conId, contract.secType,
             contract.right, contract.strike,
             contract.lastTradeDateOrContractMonth,
             position, marketPrice,
             marketValue, averageCost, unrealizedPNL, realizedPNL, accountName))

    def accountDownloadEnd(self, accountcode):
        print("AccountDownloadEnd. Account:", accountcode)
        self.disconnect()


# 下載投資組合
def downloadPortfolio(list):
    columns = ['symbol', 'conId', 'secType', 'right', 'strike', 'lastTradeDate', 'position', 'marketPrice',
               'marketValue',
               'averageCost',
               'unrealizedPNL', 'realizedPNL', 'Account']
    data = pd.DataFrame(columns=columns)
    for accountcode in list[1:]:
        app = Portfolio(accountcode)
        app.connect("127.0.0.1", 7496, 123)
        app.run()
        newdata = pd.DataFrame(app.portfolio, columns=columns)
        data = pd.concat([data, newdata])
    print(f'managedAcct : {list}')
    print('download complete')
    ibportfolio = data.set_index('Account').sort_index()
    return ibportfolio


# 模型部位
# class Multiposition(EClient, EWrapper):
#     multiposition = []
#
#     def __init__(self, accountcode='All', modelcode='FTW'):
#         EClient.__init__(self, self)
#         self.reqId = 9002
#         self.accountcode = accountcode
#         self.modelcode = modelcode
#
#     def nextValidId(self, orderId: int):
#         self.reqPositionsMulti(self.reqId, self.accountcode, self.modelcode)
#
#     def positionMulti(self, reqId: int, account: str, modelCode: str,
#                       contract: Contract, pos: float, avgCost: float):
#         self.multiposition.append((account, modelCode, contract.symbol, contract.secType, pos, avgCost))
#
#     def error(self, reqId: TickerId, errorCode: int, errorString: str):
#         print("Error: ", reqId, "", errorCode, "", errorString)
#
#     def positionMultiEnd(self, reqId: int):
#         super().positionMultiEnd(self.reqId)
#         print("positionMultiEnd:", self.reqId)
#         self.disconnect()


# 下載模型部位
# def downloadMultiposition(accountcode, modelcode):
#     columns = ['Account', 'modelcode', 'symbol', 'secType', 'pos', 'avgCost']
#     data = pd.DataFrame(columns=columns)
#     app = Multiposition(accountcode, modelcode)
#     app.connect("127.0.0.1", 7496, 123)
#     app.run()
#     newdata = pd.DataFrame(app.multiposition, columns=columns)
#     data = pd.concat([data, newdata])
#     multiposition = data.set_index('Account').sort_index()
#     return multiposition


def write_ib(AccountSummary, Portfolio):
    start = time.time()
    db = client.getdata
    collection = db.ib
    data_account = json.loads(AccountSummary.to_json())  # 到底為何要這樣處理??
    collection.insert_one(
        {'tag': 'AccountSummary', 'date': datetime.date.today().strftime("%Y/%m/%d"), 'data': data_account})
    data_portfolio = json.loads(Portfolio.to_json())  # 到底為何要這樣處理??
    collection.insert_one(
        {'tag': 'Portfolio', 'date': datetime.date.today().strftime("%Y/%m/%d"), 'data': data_portfolio})
    end = time.time()
    print(f'write_bb total time: {end - start} seconds')


if __name__ == "__main__":
    # 引入密碼
    path = "mongodb_password"
    with open(path) as f:
        word = f.readline().split(',')
        account = word[0]
        password = word[1]

    # mongodb connection
    CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
    client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
    list = downloadlist()[:]
    AccountSummary = downloadAccountSummary()
    Portfolio = downloadPortfolio(list)
    write_ib(AccountSummary, Portfolio)

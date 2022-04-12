import dash
from dash import Dash, html, dash_table, dcc
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from pymongo import MongoClient
from warnings import simplefilter
import numpy as np
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Trim
from plotly.colors import n_colors

import plotly.express as px
import datetime
from datetime import date
from plotly.subplots import make_subplots

# 列印用
desired_width = 320
pd.set_option('display.width', desired_width)
np.set_printoptions(linewidth=desired_width)
pd.set_option('display.max_columns', 10)

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
    AccountSummary["Date"] = download_date
    return AccountSummary


def read_Portfolio(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': "Portfolio"}]})
    Portfolio = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)

    return Portfolio


def Porfolio_list(download_date):
    Portfolio = read_Portfolio(download_date)

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

    Portfolio_list = {'Portfolio_STK': Portfolio_STK,
                      'Portfolio_BOND': Portfolio_BOND,
                      'Portfolio_OPT': Portfolio_OPT,
                      'Portfolio_FUT': Portfolio_FUT}

    return Portfolio_list


def read_all_AccountSummary(download_date_list):
    AccountSummary = pd.DataFrame()
    for download_date in download_date_list:
        AccountSummary = pd.concat([read_AccountSummary(download_date).reset_index(), AccountSummary], axis=0,
                                   ignore_index=True)
    return AccountSummary


# mongodb connection
CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
db = client.getdata
collection = db.ib
db_date = collection.distinct("date")
download_date_list = db_date[-10:]

check_AccountSummary = read_AccountSummary(download_date_list[-1])
check_Portfolio_STK = Porfolio_list(download_date_list[-1])["Portfolio_STK"]
check_Portfolio_BOND = Porfolio_list(download_date_list[-1])["Portfolio_BOND"]
check_Portfolio_OPT = Porfolio_list(download_date_list[-1])["Portfolio_OPT"]
check_Portfolio_FUT = Porfolio_list(download_date_list[-1])["Portfolio_FUT"]

Account_Page_Size = len(check_AccountSummary.index)
Portfolio_STK_Page_Size = len(check_Portfolio_STK.index)
Portfolio_BOND_Page_Size = len(check_Portfolio_BOND.index)
Portfolio_OPT_Page_Size = len(check_Portfolio_OPT.index)
Portfolio_FUT_Page_Size = len(check_Portfolio_FUT.index)

# make app
app = dash.Dash()

app.layout = html.Div([
    html.Div(
        dcc.Dropdown(
            id='account-dropdown',
            options=check_AccountSummary.index,
            value=check_AccountSummary.index,
            multi=True
        )
    ),
    html.Div(id='account-table'),
    html.Div(id='account-graph')
]
)


@app.callback(
    Output('account-table', 'children'),
    Input('account-dropdown', 'value')
)
def update_account_table(value):
    df = check_AccountSummary
    data = df.filter(items=value, axis=0).reset_index()

    columns = [{"name": i, "id": i, "deletable": False, "selectable": True, "type": 'numeric',
                "format": Format(precision=2, scheme=Scheme.fixed)} for i in
               data.columns]
    data = data.to_dict('records')

    return dash_table.DataTable(
        data=data,
        columns=columns,
        editable=False,
        sort_action="native",
        sort_mode="single",
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0)


@app.callback(
    Output('account-graph', "children"),
    Input('account-dropdown', 'value')
)
def update_graphs(value):
    dff = read_all_AccountSummary(download_date_list)
    dff = dff.loc[dff['Account'].isin(value)]
    dfff = pd.DataFrame()
    for date in download_date_list:
        for columns in ["NetLiquidation", "TotalCashValue", "StockValue", "BondValue"]:
            dfff.loc[date, columns] = dff[dff["Date"] == date][columns].astype(float).sum()

    return html.Div(
        [
            dcc.Graph(
                id=column,
                figure={
                    "data": [
                        {
                            "x": download_date_list,
                            "y": dfff[column],
                            "type": "scatter+line",
                            "marker": {"color": "#0074D9"},
                        }
                    ],
                    "layout": {
                        "xaxis": {"automargin": True},
                        "yaxis": {"automargin": True},
                        "height": 300,
                        'width': 1000,
                        "title": column,
                        "margin": {"t": 50, "l": 10, "r": 10},
                    },
                },
            )
            for column in ["NetLiquidation", "TotalCashValue", "StockValue", "BondValue"]
        ]
    )


if __name__ == "__main__":
    app.run_server(debug=True)

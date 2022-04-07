import dash
from dash import dcc
from dash import Dash, html, dash_table
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
    return AccountSummary


def read_Portfolio(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': "Portfolio"}]})
    Portfolio = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)
    return Portfolio


def ib_data_process(download_date):
    AccountSummary = read_AccountSummary(download_date).pivot(index="Account", columns="tag",
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


# mongodb connection
CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
db = client.getdata
collection = db.ib

download_date = '2022/04/06'
data = ib_data_process(download_date)
AccountSummary = data["AccountSummary"].reset_index()
Portfolio_BOND = data["Portfolio_BOND"].reset_index()

# make app
app = dash.Dash()

app.layout = html.Div([
    dash_table.DataTable(
        id='account-datatable-interactivity',
        columns=[
            {"name": i, "id": i, "deletable": False, "selectable": True, "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.fixed)} for i in
            AccountSummary.columns],
        data=AccountSummary.to_dict('records'),
        editable=True,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=50,
    ),
    html.Div(id='account-datatable-interactivity-container'),
    dash_table.DataTable(
        id='portfolio-datatable-interactivity',
        columns=[
            {"name": i, "id": i, "deletable": False, "selectable": True, "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.fixed)} for i in
            Portfolio_BOND.columns],
        data=Portfolio_BOND.to_dict('records'),
        editable=True,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        row_deletable=False,
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current=0,
        page_size=50,
    ),
    html.Div(id='portfolio-datatable-interactivity-container')
])


@app.callback(

    Output('account-datatable-interactivity', 'style_data_conditional'),
    Input('account-datatable-interactivity', 'selected_columns')
)
def update_styles(selected_columns):
    return [{
        'if': {'column_id': i},
        'background_color': '#D2F3FF'
    } for i in selected_columns]


@app.callback(
    Output('account-datatable-interactivity-container', "children"),
    Input('account-datatable-interactivity', "derived_virtual_data"),
    Input('account-datatable-interactivity', "derived_virtual_selected_rows"))
def update_graphs(rows, derived_virtual_selected_rows):
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = AccountSummary if rows is None else pd.DataFrame(rows)

    return [
        dcc.Graph(
            id="Account Position",
            figure={
                "data": [
                    {
                        "values": [dff["TotalCashValue"].astype(float).sum(), dff["StockValue"].sum(),
                                   dff["BondValue"].sum()],
                        "labels": ["TotalCashValue", "StockValue", "BondValue"],
                        "type": "pie",
                        "textinfo": 'percent+label',
                        "textposition": 'outside',
                        "marker": {"colors": ['#CCCCCC', '#38A67C', '#006FA6']},
                        "insidetextfont": {"size": 12},
                    }
                ],
                "layout": {
                    "height": 400,
                    "margin": {"t": 50, "l": 50, "r": 50},
                    "width": 800,
                },
            },
        )
    ]


@app.callback(
    Output('portfolio-datatable-interactivity', 'style_data_conditional'),
    Input('portfolio-datatable-interactivity', 'selected_columns')
)
def update_styles(selected_columns):
    return [{
        'if': {'column_id': i},
        'background_color': '#D2F3FF'
    } for i in selected_columns]


@app.callback(
    Output('portfolio-datatable-interactivity-container', "children"),
    Input('portfolio-datatable-interactivity', "derived_virtual_data"),
    Input('portfolio-datatable-interactivity', "derived_virtual_selected_rows"))
def update_graphs(rows, derived_virtual_selected_rows):
    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = Portfolio_BOND if rows is None else pd.DataFrame(rows)

    colors = ['#7FDBFF' if i in derived_virtual_selected_rows else '#0074D9'
              for i in range(len(dff))]

    return [
        dcc.Graph(
            id=column,
            figure={
                "data": [
                    {
                        "x": dff["Account"],
                        "y": dff[column],
                        "type": "bar",
                        "marker": {"color": colors},
                    }
                ],
                "layout": {
                    "xaxis": {"automargin": True},
                    "yaxis": {
                        "automargin": True,
                        "title": {"text": column}
                    },
                    "height": 250,
                    "margin": {"t": 10, "l": 10, "r": 10},
                },
            },
        )
        # check if column exists - user may have deleted it
        # If `column.deletable=False`, then you don't
        # need to do this check.
        for column in ["marketValue", "unrealizedPNL"]
    ]


if __name__ == "__main__":
    app.run_server(debug=True)

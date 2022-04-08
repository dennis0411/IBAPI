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

# make app
app = dash.Dash()

Account_Page_Size = len(check_AccountSummary.index)
Portfolio_STK_Page_Size = len(check_Portfolio_STK.index)
Portfolio_BOND_Page_Size = len(check_Portfolio_BOND.index)
Portfolio_OPT_Page_Size = len(check_Portfolio_OPT.index)
Portfolio_FUT_Page_Size = len(check_Portfolio_FUT.index)

app.layout = html.Div([
    dash_table.DataTable(
        id='account-datatable-interactivity',
        columns=[
            {"name": i, "id": i, "deletable": False, "selectable": True, "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.fixed)} for i in
            read_all_AccountSummary(download_date_list).columns],
        data=read_all_AccountSummary(download_date_list).to_dict('records'),
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
        page_size=Account_Page_Size,
    ),
    html.Div(id='account-datatable-interactivity-container'),
    dash_table.DataTable(
        id='portfolio-datatable-interactivity',
        columns=[
            {"name": i, "id": i, "deletable": False, "selectable": True, "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.fixed)} for i in
            Porfolio_list(download_date_list[-1])["Portfolio_BOND"].columns],
        data=Porfolio_list(download_date_list[-1])["Portfolio_BOND"].to_dict('records'),
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

    dff = read_all_AccountSummary(download_date_list) if rows is None else pd.DataFrame(rows)

    dfff = pd.DataFrame()
    for date in download_date_list:
        for columns in ["NetLiquidation", "TotalCashValue", "StockValue", "BondValue"]:
            dfff.loc[date, columns] = dff[dff["Date"] == date][columns].astype(float).sum()

    return html.Div(
        [
            dcc.Graph(
                id="NetLiquidation",
                figure={
                    go.Figure(
                        data=[
                            go.Scatter(
                                x=download_date_list,
                                y=dfff["NetLiquidation"],
                                mode="lines",
                                line=dict(color="#B0B0B0",
                                          width=2)
                            )
                        ],
                        layout={
                            "xaxis": {"automargin": True},
                            "yaxis": {"automargin": True},
                            "height": 250,
                        }
                    )
                },
            )
        ]
    )


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

    return [
        dcc.Graph(
            id="Position",
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


if __name__ == "__main__":
    app.run_server(debug=True)

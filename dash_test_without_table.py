import dash
from dash import Dash, html, dash_table, dcc, callback_context
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from pymongo import MongoClient
from warnings import simplefilter
import numpy as np
import pandas as pd
from dash.dash_table.Format import Format, Scheme, Trim
from plotly.colors import n_colors
import dash_bootstrap_components as dbc

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


def Read_Portfolio(download_date_list):
    Portfolio = pd.DataFrame()
    for download_date in download_date_list:
        df = collection.find({'$and': [{'date': download_date}, {'tag': "Portfolio"}]})
        for account_data in df:
            data = pd.DataFrame(account_data['data'])
            data['Date'] = download_date
            Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)
    return Portfolio


def Porfolio_list(download_date_list):
    Portfolio = Read_Portfolio(download_date_list)

    # 投資組合資產分類
    Portfolio_STK = Portfolio[Portfolio["secType"] == "STK"][[
        'Date', 'Account', 'symbol', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_BOND = Portfolio[Portfolio["secType"] == "BOND"][[
        'Date', 'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost',
        'unrealizedPNL']]
    Portfolio_OPT = Portfolio[Portfolio["secType"] == "OPT"][[
        'Date', 'Account', 'symbol', 'right', 'strike', 'lastTradeDate', 'position', 'marketPrice', 'marketValue',
        'averageCost', 'unrealizedPNL']]
    Portfolio_FUT = Portfolio[Portfolio["secType"] == "FUT"][[
        'Date', 'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost',
        'unrealizedPNL']]

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
download_date_list = db_date[-20:]

read_all_AccountSummary = read_all_AccountSummary(download_date_list)

check_AccountSummary = read_AccountSummary(download_date_list[-1])
Portfolio_STK = Porfolio_list(download_date_list)["Portfolio_STK"]
Portfolio_BOND = Porfolio_list(download_date_list)["Portfolio_BOND"]
Portfolio_OPT = Porfolio_list(download_date_list)["Portfolio_OPT"]
Portfolio_FUT = Porfolio_list(download_date_list)["Portfolio_FUT"]

Portfolio_STK['des'] = Portfolio_STK['Account'] + Portfolio_STK['symbol']


# make app
app = dash.Dash()

options = check_AccountSummary.index
groups = {"groupA": list(options[:10]),
          "groupB": list(options[10:])}
group_options = list(groups.keys())

app.layout = html.Div([
    html.Div(
        className="row",
        children=[
            html.Div([
                dcc.Checklist(["All"], [], id="all-checklist", inline=True),
                dcc.Checklist(group_options, [], id="group-checklist", inline=True),
                dcc.Checklist(options, [], id="account-checklist", inline=True)
            ]
            ),
            html.Div(
                children=[
                    html.Div(
                        id='account-graph',
                        style={
                            'width': "45%",
                            'padding': 10,
                            'border': 10,
                            "margin": 10,
                            "display": "inline-block"
                        }
                    )
                ]
            )]
    ),
    html.Div(
        dcc.Graph(
            id='stock-position',
            hoverData={'points': [{'customdata': Portfolio_STK.iloc[1, 8]}]}),
        style={
            'width': "45%",
            'padding': 10,
            'border': 10,
            "margin": 10,
            "display": "inline-block"
        }
    ),
    html.Div(
        dcc.Graph(id='stock-time-series'),
        style={
            'width': "40%",
            'padding': 10,
            'border': 10,
            "margin": 10,
            "display": "inline-block"
        }
    ),
    html.Div(
        dcc.Slider(
            min=0,
            max=len(download_date_list) - 1,
            step=1,
            id='stock-date-slider',
            value=len(download_date_list) - 1,
            marks={i: download_date_list[i] for i in range(len(download_date_list))}
        ),
        style={
            'width': "45%",
            'padding': 10,
            'border': 10,
            "margin": 10,
            "display": "inline-block"
        }
    )
]
)


@app.callback(
    Output("account-checklist", "value"),
    Output("group-checklist", "value"),
    Output("all-checklist", "value"),
    Input("account-checklist", "value"),
    Input("group-checklist", "value"),
    Input("all-checklist", "value"),
)
def sync_checklists(account_selected, group_selected, all_selected):
    ctx = callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if input_id == "account-checklist":
        if set(account_selected) == set(groups['groupA']):
            group_selected = ["groupA"]
        elif set(account_selected) == set(groups['groupB']):
            group_selected = ["groupB"]
        else:
            group_selected = []
    elif input_id == "group-checklist":
        if set(group_selected).issuperset(["groupA"]):
            account_selected += groups.get("groupA")
        else:
            account_selected -= groups.get("groupA")
        if set(group_selected).issuperset(["groupB"]):
            account_selected += groups.get("groupB")
        else:
            account_selected -= groups.get("groupB")
        #
        # if group_selected == ["groupB"]:
        #     account_selected += groups.get("groupB")
        if set(group_selected) == set(group_options):
            all_selected = ["All"]
        else:
            account_selected = []
    else:
        if all_selected:
            account_selected = options
            group_selected = group_options
        else:
            all_selected = []
            group_selected = []
            account_selected = []
    return account_selected, group_selected, all_selected


@app.callback(
    Output('account-graph', "children"),
    Input('account-checklist', 'value')
)
def update_account_graphs(value):
    dff = read_all_AccountSummary
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
                        'padding': 10,
                        'border': 10,
                        "title": column,
                        "margin": {"t": 50, "l": 10, "r": 10},
                        "display": "inline-block",
                    },
                },
            )
            for column in ["NetLiquidation", "TotalCashValue", "StockValue", "BondValue"]
        ]
    )



@app.callback(
    Output('stock-position', "figure"),
    Input('stock-date-slider', 'value')
)
def update_stock_graph(date_value):
    date = download_date_list[date_value]
    df = Portfolio_STK
    account_list = df['Account'].unique()

    # hover_text
    hover_text = []
    for index, row in df.iterrows():
        hover_text.append((f"{row['symbol']}<br>" +
                           f"Account: {row['Account']}<br>" +
                           f"市值: {row['marketValue']}<br>" +
                           f"未實現損益: {row['unrealizedPNL']}<br>"
                           ))
    df['hover_text'] = hover_text

    dff = df[df['Date'] == date]

    fig = go.Figure()
    for account in account_list:
        dfff = dff[dff['Account'] == account]
        fig.add_trace(go.Scatter(x=dfff['marketValue'],
                                 y=dfff['unrealizedPNL'],
                                 text=dfff['hover_text'],
                                 mode='markers',
                                 marker=dict(
                                     sizemode='diameter',
                                     size=20),
                                 name=account,
                                 showlegend=True
                                 )
                      )

    fig.update_traces(customdata=dff['des'])

    fig.update_layout(title='Stock Position',
                      xaxis=dict(title='市值',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title='未實現損益',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)',
                      )

    return fig


def create_time_series(dfff, title):
    fig = px.scatter(dfff, x='Date', y='marketValue')

    # fig.add_trace(px.scatter(dfff, x='Date', y='position'))

    fig.update_traces(mode='lines+markers')

    fig.update_xaxes(showgrid=False)

    fig.add_annotation(x=0, y=0.85, xanchor='left', yanchor='bottom',
                       xref='paper', yref='paper', showarrow=False, align='left',
                       text=title)

    fig.update_layout(margin={'l': 20, 'b': 30, 'r': 10, 't': 10})

    return fig


@app.callback(
    Output('stock-time-series', 'figure'),
    Input('stock-position', 'hoverData')
)
def update_stock_timeseries(hoverData):
    df = Portfolio_STK
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    symbol = dff['symbol'].unique().item()
    account = dff['Account'].unique().item()
    title = f'{account} : {symbol}'
    return create_time_series(dff, title)


if __name__ == "__main__":
    app.run_server(debug=True)

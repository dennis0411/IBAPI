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
stock_account = Portfolio_STK[Portfolio_STK['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_BOND = Porfolio_list(download_date_list)["Portfolio_BOND"]
bond_account = Portfolio_BOND[Portfolio_BOND['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_OPT = Porfolio_list(download_date_list)["Portfolio_OPT"]
opt_account = Portfolio_OPT[Portfolio_OPT['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_FUT = Porfolio_list(download_date_list)["Portfolio_FUT"]
fut_account = Portfolio_FUT[Portfolio_FUT['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_STK['des'] = Portfolio_STK['Account'] + " : " + Portfolio_STK['symbol']
Portfolio_BOND['des'] = Portfolio_BOND['Account'] + " : " + Portfolio_BOND['symbol'] + " " + Portfolio_BOND[
    'lastTradeDate']
Portfolio_BOND['position'] = Portfolio_BOND['position'] * 1000
Portfolio_OPT['des'] = Portfolio_OPT['Account'] + " : " + Portfolio_OPT['symbol'] + " " + Portfolio_OPT[
    'right'] + " " + Portfolio_OPT['strike'].astype(str) + " " + Portfolio_OPT['lastTradeDate']
Portfolio_FUT['des'] = Portfolio_FUT['Account'] + " : " + Portfolio_FUT['symbol'] + " " + Portfolio_FUT[
    'lastTradeDate']

# make app
app = dash.Dash()

options = check_AccountSummary.index
groups = {'with-stock': list(stock_account),
          'with-bond': list(bond_account),
          'with-opt': list(opt_account),
          'with-fut': list(fut_account)}
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
                        style={'padding': 10,
                               'border': 10,
                               "margin": 10,
                               "display": "inline-block"})
                ]
            )
        ]
    ),
    html.Div(
        dcc.Slider(
            min=0,
            max=len(download_date_list) - 1,
            step=1,
            id='date-slider',
            value=len(download_date_list) - 1,
            marks={i: download_date_list[i] for i in range(len(download_date_list))}),
        style={'width': "45%",
               'padding': 10,
               'border': 10,
               "margin": 10}),
    dcc.Tabs([
        dcc.Tab(label='Stock', children=[
            html.Div(
                dcc.Graph(
                    id='stock-position',
                    hoverData={'points': [{'customdata': 'NoData'}]}),
                style={'width': "45%",
                       'padding': 10,
                       'border': 10,
                       "margin": 10,
                       "display": "inline-block"}),
            html.Div([
                dcc.Graph(id='stock-time-series-value',
                          style={'margin': 5}),
                dcc.Graph(id='stock-time-series-position',
                          style={'margin': 5})
            ],
                style={'width': "45%",
                       'padding': 5,
                       'border': 10,
                       'margin': 10,
                       "display": "inline-block"})]),
        dcc.Tab(label='Bond', children=[
            html.Div(
                dcc.Graph(
                    id='bond-position',
                    hoverData={'points': [{'customdata': 'NoData'}]}),
                style={'width': "45%",
                       'padding': 10,
                       'border': 10,
                       'margin': 10,
                       'display': "inline-block"}),
            html.Div([
                dcc.Graph(id='bond-time-series-value',
                          style={'margin': 5}),
                dcc.Graph(id='bond-time-series-position',
                          style={'margin': 5})],
                style={'width': "45%",
                       'padding': 5,
                       'border': 10,
                       'margin': 10,
                       "display": "inline-block"})]
                ),
        dcc.Tab(label='OPT', children=[
            html.Div(
                dcc.Graph(id='opt-position',
                          hoverData={'points': [{'customdata': 'NoData'}]}),
                style={'width': "45%",
                       'padding': 10,
                       'border': 10,
                       "margin": 10,
                       "display": "inline-block"}),
            html.Div([
                dcc.Graph(id='opt-time-series-value',
                          style={
                              'margin': 5,
                          }),
                dcc.Graph(id='opt-time-series-position',
                          style={'margin': 5})],
                style={'width': "45%",
                       'padding': 5,
                       'border': 10,
                       'margin': 10,
                       "display": "inline-block"})]),
        dcc.Tab(label='FUT', children=[
            html.Div(
                dcc.Graph(id='fut-position',
                          hoverData={'points': [{'customdata': 'NoData'}]}
                          ),
                style={'width': "45%",
                       'padding': 10,
                       'border': 10,
                       "margin": 10,
                       "display": "inline-block"}),
            html.Div([
                dcc.Graph(id='fut-time-series-value',
                          style={
                              'margin': 5,
                          }),
                dcc.Graph(id='fut-time-series-position',
                          style={
                              'margin': 5,
                          })],
                style={'width': "45%",
                       'padding': 5,
                       'border': 10,
                       'margin': 10,
                       "display": "inline-block"})]
                )
    ])
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
        if set(account_selected) == set(options):
            group_selected = group_options
            all_selected = ["All"]
        elif set(account_selected).issuperset(set(groups['with-stock'])):
            group_selected = ["with-stock"]
        elif set(account_selected).issuperset(set(groups['with-bond'])):
            group_selected = ["with-bond"]
        elif set(account_selected).issuperset(set(groups['with-opt'])):
            group_selected = ["with-opt"]
        elif set(account_selected).issuperset(set(groups['with-fut'])):
            group_selected = ["with-fut"]
        else:
            group_selected = []
    elif input_id == "group-checklist":
        if group_selected == ["with-stock"]:
            account_selected += groups.get("with-stock")
        elif group_selected == ["with-bond"]:
            account_selected += groups.get("with-bond")
        elif group_selected == ["with-opt"]:
            account_selected += groups.get("with-opt")
        elif group_selected == ["with-fut"]:
            account_selected += groups.get("with-fut")
        elif set(group_selected) == set(group_options):
            account_selected = groups.get("with-bond") + groups.get("with-stock") + groups.get("with-opt") + groups.get(
                "with-fut")
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
        for column in ['NetLiquidation', 'TotalCashValue', 'StockValue', 'BondValue', 'OPTValue', 'FUTValue']:
            dfff.loc[date, column] = dff[dff["Date"] == date][column].astype(float).sum()

    for column in ['NetLiquidation', 'TotalCashValue', 'StockValue', 'BondValue', 'OPTValue', 'FUTValue']:
        hover_text = []
        for index, row in dfff.iterrows():
            hover_text.append((f"{column} : {row[column]:,.2f}<br>" +
                               f"佔淨值比 : {row[column] / row['NetLiquidation'] if row['NetLiquidation'] != 0 else 0:.2%}<br>"))
        dfff[f'{column}-des'] = hover_text

    return html.Div(
        [
            dcc.Graph(
                id=column,
                figure=go.Figure(
                    data=go.Scatter(x=dfff.index, y=dfff[column],
                                    hovertext=dfff[f'{column}-des']),
                    layout={
                        "xaxis": {"automargin": True},
                        "yaxis": {"automargin": True},
                        "title": column,
                        "margin": {"t": 30, "l": 10, "r": 10},
                    }
                ),
                style={
                    'height': 400,
                    'width': "45%",
                    'padding': 5,
                    'border': 5,
                    "margin": 5,
                    "display": "inline-block"
                }
            )
            for column in ["NetLiquidation", "TotalCashValue", "StockValue", "BondValue"]
        ]
    )


@app.callback(
    Output('stock-position', "figure"),
    Input('date-slider', 'value'),
    Input('account-checklist', 'value')
)
def update_stock_graph(date_value, account_selected):
    date = download_date_list[date_value]
    df = Portfolio_STK[Portfolio_STK['Account'].isin(account_selected)]
    dff = df[df['Date'] == date]

    fig = px.scatter(dff,
                     x=dff['marketValue'],
                     y='unrealizedPNL',
                     hover_name='des'
                     )

    fig.update_traces(customdata=dff['des'])

    fig.update_layout(title='Stock Position',
                      xaxis=dict(title='marketValue',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title='unrealizedPNL',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)',
                      )

    return fig


def create_time_series(dff, column):
    dfff = dff.copy()
    dfff['Date'] = pd.to_datetime(dff['Date']).dt.strftime('%m/%d')

    fig = px.scatter(dfff, x='Date', y=column, hover_name='des')

    fig.update_traces(mode='lines+markers')

    fig.update_layout(xaxis=dict(title=None,
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title=column,
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      height=225,
                      margin={'l': 20, 'b': 30, 'r': 10, 't': 10},
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)'
                      )

    return fig


@app.callback(
    Output('stock-time-series-value', 'figure'),
    Input('stock-position', 'hoverData')
)
def update_stock_timeseries_value(hoverData):
    df = Portfolio_STK
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'marketValue'
    return create_time_series(dff, column)


@app.callback(
    Output('stock-time-series-position', 'figure'),
    Input('stock-position', 'hoverData')
)
def update_stock_timeseries_position(hoverData):
    df = Portfolio_STK
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'position'
    return create_time_series(dff, column)


@app.callback(
    Output('bond-position', "figure"),
    Input('date-slider', 'value'),
    Input('account-checklist', 'value')
)
def update_bond_graph(date_value, account_selected):
    date = download_date_list[date_value]
    df = Portfolio_BOND[Portfolio_BOND['Account'].isin(account_selected)]
    dff = df[df['Date'] == date]

    fig = px.scatter(dff,
                     x=dff['marketValue'],
                     y='unrealizedPNL',
                     hover_name='des'
                     )

    fig.update_traces(customdata=dff['des'])

    fig.update_layout(title='Bond Position',
                      xaxis=dict(title='marketValue',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title='unrealizedPNL',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)',
                      )

    return fig


@app.callback(
    Output('bond-time-series-value', 'figure'),
    Input('bond-position', 'hoverData')
)
def update_bond_timeseries_value(hoverData):
    df = Portfolio_BOND
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'marketValue'
    return create_time_series(dff, column)


@app.callback(
    Output('bond-time-series-position', 'figure'),
    Input('bond-position', 'hoverData'),
)
def update_bond_timeseries_position(hoverData):
    df = Portfolio_BOND
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'position'
    return create_time_series(dff, column)


@app.callback(
    Output('opt-position', "figure"),
    Input('date-slider', 'value'),
    Input('account-checklist', 'value')
)
def update_opt_graph(date_value, account_selected):
    date = download_date_list[date_value]
    df = Portfolio_OPT[Portfolio_OPT['Account'].isin(account_selected)]
    dff = df[df['Date'] == date]

    fig = px.scatter(dff,
                     x=dff['marketValue'],
                     y='unrealizedPNL',
                     hover_name='des'
                     )

    fig.update_traces(customdata=dff['des'])

    fig.update_layout(title='OPT Position',
                      xaxis=dict(title='marketValue',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title='unrealizedPNL',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)',
                      )

    return fig


@app.callback(
    Output('opt-time-series-value', 'figure'),
    Input('opt-position', 'hoverData')
)
def update_opt_timeseries_value(hoverData):
    df = Portfolio_OPT
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'marketValue'
    return create_time_series(dff, column)


@app.callback(
    Output('opt-time-series-position', 'figure'),
    Input('opt-position', 'hoverData'),
)
def update_opt_timeseries_position(hoverData):
    df = Portfolio_OPT
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'position'
    return create_time_series(dff, column)


@app.callback(
    Output('fut-position', "figure"),
    Input('date-slider', 'value'),
    Input('account-checklist', 'value')
)
def update_fut_graph(date_value, account_selected):
    date = download_date_list[date_value]
    df = Portfolio_FUT[Portfolio_FUT['Account'].isin(account_selected)]
    dff = df[df['Date'] == date]

    fig = px.scatter(dff,
                     x=dff['marketValue'],
                     y='unrealizedPNL',
                     hover_name='des'
                     )

    fig.update_traces(customdata=dff['des'])

    fig.update_layout(title='FUT Position',
                      xaxis=dict(title='marketValue',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      yaxis=dict(title='unrealizedPNL',
                                 gridcolor='white',
                                 gridwidth=2,
                                 ),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)',
                      )

    return fig


@app.callback(
    Output('fut-time-series-value', 'figure'),
    Input('fut-position', 'hoverData')
)
def update_fut_timeseries_value(hoverData):
    df = Portfolio_FUT
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'marketValue'
    return create_time_series(dff, column)


@app.callback(
    Output('fut-time-series-position', 'figure'),
    Input('fut-position', 'hoverData'),
)
def update_fut_timeseries_position(hoverData):
    df = Portfolio_FUT
    des = hoverData['points'][0]['customdata']
    dff = df[df['des'] == des]
    column = 'position'
    return create_time_series(dff, column)


if __name__ == "__main__":
    app.run_server(debug=True)

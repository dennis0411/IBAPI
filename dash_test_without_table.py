import datetime
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
path = 'mongodb_password'
with open(path) as f:
    word = f.readline().split(',')
    account = word[0]
    password = word[1]


# Build Function
def read_AccountSummary(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': 'AccountSummary'}]})
    AccountSummary = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        AccountSummary = pd.concat([AccountSummary, data], axis=0, ignore_index=True)

    AccountSummary = AccountSummary.pivot(index='Account', columns='tag', values='value')

    Portfolio = read_Portfolio(download_date)

    # 帳戶資料新增持倉
    for account in AccountSummary.index:
        secType_filt = {'StockValue': (Portfolio['Account'] == account) & (Portfolio['secType'] == 'STK'),
                        'BondValue': (Portfolio['Account'] == account) & (Portfolio['secType'] == 'BOND'),
                        'OPTValue': (Portfolio['Account'] == account) & (Portfolio['secType'] == 'OPT'),
                        'FUTValue': (Portfolio['Account'] == account) & (Portfolio['secType'] == 'FUT')
                        }
        for filt in secType_filt.keys():
            AccountSummary.loc[account, filt] = Portfolio[secType_filt.get(filt)]['marketValue'].sum()
    AccountSummary['Date'] = download_date
    return AccountSummary


def read_Portfolio(download_date):
    df = collection.find({'$and': [{'date': download_date}, {'tag': 'Portfolio'}]})
    Portfolio = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)
    return Portfolio


def Read_Portfolio(download_date_list):
    Portfolio = pd.DataFrame()
    for download_date in download_date_list:
        df = collection.find({'$and': [{'date': download_date}, {'tag': 'Portfolio'}]})
        for account_data in df:
            data = pd.DataFrame(account_data['data'])
            data['Date'] = download_date
            Portfolio = pd.concat([Portfolio, data], axis=0, ignore_index=True)
    return Portfolio


def Porfolio_list(download_date_list):
    Portfolio = Read_Portfolio(download_date_list)

    # 投資組合資產分類
    Portfolio_STK = Portfolio[Portfolio["secType"] == "STK"][['Date', 'Account', 'symbol', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_BOND = Portfolio[Portfolio["secType"] == "BOND"][
        ['Date', 'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_OPT = Portfolio[Portfolio["secType"] == "OPT"][
        ['Date', 'Account', 'symbol', 'right', 'strike', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
    Portfolio_FUT = Portfolio[Portfolio["secType"] == "FUT"][
        ['Date', 'Account', 'symbol', 'lastTradeDate', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]

    Portfolio_list = {'Portfolio_STK': Portfolio_STK,
                      'Portfolio_BOND': Portfolio_BOND,
                      'Portfolio_OPT': Portfolio_OPT,
                      'Portfolio_FUT': Portfolio_FUT}

    return Portfolio_list


def read_all_AccountSummary(download_date_list):
    AccountSummary = pd.DataFrame()
    for download_date in download_date_list:
        AccountSummary = pd.concat([read_AccountSummary(download_date).reset_index(), AccountSummary], axis=0, ignore_index=True)
    return AccountSummary


# mongodb connection
CONNECTION_STRING = f'mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority'
client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
db = client.getdata
collection = db.ib
db_date = collection.distinct('date')
download_date_list = db_date[-20:]

# data ready
read_all_AccountSummary = read_all_AccountSummary(download_date_list)

check_AccountSummary = read_AccountSummary(download_date_list[-1])

Portfolio_STK = Porfolio_list(download_date_list)['Portfolio_STK']
stock_account = Portfolio_STK[Portfolio_STK['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_BOND = Porfolio_list(download_date_list)['Portfolio_BOND']
bond_account = Portfolio_BOND[Portfolio_BOND['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_OPT = Porfolio_list(download_date_list)['Portfolio_OPT']
opt_account = Portfolio_OPT[Portfolio_OPT['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_FUT = Porfolio_list(download_date_list)['Portfolio_FUT']
fut_account = Portfolio_FUT[Portfolio_FUT['Date'] == download_date_list[-1]]['Account'].unique()

Portfolio_STK['des'] = Portfolio_STK['Account'] + " : " + Portfolio_STK['symbol']
Portfolio_BOND['des'] = Portfolio_BOND['Account'] + " : " + Portfolio_BOND['symbol'] + " " + Portfolio_BOND['lastTradeDate']
Portfolio_BOND['position'] = Portfolio_BOND['position'] * 1000
Portfolio_OPT['des'] = Portfolio_OPT['Account'] + " : " + Portfolio_OPT['symbol'] + " " + Portfolio_OPT['right'] + " " + Portfolio_OPT['strike'].astype(str) + " " + Portfolio_OPT[
    'lastTradeDate']
Portfolio_FUT['des'] = Portfolio_FUT['Account'] + " : " + Portfolio_FUT['symbol'] + " " + Portfolio_FUT['lastTradeDate']

read_all_AccountSummary = read_all_AccountSummary.round(2)
Portfolio_STK = Portfolio_STK.round(2)
Portfolio_BOND = Portfolio_BOND.round(2)
Portfolio_OPT = Portfolio_OPT.round(2)
Portfolio_FUT = Portfolio_FUT.round(2)

# make app
app = dash.Dash()

options = check_AccountSummary.index
groups = {'All': options,
          'Stock': list(stock_account),
          'Bond': list(bond_account),
          'Opt': list(opt_account),
          'Fut': list(fut_account)}

group_options = list(groups.keys())

app.layout = html.Div([
    html.Div(
        children=[
            html.Div([
                dcc.Dropdown(group_options, ['All'],
                             id='group-checklist',
                             style={'width': '95%', 'margin': 10, 'display': 'inline-block'},
                             placeholder='Select Group',
                             clearable=True),
                dcc.Dropdown(options, options,
                             id='account-checklist',
                             multi=True,
                             style={'margin': 10},
                             placeholder='Select Account',
                             searchable=True)
            ],
                style={'width': '15%',
                       'display': 'inline-block',
                       'padding': 5,
                       'margin': 5}
            ),
            html.Div([
                dcc.Tabs([
                    dcc.Tab(label='graph',
                            children=[
                                html.Div(id='account-graph',
                                         style={'display': 'inline-block'})]),
                    dcc.Tab(label='table',
                            children=[
                                html.Div(id='account-table',
                                         style={'padding': 10,
                                                'border': 10,
                                                'margin': 10,
                                                'display': 'inline-block'})])
                ])],
                style={'width': '80%',
                       'display': 'inline-block',
                       'padding': 10,
                       'border': 10,
                       "margin": 10}
            )
        ]
    ),
    dcc.Tabs([
        dcc.Tab(label='Stock',
                children=[
                    html.Div(
                        dcc.Graph(id='stock-position',
                                  hoverData={'points': [{'customdata': 'NoData'}]}),
                        style={'width': '45%', 'padding': 10, 'border': 10, 'margin': 10, 'display': 'inline-block'}),
                    html.Div([
                        dcc.Graph(id='stock-time-series-value', style={'margin': 5}),
                        dcc.Graph(id='stock-time-series-position', style={'margin': 5})
                    ],
                        style={'width': '45%', 'padding': 5, 'border': 10, 'margin': 10, 'display': 'inline-block'})]
                ),
        dcc.Tab(label='Bond',
                children=[
                    html.Div(
                        dcc.Graph(id='bond-position', hoverData={'points': [{'customdata': 'NoData'}]}),
                        style={'width': "45%", 'padding': 10, 'border': 10, 'margin': 10, 'display': 'inline-block'}),
                    html.Div([
                        dcc.Graph(id='bond-time-series-value', style={'margin': 5}),
                        dcc.Graph(id='bond-time-series-position', style={'margin': 5})],
                        style={'width': '45%', 'padding': 5, 'border': 10, 'margin': 10, 'display': 'inline-block'}),
                    # html.Div([
                    #     dcc.Graph(id='bond-maturity-position', style={'margin': 5})],
                    #     style={'width': '45%', 'padding': 5, 'border': 10, 'margin': 10, 'display': 'inline-block'})
                ]
                ),
        # dcc.Tab(label='OPT',
        #         children=[
        #             html.Div(
        #                 dcc.Graph(id='opt-position', hoverData={'points': [{'customdata': 'NoData'}]}),
        #                 style={'width': '45%', 'padding': 10, 'border': 10, 'margin': 10, 'display': 'inline-block'}),
        #             html.Div([
        #                 dcc.Graph(id='opt-time-series-value', style={'margin': 5}),
        #                 dcc.Graph(id='opt-time-series-position', style={'margin': 5})],
        #                 style={'width': '45%', 'padding': 5, 'border': 10, 'margin': 10, 'display': 'inline-block'})]
        #         ),
        # dcc.Tab(label='FUT',
        #         children=[
        #             html.Div(
        #                 dcc.Graph(id='fut-position', hoverData={'points': [{'customdata': 'NoData'}]}),
        #                 style={'width': '45%', 'padding': 10, 'border': 10, 'margin': 10, 'display': 'inline-block'}),
        #             html.Div([
        #                 dcc.Graph(id='fut-time-series-value', style={'margin': 5}),
        #                 dcc.Graph(id='fut-time-series-position', style={'margin': 5})
        #             ],
        #                 style={'width': '45%', 'padding': 5, 'border': 10, 'margin': 10, 'display': 'inline-block'})]
        #         )
    ]),
    html.Div(
        dcc.RangeSlider(min=0,
                        max=len(download_date_list) - 1,
                        step=1,
                        id='date-slider',
                        value=[0, len(download_date_list) - 1],
                        marks={i: download_date_list[i] for i in range(len(download_date_list))}),
        style={'width': '45%', 'padding': 10, 'border': 10, 'margin': 10})
]
)


@app.callback(
    Output('account-checklist', 'value'),
    Output('group-checklist', 'value'),
    Input('account-checklist', 'value'),
    Input('group-checklist', 'value'),
)
def sync_checklists(account_selected, group_selected):
    ctx = callback_context
    input_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if input_id == 'account-checklist':
        if set(account_selected) == set(options):
            group_selected = ['All']
        else:
            group_selected = []

    elif input_id == 'group-checklist':
        if group_selected == ['All']:
            account_selected = options
        else:
            account_selected = groups.get(group_selected)

    return account_selected, group_selected


@app.callback(
    Output('account-graph', 'children'),
    Input('account-checklist', 'value')
)
def update_account_graphs(value):
    dff = read_all_AccountSummary
    dff = dff.loc[dff['Account'].isin(value)]
    dfff = pd.DataFrame()
    for date in download_date_list:
        for column in ['NetLiquidation', 'TotalCashValue', 'StockValue', 'BondValue', 'OPTValue', 'FUTValue']:
            dfff.loc[date, column] = dff[dff["Date"] == date][column].astype(float).sum()

    dfff = dfff.reset_index().rename(columns={'index': 'Date'})
    dfff['Date'] = pd.to_datetime(dfff['Date']).dt.strftime('%m/%d')

    for column in ['NetLiquidation', 'TotalCashValue', 'StockValue', 'BondValue', 'OPTValue', 'FUTValue']:
        hover_text = []
        base = dfff.loc[0, column].item()
        for index, row in dfff.iterrows():
            hover_text.append((f"{column} : {row[column]:,.2f}<br>" +
                               f"期間變化 : {row[column] / base - 1 :.2%}<br>" +
                               f"佔淨值比 : {row[column] / row['NetLiquidation'] if row['NetLiquidation'] != 0 else 0:.2%}"))
        dfff[f'{column}-des'] = hover_text

    return html.Div([
        dcc.Graph(id=column,
                  figure=go.Figure(data=go.Scatter(x=dfff['Date'], y=dfff[column], hovertext=dfff[f'{column}-des']),
                                   layout={'xaxis': {'automargin': True},
                                           'yaxis': {'automargin': True},
                                           'title': column,
                                           'margin': {'t': 40, 'l': 10, 'r': 10}}),
                  style={'height': 350,
                         'width': "45%",
                         'margin': 5,
                         'display': 'inline-block'})
        for column in ['NetLiquidation', 'TotalCashValue', 'StockValue', 'BondValue']])


@app.callback(
    Output('account-table', 'children'),
    Input('account-checklist', 'value')
)
def update_account_table(value):
    df = check_AccountSummary
    data = df.filter(items=value, axis=0).reset_index()

    columns = [{'name': i, 'id': i, 'deletable': False, 'selectable': True, 'type': 'numeric', 'format': Format(precision=2, scheme=Scheme.fixed)} for i in data.columns]
    data = data.to_dict('records')

    return dash_table.DataTable(data=data,
                                columns=columns,
                                editable=False,
                                row_deletable=False,
                                filter_action='native',
                                selected_columns=[],
                                selected_rows=[],
                                page_action='native',
                                page_size=20,
                                page_current=0)


@app.callback(
    Output('stock-position', 'figure'),
    [Input('date-slider', 'value')],
    Input('account-checklist', 'value')
)
def update_stock_graph(date_value, account_selected):
    date0 = download_date_list[date_value[1]]
    date1 = download_date_list[date_value[0]]
    df = Portfolio_STK[Portfolio_STK['Account'].isin(account_selected)]
    dff = df[df['Date'] == date0]
    dfff = df[df['Date'] == date1]

    pricechg = []
    for des in dff['des']:
        data = dff.loc[dff['des'] == des, 'marketPrice'].item() / dfff.loc[dfff['des'] == des, 'marketPrice'].item() - 1 if des in dfff['des'].tolist() else 0
        pricechg.append((round(data, 4)))

    dfff = dff.copy()

    dfff.loc[:, 'pricechg'] = pricechg

    fig = px.scatter(dfff,
                     x='pricechg',
                     y='unrealizedPNL',
                     size='marketValue',
                     hover_name='des',
                     size_max=60)

    fig.update_traces(customdata=dfff['des'])

    fig.update_layout(title='Stock Position',
                      xaxis=dict(title='Price Change', gridcolor='white', gridwidth=2),
                      yaxis=dict(title='unrealizedPNL', gridcolor='white', gridwidth=2),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)')

    return fig


def create_time_series(dff, column):
    dfff = dff.copy()
    dfff['Date'] = pd.to_datetime(dff['Date']).dt.strftime('%m/%d')

    hover_text = []
    df = dfff[column].values.tolist()
    base = df[0]

    for index, row in dfff.iterrows():
        hover_text.append((f" {row[column] / base - 1 :.2%}"))

    dfff['change'] = hover_text

    fig = px.scatter(dfff, x='Date', y=column, hover_name='des', hover_data=['change'])

    fig.update_traces(mode='lines+markers')

    fig.update_layout(xaxis=dict(title=None, gridcolor='white', gridwidth=2),
                      yaxis=dict(title=column, gridcolor='white', gridwidth=2),
                      height=220,
                      margin={'l': 20, 'b': 20, 'r': 10, 't': 10},
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)')

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
    Output('bond-position', 'figure'),
    [Input('date-slider', 'value')],
    Input('account-checklist', 'value')
)
def update_bond_graph(date_value, account_selected):
    date0 = download_date_list[date_value[1]]
    date1 = download_date_list[date_value[0]]
    df = Portfolio_BOND[Portfolio_BOND['Account'].isin(account_selected)]
    dff = df[df['Date'] == date0]
    dfff = df[df['Date'] == date1]

    pricechg = []
    for des in dff['des']:
        data = dff.loc[dff['des'] == des, 'marketPrice'].item() / dfff.loc[dfff['des'] == des, 'marketPrice'].item() - 1 if des in dfff['des'].tolist() else 0
        pricechg.append((round(data, 4)))

    dfff = dff.copy()

    dfff.loc[:, 'pricechg'] = pricechg

    fig = px.scatter(dfff,
                     x='pricechg',
                     y='unrealizedPNL',
                     size='marketValue',
                     hover_name='des')

    fig.update_traces(customdata=dfff['des'])

    fig.update_layout(title='Bond Position',
                      xaxis=dict(title='Price Change', gridcolor='white', gridwidth=2),
                      yaxis=dict(title='unrealizedPNL', gridcolor='white', gridwidth=2),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)')

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
    Output('bond-maturity-position', 'figure'),
    Input('date-slider', 'value'),
    Input('account-checklist', 'value')
)
def update_bond_maturity_graph(date_value, account_selected):
    date = download_date_list[date_value[1]]
    df = Portfolio_BOND[Portfolio_BOND['Account'].isin(account_selected)]
    dff = df[df['Date'] == date]
    year = datetime.date.today().strftime('%Y')

    maturity = []
    for index, row in dff.iterrows():
        maturity_period = float(row['lastTradeDate'][:4]) - float(year)
        if maturity_period <= 5:
            maturity.append(('1~5y'))
        elif maturity_period > 5 and maturity_period <= 10:
            maturity.append(('5~10y'))
        elif maturity_period > 10:
            maturity.append(('10y+'))
        else:
            maturity.append(('None'))

    dff['maturity'] = maturity

    data = []
    for account in dff['Account'].unique():
        for maturity in ['1~5y', '5~10y', '10y+']:
            position = dff.loc[(dff['Account'] == account) & (dff['maturity'] == maturity), 'position'].sum()
            data.append((account, maturity, position))

    dfff = pd.DataFrame(data, columns=['Account', 'maturity', 'position'])
    dfff.round(2)

    fig = px.bar(dfff,
                 x='maturity',
                 y='position',
                 color='Account'
                 )

    fig.update_layout(title='Bond Position Maturity',
                      xaxis=dict(title='maturity', gridcolor='white', gridwidth=2),
                      yaxis=dict(title='position', gridcolor='white', gridwidth=2),
                      paper_bgcolor='rgb(243, 243, 243)',
                      plot_bgcolor='rgb(243, 243, 243)')

    return fig


# @app.callback(
#     Output('opt-position', "figure"),
#     Input('date-slider', 'value'),
#     Input('account-checklist', 'value')
# )
# def update_opt_graph(date_value, account_selected):
#     date = download_date_list[date_value]
#     df = Portfolio_OPT[Portfolio_OPT['Account'].isin(account_selected)]
#     dff = df[df['Date'] == date]
#     dfff = df[df['Date'] == download_date_list[0]]
#
#     pricechg = []
#     for des in dff['des']:
#         data = dff.loc[dff['des'] == des, 'marketPrice'].item() / dfff.loc[dfff['des'] == des, 'marketPrice'].item() - 1 if des in dfff['des'].tolist() else 0
#         pricechg.append((data))
#
#     dff['pricechg'] = pricechg
#
#     fig = px.scatter(dff,
#                      x='pricechg',
#                      y='unrealizedPNL',
#                      size='marketValue',
#                      hover_name='des')
#
#     fig.update_traces(customdata=dff['des'])
#
#     fig.update_layout(title='OPT Position',
#                       xaxis=dict(title='Price Change', gridcolor='white', gridwidth=2),
#                       yaxis=dict(title='unrealizedPNL', gridcolor='white', gridwidth=2),
#                       paper_bgcolor='rgb(243, 243, 243)',
#                       plot_bgcolor='rgb(243, 243, 243)')
#
#     return fig
#
#
# @app.callback(
#     Output('opt-time-series-value', 'figure'),
#     Input('opt-position', 'hoverData')
# )
# def update_opt_timeseries_value(hoverData):
#     df = Portfolio_OPT
#     des = hoverData['points'][0]['customdata']
#     dff = df[df['des'] == des]
#     column = 'marketValue'
#     return create_time_series(dff, column)
#
#
# @app.callback(
#     Output('opt-time-series-position', 'figure'),
#     Input('opt-position', 'hoverData'),
# )
# def update_opt_timeseries_position(hoverData):
#     df = Portfolio_OPT
#     des = hoverData['points'][0]['customdata']
#     dff = df[df['des'] == des]
#     column = 'position'
#     return create_time_series(dff, column)
#
#
# @app.callback(
#     Output('fut-position', 'figure'),
#     Input('date-slider', 'value'),
#     Input('account-checklist', 'value')
# )
# def update_fut_graph(date_value, account_selected):
#     date = download_date_list[date_value]
#     df = Portfolio_FUT[Portfolio_FUT['Account'].isin(account_selected)]
#     dff = df[df['Date'] == date]
#     dfff = df[df['Date'] == download_date_list[0]]
#     print(dff)
#
#     pricechg = []
#     for des in dff['des']:
#         data = dff.loc[dff['des'] == des, 'marketPrice'].item() / dfff.loc[dfff['des'] == des, 'marketPrice'].item() - 1 if des in dfff['des'].tolist() else 0
#         pricechg.append((data))
#
#     dff['pricechg'] = pricechg
#
#     fig = px.scatter(dff,
#                      x='pricechg',
#                      y='unrealizedPNL',
#                      size='marketValue',
#                      hover_name='des')
#
#     fig.update_traces(customdata=dff['des'])
#
#     fig.update_layout(title='FUT Position',
#                       xaxis=dict(title='Price Change', gridcolor='white', gridwidth=2),
#                       yaxis=dict(title='unrealizedPNL', gridcolor='white', gridwidth=2),
#                       paper_bgcolor='rgb(243, 243, 243)',
#                       plot_bgcolor='rgb(243, 243, 243)')
#
#     return fig
#
#
# @app.callback(
#     Output('fut-time-series-value', 'figure'),
#     Input('fut-position', 'hoverData')
# )
# def update_fut_timeseries_value(hoverData):
#     df = Portfolio_FUT
#     des = hoverData['points'][0]['customdata']
#     dff = df[df['des'] == des]
#     column = 'marketValue'
#     return create_time_series(dff, column)
#
#
# @app.callback(
#     Output('fut-time-series-position', 'figure'),
#     Input('fut-position', 'hoverData'),
# )
# def update_fut_timeseries_position(hoverData):
#     df = Portfolio_FUT
#     des = hoverData['points'][0]['customdata']
#     dff = df[df['des'] == des]
#     column = 'position'
#     return create_time_series(dff, column)


if __name__ == "__main__":
    app.run_server(debug=True)

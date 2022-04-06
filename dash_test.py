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


if __name__ == "__main__":
    # mongodb connection
    CONNECTION_STRING = f"mongodb+srv://{account}:{password}@getdata.dzc20.mongodb.net/getdata?retryWrites=true&w=majority"
    client = MongoClient(CONNECTION_STRING, tls=True, tlsAllowInvalidCertificates=True)
    db = client.getdata
    collection = db.ib

    # make app
    app = dash.Dash()

    download_date = '2022/04/06'
    df = collection.find({'$and': [{'date': download_date}, {'tag': "AccountSummary"}]})
    AccountSummary = pd.DataFrame()
    for account_data in df:
        data = pd.DataFrame(account_data['data'])
        AccountSummary = pd.concat([AccountSummary, data], axis=0, ignore_index=True)

    app.layout = html.Div([
        dash_table.DataTable(
            id='datatable-interactivity',
            columns=[
                {"name": i, "id": i, "deletable": True, "selectable": True} for i in AccountSummary.columns
            ],
            data=AccountSummary.to_dict('records'),
            editable=True,
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            column_selectable="single",
            row_selectable="multi",
            row_deletable=True,
            selected_columns=[],
            selected_rows=[],
            page_action="native",
            page_current=0,
            page_size=50,
        ),
        html.Div(id='datatable-interactivity-container')
    ])


    @app.callback(
        Output('datatable-interactivity', 'style_data_conditional'),
        Input('datatable-interactivity', 'selected_columns')
    )
    def update_styles(selected_columns):
        return [{
            'if': {'column_id': i},
            'background_color': '#D2F3FF'
        } for i in selected_columns]


    @app.callback(
        Output('datatable-interactivity-container', "children"),
        Input('datatable-interactivity', "derived_virtual_data"),
        Input('datatable-interactivity', "derived_virtual_selected_rows"))
    def update_graphs(rows, derived_virtual_selected_rows):
        if derived_virtual_selected_rows is None:
            derived_virtual_selected_rows = []

        dff = AccountSummary if rows is None else pd.DataFrame(rows)

        colors = ['#7FDBFF' if i in derived_virtual_selected_rows else '#0074D9'
                  for i in range(len(dff))]

        return [
            dcc.Graph(
                id=column,
                figure={
                    "data": [
                        {
                            "x": dff["country"],
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
            for column in ["pop", "lifeExp", "gdpPercap"] if column in dff
        ]


    if __name__ == '__main__':
        app.run_server(debug=True)

    # app.layout = html.Div([
    #
    #     dcc.DatePickerSingle(
    #         id='my-date-picker-single',
    #         min_date_allowed=date(2022, 1, 1),
    #         max_date_allowed=date.today(),
    #         initial_visible_month=date.today(),
    #         date=date.today()
    #     ),
    #     dcc.Graph(id="graph")
    # ])


    # @app.callback(
    #     Output('graph', 'figure'),
    #     Input('my-date-picker-single', 'date_value'))
    # def update_graphs(date_value):
    #     AccountSummary = read_AccountSummary(date_value)
    #     fig = go.Figure(data=[go.Table(
    #         header=dict(
    #             values=['<b>Column A</b>', '<b>Column B</b>', '<b>Column C</b>'],
    #             line_color='white', fill_color='white',
    #             align='center', font=dict(color='black', size=12)
    #         ),
    #         cells=dict(
    #             values=[a, b, c],
    #             line_color=[np.array(colors)[a], np.array(colors)[b], np.array(colors)[c]],
    #             fill_color=[np.array(colors)[a], np.array(colors)[b], np.array(colors)[c]],
    #             align='center', font=dict(color='white', size=11)
    #         ))
    #     ])
    #     return fig




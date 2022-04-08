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


# make app
app = dash.Dash()


app.layout = html.Div([
    html.Div('Example Div', style={'color': 'blue', 'fontSize': 14}),
    html.Div('Example Div', style={'color': 'blue', 'fontSize': 14}),
    html.P('Example P', className='my-class', id='my-p-element')
])




if __name__ == "__main__":
    app.run_server(debug=True)

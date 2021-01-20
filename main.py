import dash
import pandas as pd
import numpy as np
import base64
import datetime as dt
import io

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

import dash_html_components as html
import dash_core_components as dcc
import dash_table

import plotly.express as px

app = dash.Dash(__name__)
server = app.server


days = [1, 2, 3, 4, 5, 6, 7, 14, 21]
used_acriss = ['MBMR', 'EDMR', 'CDMR', 'IDMD', 'CCAR', 'PDMD', 'JVMD', 'SVMD']

bench_columns = {'Fecha': 'Date', 'Site': 'Web', 'Días': 'Days', 'Coche': 'Car', 'Categoria': 'Category','Acriss': 'Acriss',
                 'Transmisión': 'Transmition','Asientos': 'Seats', 'Puertas': 'Doors','Proveedor': 'Competitor', 'Precio': 'Price'}
index = pd.MultiIndex.from_tuples([(d, a) for d in days for a in used_acriss], names=["Days", "Car Group"])
df = pd.DataFrame(data='europcar', index=index, columns=[str(x) for x in range(1, 32)])
df.reset_index(inplace=True)

def pivot_table_bench(df):
    df.rename(columns=bench_columns, inplace=True)
    df.dropna(inplace=True, axis=0)
    pricing_pivot = pd.pivot_table(df,
                                   index=['Competitor', 'Days', 'Date', 'Acriss'],
                                   values=['Price'],
                                   aggfunc=np.min)
    pricing_pivot.reset_index(inplace=True)
    pricing_pivot['Date'] = pd.to_datetime(pricing_pivot['Date'])
    pricing_pivot.sort_values(by=['Competitor', 'Date'], ascending=True, inplace=True)
    return pricing_pivot

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xlsx' in filename:
            # Assume that the user uploaded an excel file
            sh_bench = pd.read_excel(io.BytesIO(decoded), sheet_name='bench')
            df = pivot_table_bench(sh_bench)
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])
    return df.to_json(date_format='iso', orient='split')

def create_figure(dff):
    fig = px.line(dff, x='Date', y="Price", color='Competitor')
    fig.update_xaxes(
        dtick=86400000.0)
    return fig

app.layout = html.Div([
    dcc.Store(id='memory-output',
              storage_type='memory'),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    dcc.DatePickerRange(
        id='date-picker-range',
        display_format='DD/MM/YY',
        min_date_allowed=dt.date.today(),
        start_date=dt.date.today(),
        end_date=(dt.date.today() + dt.timedelta(31))
    ),
    dcc.Dropdown(id='memory-days', options=[
        {'value': x, 'label': x} for x in days
    ], multi=False, value=7),
    dcc.Dropdown(id='memory-acriss', options=[
        {'value': x, 'label': x} for x in used_acriss
    ], multi=False, value='MBMR'),
    # Hidden div inside the app that stores the intermediate value
    html.Div(id='intermediate-value', style={'display': 'none'}),
    dcc.Graph(id='graph'),
    dash_table.DataTable(
        id='strategy-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        fixed_rows={'headers': True, 'data': 0},
        editable=True,
        column_selectable="multi",
        row_selectable="multi",
        #selected_columns=[],
        #selected_rows=[],
        #page_action="native",
        #page_current=0,
        page_size=8,
        #export_format='xlsx',
        #export_headers='display',
        style_table={'overflowX': 'auto'},
        style_cell={
            'height': 'auto',
            # all three widths are needed
            'minWidth': '30px', 'width': '60px', 'maxWidth': '180px',
            'whiteSpace': 'normal'
    },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        }
    ),
    dash_table.DataTable(
        id='pricing-table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        fixed_rows={'headers': True, 'data': 0},
        editable=True,
        column_selectable="multi",
        row_selectable="multi",
        # selected_columns=[],
        # selected_rows=[],
        # page_action="native",
        # page_current=0,
        page_size=8,
        export_format='xlsx',
        export_headers='display',
        style_table={'overflowX': 'auto'},
        style_cell={
            'height': 'auto',
            # all three widths are needed
            'minWidth': '30px', 'width': '60px', 'maxWidth': '180px',
            'whiteSpace': 'normal'
        }
    ),

])
# Load data in-memory: type session
@app.callback(Output('memory-output', 'data'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))
def update_output(list_of_contents, list_of_names):
    if list_of_contents is not None:
        for c, n in zip(list_of_contents, list_of_names):
            children = parse_contents(c, n)
        return children

@app.callback(Output('intermediate-value', 'children'),
              Input('memory-output', 'data'),
              Input('memory-days', 'value'),
              Input('memory-acriss', 'value'))
def intermediate_table(memory_data, days_value, acriss_value):
    if memory_data is None:
        raise PreventUpdate
    memory_table = pd.read_json(memory_data, orient='split')
    memory_table = memory_table[(memory_table.Acriss == acriss_value) & (memory_table.Days == days_value)]
    return memory_table.to_json(date_format='iso', orient='split')

@app.callback(Output('graph', 'figure'), Input('intermediate-value', 'children'))
def update_graph(jsonified_cleaned_data):
    if jsonified_cleaned_data is None:
        raise PreventUpdate
    else:
        dff = pd.read_json(jsonified_cleaned_data, orient='split')
        figure = create_figure(dff)
        return figure


if __name__ == '__main__':
    app.run_server(debug=True)

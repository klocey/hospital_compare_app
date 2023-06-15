import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash import dash_table

import pandas as pd
import plotly
import plotly.graph_objects as go
import plotly.express as px
import warnings
import sys
import re
import csv
import math
import random
import timeit

import urllib
import numpy as np
import statsmodels.api as sm
from scipy import stats
from sklearn.preprocessing import PolynomialFeatures
from statsmodels.stats.outliers_influence import summary_table

px.set_mapbox_access_token('pk.eyJ1Ijoia2xvY2V5IiwiYSI6ImNrYm9uaWhoYjI0ZDcycW56ZWExODRmYzcifQ.Mb27BYst186G4r5fjju6Pw')

#########################################################################################
################################# CONFIG APP ############################################
#########################################################################################

FONT_AWESOME = "https://use.fontawesome.com/releases/v5.10.2/css/all.css"

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)

external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, 
                external_stylesheets = external_stylesheets,
                #long_callback_manager = long_callback_manager,
                )

app.config.suppress_callback_exceptions = True
server = app.server

################################# LOAD DATA ##################################

gendat_df = pd.read_pickle('dataframe_data/GenDat4App.pkl')

gendat_df = gendat_df[~gendat_df['Name and Num'].isin([np.nan, float('NaN')])]
gendat_df['State'] = gendat_df['State'].replace(np.nan, 'Not given')
gendat_df['Hospital Type'] = gendat_df['Hospital Type'].replace(np.nan, 'Not given')
gendat_df['Hospital Ownership'] = gendat_df['Hospital Ownership'].replace(np.nan, 'Not given')

gendat_df.loc[gendat_df['Name and Num'] == ' HIMA SAN PABLO BAYAMON (400109)', 'Name and Num'] = 'HIMA SAN PABLO BAYAMON (400109)'
gendat_df.loc[gendat_df['Name and Num'] == ' KETCHIKAN MEDICAL CENTER (021311)', 'Name and Num'] = 'KETCHIKAN MEDICAL CENTER (021311)'
gendat_df.loc[gendat_df['Name and Num'] == '(CLOSED) CUMBERLAND RIVER HOSPITAL (441319)', 'Name and Num'] = 'CUMBERLAND RIVER HOSPITAL (441319)'
gendat_df.loc[gendat_df['Name and Num'] == '1st Medical Group (Langley AFB) (49005F)', 'Name and Num'] = 'Langley AFB (49005F)'
gendat_df.loc[gendat_df['Name and Num'] == '60th Medical Group (Travis AFB) (05015F)', 'Name and Num'] = 'Langley AFB (49005F)'
gendat_df.loc[gendat_df['Name and Num'] == '633rd Medical Group (Joint Base Langley-Eustis) (49005F)', 'Name and Num'] = 'Langley AFB (49005F)'
gendat_df.loc[gendat_df['Name and Num'] == '673rd Medical Group (Joint Base Elmendorf-Richardson) (02013F)', 'Name and Num'] = 'Elmendorf-Richardson Joint Base (02013F)'
gendat_df.loc[gendat_df['Name and Num'] == '81st Medical Group (Keesler AFB) (25039F)', 'Name and Num'] = 'Keesler AFB (25039F)'
gendat_df.loc[gendat_df['Name and Num'] == '88th Medical Group (Wright-Patterson AFB) (36006F)', 'Name and Num'] = 'Wright-Patterson AFB (36006F)'
gendat_df.loc[gendat_df['Name and Num'] == '96th Medical Group (Eglin AFB) (10021F)', 'Name and Num'] = 'Eglin AFB (10021F)'
gendat_df.loc[gendat_df['Name and Num'] == '99th Medical Group (Nellis AFB) (29001F)', 'Name and Num'] = 'Nellis AFB (29001F)'

######################## SELECTION LISTS #####################################

HOSPITALS = gendat_df['Name and Num'].tolist()
beds = gendat_df['Beds'].tolist()

states = gendat_df['State'].tolist()
htypes = gendat_df['Hospital Type'].tolist()
ctypes = gendat_df['Hospital Ownership'].tolist()
lons = gendat_df['Lon'].tolist()
lats = gendat_df['Lat'].tolist()

states = ['NaN' if x is np.nan else x for x in states]
htypes = ['NaN' if x is np.nan else x for x in htypes]
ctypes = ['NaN' if x is np.nan else x for x in ctypes]

HOSPITALS_SET = sorted(list(set(HOSPITALS)))

ddfs = "100%"

with open('dataframe_data/report_categories.csv', newline='') as csvfile:
    categories = csv.reader(csvfile, delimiter=',')
    for row in categories:
        report_categories = row
        report_categories = report_categories[1:]
        
report_categories.remove('file date')
report_categories.remove('Name and Num')
report_categories.sort()


with open('dataframe_data/sub_categories.csv', newline='') as csvfile:
    categories = csv.reader(csvfile, delimiter=',')
    for row in categories:
        sub_categories = row
sub_categories.remove('HVBP Efficiency, Fiscal Year')
sub_categories.remove('HAC, Fiscal Year')
sub_categories.remove('file date, file date')
sub_categories.sort()

url = 'https://raw.githubusercontent.com/Rush-Quality-Analytics/hospitals-data-archive/main/hospital_files/010001.csv'

main_df = pd.read_csv(url, index_col=[0], header=[0, 1])
main_df = pd.DataFrame(columns = main_df.columns)

print(main_df.shape[1], 'features')
print(len(gendat_df['Facility ID'].unique()), 'CMS numbers')
print(len(list(set(HOSPITALS))), 'hospitals')

random.seed(42)

COLORS = []
for h in HOSPITALS:
    if 'RUSH UNIVERSITY' in h:
        clr = '#167e04'
    else:
        clr = '#' + "%06x" % random.randint(0, 0xFFFFFF)
    COLORS.append(clr)
    

print(len(sub_categories), 'choosable features')

################# DASH APP CONTROL FUNCTIONS #################################

def obs_pred_rsquare(obs, pred):
    r2 = 1 - sum((obs - pred) ** 2) / sum((obs - np.mean(obs)) ** 2)
    return r2
    


def description_card1():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card1",
        children=[
            html.H5("Hospital Compare", style={
            'textAlign': 'left',
        }),
           dcc.Markdown("The Centers for Medicare & Medicaid Services offers quarterly updated data" +
                        " on the quality, safety, and value of care for thousands of US hospitals." +
                        " However, aggregating, curating, and analyzing these [publicly available" +
                        " data] (https://data.cms.gov/provider-data/archived-data/hospitals) can require substantial time and energy."
                        ),
           
           dcc.Markdown("This open-source application allows analyses of 700+ data features for 6,000+ hospitals" +
                        " for each year since 2013. Get the source code for the app" +
                        " [here] (https://github.com/Rush-Quality-Analytics/hospital_compare_app)" + 
                        " and the curated data files [here]" + 
                        " (https://github.com/Rush-Quality-Analytics/hospitals-data-archive/tree/main/MergeFacilityFiles/dataframe_data/hospitals)." +
                        " The [data dictionary] (https://data.cms.gov/provider-data/sites/default/files/data_dictionaries/HospitalCompare-DataDictionary.pdf) is also handy."),
           
        ],
    )


def generate_control_card1():
    
    """
    :return: A Div containing controls for graphs.
    """
    
    return html.Div(
        id="control-card1",
        children=[
            
            html.Br(),
            html.H5("1. Filter on the options below"),
            
            html.Div(id='Filterbeds1'),
            dcc.RangeSlider(
                id='beds1',
                min=0,
                max=2800,
                step=50,
                marks={
                        100: '100',
                        500: '500',
                        1000: '1000',
                        1500: '1500',
                        2000: '2000',
                        2500: '2500',
                    },
                value=[1, 2800],
                ),
            
            html.Br(),
            
            dbc.Button("Hospital types",
                       id="open-centered4",
                       style={
                           "background-color": "#2a8cff",
                           'width': '80%',
                               'font-size': 12,
                           'display': 'inline-block',
                           'margin-left': '10%',
                           },
                ),
            dbc.Modal(
                [dbc.ModalBody([
                                html.P("Select hospital types",style={'font-size': 16,}),
                                dcc.Dropdown(
                                    id="hospital_type1",
                                    options=[{"label": i, "value": i} for i in sorted(list(set(htypes)))],
                                    multi=True,
                                    value=sorted(list(set(htypes))),
                                    style={
                                        'font-size': 16,
                                        },
                                    ),
                                html.Br(),
                                html.Br(), 
                                ]),
                                dbc.ModalFooter(
                                dbc.Button("Save & Close", id="close-centered4", className="ml-auto", 
                                           style={'font-size': 12,})
                                ),
                        ],
                id="modal-centered4",
                is_open=False,
                centered=True,
                autoFocus=True,
                size="xl",
                keyboard=True,
                fade=True,
                backdrop=True,
                ),
            html.Br(),
            html.Br(),
            
            
            dbc.Button("Hospital ownership",
                       id="open-centered1",
                       style={
                           "background-color": "#2a8cff",
                           'width': '80%',
                               'font-size': 12,
                           'display': 'inline-block',
                           'margin-left': '10%',
                           },
                ),
            dbc.Modal(
                [dbc.ModalBody([
                                html.P("Select hospital ownership types",style={'font-size': 16,}),
                                dcc.Dropdown(
                                    id="control_type1",
                                    options=[{"label": i, "value": i} for i in sorted(list(set(ctypes)))],
                                    multi=True,
                                    value=sorted(list(set(ctypes))),
                                    style={
                                        #'width': '320px', 
                                        'font-size': 16,
                                        },
                                    ),
                                html.Br(),
                                html.Br(), 
                                ]),
                                dbc.ModalFooter(
                                dbc.Button("Save & Close", id="close-centered1", className="ml-auto",
                                           style={'font-size': 12,})
                                ),
                        ],
                id="modal-centered1",
                is_open=False,
                centered=True,
                autoFocus=True,
                size="xl",
                keyboard=True,
                fade=True,
                backdrop=True,
                ),
            html.Br(),
            html.Br(),
            
            
            dbc.Button("US states & territories",
                       id="open-centered3",
                       style={
                           "background-color": "#2a8cff",
                           'width': '80%',
                               'font-size': 12,
                           'display': 'inline-block',
                           'margin-left': '10%',
                           },
                ),
            dbc.Modal(
                [dbc.ModalBody([
                                html.P("Select a set of US states and/or territories",style={'font-size': 16,}),
                                dcc.Dropdown(
                                    id="states-select1",
                                    options=[{"label": i, "value": i} for i in sorted(list(set(states)))],
                                    multi=True,
                                    value=sorted(list(set(states))),
                                    style={
                                        'font-size': 16,
                                        }
                                ),
                                html.Br(),
                                html.Br(), 
                                ]),
                                dbc.ModalFooter(
                                dbc.Button("Save & Close", id="close-centered3", className="ml-auto", 
                                           style={'font-size': 12,})
                                ),
                        ],
                id="modal-centered3",
                is_open=False,
                centered=True,
                autoFocus=True,
                size="xl",
                keyboard=True,
                fade=True,
                backdrop=True,
                ),
            html.Br(),
            html.Br(),
            
            dbc.Button("Hospital names & numbers",
                       id="open-centered2",
                       style={
                           "background-color": "#2a8cff",
                           'width': '80%',
                               'font-size': 12,
                           'display': 'inline-block',
                           'margin-left': '10%',
                           },
                ),
            dbc.Modal(
                [dbc.ModalBody([
                                html.P("This app returns data for the hospitals you choose and for any hospitals with matching CMS numbers. Note: If you are using the web-application, do not load more than 20 hospitals at a time. Otherwise, the application may timeout.",
                                       style={'font-size': 16,}),
                                dcc.Dropdown(
                                    id="hospital-select1",
                                    options=[{"label": i, "value": i} for i in HOSPITALS_SET],
                                    multi=True,
                                    value=None,
                                    optionHeight=50,
                                    style={
                                        'font-size': 14,
                                        }
                                ),
                                html.Br(), 
                                ]),
                                dbc.ModalFooter(
                                dbc.Button("Save & Close", id="close-centered2", className="ml-auto",
                                           style={'font-size': 12,})
                                ),
                        ],
                id="modal-centered2",
                is_open=False,
                centered=True,
                autoFocus=True,
                size="xl",
                keyboard=True,
                fade=True,
                backdrop=True,
                ),
            html.Br(),
            html.Br(),
            
            html.Hr(),
            html.H5("2. Load Data",
                   style={'display': 'inline-block', 'width': '135px'},),
            
            html.I(className="fas fa-question-circle fa-lg", id="target2",
                style={'display': 'inline-block', 'width': '10%', 'color':'#99ccff'},
                ),
            dbc.Tooltip("If you add or remove any hospitals, you will need to click the button in order for your changes to take effect.", 
                        target="target2",
                style = {'font-size': 12},
                ),
            
            dbc.Button("Load or update data",
                       id="btn1",
                       style={
                           "background-color": "#2a8cff",
                           'width': '80%',
                               'font-size': 12,
                           'display': 'inline-block',
                           'margin-left': '10%',
                           },
                ),
            
            html.Br(),
            html.Br(),
            html.Hr(),
            dcc.Loading(
                id="loading-fig1",
                type="default",
                fullscreen=False,
                children=[
                    
                     html.Div(
                        [html.B("6,095 Facility IDs", style={'fontSize':16,
                                                                                         'display': 'inline-block',
                                                                                         }),
                         html.B(id="text1", style={'fontSize':16, 
                                                    'display': 'inline-block'}),
                         ],
                        id="des1",
                        className="mini_container",
                        style={
                            'width': '100%',
                            'fontSize':16,
                            'textAlign': 'center',
                            },
                        ),
                    
                    html.Button("Download data", id="download-btn",
                        style={'width': '80%',
                            'margin-left': '10%',
                            },
                        ),
                    dcc.Download(id="data-download"),
                    
                    html.Br(),
                    html.Br(),
                    ],
            ), 
        ],
    )


def generate_control_card3():
    
    """
    :return: A Div containing controls for graphs.
    """
    
    return html.Div(
        id="control-card3",
        children=[
            
            html.H5("Examine relationships between variables"),
            html.P("Select a category, feature, and scale for your x-variable. "),
            dcc.Dropdown(
                id="categories-select2",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-bottom': '0px',
                    }
            ),
            dcc.Dropdown(
                id="categories-select22",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '10px',
                    }
            ),
            
            dcc.Dropdown(
                    id='x_transform',
                    options=[{"label": i, "value": i} for i in ['linear', 'log10', 'square root']],
                    multi=False, value='linear',
                    style={'width': '120px', 
                            'font-size': 13,
                            'display': 'inline-block',
                            'border-radius': '15px',
                            'padding': '0px',
                            'margin-left': '10px',
                         },
                    ),
            
            
            html.P("Select a category, feature, and scale for your y-variable. "),
            dcc.Dropdown(
                id="categories-select2-2",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-bottom': '0px',
                    }
            ),
            dcc.Dropdown(
                id="categories-select22-2",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '10px',
                    }
            ),
            
            dcc.Dropdown(
                    id='y_transform',
                    options=[{"label": i, "value": i} for i in ['linear', 'log10', 'square root']],
                    multi=False, value='linear',
                    style={'width': '120px', 
                            'font-size': 13,
                            'display': 'inline-block',
                            'border-radius': '15px',
                            'padding': '0px',
                            'margin-left': '10px',
                         },
                    ),
            
            
        ],
        style={
            'font-size': "100%",
            'display': 'inline-block',
            },
    )


def generate_control_card4():
    
    """
    :return: A Div containing controls for graphs.
    """
    
    return html.Div(
        id="control-card4",
        children=[
            html.Hr(),
            html.Br(),
            
            dcc.Dropdown(
                id='year-1',
                value='All report years',
                placeholder='Select a report year',
                options=[{"label": i, "value": i} for i in ['All report years', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023']],
                multi=False,
                style={
                    'width': '250px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '0px',
                    }
            ),
            
            dcc.Dropdown(
                id='trendline-1',
                value=None,
                placeholder='Select a model to fit (optional)',
                style={
                    'width': '250px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '10px',
                    }
            ),
            dcc.Dropdown(
                id='hospital-select1c',
                options=[{"label": i, "value": i} for i in []],
                value=None,
                placeholder='Select a focal hospital (optional)',
                optionHeight=75,
                style={
                    'width': '350px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '15px',
                    }
            ),
            
            
            dbc.Button("Run", id="run-btn2",
                            style={'width': '250px', 
                                    'font-size': 13,
                                    "background-color": "#2a8cff",
                                    'display': 'inline-block',
                                    'border-radius': '24px',
                                    'padding': '0px',
                                    'margin-left': '35px',
                                    'verticalAlign':'top',
                                },
                            ),
            
        ],
        style={
            'font-size': "100%",
            'display': 'inline-block',
            },
    )


def generate_control_card5():
    
    """
    :return: A Div containing controls for graphs.
    """
    
    return html.Div(
        id="control-card5",
        children=[
            
            html.H5("Build rate variables and examine them across time"),
            html.P("Select a category and feature for your numerator."),
            dcc.Dropdown(
                id="categories-select3",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-bottom': '0px',
                    }
            ),
            dcc.Dropdown(
                id="categories-select33",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '10px',
                    }
            ),
            
            
            html.P("Select a category and feature for your denominator."),
            dcc.Dropdown(
                id="categories-select3-2",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-bottom': '0px',
                    }
            ),
            dcc.Dropdown(
                id="categories-select33-2",
                options=[{"label": i, "value": i} for i in report_categories],
                value=None,
                optionHeight=65,
                style={
                    'width': '400px', 
                    'font-size': 13,
                    'display': 'inline-block',
                    'border-radius': '15px',
                    'padding': '0px',
                    'margin-left': '10px',
                    }
            ),
            
        ],
        style={
            'font-size': "100%",
            'display': 'inline-block',
            },
    )


#########################################################################################
#############################   DASH APP LAYOUT   #######################################
#########################################################################################    


app.layout = html.Div([
    
    dcc.Store(id='df_tab1', storage_type='memory'),
    
    html.Div(
        id='url_ls',
        style={'display': 'none'}
        ),
    
    # Banner
    html.Div(
            style={'background-color': '#f9f9f9'},
            id="banner1",
            className="banner",
            children=[html.Img(src=app.get_asset_url("RUSH_full_color.jpg"), 
                               style={'textAlign': 'left'}),
                      html.Img(src=app.get_asset_url("plotly_logo.png"), 
                               style={'textAlign': 'right'})],

        ),
        
    # Left column
    html.Div(
            id="left-column1",
            className="three columns",
            children=[description_card1(), 
                      generate_control_card1(),
                      ],
            style={'width': '24%', 'display': 'inline-block',
                                 'border-radius': '15px',
                                 'box-shadow': '1px 1px 1px grey',
                                 'background-color': '#f0f0f0',
                                 'padding': '10px',
                                 'margin-bottom': '10px',
            },
        ),
    
    
    
    # Right column 1
    html.Div(
            id="right-column1",
            className="eight columns",
            children=[
                
                html.Div(
                    id="map1",
                    children=[
                        html.B("Map of selected hospitals"),
                        html.Hr(),
                        
                        dcc.Loading(
                            id="loading-map1",
                            type="default",
                            fullscreen=False,
                            children=[dcc.Graph(id="map_plot1"),],),
                    ],
                    style={'width': '107%',
                                 'border-radius': '15px',
                                 'box-shadow': '1px 1px 1px grey',
                                 'background-color': '#f0f0f0',
                                 'padding': '10px',
                                 'margin-bottom': '10px',
                            },
                ),
                
                
                html.Div(
                    id="data_report1",
                    children=[
                        html.H5("Examine trends across time"),
                        dcc.Dropdown(
                            id="categories-select1",
                            options=[{"label": i, "value": i} for i in report_categories],
                            value=None,
                            placeholder='Select a category',
                            optionHeight=75,
                            style={
                                'width': '350px', 
                                'font-size': 13,
                                'display': 'inline-block',
                                'border-radius': '15px',
                                'padding': '0px',
                                'margin-bottom': '0px',
                                }
                        ),
                        dcc.Dropdown(
                            id="categories-select11",
                            options=[{"label": i, "value": i} for i in report_categories],
                            value=None,
                            placeholder='Select a feature',
                            optionHeight=75,
                            style={
                                'width': '350px', 
                                'font-size': 13,
                                'display': 'inline-block',
                                'border-radius': '15px',
                                'padding': '0px',
                                'margin-left': '10px',
                                }
                        ),
                        dcc.Dropdown(
                            id='hospital-select1b',
                            options=[{"label": i, "value": i} for i in []],
                            value=None,
                            placeholder='Select a focal hospital (optional)',
                            optionHeight=75,
                            style={
                                'width': '350px', 
                                'font-size': 13,
                                'display': 'inline-block',
                                'border-radius': '15px',
                                'padding': '0px',
                                #'margin-left': '15px',
                                }
                        ),
                        
                        html.Button("Run", id="run-btn1",
                            style={'width': '350px', 
                                    'font-size': 12,
                                    'display': 'inline-block',
                                    'border-radius': '15px',
                                    'padding': '0px',
                                    'margin-left': '20px',
                                    'verticalAlign':'top',
                                },
                            ),
                        
                        html.Hr(),
                        dcc.Graph(id="data_report_plot1"),
                    ],
                    style={'width': '107%', 'display': 'inline-block',
                                 'border-radius': '15px',
                                 'box-shadow': '1px 1px 1px grey',
                                 'background-color': '#f0f0f0',
                                 'padding': '10px',
                                 'margin-bottom': '10px',
                            },
                ),
                html.Br(),
                html.Br(),
            ],
        ),
    
    # Left column
    html.Div(
            id="left-column2",
            className="eleven columns",
            children=[
                
                html.Div(
                    id="data_report2",
                    children=[
                        generate_control_card3(),
                        dcc.Graph(id="data_report_plot2"),
                        generate_control_card4(),
                        ],
                    style={
                        'width': '105%',
                        'display': 'inline-block',
                        'border-radius': '15px',
                        'box-shadow': '1px 1px 1px grey',
                        'background-color': '#f0f0f0',
                        'padding': '10px',
                        'margin-bottom': '10px',
                        'height': '810px',
                        },
                ),
                html.Br(),
                
                
                html.Div(
                    id="data_report3",
                    children=[
                        generate_control_card5(),
                        dcc.Graph(id="data_report_plot3"),
                        html.Hr(),
                        dbc.Button("Run", id="run-btn3",
                            style={'width': '250px', 
                                    'font-size': 12,
                                    "background-color": "#2a8cff",
                                    'display': 'inline-block',
                                    'border-radius': '15px',
                                    'padding': '0px',
                                    'margin-left': '0px',
                                    'verticalAlign':'top',
                                },
                            ),

                        
                        dcc.Dropdown(
                            id='hospital-select1d',
                            options=[{"label": i, "value": i} for i in []],
                            value=None,
                            placeholder='Select a focal hospital (optional)',
                            optionHeight=75,
                            style={
                                'width': '250px', 
                                'font-size': 13,
                                'display': 'inline-block',
                                'border-radius': '15px',
                                'padding': '0px',
                                'margin-left': '10px',
                                }
                        ),
                        ],
                    style={
                        'width': '105%',
                        'display': 'inline-block',
                        'border-radius': '15px',
                        'box-shadow': '1px 1px 1px grey',
                        'background-color': '#f0f0f0',
                        'padding': '10px',
                        'margin-bottom': '10px',
                        'height': '780px',
                        },
                ),
                ],
            ),

    ],
)

  
##############################   Callbacks   ############################################
#########################################################################################

@app.callback(
    Output("modal-centered1", "is_open"),
    [Input("open-centered1", "n_clicks"), Input("close-centered1", "n_clicks")],
    [State("modal-centered1", "is_open")],
)
def toggle_modal1(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("modal-centered2", "is_open"),
    [Input("open-centered2", "n_clicks"), Input("close-centered2", "n_clicks")],
    [State("modal-centered2", "is_open")],
)
def toggle_modal2(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output("modal-centered3", "is_open"),
    [Input("open-centered3", "n_clicks"), Input("close-centered3", "n_clicks")],
    [State("modal-centered3", "is_open")],
)
def toggle_modal3(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open

@app.callback(
    Output("modal-centered4", "is_open"),
    [Input("open-centered4", "n_clicks"), Input("close-centered4", "n_clicks")],
    [State("modal-centered4", "is_open")],
)
def toggle_modal1(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback( # Updated number of beds text
    Output('Filterbeds1', 'children'),
    [
     Input('beds1', 'value'),
     ],
    )
def update_output1(value):
    return 'Number of beds: {}'.format(value)


@app.callback( # Update available sub_categories
    Output('categories-select11', 'options'),
    [
     Input('categories-select1', 'value'),
     Input('df_tab1', "data"),
     ],
    )
def update_output3(value, df):
    
    df2 = main_df.iloc[:, (main_df.columns.get_level_values(0)==value)]
    sub_cat = df2.columns.get_level_values(1).tolist()
    
    try:
        sub_cat.remove('Fiscal Year')
    except:
        pass
    try:
        sub_cat.remove('file date')
    except:
        pass
    
    del df2
    
    if df is not None:
        
        df = pd.read_json(df)
        df.dropna(axis=1, how='all', inplace=True)
        cols1 = list(df)
        cols2 = []
        for c in cols1:
            s = c.split("', ")[-1]
            s = s[1:-2]
            cols2.append(s)
            
        sub_categories = []
        for c in sub_cat:
            if c in cols2:
                sub_categories.append(c)
    
    else:
        sub_categories = sub_cat
    
    try:
        sub_categories.remove('Fiscal Year')
    except:
        pass
    try:
        sub_categories.remove('file date')
    except:
        pass
    
    return [{"label": i, "value": i} for i in sub_categories]


@app.callback( # Select sub-category
    Output('categories-select11', 'value'),
    [
     Input('categories-select11', 'options'),
     ],
    )
def update_output4(available_options):
    try:
        return available_options[0]['value']
    except:
        return 'NUMBER OF BEDS'

    
    
@app.callback(
    Output("hospital-select1", 'options'),
    [
     Input('beds1', 'value'),
     Input('states-select1', 'value'),
     Input('hospital_type1', 'value'),
     Input('control_type1', 'value'),
     ],
    )
def update_hospitals(bed_range, states_vals, htype_vals, ctype_vals):
    
    low, high = bed_range
    hospitals = []
    for i, h in enumerate(HOSPITALS):
        b = beds[i]
        s = states[i]
        ht = htypes[i]
        ct = ctypes[i]
        if b > low and b < high:
            if s in states_vals and ht in htype_vals:
                if ct in ctype_vals:
                    hospitals.append(h)
            
    hospitals = sorted(list(set(hospitals)))
    return [{"label": i, "value": i} for i in hospitals]


@app.callback(
    [Output('url_ls', "children"),
     Output('hospital-select1b', 'options'),
     Output('hospital-select1c', 'options'),
     Output('hospital-select1d', 'options'),
     ],
    [Input('btn1', 'n_clicks')],
    [State("hospital-select1", "value"),
     State("hospital-select1", "options"),],
    )
def get_urls(btn1, hospitals, hospital_options):
    
    options = []
    for h in hospital_options:
        h1 = list(h.values())
        options.append(h1[0])
    
    if hospitals is None or hospitals == []:
        ls1 = [{"label": i, "value": i} for i in ['No focal hospital']]
        return None, ls1, ls1, ls1
    
    if isinstance(hospitals, str) == True:
        hospitals = [hospitals]
    
    hospitals = list(set(hospitals) & set(options))
    
    if hospitals == []:
        ls1 = [{"label": i, "value": i} for i in ['No focal hospital']]
        return None, ls1, ls1, ls1
    
    url_ls = []
    for i, val in enumerate(hospitals):
        
        val = val[-9:]
        prvdr = re.sub('\ |\?|\.|\!|\/|\;|\:', '', val)
        prvdr = prvdr[prvdr.find("(")+1:prvdr.find(")")]
        
        url = 'https://raw.githubusercontent.com/Rush-Quality-Analytics/hospitals-data-archive/main/hospital_files/' + prvdr + '.csv'
        url_ls.append(url)
    
    #txt = ', ' + str(len(hospitals)) + ' selected'
    hospitals = ['No focal hospital'] + hospitals
    ls1 = [{"label": i, "value": i} for i in hospitals]
    
    return url_ls, ls1, ls1, ls1
    

@app.callback(
    [Output('df_tab1', "data"),
     Output("text1", 'children'),],
    [
     Input('url_ls', 'children'),
     Input('df_tab1', "data"),
     ],
    )
def update_df1_tab1(urls, df):
    
    if urls is None or urls is []:
        return None, ""
    
    elif df is None:
        
        for i, url in enumerate(urls):
            
            tdf = pd.read_csv(url, header=[0,1], index_col=[0])
            tdf[('data url', 'data url')] = [url] * tdf.shape[0]
            
            if i == 0:
                df = tdf.copy(deep=True)
            else:
                df = pd.concat([df, tdf]) 
        
        df.dropna(axis=1, how='all', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        df = df[~df[('Name and Num', 'Name and Num')].isin([np.nan, float('NaN'), None])]
        df = df.replace({None: np.nan})
        df = df.replace({'Not Available': np.nan})
        
        num_h = len(df[('Facility ID', 'Facility ID')].unique())
        return df.to_json(), ", " + str(num_h) + " Loaded"

    else:
        df = pd.read_json(df)
        
        df = df[df["('data url', 'data url')"].isin(urls)]
        df_urls = df["('data url', 'data url')"].unique()
        
        url_ls = list(set(urls)-set(df_urls))
        
        if len(url_ls) > 0:
            df2 = 0
            for i, url in enumerate(url_ls):
                
                tdf = pd.read_csv(url, header=[0,1], index_col=[0])
                tdf[('data url', 'data url')] = [url] * tdf.shape[0]
                
                if i == 0:
                    df2 = tdf.copy(deep=True)
                else:
                    df2 = pd.concat([df2, tdf]) 
            
            df2.reset_index(inplace=True)
            df2 = df2.to_json()
            df2 = pd.read_json(df2)
            df = pd.concat([df, df2])
            del df2
        
        df.dropna(axis=1, how='all', inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        x = "('Name and Num', 'Name and Num')"
        df = df[~df[x].isin([np.nan, float('NaN'), None])]
        df = df.replace({None: np.nan})
        df = df.replace({'Not Available': np.nan})
        
        num_h = len(df["('Name and Num', 'Name and Num')"].unique())
        
        return df.to_json(), ", " + str(num_h) + " Loaded"


@app.callback(
     Output("map_plot1", "figure"),
     [
     Input("df_tab1", "data"),
     [State("hospital-select1", "value")],
     ],
    )
def update_map_plot1(df, h):
    
    figure = go.Figure()
    figure.add_trace(go.Scattermapbox(
    ),
    )
    
    figure.update_layout(
        autosize=True,
        hovermode='closest',
        mapbox=dict(
            accesstoken='pk.eyJ1Ijoia2xvY2V5IiwiYSI6ImNrYm9uaWhoYjI0ZDcycW56ZWExODRmYzcifQ.Mb27BYst186G4r5fjju6Pw',
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=39,
                lon=-98
        ),
        pitch=20,
        zoom=3,
        style='light',
        )
    )

    figure.update_layout(
        height=300, 
        margin={"r":0,"t":0,"l":0,"b":0},
        )

    if df is None:
        return figure#, ', 0 Selected'
    
    df = pd.read_json(df)
    
    h = df["('Name and Num', 'Name and Num')"].unique()
    
    tdf = gendat_df[gendat_df['Name and Num'].isin(h)]
    
    figure = go.Figure()
    figure.add_trace(go.Scattermapbox(
        lon = tdf['Lon'],
        lat = tdf['Lat'],
        text = tdf['Name and Num'],
               
        marker = dict(
            size = 10,
            color = 'rgb(0, 170, 255)',
            opacity = 0.8,

        ),
        ),
        )
        
    figure.update_layout(
        autosize=True,
        hovermode='closest',
        mapbox=dict(
            accesstoken='pk.eyJ1Ijoia2xvY2V5IiwiYSI6ImNrYm9uaWhoYjI0ZDcycW56ZWExODRmYzcifQ.Mb27BYst186G4r5fjju6Pw',
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=39,
                lon=-98
        ),
        pitch=20,
        zoom=3,
        style='light',
        )
    )

    figure.update_layout(
        height=300, 
        margin={"r":0,"t":0,"l":0,"b":0},
        )
    
    return figure



@app.callback(
    Output("data-download", "data"),
    Input("download-btn", "n_clicks"),
    [State('df_tab1', "data")],
    prevent_initial_call=True,
)
def update_download(n_clicks, df):
    
    if df is None:
        return dcc.send_data_frame(main_df.to_csv, "data.csv")
            
    df = pd.read_json(df)
    if df.shape[0] == 0:
        return dcc.send_data_frame(main_df.to_csv, "data.csv")
        
    else:
        tdf = main_df.copy(deep=True)
        cols = list(df)
        
        for i, c in enumerate(cols):
            vals = df[c].tolist()
            
            c = list(eval(c))
            tdf[(c[0], c[1])] = vals
    
    return dcc.send_data_frame(tdf.to_csv, "data.csv")
    

    

@app.callback( # Update available sub_categories
    Output('categories-select22', 'options'),
    [
     Input('categories-select2', 'value'),
     Input('df_tab1', 'data'),
     ],
    )
def update_output7(value, df):
    
    df2 = main_df.iloc[:, (main_df.columns.get_level_values(0)==value)]
    sub_cat = df2.columns.get_level_values(1).tolist()
    
    try:
        sub_cat.remove('Fiscal Year')
    except:
        pass
    try:
        sub_cat.remove('file date')
    except:
        pass
    
    del df2
    
    if df is not None:
        df = pd.read_json(df)
        df.dropna(how='all', axis=1, inplace=True)
        
        cols1 = list(df)
        cols2 = []
        for c in cols1:
            s = c.split("', ")[-1]
            s = s[1:-2]
            cols2.append(s)
            
        sub_categories = []
        for c in sub_cat:
            if c in cols2:
                sub_categories.append(c)
    else:
        sub_categories = sub_cat
    
    try:
        sub_categories.remove('Fiscal Year')
    except:
        pass
    try:
        sub_categories.remove('file date')
    except:
        pass
    
    return [{"label": i, "value": i} for i in sub_categories]



@app.callback( # Select sub-category
    Output('categories-select22', 'value'),
    [
     Input('categories-select22', 'options'),
     ],
    )
def update_output8(available_options):
    try:
        return available_options[0]['value']
    except:
        return 'NUMBER OF BEDS'

    
    
@app.callback( # Update available sub_categories
    Output('categories-select22-2', 'options'),
    [
     Input('categories-select2-2', 'value'),
     Input('df_tab1', "data"),
     ],
    )
def update_output9(value, df):

    df2 = main_df.iloc[:, (main_df.columns.get_level_values(0)==value)]
    sub_cat = df2.columns.get_level_values(1).tolist()
    
    try:
        sub_cat.remove('Fiscal Year')
    except:
        pass
    try:
        sub_cat.remove('file date')
    except:
        pass
    
    del df2
    
    if df is not None:
        df = pd.read_json(df)
        df.dropna(how='all', axis=1, inplace=True)
        
        cols1 = list(df)
        cols2 = []
        for c in cols1:
            s = c.split("', ")[-1]
            s = s[1:-2]
            cols2.append(s)
            
        sub_categories = []
        for c in sub_cat:
            if c in cols2:
                sub_categories.append(c)
    else:
        sub_categories = sub_cat
    
    try:
        sub_categories.remove('Fiscal Year')
    except:
        pass
    try:
        sub_categories.remove('file date')
    except:
        pass
    
    return [{"label": i, "value": i} for i in sub_categories]



@app.callback( # Select sub-category
    Output('categories-select22-2', 'value'),
    [
     Input('categories-select22-2', 'options'),
     ],
    )
def update_output10(available_options):
    try:
        return available_options[0]['value']
    except:
        return 'NUMBER OF BEDS'



@app.callback( # Update available sub_categories
    Output('categories-select33', 'options'),
    [
     Input('categories-select3', 'value'),
     Input('df_tab1', "data"),
     ],
    )
def update_output11(value, df):
    
    df2 = main_df.iloc[:, (main_df.columns.get_level_values(0)==value)]
    sub_cat = df2.columns.get_level_values(1).tolist()
    
    try:
        sub_cat.remove('Fiscal Year')
    except:
        pass
    try:
        sub_cat.remove('file date')
    except:
        pass
    
    del df2
    
    if df is not None:
        df = pd.read_json(df)
        df.dropna(how='all', axis=1, inplace=True)
        
        cols1 = list(df)
        cols2 = []
        for c in cols1:
            s = c.split("', ")[-1]
            s = s[1:-2]
            cols2.append(s)
            
        sub_categories = []
        for c in sub_cat:
            if c in cols2:
                sub_categories.append(c)
    else:
        sub_categories = sub_cat
    
    try:
        sub_categories.remove('Fiscal Year')
    except:
        pass
    try:
        sub_categories.remove('file date')
    except:
        pass
    
    return [{"label": i, "value": i} for i in sub_cat]


@app.callback( # Select sub-category
    Output('categories-select33', 'value'),
    [
     Input('categories-select33', 'options'),
     ],
    )
def update_output12(available_options):
    try:
        return available_options[0]['value']
    except:
        return 'NUMBER OF BEDS'    
    


@app.callback( # Update available sub_categories
    Output('categories-select33-2', 'options'),
    [
     Input('categories-select3-2', 'value'),
     Input('df_tab1', "data"),
     ],
    )
def update_output13(value, df):
    
    df2 = main_df.iloc[:, (main_df.columns.get_level_values(0)==value)]
    sub_cat = df2.columns.get_level_values(1).tolist()
    
    try:
        sub_cat.remove('Fiscal Year')
    except:
        pass
    try:
        sub_cat.remove('file date')
    except:
        pass
    
    del df2
    
    if df is not None:
        df = pd.read_json(df)
        df.dropna(how='all', axis=1, inplace=True)
        
        cols1 = list(df)
        cols2 = []
        for c in cols1:
            s = c.split("', ")[-1]
            s = s[1:-2]
            cols2.append(s)
            
        sub_categories = []
        for c in sub_cat:
            if c in cols2:
                sub_categories.append(c)
    else:
        sub_categories = sub_cat
    
    try:
        sub_categories.remove('Fiscal Year')
    except:
        pass
    try:
        sub_categories.remove('file date')
    except:
        pass
    
    return [{"label": i, "value": i} for i in sub_cat]



@app.callback( # Select sub-category
    Output('categories-select33-2', 'value'),
    [
     Input('categories-select33-2', 'options'),
     ],
    )
def update_output14(available_options):
    try:
        return available_options[0]['value']
    except:
        return 'NUMBER OF BEDS'
  

@app.callback( # Update Line plot
    Output("data_report_plot1", "figure"),
    [Input("run-btn1", "n_clicks")],
    [State('df_tab1', "data"),
     State('categories-select1', 'value'),
     State('categories-select11', 'value'),
     State('hospital-select1b', 'value'),
     ],
    )
def update_data_report_plot1(n_clicks, df, var1, var2, focal_h):
    
    if df is None or var1 is None or var1 is None:
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))

        fig.update_yaxes(title_font=dict(size=14, 
                                         #family='sans-serif', 
                                         color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                         #family='sans-serif', 
                                         color="rgb(38, 38, 38)"))

        fig.update_layout(title_font=dict(size=14, 
                          color="rgb(38, 38, 38)", 
                          ),
                          showlegend=True,
                          height=439,
                          margin=dict(l=100, r=10, b=10, t=10),
                          paper_bgcolor="#f0f0f0",
                          plot_bgcolor="#f0f0f0",
                          )
        return fig
         
    
    df = pd.read_json(df)
    if df.shape[0] == 0:
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))

        fig.update_yaxes(title_font=dict(size=14, 
                                         #family='sans-serif', 
                                         color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                         #family='sans-serif', 
                                         color="rgb(38, 38, 38)"))

        fig.update_layout(title_font=dict(size=14, 
                          color="rgb(38, 38, 38)", 
                          ),
                          showlegend=True,
                          height=439,
                          margin=dict(l=100, r=10, b=10, t=10),
                          paper_bgcolor="#f0f0f0",
                          plot_bgcolor="#f0f0f0",
                          )
        return fig
        
    
    fig_data = []
    
    x = "('Name and Num', 'Name and Num')"
    df = df[~df[x].isin([np.nan, float('NaN'), None])]
    
    str_ = "('" + var1 + "', '" + var2 + "')"
    df[str_] = pd.to_numeric(df[str_], errors='coerce')
    
    hospitals = sorted(df[x].unique())
    
    try:
        hospitals.remove(focal_h)
        hospitals.append(focal_h)
    except:
        pass
    
    for i, hospital in enumerate(hospitals):
            
        sub_df = df[df[x] == hospital]
        sub_df.sort_values(by=["('file date', 'file date')"], ascending=True, inplace=True)
        dates = sub_df["('file date', 'file date')"]
        
        str_ = "('" + var1 + "', '" + var2 + "')"
        column = [col for col in sub_df.columns if col.endswith(str_)]  
        
        if len(column) == 0:
            fig = go.Figure(data=go.Scatter(x = [0], y = [0]))

            fig.update_yaxes(title_font=dict(size=14, color="rgb(38, 38, 38)"))
            fig.update_xaxes(title_font=dict(size=14, color="rgb(38, 38, 38)"))

            fig.update_layout(title_font=dict(size=14, 
                              color="rgb(38, 38, 38)"),
                              showlegend=True,
                              height=452,
                              margin=dict(l=100, r=10, b=10, t=10),
                              paper_bgcolor="#f0f0f0",
                              plot_bgcolor="#f0f0f0")
            
            return fig
        
        column = column[0]
        obs_y = sub_df[column].tolist()     
        hospital = str(hospital)
        
        hi = HOSPITALS.index(hospital)
        if hospital == focal_h or focal_h == 'No focal hospital' or focal_h not in hospitals:
            clr = COLORS[hi]
        else:
            clr = '#cccccc'
        
        if len(hospital) > 30:
            hospital = hospital[0:20] + ' ... ' + hospital[-8:]
        
        fig_data.append(
                    go.Scatter(
                        x=dates,
                        y=obs_y,
                        name=hospital,
                        mode='lines+markers',
                        marker=dict(color=clr),
                    )
                )
        
        
        
    str_ = "('" + var1 + "', '" + var2 + "')"
    tdf = pd.DataFrame(columns=['mean', 'median', 'std'])
    tdf['mean'] = df.groupby("('file date', 'file date')")[str_].mean()
    tdf['median'] = df.groupby("('file date', 'file date')")[str_].median()
    tdf['std'] = df.groupby("('file date', 'file date')")[str_].std()
    tdf['file_date'] = tdf.index
    
    fig_data.append(
                    go.Scatter(
                        x=tdf['file_date'],
                        y=tdf['mean'],
                        name='Mean',
                        mode='lines',
                        #marker=dict(color='#ff0000'),
                        line = dict(color='#ff0000', width=2),
                    )
            )
    
    fig_data.append(
                    go.Scatter(
                        x=tdf['file_date'],
                        y=tdf['mean'] + tdf['std'],
                        name='mean + 1 std',
                        mode='lines',
                        line = dict(color='#ff6666', width=2, dash='dash'),
                    )
            )
    
    fig_data.append(
                    go.Scatter(
                        x=tdf['file_date'],
                        y=tdf['mean'] - tdf['std'],
                        name='mean - 1 std',
                        mode='lines',
                        line = dict(color='#ff6666', width=2, dash='dash'),
                    )
            )
    
        
        
    txt_ = '<b>' + var1 + '<b>'
    var2b = re.sub("\(.*?\)|\[.*?\]","", var2)
        
    if len(var2b) > 40:
        var_ls = []
        for j in range(0, len(var2b), 40):
            var_ls.append(var2b[j : j + 40])
            
        for j in var_ls:
            txt_ = txt_ + '<br>' + j 
    else:
        txt_ = txt_ + '<br>' + var2b 
            
    figure = go.Figure(
            data=fig_data,
            layout=go.Layout(
                transition = {'duration': 500},
                xaxis=dict(
                    title=dict(
                        text="<b>Date</b>",
                        font=dict(
                            family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                            " Helvetica, Arial, sans-serif",
                            size=18,
                        ),
                    ),
                    #rangemode="tozero",
                    zeroline=False,
                    showticklabels=True,
                ),
                
                yaxis=dict(
                    title=dict(
                        text=txt_,
                        font=dict(
                            family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                            " Helvetica, Arial, sans-serif",
                            size=14,
                            
                        ),
                    ),
                    #rangemode="tozero",
                    zeroline=False,
                    showticklabels=True,
                    
                ),
                
                margin=dict(l=100, r=30, b=10, t=40),
                showlegend=True,
                height=439,
                paper_bgcolor="#f0f0f0",
                plot_bgcolor="#f0f0f0",
            ),
    )
        
    figure.update_layout(
            legend=dict(
                traceorder="normal",
                font=dict(
                    size=10,
                    color="rgb(38, 38, 38)"
                ),
                
            )
    )    
    
    
    del df
    del hospitals
    del fig_data
    del dates
    del x
    return figure


@app.callback( # Update Line plot
    Output("data_report_plot2", "figure"),
    [Input("run-btn2", "n_clicks")],
    [State('categories-select2', 'value'),
     State('categories-select22', 'value'),
     State('categories-select2-2', 'value'),
     State('categories-select22-2', 'value'),
     State('x_transform', 'value'),
     State('y_transform', 'value'),
     State('trendline-1', 'value'),
     State('hospital-select1c', 'value'),
     State("df_tab1", "data"),
     State('year-1', 'value')],
    )
def update_data_report_plot2(n_clicks, xvar1, xvar2, yvar1, yvar2, xscale, yscale, model, focal_h, df, yr1):
    
    if df is None or xvar1 is None or xvar2 is None or yvar1 is None or yvar2 is None or yvar2 == 'NUMBER OF BEDS':
            
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))
        
        fig.update_yaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_layout(title_font=dict(size=14, 
                      color="rgb(38, 38, 38)", 
                      ),
                      showlegend=True,
                      margin=dict(l=100, r=10, b=10, t=10),
                      paper_bgcolor="#f0f0f0",
                      plot_bgcolor="#f0f0f0",
                      )
        
        return fig
            
    
    df = pd.read_json(df)
    
    if yr1 == 'All report years':
        pass
    else:
        df = df[df["('file_year', 'file_year')"] == int(yr1)]
    
    fig_data = []
    
    x = "('Name and Num', 'Name and Num')"
    df = df[~df[x].isin([np.nan, float('NaN'), None])]
    df = df.replace({None: np.nan})
    df = df.replace({'Not Available': np.nan})
    
    str_1 = xvar1 + "', '" + xvar2 + "')"
    str_2 = yvar1 + "', '" + yvar2 + "')"
    
    df[str_1] = pd.to_numeric(df["('" + str_1], errors='coerce')
    df[str_2] = pd.to_numeric(df["('" + str_2], errors='coerce')
    
    column1 = [col for col in df.columns if col.endswith(str_1)]
    column2 = [col for col in df.columns if col.endswith(str_2)]
    
    if len(column1) == 0 or len(column2) == 0:
        
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))
        
        fig.update_yaxes(title_font=dict(size=14, 
                                     color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                     color="rgb(38, 38, 38)"))
        fig.update_layout(title_font=dict(size=14, 
                      color="rgb(38, 38, 38)", 
                      ),
                      showlegend=True,
                      margin=dict(l=100, r=10, b=10, t=10),
                      paper_bgcolor="#f0f0f0",
                      plot_bgcolor="#f0f0f0",
                      )
        return fig
    
    
    hospitals = sorted(df["('Name and Num', 'Name and Num')"].unique())
    
    try:
        hospitals.remove(focal_h)
        hospitals.append(focal_h)
    except:
        pass
    
    fig_data = []
    for i, hospital in enumerate(hospitals):
        
        tdf = df[df["('Name and Num', 'Name and Num')"] == hospital]
                
        column1 = [col for col in tdf.columns if col.endswith(str_1)]
        column2 = [col for col in tdf.columns if col.endswith(str_2)]
        
        column1 = column1[0]
        x = tdf[column1].tolist()
        
        column2 = column2[0]
        y = tdf[column2].tolist()
        
        dates = tdf["('file date', 'file date')"]
        
        names = tdf["('Name and Num', 'Name and Num')"]
        
        text = names + '<br>' + dates.astype(str)
        
        x, y, dates, names = map(list, zip(*sorted(zip(x, y, dates, names), reverse=False)))
        
        # 1. linear-linear
        
        # 2. 
        if xscale == 'log10' and yscale == 'log10':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] > 0 and y[i] > 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.log10(x2).tolist()
            y = np.log10(y2).tolist()
            dates = list(dates2)
        
        # 3.
        elif xscale == 'square root' and yscale == 'square root':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] >= 0 and y[i] >= 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.sqrt(x2).tolist()
            y = np.sqrt(y2).tolist()
            dates = list(dates2)

        # 4.
        elif xscale == 'log10' and yscale == 'linear':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] > 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.log10(x2).tolist()
            y = list(y2)
            dates = list(dates2)
        
        # 5.
        elif yscale == 'log10' and xscale == 'linear':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if y[i] > 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = list(x2)
            y = np.log10(y2)
            dates = list(dates2)
        
        # 6.
        elif xscale == 'square root' and yscale == 'linear':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] >= 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.sqrt(x2).tolist()
            y = list(y2)
            dates = list(dates2)
        
        # 7.
        elif yscale == 'square root' and xscale == 'linear':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if y[i] >= 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = list(x2)
            y = np.sqrt(y2).tolist()
            dates = list(dates2)
            
        # 8. 
        elif xscale == 'log10' and yscale == 'square root':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] > 0 and y[i] >= 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.log10(x2).tolist()
            y = np.sqrt(y2).tolist()
            dates = list(dates2)
          
        # 9.
        elif yscale == 'log10' and xscale == 'square root':
            x2, y2, dates2 = [], [], []
            for i, val in enumerate(x):
                if x[i] >= 0 and y[i] > 0:
                    x2.append(x[i])
                    y2.append(y[i])
                    dates2.append(dates[i])
                    
            x = np.sqrt(x2).tolist()
            y = np.log10(y2).tolist()
            dates = list(dates2)
            
            
        hi = HOSPITALS.index(hospital)
        if hospital == focal_h or focal_h == 'No focal hospital' or focal_h not in hospitals:
            clr = COLORS[hi]
        else:
            clr = '#b3b3b3'
        
        if len(hospital) > 30:
            hospital = hospital[0:20] + ' ... ' + hospital[-8:]
        
        fig_data.append(
                    go.Scatter(
                        x=x,
                        y=y,
                        name=hospital,
                        mode='markers',
                        marker=dict(color=clr),
                        text= text,
                    )
                )
    
    column1 = [col for col in df.columns if col.endswith(str_1)]
    column2 = [col for col in df.columns if col.endswith(str_2)]
    
    dates = df["('file date', 'file date')"].tolist()
    
    column1 = column1[0]
    x = df[column1].tolist()
    
    column2 = column2[0]
    y = df[column2].tolist()
    
    # 1. linear-linear
    
    # 2. 
    if xscale == 'log10' and yscale == 'log10':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] > 0 and y[i] > 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.log10(x2).tolist()
        y = np.log10(y2).tolist()
        dates = list(dates2)
    
    # 3.
    elif xscale == 'square root' and yscale == 'square root':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] >= 0 and y[i] >= 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.sqrt(x2).tolist()
        y = np.sqrt(y2).tolist()
        dates = list(dates2)

    # 4.
    elif xscale == 'log10' and yscale == 'linear':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] > 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.log10(x2).tolist()
        y = list(y2)
        dates = list(dates2)
    
    # 5.
    elif yscale == 'log10' and xscale == 'linear':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if y[i] > 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = list(x2)
        y = np.log10(y2)
        dates = list(dates2)
    
    # 6.
    elif xscale == 'square root' and yscale == 'linear':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] >= 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.sqrt(x2).tolist()
        y = list(y2)
        dates = list(dates2)
    
    # 7.
    elif yscale == 'square root' and xscale == 'linear':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if y[i] >= 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = list(x2)
        y = np.sqrt(y2).tolist()
        dates = list(dates2)
        
    # 8. 
    elif xscale == 'log10' and yscale == 'square root':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] > 0 and y[i] >= 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.log10(x2).tolist()
        y = np.sqrt(y2).tolist()
        dates = list(dates2)
      
    # 9.
    elif yscale == 'log10' and xscale == 'square root':
        x2, y2, dates2 = [], [], []
        for i, val in enumerate(x):
            if x[i] >= 0 and y[i] > 0:
                x2.append(x[i])
                y2.append(y[i])
                dates2.append(dates[i])
                
        x = np.sqrt(x2).tolist()
        y = np.log10(y2).tolist()
        dates = list(dates2)
        
        
    tdf = pd.DataFrame(columns = ['x', 'y'])
    tdf['x'] = x
    tdf['y'] = y
    tdf['dates'] = dates
    tdf.dropna(how='any', inplace=True)
    tdf.sort_values(by='x', inplace=True, ascending=True)
    
    x = tdf['x']
    y = tdf['y']
    dates = tdf['dates'].tolist()
        
    ty = []
    r2 = ''
        
    if x.tolist() == [] or y.tolist() == []:
        slope, intercept, r_value, p_value, std_err = np.nan, np.nan, np.nan, np.nan, np.nan
        r2 = np.nan
    
        
    tdf.replace([np.inf, -np.inf], np.nan, inplace=True)
    tdf.dropna(how='any', inplace=True)
        
    x_o = tdf['x'].values.tolist()
    y_o = tdf['y'].values.tolist()
    
    if x_o is None or y_o is None or len(x_o) == 0 or len(y_o) == 0:
        
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))
        
        fig.update_yaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_layout(title_font=dict(size=14, 
                      color="rgb(38, 38, 38)", 
                      ),
                      showlegend=True,
                      margin=dict(l=100, r=10, b=10, t=10),
                      paper_bgcolor="#f0f0f0",
                      plot_bgcolor="#f0f0f0",
                      )
        
        return fig
        
    x_o, y_o = zip(*sorted(zip(x_o, y_o)))
    
    x_o = np.array(x_o)
    y_o = np.array(y_o)
    
    #Create single dimension
    x = x_o[:, np.newaxis]
    y = y_o[:, np.newaxis]

    inds = x.ravel().argsort()  # Sort x values and get index
    x = x.ravel()[inds].reshape(-1, 1)
    y = y[inds] #Sort y according to x sorted index
    
    d = int()
    if model == 'linear': d = 1
    elif model == 'quadratic': d = 2
    elif model == 'cubic': d = 3
    else: d = 1
    
    polynomial_features = PolynomialFeatures(degree = d)
    xp = polynomial_features.fit_transform(x)
        
    model = sm.OLS(y, xp).fit()
    ypred = model.predict(xp)
    ypred = ypred.tolist()
    
    poly_coefs = model.params[1:].tolist()
    poly_coefs.reverse()
    
    poly_exponents = list(range(1, len(poly_coefs)+1))
    poly_exponents.reverse()
    
    
    eqn = 'y = '
    for i, p in enumerate(poly_coefs):
        exp = poly_exponents[i]
        
        if exp == 1:
            exp = 'x'
        elif exp == 2:
            exp = 'x²'
        elif exp == 3:
            exp = 'x³'
        
        if i == 0:
            p = round(p, 4)
            eqn = eqn + str(p) + exp
            
        else:
            if p >= 0:
                p = round(p, 4)
                eqn = eqn + ' + ' + str(p) + exp
            else:
                p = round(p, 4)
                eqn = eqn + ' - ' + str(np.abs(p)) + exp
    
    b = model.params[0]
    if b >= 0:
        b = round(b, 4)
        eqn = eqn + ' + ' + str(b)
    else:
        b = round(b, 4)
        eqn = eqn + ' - ' + str(np.abs(b))
        
    r2 = model.rsquared_adj
    if r2 < 0:
        r2 = 0
        
    #r2_obs_pred = obs_pred_rsquare(np.array(y_o), np.array(ypred))
    #if r2_obs_pred < 0:
    #    r2_obs_pred = 0
    #r2_obs_pred = str(round(r2_obs_pred, 2))
    
    #print(model.summary, '\n')
    #print('mean rate:', np.nanmean(np.array(y_o)/np.array(x_o)))
    #print('SD:', np.nanstd(np.array(y_o)/np.array(x_o)))
    #print('SE:', stats.sem(np.array(y_o)/np.array(x_o)), '\n')
    
    st, data, ss2 = summary_table(model, alpha=0.05)
    predict_mean_ci_low, predict_mean_ci_upp = data[:, 4:6].T
    predict_ci_low, predict_ci_upp = data[:, 6:8].T
    
    outlier_y = []
    outlier_x = []
    nonoutlier_y = []
    nonoutlier_x = []
    for i, yi in enumerate(y_o):
        if yi > predict_ci_upp[i] or yi < predict_ci_low[i]:
            outlier_y.append(yi)
            outlier_x.append(x_o[i])
        else:
            nonoutlier_y.append(yi)
            nonoutlier_x.append(x_o[i])
            
    clr = "#3399ff"
    
    fig_data.append(go.Scatter(
                        x = nonoutlier_x,
                        y = nonoutlier_y,
                        name = 'Non-outliers',
                        mode = "markers",
                        opacity = 1.0,
                        marker = dict(size=10,
                                    color=clr,
                                    symbol="diamond-open",
                                    )
                    )
                )
                
    fig_data.append(go.Scatter(
            x = outlier_x,
            y = outlier_y,
            name = 'Outliers',
            mode = "markers",
            opacity = 1.0,
            marker = dict(size=10,
                        color="#ff0000",
                        symbol="diamond-open",
                        )
        )
    )
    
    fig_data.append(
                go.Scatter(
                    x = x_o,
                    y = ypred,
                    mode = "lines",
                    name = 'fitted: r2 = <sup>'+str(round(r2, 3))+'</sup>',
                    opacity = 0.75,
                    line = dict(color = clr, width = 2),
                )
            )
    
    fig_data.append(
        go.Scatter(
            x = x_o,
            y = predict_mean_ci_upp,
            mode = "lines",
            name = 'upper 95 CI',
            opacity = 0.75,
            line = dict(color = clr, width = 2, dash='dash'),
        )
    )
    
    fig_data.append(
        go.Scatter(
            x = x_o,
            y = predict_mean_ci_low,
            mode = "lines",
            name = 'lower 95 CI',
            opacity = 0.75,
            line = dict(color = clr, width = 2, dash='dash'),
        )
    )
    
    fig_data.append(
        go.Scatter(
            x = x_o,
            y = predict_ci_upp,
            mode = "lines",
            name = 'upper 95 PI',
            opacity = 0.75,
            line = dict(color = clr, width = 2, dash='dot'),
        )
    )
    
    fig_data.append(
        go.Scatter(
            x = x_o,
            y = predict_ci_low,
            mode = "lines",
            name = 'lower 95 PI',
            opacity = 0.75,
            line = dict(color = clr, width = 2, dash='dot'),
        )
    )
    
    txt1 = '<b>' + xvar1 + '<b>'
    xvar2b = re.sub("\(.*?\)|\[.*?\]","", xvar2)
    if len(xvar2b) > 40:
        var_ls = []
        for j in range(0, len(xvar2b), 40):
            var_ls.append(xvar2b[j : j + 40])
        
        for j in var_ls:
            txt1 = txt1 + '<br>' + j 
    else:
        txt1 = txt1 + '<br>' + xvar2b
    
        
    txt2 = '<b>' + yvar1 + '<b>'
    yvar2b = re.sub("\(.*?\)|\[.*?\]","", yvar2)
    if len(yvar2b) > 40:
        var_ls = []
        for j in range(0, len(yvar2b), 40):
            var_ls.append(yvar2b[j : j + 40])
        
        for j in var_ls:
            txt2 = txt2 + '<br>' + j 
    else:
        txt2 = txt2 + '<br>' + yvar2b
        
    figure = go.Figure(
        data=fig_data,
        layout=go.Layout(
            transition = {'duration': 500},
            xaxis=dict(
                title=dict(
                    text=txt1,
                    font=dict(
                        family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                        " Helvetica, Arial, sans-serif",
                        size=14,
                    ),
                ),
                zeroline=True,
                showticklabels=True,
            ),
                
            yaxis=dict(
                title=dict(
                    text=txt2,
                    font=dict(
                        family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                        " Helvetica, Arial, sans-serif",
                        size=14,
                            
                    ),
                ),
                zeroline=True,
                showticklabels=True,
                    
            ),
                
            margin=dict(l=80, r=10, b=80, t=60),
            showlegend=True,
            height=500,
            paper_bgcolor="#f0f0f0",
            plot_bgcolor="#f0f0f0",
        ),
    )
        
    if x.tolist() != [] and y.tolist() != []:
        figure.update_layout(
            title="Adjusted r<sup>2</sup>: " + str(round(r2, 3)) + ', Model equation: ' + eqn,
            font=dict(
                size=10,
                color="rgb(38, 38, 38)"
                ),
            )
    
    figure.update_layout(
        legend=dict(
            traceorder="normal",
            font=dict(
                size=10,
                color="rgb(38, 38, 38)"
            ),
            
        )
    )    
    
    del tdf
    del df
    del hospitals
    del fig_data
    del dates
    del names
    del y
    del x
    del txt1
    del txt2
    return figure




@app.callback(
    Output("data_report_plot3", "figure"),
    [Input("run-btn3", "n_clicks")],
    [State("df_tab1", "data"),
     State('categories-select3', 'value'),
     State('categories-select33', 'value'),
     State('categories-select3-2', 'value'),
     State('categories-select33-2', 'value'),
     State('hospital-select1d', 'value'),
     ],
)
def update_data_report_plot3(n_clicks, df, numer1, numer2, denom1, denom2, focal_h):
    
    if df is None or numer1 is None or numer2 is None or denom1 is None or denom2 is None or denom2 == 'NUMBER OF BEDS':
            
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))
        
        fig.update_yaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_layout(title_font=dict(size=14, 
                      color="rgb(38, 38, 38)", 
                      ),
                      showlegend=True,
                      margin=dict(l=100, r=10, b=10, t=10),
                      paper_bgcolor="#f0f0f0",
                      plot_bgcolor="#f0f0f0",
                      )
        return fig
            
    
    df = pd.read_json(df)
    
    fig_data = []
    
    numer = numer1 + "', '" + numer2 + "')"
    denom = denom1 + "', '" + denom2 + "')"
    
    column1 = [col for col in df.columns if col.endswith(numer)]
    column2 = [col for col in df.columns if col.endswith(denom)]
    
    if len(column1) == 0 or len(column2) == 0:
        
        fig = go.Figure(data=go.Scatter(x = [0], y = [0]))
        
        fig.update_yaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_xaxes(title_font=dict(size=14, 
                                     #family='sans-serif', 
                                     color="rgb(38, 38, 38)"))
        fig.update_layout(title_font=dict(size=14, 
                      color="rgb(38, 38, 38)", 
                      ),
                      showlegend=True,
                      margin=dict(l=100, r=10, b=10, t=10),
                      paper_bgcolor="#f0f0f0",
                      plot_bgcolor="#f0f0f0",
                      )
        return fig
    
    
    x = "('Name and Num', 'Name and Num')"
    df = df[~df[x].isin([np.nan, float('NaN'), None])]
    
    hospitals = sorted(df["('Name and Num', 'Name and Num')"].unique())
    
    try:
        hospitals.remove(focal_h)
        hospitals.append(focal_h)
    except:
        pass
    
    fig_data = []
    for hospital in hospitals:
        
        name_var = "('Name and Num', 'Name and Num')"
        tdf = df[df[name_var] == hospital]
        
        date_var = "('file date', 'file date')"
        tdf.sort_values(by=date_var, inplace=True, ascending=True)
        
        column1 = [col for col in tdf.columns if col.endswith(numer)]
        column2 = [col for col in tdf.columns if col.endswith(denom)]
        
        column1 = column1[0]
        column2 = column2[0]
        tdf['y'] = tdf[column1]/tdf[column2]
        tdf = tdf.filter(items=['y', date_var, name_var], axis=1)
        tdf.dropna(how='any', inplace=True)
        
        dates = tdf["('file date', 'file date')"]
        names = tdf["('Name and Num', 'Name and Num')"]
        y = tdf['y']
        
        text = names + '<br>' + dates.astype(str)
        
        hi = HOSPITALS.index(hospital)
        if hospital == focal_h or focal_h == 'No focal hospital' or focal_h not in hospitals:
            clr = COLORS[hi]
        else:
            clr = '#cccccc'
        
        if len(hospital) > 30:
            hospital = hospital[0:20] + ' ... ' + hospital[-8:]
            
        fig_data.append(
                    go.Scatter(
                        x=dates,
                        y=y,
                        name=hospital,
                        mode='lines+markers',
                        marker=dict(color=clr),
                        text= text,
                    )
                )
    
    numer2 = re.sub("\(.*?\)|\[.*?\]","", numer2)
    denom2 = re.sub("\(.*?\)|\[.*?\]","", denom2)
    
    figure = go.Figure(
        data=fig_data,
        layout=go.Layout(
            transition = {'duration': 500},
            xaxis=dict(
                title=dict(
                    text="<b>Date</b>",
                    font=dict(
                        family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                        " Helvetica, Arial, sans-serif",
                        size=18,
                    ),
                ),
                #rangemode="tozero",
                zeroline=True,
                showticklabels=True,
            ),
                
            yaxis=dict(
                title=dict(
                    text= "<b>" + numer2 + ' /<br>' + denom2 + "</b>",
                    font=dict(
                        family='"Open Sans", "HelveticaNeue", "Helvetica Neue",'
                        " Helvetica, Arial, sans-serif",
                        size=14,
                            
                    ),
                ),
                zeroline=True,
                showticklabels=True,
                    
            ),
                
            margin=dict(l=80, r=10, b=80, t=60),
            showlegend=True,
            height=500,
            paper_bgcolor="#f0f0f0",
            plot_bgcolor="#f0f0f0",
        ),
    )
        
    figure.update_layout(
        legend=dict(
            traceorder="normal",
            font=dict(
                size=10,
                color="rgb(38, 38, 38)"
            ),
            
        )
    )    
    
    del tdf
    del df
    del hospitals
    del fig_data
    del dates
    del names
    del y
    del date_var
    del name_var
    return figure



@app.callback( # Update available sub_categories
    Output('trendline-1', 'options'),
    [
     Input('trendline-1', 'value'),
     ],
    )
def update_output15(value):
    options = ['linear', 'quadratic', 'cubic']
    
    return [{"label": i, "value": i} for i in options]



#########################################################################################


# Run the server
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', debug = False) # modified to run on linux server


import streamlit as st
import pydeck as pdk

import pandas as pd
import geopandas as gpd
import json
import numpy as np
import altair as alt

from math import pi
from bokeh.plotting import figure
from bokeh.transform import cumsum

from time import mktime
from datetime import datetime, time, timedelta, date
import pytz

utc=pytz.UTC


@st.cache
def get_qmj(filepath):
    df = pd.read_csv(filepath, sep=',')
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


@st.cache
def get_qi(filepath):
    df = pd.read_csv(filepath, sep=',')
    df['date'] = pd.to_datetime(df['date']).apply(lambda x: datetime.fromtimestamp(mktime(x.timetuple())))
    df["date"] = df["date"].apply(utc.localize)
    df["date"] = df["date"].dt.tz_convert('Europe/Paris')
    return df



def process_stations(station, data):
    subset_data = data[['date','debit']][data['code_station']==station].set_index('date')
    return subset_data[~subset_data.index.duplicated(keep='first')].rename(columns={'debit': station})


def get_station_status(qmj, doe, da, dar, dcr):
    # 1 = au dessus du DOE(Q_Obj_m3)
    # 2 = sous DOE, au dessus du DA(Q_80pDOE_m3)
    # 3 = sous DA, au dessus DAR(Q_alerte_renf)
    # 4 = sous DAR, au dessus DCR(Q_Crise_m3)
    # 5 = sous DCR

    if qmj>=doe:
        return 1
    if qmj<doe and qmj>=da:
        return 2
    elif qmj<da and qmj>=dar:
        return 3
    elif qmj<dar and qmj>=dcr:
        return 4
    elif qmj<dcr:
        return 5
    
    return 0


def get_hydro_status(id_hydro, map_stations_status, map_station_hydro):
    return map_stations_status.loc[map_station_hydro==id_hydro].max()

def get_ug_status(id_ug, map_hydro_status, map_hydro_ug):
    return map_hydro_status.loc[map_hydro_ug==id_ug].max()


def get_status_color(status, t=None):
    if status == 1:
        rgb = [136, 206, 51]
    elif status == 2:
        rgb = [245, 220, 11]
    elif status == 3:
        rgb = [245, 134, 11]
    elif status == 4:
        rgb = [229, 62, 29]
    elif status == 5:
        rgb = [39, 39, 39]
    else:
        rgb = [189, 206, 217]
    
    if t=='hydro':
        rgb = [x-50 for x in rgb]
    elif t=='ug':
        rgb = [x+50 for x in rgb]
        rgb.append(100)

    return rgb


def get_threshold(map_stations, threshold_name_dict, selected_stations):
    col_names = [threshold_name_dict[x] for x in threshold_name_dict.keys()]
    v = map_stations[map_stations['COD_STAT']==selected_stations[0]][col_names].values
    return v[0][0], v[0][1], v[0][2], v[0][3]


def print_stations(stations):
    if len(stations)==1:
        text = 'pour la station '
    else:
        text = 'pour les stations '
    for i in range(0,len(stations)):
        text = text + str(stations[i])
        if i < len(stations)-1:
            text = text + ', '
    return text


def process_rivers(river, map_stations, rivers):
    map_stations_river = map_stations.loc[map_stations['index'].isin(rivers[river])].drop(columns={'geometry'}).rename(columns={'index': 'COD_STAT'})
    map_stations_river['river_name'] = river
    return map_stations_river.reset_index(drop=True).reset_index()
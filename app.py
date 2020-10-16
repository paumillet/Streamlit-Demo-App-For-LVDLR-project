import streamlit as st
import pydeck as pdk
import pandas as pd
import geopandas as gpd
import numpy as np
import altair as alt
from math import pi
from bokeh.plotting import figure
from bokeh.transform import cumsum
from time import mktime
from datetime import datetime, time, timedelta, date
import pytz
from utils import *

utc=pytz.UTC


def main():
    """Streamlit demo web app for LVDLR"""

    # Initiate useful variables
    river_theme_color = ['#57A0D3', '#4F97A3', '#7285A5', '#73C2FB', '#008081', '#4C516D', '#6593F5', '#008ECC', '#95C8D8', '#4682B4', '#0F52BA', '#0080FF']

    threshold_colors=['#88CE33','#F5DC0B','#F5860B','#E53E1D', '#000000', '#efefef']

    threshold_value_dict = {
        'DOE': 2,
        'DA': 3,
        'DAR': 4,
        'DC': 5
    }

    threshold_name_dict = {
        'DOE': 'Q_Obj_m3',
        'DA': 'Q_80pDOE_m3',
        'DAR': 'Q_alerte_renf',
        'DC': 'Q_Crise_m3'
    }

    lot_amont = ['O7001510','O7021530','O7041510','O7101510','O7161510_E','O7191510']
    colagne = ['O7054010','O7074020','O7094010']
    lot_domanial = ['O7701540','O7971510','O8231530','COUTET','O8661520']
    cele = ['O8113520','O8133520']

    rivers = {
        'Lot amont': lot_amont,
        'Colagne': colagne, 
        'Lot domanial': lot_domanial, 
        'Célé': cele
    }

    qi_stations = ['CAHEDF','COUTET','D_GANIVET','D_MOULINET','ENTEDF','GOUL','NAT_O77015','O6140010','O7041510','O7054010','O7074020','O7094010','O7101510','O7145220','O7161510_E','O7191510','O7202510','O7234010','O7234030','O7245010','O7265010','O7272510','O7354010','O7410401','O7434010','O7444010','O7515510','O7535010','O7635010','O7701540','O7874010','O7944020','O7971510','O8113520','O8133520','O8231530','O8255010','O8264010','O8344020','O8661510','O8661520','O9000010']

    # Read all needed data
    ug_filename = 'data/ss-unites-gestion.geojson'
    map_ug = gpd.read_file(ug_filename)
    hydro_filename = 'data/hydrographie.geojson'
    map_hydro = gpd.read_file(hydro_filename)
    stations_filename = 'data/stations.geojson'
    map_stations = gpd.read_file(stations_filename)

    data_qmj = get_qmj('data/hbv_qmj.csv')
    data_qi = get_qi('data/hbv_qi.csv')

    # Explore Qmj data
    '# La Vie De La Rivière'
    'Explorateur des données des rivières du bassin du Lot'

    ## Select Qmj stations for visualization
    stations = data_qmj['code_station'].unique()
    selected_stations = st.multiselect('Sélectionnez une ou plusieurs stations', stations)

    if not selected_stations:
        st.warning('Renseignez au moins une station.')
        st.stop()

    ## Subset data for selected stations
    data_qmj_selected = data_qmj.copy()
    data_qmj_selected = data_qmj_selected.loc[data_qmj_selected['code_station'].isin(selected_stations)]

    ## Display sliders to filter data subset
    ### Flow slider
    min_flow = int(data_qmj_selected['debit'].min().round())
    max_flow = int(data_qmj_selected['debit'].max().round()+1)
    flow_slider = st.slider(
        'Intervalle de débits à visualiser [m3]',
        min_value=min_flow,
        max_value=max_flow, 
        value=(min_flow, max_flow)
        )

    ### Date slider
    min_date = data_qmj_selected['date'].min()
    max_date = data_qmj_selected['date'].max()

    date_slider = st.slider(
        'Intervalle de dates à visualiser',
        min_value=min_date,
        max_value=max_date, 
        value=(min_date, max_date),
        format="DD/MM/YYYY"
        )

    ### Filter data given sliders values
    data_qmj_selected = data_qmj_selected.loc[(data_qmj_selected['debit']>=flow_slider[0]) & (data_qmj_selected['debit']<flow_slider[1]) & (data_qmj_selected['date']>=date_slider[0]) & (data_qmj_selected['date']<=date_slider[1])]


    ## Display qmj data in line chart
    ### Allow legend filter
    selection = alt.selection_multi(fields=['code_station'], bind='legend')



    ### Get threshold flow values. If they exist, and only station is selected, they are display on the chart.
    DOE, DA, DAR, DC = get_threshold(map_stations, threshold_name_dict, selected_stations)

    if len(selected_stations) == 1 and not np.isnan(DOE):
        ### Line chart of flow
        qmj_line = alt.Chart().mark_line().encode(
            x=alt.X('date:T', axis=alt.Axis(domain=False, format='%_d/%m/%Y'), title=None),
            y=alt.Y('debit:Q', title='débit [m3]'),
            color=alt.value('#57A0D3'),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.1))
        ).properties(
            title='Débit moyen journalier'
        ).add_selection(
            selection
        )

        ### Horizontal lines of flow thresholds
        aggregates = alt.Chart().mark_rule().transform_fold(
            fold=['DOE', 'DA', 'DAR', 'DC'],
            as_=['variable', 'value']
        ).mark_rule().encode(
            y='value:Q',
            color=alt.Color('variable:N', legend=alt.Legend(title='Débits seuils'), scale=alt.Scale(domain=['DOE', 'DA', 'DAR', 'DC'],range=threshold_colors))
        )

        ### Agregate Line chart and horizontal lines into one single chart
        qmj_all = alt.layer(
            qmj_line, aggregates,
            data=data_qmj_selected
        ).transform_calculate(
            DOE=f"{DOE}",
            DA=f"{DA}",
            DAR=f"{DAR}",
            DC=f"{DC}"
        ).interactive()

    else:
        ### If ther more than one station selected, only display flow values
        qmj_line = alt.Chart().mark_line().encode(
            x=alt.X('date:T', axis=alt.Axis(domain=False, format='%_d/%m/%Y'), title=None),
            y=alt.Y('debit:Q', title='débit [m3]'),
            color=alt.Color('code_station:N', title='Code station', scale=alt.Scale(domain=selected_stations,range=river_theme_color)),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.1)),
            tooltip=['code_station','debit']
        ).properties(
            title='Débit moyen journalier'
        ).add_selection(
            selection
        )
        qmj_all = alt.layer(
            qmj_line,
            data=data_qmj_selected
        ).interactive()

    ### Display flow chart
    st.altair_chart(qmj_all, use_container_width=True)

    ## Display raw data if checkbox if checked
    if st.checkbox("Voir les données brutes"):
        st.subheader(f'Données de débit moyen journalier (Qmj), {print_stations(selected_stations)}')
        ### Reshape data to ease raw data visualization
        frames = [process_stations(station, data_qmj_selected) for station in selected_stations]
        data_qmj_selected_viz = pd.concat(frames, axis=1)

        ### and display
        data_qmj_selected_viz


    # Overview of the watershed at a given date
    "## Situation du bassin du Lot à une date donnée"

    ## Select the day of visualization
    date_qmj = st.date_input(
        'Choisir une date',
        value=date_slider[1]
        )

    ## Reshape data to ease qmj selection
    frames = [process_stations(station, data_qmj) for station in stations]
    reshape_data = pd.concat(frames, axis=1)

    ## Concat stations with their corresponding qmj
    map_stations = pd.concat([map_stations.set_index('COD_STAT'),reshape_data.loc[date_qmj][['O6140010','O9000010','O8584010','O8394310','O8344020','O8255010','O8264010','O8113520','O8133520','O7434010','O7354010','O7635010','O7265010','O7234030','O7234010','O7272510','O7202510','O7410401','O7444010','O7245010','GOUL','O7515510','O7535010','O7094010','O7054010','O7074020','O7085010','O7874010','O7825010','O7944020','O7145220','O7035010','O7001510','O7041510','O7101510','O7191510','O7161510_E','O7021530','O7015810','O8661520','COUTET','CAHEDF','O8231530','ENTEDF','O7701540','O7971510']].round(4)], axis=1).rename(columns={date_qmj: "qmj_selected"})

    ## Compute status given the qmj and the corresponding flow thresholds
    ### For stations
    map_stations['status'] = [get_station_status(row[0], row[1], row[2], row[3], row[4]) for row in map_stations[['qmj_selected', 'Q_Obj_m3', 'Q_80pDOE_m3', 'Q_alerte_renf', 'Q_Crise_m3']].to_numpy()]

    ### For hydro
    map_hydro['status'] = [get_hydro_status(x, map_stations) for x in map_hydro['ID_hydrographie']]

    ### For management units
    map_ug['status'] = [get_ug_status(x, map_hydro) for x in map_ug['ID_ss-unite-gestion']]

    ## Associate color to the status
    map_stations['color'] = map_stations['status'].apply(get_status_color)
    map_stations['color_stroke'] = [get_status_color(x, 'hydro') for x in map_stations['status']]
    map_hydro['color'] = [get_status_color(x, 'hydro') for x in map_hydro['status']]
    map_ug['color'] = [get_status_color(x, 'ug') for x in map_ug['status']]

    map_stations.reset_index(inplace=True)

    ## Give the opportuniy to filter given the selected stations
    if st.checkbox("Filtrer selon les stations sélectionnées"):
        ### Filter the data what will be display on map
        map_stations = map_stations.loc[map_stations['index'].isin(selected_stations)]
        ### And write the qmj for the selected stations
        f"### Débit moyen journalier des stations sélectionnées le {date_qmj.strftime('%_d/%m/%Y')}"
        for station in selected_stations:
            value = reshape_data.loc[date_qmj][station].round(4)
            f"à la station {station} : **{value}** m3"


    ## Map Data
    f"### Cartographie au {date_qmj.strftime('%_d/%m/%Y')}"
    ## Get the center of the map given the spatial repartition of the hydrometry
    bbox = map_hydro.total_bounds
    midpoint = [(bbox[1]+bbox[3])/2, (bbox[0]+bbox[2])/2]

    ## Prepare Tooltip template for the map
    tooltip_template = {
    "html": """
    <p style="font-size:15px">
    {index} <b>{NOM_COMPLET}</b> <br>
    Qmj du jour : {qmj_selected} m3 <br>
    </p>
    <p style="font-size:10px">
    DOE : {Q_Obj_m3} m3 &nbsp;
    DA : {Q_80pDOE_m3} m3 <br>
    DAR : {Q_alerte_renf} m3 &nbsp;
    DC : {Q_Crise_m3} m3</p>
    """,
    "style": {
            "backgroundColor": "steelblue",
            "color": "white"
    }
    }

    ## Create the map and display
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state={
            "latitude": midpoint[0],
            "longitude": midpoint[1],
            "zoom": 7,
        },
        tooltip=tooltip_template,
        layers=[
            pdk.Layer(
                "GeoJsonLayer",
                data=map_ug,
                stroked=True,
                filled = True,
                get_fill_color="color",
                getLineColor=[120,120,120,150],
                getLineWidth=200,
                pickable=False,
            ),
            pdk.Layer(
                "GeoJsonLayer",
                data=map_hydro,
                getLineColor="color",
                getLineWidth=500,
                pickable=False,
            ),
            pdk.Layer(
                "GeoJsonLayer",
                data=map_stations,
                filled = True,
                stroked = True,
                get_fill_color="color",
                getLineColor="color_stroke",
                get_radius=2000,
                getLineWidth=1000,
                pickable=True,
                auto_highlight=True,
                highlightColor=[250, 0, 100],
            ),
        ],
    ))

    # Table of stations under a given threshold on the day of visualization
    f"### Table des stations sous un débit seuil au {date_qmj.strftime('%_d/%m/%Y')}"

    threshold = st.radio(
            'Choisir un seuil',
            options=['DOE', 'DA', 'DAR', 'DC']
            )

    threshold_table = map_stations[map_stations['status']>=threshold_value_dict[threshold]][['index','NOM_COMPLET','qmj_selected',threshold_name_dict[threshold],'hydrographie','UG','Unite_Gestion']].rename(columns={'NOM_COMPLET': 'nom complet','qmj_selected': f'QMJ {date_qmj} [m3]', threshold_name_dict[threshold]: f'{threshold} [m3]','Unite_Gestion': 'unité de gestion'}).set_index('index')

    if len(threshold_table)>0:
        st.table(threshold_table)
    else:
        st.write(f"*Aucune station sous le {threshold}*")

    ## Example of combined charts
    '### Visualisations combinées'
    scale = alt.Scale(domain=['0','1', '2', '3', '4', '5'],
                    range=['#828282', '#88CE33','#F5DC0B','#F5860B','#E53E1D', '#000000'])
    color = alt.Color('status:N', scale=scale)

    ## We create two selections:
    ## - a brush that is active on the top panel
    ## - a multi-click that is active on the bottom panel
    brush = alt.selection(type='interval') #alt.selection_interval(encodings=['x'])
    click = alt.selection_multi(encodings=['color'])

    ## Top panel is scatter plot of hydrometric stations given their longitude and latitude
    points = alt.Chart().mark_circle().encode(
        alt.X('X_LONG_E:Q', title='Longitude'),
        alt.Y('Y_LAT_N:Q', title='Latitude', scale=alt.Scale(domain=[bbox[1]-0.05,bbox[3]+0.05])),
        color=alt.condition(brush, color, alt.value('lightgray')),
        size=alt.Size('qmj_selected:Q', scale=alt.Scale(range=[20, 300])),
        tooltip=['index','qmj_selected'],
    ).properties(
        width=550,
        height=300
    ).add_selection(
        brush
    ).transform_filter(
        click
    )

    ## Bottom panel is a bar chart giving the distibution of the stations according to their status
    bars = alt.Chart().mark_bar().encode(
        x=alt.X('count()', title='Nombre de stations par intervalle de seuils'),
        y=alt.Y('status:N', scale=alt.Scale(domain=[0, 1, 2, 3, 4, 5]), title='Seuils'),
        color=alt.condition(click, color, alt.value('lightgray')),
    ).transform_filter(
        brush
    ).properties(
        width=550,
    ).add_selection(
        click
    )

    ## Concat and display the charts
    bars_points = alt.vconcat(
        points,
        bars,
        data=map_stations.drop(columns={'geometry'}),
        title="Situation du bassin"
    ).configure_axis(
        grid=False
    )
    st.altair_chart(bars_points, use_container_width=True)


    # Try a new visualization kind : stations on a given river
    "### Stations le long d'un cours d'eau"
    ## Reshape to ease manipulation
    frames_river = [process_rivers(river, map_stations, rivers) for river in rivers.keys()]
    map_stations_river = pd.concat(frames_river, ignore_index=True, sort=False)

    ## Create chart
    river_chart = alt.Chart(map_stations_river).mark_circle().encode(
        alt.X('river_name:O', title='Rivières', axis=alt.Axis(labelAngle=0, orient="top")),
        alt.Y('index:O', title=''),
        color=color,
        size=alt.Size('qmj_selected:Q', scale=alt.Scale(range=[20, 500])),
        tooltip=['COD_STAT','qmj_selected'],
    ).properties(
        height=400
    )

    ## and display
    st.altair_chart(river_chart, use_container_width=True)

    # Pie chart are useful for global overview of share
    # Not available with Altair so this one is a try with Bokeh
    '### Pie Chart'
    data_pie = {
        'Au-dessus DOE': len(map_stations[map_stations.status==1]),
        'Sous DOE': len(map_stations[map_stations.status==2]),
        'Sous DA': len(map_stations[map_stations.status==3]),
        'Sous DAR': len(map_stations[map_stations.status==4]),
        'Sous DC': len(map_stations[map_stations.status==5]),
        'Sans information': len(map_stations[map_stations.status==0])
    }


    data_pie = pd.Series(data_pie).reset_index(name='value').rename(columns={'index':'categorie'})
    data_pie['angle'] = data_pie['value']/data_pie['value'].sum() * 2*pi
    data_pie['color'] = threshold_colors

    p = figure(plot_height=350, toolbar_location=None,
            tools="hover", tooltips="@categorie: @value", x_range=(-0.5, 1.0))

    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
            line_color="white", fill_color='color', legend_field='categorie', source=data_pie)

    p.axis.axis_label=None
    p.axis.visible=False
    p.grid.grid_line_color = None

    st.bokeh_chart(p)



    # Visualize Qi data
    # It's the exact same approach as with Qmj
    "# Visualiser les débits instantanés Qi"

    selected_qi_stations = st.multiselect("Choisir une station",options=qi_stations)

    if not selected_qi_stations:
        st.warning('Renseignez au moins une station.')
        st.stop()

    data_qi_selected = data_qi.copy()
    data_qi_selected = data_qi_selected.loc[data_qi_selected['code_station'].isin(selected_qi_stations)]
    min_flow_qi = int(data_qi_selected['debit'].min().round())
    max_flow_qi = int(data_qi_selected['debit'].max().round()+1)
    flow_slider_qi = st.slider(
        'Intervalle de débits à visualiser [m3]',
        min_value=min_flow_qi,
        max_value=max_flow_qi, 
        value=(min_flow_qi, max_flow_qi)
        )

    max_date_qi = st.date_input('Sélectionner la date de fin de la visualisation', min_value=data_qi_selected['date'].min().date(), max_value=data_qi_selected['date'].max().date())
    delta = st.radio("Choisir une période de visualisation",options=["7 jours", "15 jours", "1 mois", "2 mois", "3 mois"])
    delta_dict = {
        "7 jours": 7,
        "15 jours": 15,
        "1 mois": 30,
        "2 mois": 60,
        "3 mois": 90
    }

    date_slider_qi = [max_date_qi-timedelta(delta_dict[delta]), max_date_qi]

    date_slider_qi0 = utc.localize(datetime.fromtimestamp(mktime(date_slider_qi[0].timetuple())))
    date_slider_qi1 = utc.localize(datetime.fromtimestamp(mktime(date_slider_qi[1].timetuple())))

    data_qi_selected = data_qi_selected.loc[(data_qi_selected['debit']>=flow_slider_qi[0]) & (data_qi_selected['debit']<flow_slider_qi[1]) & (data_qi_selected['date']>=date_slider_qi0) & (data_qi_selected['date']<date_slider_qi1)]

    chart_data_qi = data_qi_selected.copy()
    chart_data_qi = chart_data_qi.drop(columns=['code_station']).set_index('date').rename(columns={'debit':'Qi [m3]'})

    frames_qi = [process_stations(station, data_qi) for station in selected_qi_stations]
    chart_data_qi = pd.concat(frames_qi, axis=1)

    qi_line = alt.Chart(data_qi_selected).mark_line().encode(
            x=alt.X('date:T', axis=alt.Axis(domain=False, format='%_d/%m/%Y'), title=None),
            y=alt.Y('debit:Q', title='débit [m3]'),
            color=alt.Color('code_station:N', title='Code station', scale=alt.Scale(domain=selected_qi_stations,range=river_theme_color)),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.1)),
            tooltip=['code_station','debit']
        ).properties(
            title='Débit instantané'
        ).add_selection(
            selection
        ).interactive()

    st.altair_chart(qi_line, use_container_width=True)

    if st.checkbox("Voir les données brutes de Qi"):
        st.subheader(f'Données de débits instantanés, {print_stations(selected_qi_stations)}')
        chart_data_qi


if __name__ == "__main__":
    main()
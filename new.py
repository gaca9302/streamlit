import streamlit as st
import os, pymysql
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO
import base64

st.set_page_config(page_title="Krisha", page_icon="💹", layout="wide")

db = {
        'host':'localhost',
        'user':'root',
        'password':'root',
        'database':'flats',
        'use_unicode':True,
        'charset':'utf8mb4',
        'cursorclass':pymysql.cursors.DictCursor
    }

@st.fragment(run_every="3h")
def get_date(sql, params=None):
    conn = pymysql.connect(**db)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

def get_sql_data(sql, params=None):
    conn = pymysql.connect(**db)
    with conn:
        with conn.cursor() as cursor:
            if params:
                cursor.executemany(sql,[params])
                return cursor.fetchall()
            else:
                cursor.execute(sql)
                return cursor.fetchall()
               
with st.sidebar:
    sql = 'select dt from dt'
    list_date = [i.get('dt') for i in get_date(sql)]
    date_use = st.selectbox('Выберите дату', list_date[::-1])
    idx = list_date.index(date_use)
    if idx:
        last_date = list_date[idx-1]
    else:
        last_date = list_date[idx]

sql = '''
    select avg(cast(price as SIGNED)) avg_price, count(*) count_flats 
    FROM flats f join flats_dt fd on f.id=fd.flat_id join dt on fd.dt_id=dt.id
    where dt.dt = %s
    ''' 
        
#st.write(type(date_use))
data = get_sql_data(sql, date_use)[0]
count = data.get('count_flats')
avg = data.get('avg_price')

last_data = get_sql_data(sql, last_date)[0]
last_count = last_data.get('count_flats')
last_avg = last_data.get('avg_price')

sql_df = '''
    select url, title, address, description, owner, price 
    FROM flats f join flats_dt fd on f.id=fd.flat_id join dt on fd.dt_id=dt.id 
    where dt.dt = %s
    '''

df = pd.DataFrame(get_sql_data(sql_df, date_use))


#st.html('<h1 class="title">Анализ квартир в г. Алмата</h1>')
st.title(f'Анализ квартир г. Алмата {str(date_use)}')

sql_gr_date = '''
select dt.dt, avg(cast(price as SIGNED)) avg_date, count(*) count_date,
avg(CAST(price AS UNSIGNED) / CAST(REGEXP_SUBSTR(title, '[0-9]+(\.[0-9]+)?(?= м²)') AS DECIMAL(6,2))) AS area_price
FROM flats f join flats_dt fd on f.id=fd.flat_id join dt on fd.dt_id=dt.id group by dt.dt order by 1
'''
gr_df = pd.DataFrame(get_sql_data(sql_gr_date))
gr_df['dt'] = gr_df['dt'].astype('str')
gr_df['avg_date'] = gr_df.avg_date.astype('int')
gr_df['area_price'] = gr_df.area_price.astype('float')

def filedownload(df): 
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl') 
    excel_data = output.getvalue() 
    b64 = base64.b64encode(excel_data).decode() 
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="krisha{str(date_use)}.xlsx">Download Excel File</a>' 
    return href

def plot_candlestick(gr_df):
    f_candle = make_subplots(rows=3, cols=1, shared_xaxes=True,row_heights=[0.4, 0.4, 0.3])
    f_candle.add_trace(
            go.Scatter(x=gr_df['dt'], y=gr_df['area_price'], mode='lines', name='Line'),
        row=1,
        col=1,
    )
    f_candle.add_trace(
            go.Scatter(x=gr_df['dt'], y=gr_df['avg_date'], mode='lines', name='Line'),
        row=2,
        col=1,
    )
    f_candle.add_trace(
        go.Scatter( x=gr_df['dt'],  y=gr_df['count_date'], mode='lines', name='Line'),
        row=3,
        col=1,
    )
    f_candle.update_layout(
        title='Сред. цена и кол.',
        #xaxis=dict(title='Дата', tickangle=45),
        yaxis=dict(title="сред. цена за кв. м"),
        yaxis2=dict(title='Цена'),
        xaxis3=dict(title="Дата", tickangle=45),
        yaxis3=dict(title="Количество"),
        showlegend=True,
    )
    return f_candle

col1, col2 = st.columns([.7,.3])

with col1:
    st.plotly_chart(plot_candlestick(gr_df),use_container_width=True)
    with st.expander('Загрузка'):
        st.markdown(filedownload(df), unsafe_allow_html=True)
        st.dataframe(df)
        
with col2:
        st.metric("сред. цена", int(avg), int(avg-last_avg))
        farea = int(gr_df['area_price'][len(gr_df)-1])
        larea = farea - int(gr_df['area_price'][len(gr_df)-2])
        st.metric("сред. цена за кв. м", farea, larea)
        st.metric("Кол. квартир", count, count-last_count)

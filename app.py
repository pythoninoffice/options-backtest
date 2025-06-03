import os, re
import pandas as pd
import sqlite3
import datetime as dt
#import pathlib
import calendar
import datetime
import plotly.express as px
import time

import streamlit as st
from PIL import Image
from bt_engine import OptionBacktest
from strategies import Strategy



class EMOJI:
    ROBOT = '🤖'
    DATA = '💾'
    TESTING = '📈'
    PLAN = '📗'
    WAVE_HAND = '👋'
    FINGER_POINT = '👉'
    PEACE = '✌️'
    THANK = '🙏'
    STRONG = '💪'
    EDUCATION = '🧐'


st.set_page_config(layout='wide', page_icon = '⚡', page_title='Option Backtest - A Free option backtest tool',) 

hide_streamlit_styles = """
                        <style>
                        #MainMenu {visibility:hidden;}
                        footer {visibility:hidden;}
                        </style>
"""
hide_table_row_index = """
            <style>
            tbody th {display:none}
            .blank {display:none}
            </style>
            """

st.markdown(hide_streamlit_styles, unsafe_allow_html=True)
#st.markdown(hide_table_row_index, unsafe_allow_html=True)


# st.balloons()
st.title('A Free option backtest tool')
st.markdown("Option backtesting can be difficult due to the amount of data involved. This tool will help make the testing process easier.")
st.markdown(f"{EMOJI.WAVE_HAND} Hi, my name is Jay and I made this tool for option backtesting. If you are interested in option trading, this tool might help you.")
st.markdown(f"{EMOJI.FINGER_POINT} Provide a few testing inputs (box on the left), and the program will take care of the rest.")
st.markdown(f"{EMOJI.THANK} Please stay tuned as we're working on adding more excitingfeatures!")
st.markdown(f" {EMOJI.EDUCATION} For educational purpose only, not financial advice.")
st.write('*************************************')

################################################################################################
######    SIDE BAR                                                                        ######
################################################################################################
with st.sidebar:
    with st.form(key='option_input'):
        start_date = st.date_input('Start Date', value = dt.date(2019,1,1))
        end_date = st.date_input('End Date', value = dt.date(2020,12,31))
        input_symbol = st.selectbox('Select A Stock',['SPY']).lower()
        input_strategy_name = st.selectbox('Select A Strategy',['Single','Strangle', 'Wheel']).lower()

        col_c_p = st.columns([1,2,3])
        with col_c_p[0]:
            input_c_p_1 = st.selectbox('Call/Put?',['P','C'], index = 0)
            input_c_p_2 = st.selectbox('',['P','C'], index = 1)
        with col_c_p[1]:
            input_delta_threshold_1 = st.number_input('Delta threshold', min_value = 0.0, max_value = 1.0, value = 0.45, step=0.01, key='delta-1')
            input_delta_threshold_2 = st.number_input('', min_value = 0.0, max_value = 1.0, value = 0.45, step=0.01, key='delta-2')
        with col_c_p[2]:
            input_leg1_long_short = st.selectbox('Long/Short', ['Long', 'Short'], index=0, key='leg1_long_short')
            input_leg2_long_short = st.selectbox('Long/Short', ['Long', 'Short'], index=0, key='leg2_long_short')
        input_l_s = st.selectbox('Long or Short?',['Long', 'Short']).upper()
        #aa = st.sidebar.number_input('Select delta throu', min_value = 0.0, max_value = 1.0, value = 0.5, step=0.01)
        input_num_days = st.number_input('Select a DTE', min_value = 0, max_value = 500, value = 30, step=1)
        input_expiration = st.selectbox('Select option chains',['Monthly','Weekly','All'],0)
        sticky_strike = st.checkbox("Use Sticky Strike?", value = False)
        input_trade_detail = st.checkbox("Show trade details (slower run time)", value = False)
        input_allow_overlap = st.checkbox("Allow overlap options?", value = False)
        submit_button = st.form_submit_button(label='Run Backtests')
    

    st.subheader(f"{EMOJI.ROBOT} How to use")
    with st.expander("3 Steps"):
        st.markdown("""
                    1. Select desired parameters above.
                    2. Long for buy positions, and Short for sell positions.
                    3. Once parameters are set, click on button "Run Backtest", results will be displayed on the main page shortly. 
                
    """)


    st.subheader(f"{EMOJI.TESTING} Backtesting strategy")
    with st.expander("See strategy"):
        st.markdown("""
                1. Three strategies are available: Single options, Strangle, and Wheel. For single strategies, only the first option is used.
                2. Each expiration cycle, 1 option contract is opened (1 call + 1 put in the case of a strangle).
                3. Prices are as of at daily close.
                4. Once a position is opened, it's held until expiration:
                    - OTM at expiration: held to expiration as price goes to 0, resulting in a pnl.
                    - ITM at expiration: position is closed using the stock's closing price. pnl is calculated as the difference between the strike price and the stock's closing price.
                5. Delta threshold sets the minimum delta for choosing options.
                    - 0.45 means the first option with a delta exceeding 0.45 will be selected.
                6. Days to expiration (DTE) sets the minimum days to expiration for testing.
                    - 45 means the first option with a DTE exceeding 45 days will be selected.
                7. No account/risk management is included at the moment.
                8. Currently does not look at volume/liquidity.
                """)


chart_list = []
entry_date_list = []
exp_date_list = []
selected_strike_list = []
entry_stock_price_list = []
total_pnl= []
valid_fridays = []
cum_pnl_df = pd.DataFrame()
cumulative_pnl = []


start_date = start_date.strftime('%Y-%m-%d')
end_date = end_date.strftime('%Y-%m-%d')

with st.spinner("Running backtests..."):

    strategy= Strategy(name=input_strategy_name, symbol=input_symbol, long_short=input_l_s, c_p=input_c_p_1, dte=input_num_days,num_legs=1)
    
    a =OptionBacktest(symbol=input_symbol,strategy = strategy, long_short='S', delta_limit=input_delta_threshold_1, delta_threshold=0.05, 
                      dte =input_num_days,begin=start_date, end=end_date,exp_cycles=input_expiration,sticky_strike=sticky_strike,
                      allow_overlap= input_allow_overlap)#,,allow_early_roll=True)# profit_limit=0.5,

    trade_detail_df = a.trade_history_summary_df
    
    trade_count = trade_detail_df.shape[0]
    win_count = trade_detail_df.loc[trade_detail_df['PnL'] > 0].shape[0]
    loss_count = trade_count - win_count
    try:
        win_rate = win_count/trade_count
    except:
        win_rate = 9999
    max_daily_drawdown = a.max_daily_draw_down
  
title_col1, title_col2 = st.columns([1,10])
with title_col1:
    try:
        company_logo = Image.open(f'{a.symbol}_logo.png')
        st.image(company_logo, width = 80)
    except:
        st.header(f'{a.symbol.upper()}')

    
with title_col2:
    st.header('')




print('*************************************')
print(f'monthly pnl: {total_pnl}')
print(f'total pnl: {sum(total_pnl)}')
print('*************************************')

total_pnl_amt = round(a.trade_history_summary_df['PnL'].sum()*100,0)
total_pnl_color = 'lime' if total_pnl_amt > 0 else 'red'

var_color = 'Aqua'


main_col1, main_col2 = st.columns(2)
with main_col1:

    st.markdown("""Strategy performance over the backtesting period:""")
    st.markdown(f"""
                    - Total P&L: <font color='{total_pnl_color}'>${total_pnl_amt:,.0f}</font>  
                    - Max daily drawdown: <font color='red'><b>${max_daily_drawdown:,.0f}</b></font>
                    - Backtest period: <font color = '{var_color}'>{start_date} - {end_date}</b></font>
                    - Number of trades: <font color='{var_color}'><b>{trade_count:,.0f}</b></font>  
                    - Win rate: <font color='{var_color}'>{win_rate*100:.2f}%</font>""", unsafe_allow_html=True)
    
    if input_l_s == 'Short':
        st.markdown(f"""The maximum required buying power/margin was <font color='lime'>${max(a.trade_history_summary_df['Strike'])*100/3:,.0f}</font>. 
                        The ROI on this strategy is <font color='{total_pnl_color}'>{total_pnl_amt/(max(a.trade_history_summary_df['Strike'])*100/3)*100:.2f}%</font>. """, unsafe_allow_html=True)
    st.markdown(f"""P&L from each month is shown in the table on the left-hand side.  
                    <br>
                    <br>
                    **The following parameters are used:**  
                    1. <font color='{var_color}'>{a.symbol}</font> options  
                    2. <font color='{var_color}'>{input_l_s} {input_strategy_name}</font>  
                    3. Minimum Delta: <font color='{var_color}'>{input_delta_threshold_1}</font>  
                    4. Minimum DTE: <font color='{var_color}'>{input_num_days:.0f}</font> days""", unsafe_allow_html=True)

with main_col2:
    st.dataframe(trade_detail_df,height = 500)
    
a.trade_history_summary_df['Cumulative PnL'] = a.trade_history_summary_df['PnL'].cumsum()
fig_cum_pnl = px.line(a.trade_history_summary_df, x= a.trade_history_summary_df.index, y=a.trade_history_summary_df['Cumulative PnL'])
fig_cum_pnl.update_xaxes(showgrid = False, zeroline=False, visible=False, showticklabels=False)
fig_cum_pnl.update_yaxes(showgrid = False, zeroline=False)
st.plotly_chart(fig_cum_pnl,use_container_width=True)

for i in a.trade_option_list:
    st.dataframe(i.chain, height=700)



if input_trade_detail:
    chart_rows = len(chart_list) // 2
    for i in range(chart_rows):
        col1, col2 = st.columns(2)
        with col1:
            _exp_date_1 = [exp_date_list[i*2].strftime("%Y-%m-%d")]
            df_col1 = pd.DataFrame({'Entry Date':[entry_date_list[i*2].strftime("%Y-%m-%d")],
                                    'Entry Stock Price': entry_stock_price_list[i*2],
                                    'Exp Date':_exp_date_1,
                                    'Strike': selected_strike_list[i*2],
                                    'PnL':total_pnl[i*2]*100})

            
            st.subheader(f"{_exp_date_1}: {total_pnl[i*2]*100:,.0f}")
            st.plotly_chart(chart_list[i*2])
            st.table(df_col1)
            
        with col2:
            _exp_date_2 = [exp_date_list[i*2+1].strftime("%Y-%m-%d")]
            df_col2 = pd.DataFrame({'Entry Date':[entry_date_list[i*2+1].strftime("%Y-%m-%d")],
                                    'Entry Stock Price': entry_stock_price_list[i*2+1],
                                    'Exp Date':_exp_date_2,
                                    'Strike': selected_strike_list[i*2+1],
                                    'PnL':total_pnl[i*2+1]*100})

            st.subheader(f"{_exp_date_2}: {total_pnl[i*2+1]*100:,.0f}")
            st.plotly_chart(chart_list[i*2+1])
            st.table(df_col2)


with st.expander("Release Notes"):
    st.header('v.0.0.0')
    st.write('Initial release')

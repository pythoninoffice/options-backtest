import os, re
import pandas as pd
import sqlite3
import datetime as dt
#import pathlib
import calendar
import datetime
import plotly.express as px
import time
from config import DB_PATH
import streamlit as st
from PIL import Image
#from options import Option
from strategies import Strategy

conn_url = DB_PATH


class OptionBacktest:
    
    def __init__(self,symbol=None, c_p=None, strategy=None, long_short=None, delta_limit=None, delta_threshold= 0, strike=None, 
                 exp_date=None, dte=0, _id = 0, begin=None, end=None, exp_cycles=None, profit_limit = 0, loss_limit=0, allow_early_roll=False,
                 sticky_strike = False, allow_overlap = False):
        self.conn = sqlite3.connect(conn_url)
        self.symbol = symbol
        self.long_short = long_short.upper()
        self.delta_limit = delta_limit
        self.delta_threshold = delta_threshold
        self.strike = strike
        self.selected_strike = strike
        self.dte = dte
        self.exp_date = exp_date
        self.option_id = f'{symbol}_{exp_date}_{c_p}_{strike}'
        self.chain = None
        self.need_roll = False
        self._id = _id
        self.exp_date = None
        self.trade_option_list = []
        self.begin = begin
        self.end = end
        self.exp_cycles = exp_cycles
        self.all_available_exp_dates = None
        self.exp_date_list = self.get_exp_dates(exp_cycles=exp_cycles)
        self.profit_limit = profit_limit
        self.loss_limit = loss_limit
        self.sticky_strike = sticky_strike
        self.trade_history_summary = []
        self.strategy = strategy
        self.max_daily_draw_down = 0
        self.allow_overlap_options = allow_overlap
        
        self.get_tradable_options(symbol,c_p,strategy = strategy, dte = self.dte, delta_limit = delta_limit, delta_threshold=delta_threshold,
                                  begin=begin, end=end,  allow_early_roll=allow_early_roll, sticky_strike=sticky_strike,
                                  allow_overlap=allow_overlap)
        
        self.allow_early_roll = allow_early_roll

        

    def get_exp_dates(self, year=None, exp_cycles = None):
        if self.begin != None:
            date_str = f'where EXPIRE_DATE >= "{self.begin}"'
        if (self.end != None) and ('where' in date_str):
            date_str += f'and EXPIRE_DATE <= "{self.end}"'

        #tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", self.conn)
        
        self.all_available_exp_dates = pd.read_sql(f'SELECT DISTINCT EXPIRE_DATE from option_chain_{self.symbol} {date_str}', self.conn)['EXPIRE_DATE'].tolist()

        selected_exp_dates = []
        if exp_cycles == 'All':
            exp_dates = self.all_available_exp_dates
        else:
            begin_year = int(self.begin[:4])
            end_year = int(self.end[:4])
            if begin_year == end_year:
                if exp_cycles == 'Monthly':
                    selected_exp_dates = self.get_third_fridays(begin_year)
                elif exp_cycles == 'Weekly':
                    selected_exp_dates = self.get_all_fridays(begin_year)
            else:
                for year in range(begin_year, end_year+1):
                    if exp_cycles == 'Monthly':
                        selected_exp_dates += self.get_third_fridays(year)
                    elif exp_cycles == 'Weekly':
                        selected_exp_dates += self.get_all_fridays(year)
           
            missing_exp_date_index = [d for d in selected_exp_dates if d not in self.all_available_exp_dates]
            exp_dates = [d for d in selected_exp_dates if d in self.all_available_exp_dates]
            if len(missing_exp_date_index) > 0:
                missing_exp_date = self.find_nearest_friday(missing_exp_date_index[0], self.all_available_exp_dates)
                
                if missing_exp_date is not None:
                    missing_exp_date = missing_exp_date.strftime('%Y-%m-%d')
                    exp_dates.append(missing_exp_date)             
        exp_dates.sort()
        
        return exp_dates
       
    def get_third_fridays(self, year):
        c = calendar.Calendar(firstweekday=calendar.SUNDAY)
        third_fri = []
        for m in range(1,13):
            monthcal = c.monthdatescalendar(year, m)
            temp = [day for week in monthcal for day in week if day.weekday() == calendar.FRIDAY][2]
            temp_str = temp.strftime('%Y-%m-%d')
            third_fri.append(temp_str)
        return third_fri    
    
    def get_all_fridays(self, year):
        c = calendar.Calendar(firstweekday=calendar.SUNDAY)
        all_fri = []
        for m in range(1,13):
            monthcal = c.monthdatescalendar(year, m)
            temp_fridays = [day for week in monthcal for day in week if (day.weekday() == calendar.FRIDAY) & (day.month == m)]
            temp_fridays_str = [temp.strftime('%Y-%m-%d') for temp in temp_fridays]
            all_fri += temp_fridays_str

        return all_fri  
    

    def find_nearest_friday(self, friday, friday_list):
        if isinstance(friday, str):
            friday = dt.datetime.strptime(friday, '%Y-%m-%d')
        elif isinstance(friday, datetime.date):
            friday = dt.datetime.combine(friday, dt.datetime.min.time())
        friday_list = [dt.datetime.strptime(i, '%Y-%m-%d') for i in friday_list]
        
        #calculate the difference in days between friday and everyday in the friday_list
        nearest_day_index = [abs(i - friday) for i in friday_list]
        
        #the missing_friday is the day with minimum days difference, i.e. the closest day
        missing_friday = friday_list[nearest_day_index.index(min(nearest_day_index))]
        return missing_friday



    def _search_single_leg_options(self, strategy, open_date, exp_date):
        if strategy.name.lower() != 'single':
            raise Exception('need to be a single leg strategy!')
        c_p = strategy.c_p_1
        symbol = strategy.symbol
        sql_str = f"""select QUOTE_DATE, UNDERLYING_LAST, EXPIRE_DATE, STRIKE, {c_p.upper()}_DELTA, {c_p.upper()}_LAST, option_{c_p}_id
                                from option_chain_{symbol} 
                                where EXPIRE_DATE = "{exp_date}" and QUOTE_DATE >= "{open_date}" """
        return pd.read_sql(sql_str, self.conn)


    def _search_multi_leg_options(self, strategy, open_date, exp_date):
        if strategy.name.lower() != 'single':
            c_p_1 = strategy.c_p_1
            c_p_2 = strategy.c_p_2
            symbol = strategy.symbol
            if c_p_1 == c_p_2:
                sql_str = f"""select QUOTE_DATE, UNDERLYING_LAST, EXPIRE_DATE, STRIKE, {c_p.upper()}_DELTA, {c_p.upper()}_LAST, option_{c_p}_id
                                    from option_chain_{symbol} 
                                    where EXPIRE_DATE = "{exp_date}" and QUOTE_DATE >= "{open_date}" """
            else:
                sql_str = f"""select QUOTE_DATE, UNDERLYING_LAST, EXPIRE_DATE, STRIKE, C_DELTA, C_LAST, option_c_id, P_DELTA, P_LAST, option_p_id
                                from option_chain_{symbol} 
                                where EXPIRE_DATE = "{exp_date}" and QUOTE_DATE >= "{open_date}" """
        return pd.read_sql(sql_str, self.conn)



    def _get_open_date(self, i, exp_date, dte, allow_overlap):
        exp_date_dt = dt.datetime.strptime(exp_date, '%Y-%m-%d')
        
        if (i>0) and (self.trade_option_list[i-1].allow_early_roll) and (self.trade_option_list[i-1].closed_early):  
            self.open_date = self.trade_option_list[i-1].opt_close_date
        else:
            self.open_date = (exp_date_dt - dt.timedelta(days=dte))
            if (i>0) & (not allow_overlap) : # if this is not the first trade, check the previous close date
                self.open_date = max(self.open_date, dt.datetime.strptime(self.trade_option_list[i-1].opt_close_date,'%Y-%m-%d'))
            self.open_date = self.open_date.strftime('%Y-%m-%d')

        
    def _get_testing_strikes(self, i, j, sticky_strike, exp_date, delta_limit, delta_threshold, c_p):
        if i >1:
            print(self.trade_option_list[i-1].chain)
        if (i>0) and (self.trade_option_list[i-1].loss_limit_reached) and sticky_strike:
            
            previous_opt_strike = self.trade_option_list[i-1].legs[j].strike
            sql_strike_str = f"""select STRIKE
                    from option_chain_{self.symbol} 
                    where EXPIRE_DATE = "{exp_date}" 
                    and QUOTE_DATE >= "{self.open_date}" 
                    ORDER BY ABS(STRIKE - {previous_opt_strike})
                    LIMIT 1
                    """ 
         
            cursor = self.conn.cursor()
            cursor.execute(sql_strike_str)
            self.selected_strike = cursor.fetchone()[0]
            print(f'previous option strike is: {previous_opt_strike}')
            print(f'new selected strike is:{self.selected_strike}')
        else:
            if c_p == 'C':
                delta_criteria = f"C_DELTA <= {delta_limit} and C_DELTA >= {max(0,delta_limit - delta_threshold)} "
                strike_index = -1
            elif c_p == 'P':
                delta_criteria = f"P_DELTA <= -{delta_limit} and P_DELTA >= -{delta_limit + delta_threshold}"
                strike_index = 0
            
            sql_strike_str = f"""select STRIKE 
                                from option_chain_{self.symbol} 
                                where EXPIRE_DATE = "{exp_date}" and {delta_criteria} and QUOTE_DATE >= "{self.open_date}" """
            cursor = self.conn.cursor()
            cursor.execute(sql_strike_str)
            self.selected_strike = cursor.fetchone()[0]


    def get_tradable_options(self, symbol, c_p, strategy = None, exp_date=None, dte=None, delta_limit=None, delta_threshold = 0,
                             begin=None, end=None, strike = None, allow_early_roll=False,
                             sticky_strike=False, allow_overlap=False):
        wheel_pos = 'P'
        self.max_daily_draw_down = 0
        for i, exp_date in enumerate(self.exp_date_list):

            self._get_open_date(i, exp_date=exp_date, dte = dte, allow_overlap=allow_overlap)
            print(exp_date)
            temp_strikes = []
            for j, leg in enumerate(strategy.legs):
                if strategy.name != 'wheel':
                    self._get_testing_strikes(i, j, sticky_strike= sticky_strike,exp_date = exp_date, delta_limit= delta_limit, delta_threshold=delta_threshold, c_p=leg.c_p)
                    temp_strikes.append(self.selected_strike)
                
            if strategy.name =='single':
                temp_strategy = Strategy(name=strategy.name, symbol=self.symbol, strikes = temp_strikes, long_short = strategy.long_short, c_p = strategy.c_p,
                                     open_date = self.open_date, exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                allow_early_roll=allow_early_roll)
                self.max_daily_draw_down = min(self.max_daily_draw_down, temp_strategy.max_daily_draw_down)
            elif strategy.name =='strangle':
                temp_strategy = Strategy(name=strategy.name, symbol=self.symbol, c_p='P', strikes = temp_strikes, long_short = strategy.long_short,
                                     open_date = self.open_date, exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                allow_early_roll=allow_early_roll)
            elif strategy.name =='wheel':
                self._get_testing_strikes(i, 0, sticky_strike= sticky_strike,exp_date = exp_date, delta_limit= delta_limit, 
                                          delta_threshold=delta_threshold, c_p=wheel_pos)
                temp_strikes.append(self.selected_strike)

                if i ==0:
                   
                    temp_strategy = Strategy(name='wheel', symbol=self.symbol, strikes = temp_strikes, long_short = strategy.long_short,
                                     open_date = self.open_date, exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                allow_early_roll=allow_early_roll)
                    print('start')
                else:
                    previous_position = self.trade_option_list[i-1]
                    if previous_position.c_p == 'P' and previous_position.long_short in ['S', 'SHORT'] and previous_position.closed_itm:
                        temp_strategy = Strategy(name='wheel', symbol=self.symbol, strikes = temp_strikes, long_short = 'S',
                                        open_date = self.open_date, c_p='C',exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                    allow_early_roll=allow_early_roll, have_shares=True)

                    elif previous_position.c_p == 'C' and previous_position.long_short in ['S', 'SHORT'] and not previous_position.closed_itm:
                        temp_strategy = Strategy(name='wheel', symbol=self.symbol, strikes = temp_strikes, long_short = 'S',
                                        open_date = self.open_date, c_p='C',exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                    allow_early_roll=allow_early_roll, have_shares=True)
  
                   
                    else: 
                        temp_strategy = Strategy(name='wheel', symbol=self.symbol, strikes = temp_strikes, long_short = strategy.long_short,
                                        open_date = self.open_date, exp_date = exp_date, profit_limit = self.profit_limit, loss_limit = self.loss_limit,
                                    allow_early_roll=allow_early_roll)
             
                if temp_strategy.closed_itm and temp_strategy.c_p == 'P':
                    wheel_pos = 'C'
                elif temp_strategy.closed_itm and temp_strategy.c_p == 'C':
                    wheel_pos = 'P'

            elif strategy.name == 'custom':
                pass
            
            if temp_strategy.summary != None:
                self.trade_history_summary.append(temp_strategy.summary)
                self.trade_option_list.append(temp_strategy)

        if strategy.name == 'single':
            self.trade_history_summary_df = pd.DataFrame(self.trade_history_summary,
                                                    columns=['Open Date', 'Close Date','Strike','Call_Put','Stock Price At Open','Stock Price At Close',
                                                    'Open Price','Close Price','PnL','Rolled Early', 'Closed ITM'])
        elif strategy.name == 'strangle':

            self.trade_history_summary_df = pd.DataFrame(self.trade_history_summary,
                                                    columns=['Open Date', 'Close Date','Strike 1','Stock Price At Open','Stock Price At Close','Strike 2',
                                                    'Open Price','Close Price','PnL','Rolled Early', 'Closed ITM'])
        elif strategy.name == 'wheel':
            self.trade_history_summary_df = pd.DataFrame(self.trade_history_summary,
                                                    columns=['Open Date', 'Close Date','Strike','Call_Put','Stock Price At Open','Stock Price At Close',
                                                    'Open Price','Close Price','PnL','Rolled Early', 'Closed ITM'])
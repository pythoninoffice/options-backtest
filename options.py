import pandas as pd
import sqlite3
from config import DB_PATH

# Use a relative path to one of your existing database files
conn_url = DB_PATH

class Option:

    def __init__(self, symbol=None, c_p=None, long_short=None, strike=None, open_date=None, exp_date=None, dte=0, chain=None, _id = 0, 
                 profit_limit = 0, loss_limit = 0, allow_early_roll = False, opt_open_date = None, opt_close_date = None,
                 profit_limit_reached = False, loss_limit_reached = False, query_db = False, have_shares=False):
        self.symbol = symbol.lower()
        if isinstance(c_p, str):
            self.c_p = c_p.upper()
        self.long_short = long_short
        self.strike = strike
        self.dte = dte
        self.open_date = open_date
        self.exp_date = exp_date
        self.opt_open_date = opt_open_date
        self.opt_close_date = opt_close_date
        self.option_id = f'{symbol}_{exp_date}_{c_p}_{strike}'
        
        self.chain = self.query_db() if query_db else chain
        self.need_roll = False
        self._id = _id
        self.summary = None
        #self.open_price = self.get_open_price()
        self.close_price = 0
        self.add_on_limit = 0.01
        self.pnl_amount = 0
        self.profit_limit = profit_limit
        self.loss_limit = loss_limit
        self.closed_early = False
        self.allow_early_roll = allow_early_roll
        self.profit_limit_reached = profit_limit_reached
        self.loss_limit_reached = loss_limit_reached
        self.closed_itm = False
        self.have_shares = have_shares
        self.max_daily_draw_down = 0
            
        
    def __str__(self):
        return f'Option(\'{self.symbol}\', \'{self.exp_date}\',\'{self.c_p}\', {self.strike})'

    def __repr__(self):
        return f'Option(\'{self.symbol}\', \'{self.exp_date}\',\'{self.c_p}\', {self.strike})'
    
    def get_chain_from_db(self):
        self.conn = sqlite3.connect(conn_url, check_same_thread=False)

        sql_str = f"""select QUOTE_DATE, UNDERLYING_LAST, EXPIRE_DATE, STRIKE, {self.c_p}_DELTA, {self.c_p}_LAST, {self.c_p}_ASK,{self.c_p}_BID,option_{self.c_p}_id
                    from option_chain_{self.symbol} 
                    where EXPIRE_DATE = "{self.exp_date}" 
                    and QUOTE_DATE >= "{self.open_date}" 
                    and STRIKE = {self.strike} """
        df = pd.read_sql(sql_str, self.conn)
        df.reset_index(drop=True, inplace=True)

        #if the price of a given day is 0 due to no volume, use the price of a later day
        
        df[f'{self.c_p}_LAST'].replace(to_replace=0, method='bfill', inplace=True) 
        df[f'{self.c_p}_ASK'].replace(to_replace=0, method='bfill', inplace=True) 
        df[f'{self.c_p}_BID'].replace(to_replace=0, method='bfill', inplace=True) 
        
        print(sql_str)
        self.chain = df
        #self.get_pnl(profit_limit = self.profit_limit, loss_limit = self.loss_limit)
        #self._get_summary()
        

    
    def get_open_price(self):
        if (self.chain is not None) and (self.chain.shape[0] > 0) and (self.c_p):            
            if ('C_LAST' in self.chain.columns) and ('P_LAST' in self.chain.columns):
                self.chain['Total_Premium'] = self.chain['P_LAST'] + self.chain['C_LAST']

            else:

                self.chain['Total_Premium'] = (self.chain[f'{self.c_p}_ASK'] + self.chain[f'{self.c_p}_BID'])/2
            self.open_price = self.chain['Total_Premium'].iloc[0]
            self.close_price = self.chain['Total_Premium'].iloc[-1]

    def get_close_price(self, chain, close_date=None):
        if self.chain is not None:
            return chain['Total_Premium'].iloc[-1]

    def get_pnl(self, profit_limit=0, loss_limit=0, have_shares=False):
        self.get_open_price()
        print(self.chain)
        if (self.chain is not None) and (self.chain.shape[0] > 0):
            if self.long_short in ['LONG','L']:
                self.chain['daily_pnl'] = self.chain['Total_Premium'].diff(periods=1)
                self.chain['cumulative_pnl'] = self.chain['Total_Premium'] - self.open_price
            elif self.long_short in ['SHORT','S']:
                self.chain['daily_pnl'] = self.chain['Total_Premium'].diff(periods=-1).shift(1)
                self.chain['cumulative_pnl'] = self.open_price - self.chain['Total_Premium']
            
            if profit_limit > 0 or loss_limit < 0:
                self.set_early_close(profit_limit = profit_limit, loss_limit = loss_limit)
            

            self.pnl_amount = round(self.chain['cumulative_pnl'].iloc[-1],2)
            self.opt_open_date = self.chain['QUOTE_DATE'].iloc[0]
            self.opt_close_date = self.chain['QUOTE_DATE'].iloc[-1]
            if self.c_p == 'C':
                self.chain['closed_itm'] = self.chain['UNDERLYING_LAST'] >= self.strike
            elif self.c_p == 'P':
                self.chain['closed_itm'] = self.chain['UNDERLYING_LAST'] <= self.strike

            if have_shares:
                self.chain['shares_daily_pnl'] = self.chain['UNDERLYING_LAST'].diff(periods=1)
                self.chain['shares_cum_pnl'] = self.chain['UNDERLYING_LAST'] - self.chain['UNDERLYING_LAST'][0]
                self.chain['daily_pnl_all'] = self.chain['daily_pnl']+self.chain['shares_daily_pnl']
                self.chain['cumulative_pnl_all'] =  self.chain['cumulative_pnl'] + self.chain['shares_cum_pnl']
                self.pnl_amount = round(self.chain['cumulative_pnl_all'].iloc[-1],2)
        if self.chain['closed_itm'].iloc[-1]:
            self.loss_limit_reached = True

        self.max_daily_draw_down = min(0, self.chain['daily_pnl'].min()) * 100

    def roll(self):
        pass

    def set_early_close(self, profit_limit=0, loss_limit=0):
        self.chain['pnl_pct'] = self.chain['cumulative_pnl'] / self.open_price
        if profit_limit > 0: # e.g. 50% close
            meet_profit_row = (self.chain['pnl_pct'] >= profit_limit).idxmax()
            if meet_profit_row > 0:
                self.chain = self.chain.loc[:meet_profit_row,:]
                self.closed_early = True
                self.profit_limit_reached = True
                print('closed early')
            self.close_price = self.chain['Total_Premium'].iloc[-1]

        if loss_limit < 0:
            meet_loss_row = (self.chain['pnl_pct'] <= loss_limit).idxmax()
            if meet_loss_row > 0:
                self.chain = self.chain.loc[:meet_loss_row,:]
                self.closed_early = True
                self.loss_limit_reached = True
            self.close_price = self.chain['Total_Premium'].iloc[-1]
    
    def _get_summary(self,strike_1, strike_2=None):
        if (self.chain is not None) and (self.chain.shape[0] > 0):
            self.underlying_price_at_open = self.chain['UNDERLYING_LAST'].iloc[0]
            self.underlying_price_at_close = self.chain['UNDERLYING_LAST'].iloc[-1]
            if self.c_p == 'P':
                self.closed_itm = self.underlying_price_at_close <= strike_1
            elif self.c_p == 'C':
                self.closed_itm = self.underlying_price_at_close >= strike_1
            if strike_2:
                self.summary = [self.opt_open_date, self.opt_close_date, strike_1, self.underlying_price_at_open, self.underlying_price_at_close,strike_2, 
                                self.open_price, self.close_price, self.pnl_amount, self.closed_early, self.closed_itm]
            else:
                self.summary = [self.opt_open_date, self.opt_close_date, strike_1, self.c_p, self.underlying_price_at_open,  self.underlying_price_at_close,
                                self.open_price, self.close_price, self.pnl_amount, self.closed_early, self.closed_itm]


    def _trade_shares(self, num_shares=100, long_short="L", open_date=None, close_date=None):
        self.stock_open_date = open_date

    def query_db(self):
        self.conn = sqlite3.connect(conn_url, check_same_thread=False)
        sql_str = f"""select QUOTE_DATE, UNDERLYING_LAST, EXPIRE_DATE, STRIKE, {self.c_p}_DELTA, {self.c_p}_LAST, option_{self.c_p.lower()}_id
                                from option_chain_{self.symbol} 
                                where EXPIRE_DATE = "{self.exp_date}" 
                                and QUOTE_DATE >= "{self.open_date}" 
                                and STRIKE = {self.strike}"""

        df= pd.read_sql(sql_str, self.conn)
        df.rename(columns={'STRIKE':f'{self.c_p}_STRIKE'}, inplace=True)
        return df
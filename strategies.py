from options import Option

class Strategy(Option):

    def __init__(self, name=None, symbol=None, strike_1=0, strike_2=0, strikes = None, strike = 0, c_p=None, long_short=None, dte=None, _id=None, 
                 open_date=None, exp_date=None, profit_limit=0, loss_limit=0, allow_early_roll=False,num_legs=0, have_shares=None):
        super().__init__(symbol=symbol, c_p=c_p, long_short=long_short, strike=strike, open_date=open_date, exp_date=exp_date, dte=dte, _id=_id, 
                 profit_limit=profit_limit, loss_limit=loss_limit, allow_early_roll=allow_early_roll)

      
        self.name = name.lower()
        self.strike_1 = strike_1
        self.strike_2 = strike_2
        self.strikes = strikes
        if strikes:
            self.strike = strikes[0]
        self.long_short = long_short
        self.dte = dte
        self._id  = _id
        self.exp_date = exp_date
        self.open_date = open_date
        self.profit_limit = profit_limit
        self.loss_limit = loss_limit
        self.allow_early_roll = allow_early_roll
        self.num_legs = num_legs
        self.num_shares = 0
        self.have_shares = have_shares
        self.shares_long_short = 'L'
        
        if name == 'strangle':
            self.leg_1 = Option(symbol=self.symbol, c_p = 'P', long_short = self.long_short)
            self.leg_2 = Option(symbol=self.symbol, c_p = 'C', long_short = self.long_short)
            self.legs = [self.leg_1, self.leg_2]
        elif name =='single':
            self.leg_1 = Option(symbol=self.symbol, c_p = c_p, long_short = self.long_short)
            self.legs = [self.leg_1]
        elif name == 'wheel':
            self.c_p = 'P'
            self.leg_1 = Option(symbol=self.symbol, c_p = self.c_p, long_short = self.long_short)
            self.legs = [self.leg_1]
        if c_p:
            self.c_p =c_p
        
        if self.strikes:
            self.set_strategies()


    def set_strategies(self):
        if self.name == 'strangle':
            self._strangle(symbol=self.symbol, strikes = self.strikes, open_date = self.open_date, exp_date = self.exp_date,
                            profit_limit = self.profit_limit, loss_limit = self.loss_limit, allow_early_roll = self.allow_early_roll)
        elif self.name == 'single':
            self._single(symbol=self.symbol, strikes = self.strikes, c_p= self.c_p, open_date = self.open_date, exp_date = self.exp_date,
                            profit_limit = self.profit_limit, loss_limit = self.loss_limit, allow_early_roll = self.allow_early_roll)
        elif self.name == 'wheel':
            self._wheel(symbol=self.symbol, strikes = self.strikes, c_p= self.c_p, open_date = self.open_date, exp_date = self.exp_date,
                            profit_limit = self.profit_limit, loss_limit = self.loss_limit, allow_early_roll = self.allow_early_roll, have_shares = self.have_shares)


    def _single(self, **kwargs):
        self.symbol = kwargs['symbol']
        if len(self.strikes) == 1:
            self.strike_1 = kwargs['strikes'][0]
        exp_date = kwargs['exp_date']
        open_date = kwargs['open_date']
        profit_limit=kwargs['profit_limit']
        loss_limit=kwargs['loss_limit']
        allow_early_roll=kwargs['allow_early_roll']
        c_p = kwargs['c_p']

        self.leg_1 = Option(symbol=self.symbol, c_p = c_p, long_short = self.long_short, strike = self.strike_1, open_date=open_date, exp_date = exp_date, profit_limit = profit_limit,
                            loss_limit = loss_limit, allow_early_roll = allow_early_roll)
        self.num_legs=1
        self.single = [self.leg_1]
        self.legs = [self.leg_1]
        self.leg_1.get_chain_from_db()
        self._combine()
        self.get_pnl(profit_limit=profit_limit, loss_limit=loss_limit)
        self._get_summary(strike_1 =self.strike_1)
        self.max_daily_draw_down = self.leg_1.max_daily_draw_down
        print(f'{self.long_short} {self.c_p}')


    def _strangle(self, **kwargs):
        self.symbol = kwargs['symbol']
        if len(self.strikes) == 2:
            self.strike_1 = self.strikes[0]
            self.strike_2 = self.strikes[1]
        self.num_legs=2
        exp_date = kwargs['exp_date']
        open_date = kwargs['open_date']
        profit_limit=kwargs['profit_limit']
        loss_limit=kwargs['loss_limit']
        allow_early_roll=kwargs['allow_early_roll']

        self.leg_1 = Option(symbol=self.symbol, c_p = 'P', long_short = self.long_short, strike = self.strike_1, open_date=open_date, exp_date = exp_date, profit_limit = profit_limit,
                            loss_limit = loss_limit, allow_early_roll = allow_early_roll)
        self.leg_2 = Option(symbol=self.symbol, c_p = 'C', long_short = self.long_short, strike = self.strike_2, open_date=open_date, exp_date = exp_date, profit_limit = profit_limit,
                            loss_limit = loss_limit, allow_early_roll = allow_early_roll)
        self.leg_1.get_chain_from_db()
        self.leg_2.get_chain_from_db()

        self.strangle = [self.leg_1, self.leg_2]
        self.legs = [self.leg_1, self.leg_2]
        self._combine()

        self.get_pnl(profit_limit=profit_limit, loss_limit=loss_limit)
        self._get_summary(strike_1 =self.strike_1, strike_2 =self.strike_2)

    def _straddle(self):
        pass
    
    def _wheel(self, **kwargs):
        ## start off by selling put
        ## keep selling put until assigned
        ## once assigned, sell stock immidiately (or wait a few days?)
        self.symbol = kwargs['symbol']
        if len(self.strikes) == 1:
            self.strike_1 = kwargs['strikes'][0]
        self.legs = [self.leg_1]
        exp_date = kwargs['exp_date']
        open_date = kwargs['open_date']
        profit_limit=kwargs['profit_limit']
        loss_limit=kwargs['loss_limit']
        allow_early_roll=kwargs['allow_early_roll']
        self.have_shares=kwargs['have_shares']
        self.long_short = 'S'

        self.num_legs = 1
        
        if not self.have_shares:
            print('selling a put')
            self.c_p = 'P'
            
            self.leg_1 = Option(symbol=self.symbol, c_p = self.c_p, long_short = self.long_short, strike = self.strike_1, open_date=open_date, exp_date = exp_date, 
                                profit_limit = profit_limit, loss_limit = loss_limit, allow_early_roll = allow_early_roll)
        else:
            self.c_p = 'C'
            self.num_shares = 100
            print('selling a call')

            self.leg_1 = Option(symbol=self.symbol, c_p = self.c_p, long_short = self.long_short, strike = self.strike_1, open_date=open_date, exp_date = exp_date, 
                                profit_limit = profit_limit, loss_limit = loss_limit, allow_early_roll = allow_early_roll, have_shares=self.have_shares)
            

        self.leg_1.get_chain_from_db()
        self._combine()
        self.get_pnl(profit_limit=profit_limit, loss_limit=loss_limit, have_shares = self.have_shares)
        self._get_summary(strike_1 =self.strike_1)

    def _combine(self):
        if self.num_legs == 2:
            self.leg_2.chain.drop(columns=['UNDERLYING_LAST','EXPIRE_DATE'],inplace=True)
            self.chain = self.leg_1.chain.merge(self.leg_2.chain, on= 'QUOTE_DATE', suffixes=('_P', '_C'))
        elif self.num_legs == 1:
            self.chain = self.leg_1.chain

    def _get_open_prices(self):
        self.open_prices = [leg.get_open_price() for leg in self.legs]

    def _get_pnls(self):
        [leg.get_pnl() for leg in self.legs]
        self.pnl_amounts = [leg.pnl_amount for leg in self.legs]
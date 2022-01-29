import datetime
import os.path
import sys
import numpy as np
import backtrader as bt
from backtrader.indicators import EMA


"""
孕线策略：
看涨孕线买入，盈利10%卖出
"""
class TestStrategy(bt.Strategy):
    params = (
        ('code', 0),
        ('profits', [])
    )
    def log(self, txt, dt=None):
        """ Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print("%s, %s" % (dt.isoformat(), txt))

    @staticmethod
    def percent(today, yesterday):
        return float(today - yesterday) / today

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.params.profits = []

        self.sma20 = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)

        me1 = EMA(self.data, period=12)
        me2 = EMA(self.data, period=26)
        self.macd = me1 - me2
        self.signal = EMA(self.macd, period=9)

        bt.indicators.MACDHisto(self.data)

    def notify_order(self, order):
        # 交易状态处理
        # Python实用宝典
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                
                # 记录买入价格
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed_close = self.dataclose[0]
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
                # 收益率计算
                profit_rate = float(order.executed.price - self.buyprice)/float(self.buyprice)
                # 存入策略变量
                self.params.profits.append(profit_rate)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    # Python 实用宝典
    def next(self):
        # self.log("Close, %.2f" % self.dataclose[0])
        if self.order:
            return

        if not self.position:
            # condition1 = self.sma20[0] > self.dataclose[0]
            if self.dataclose[-1] < self.dataopen[-1]:
                harami = (
                    self.datahigh[0] < self.dataopen[-1]
                    and self.datalow[0] > self.dataclose[-1]
                )
            else:
                harami = (
                    self.datahigh[0] < self.dataclose[-1]
                    and self.datalow[0] > self.dataopen[-1]
                )

            if harami:
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
                self.order = self.buy()

        else:
            condition = (self.dataclose[0] - self.bar_executed_close) / self.dataclose[0]
            if condition > 0.1 or condition < -0.1:
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()


if __name__ == "__main__":
    cerebro = bt.Cerebro(maxcpus=None)

    cerebro.addstrategy(TestStrategy)

    datapath = '../data/600519.csv'

    # 加载数据到模型中
    data = bt.feeds.GenericCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2010, 1, 1),
        todate=datetime.datetime(2020, 8, 15),
        dtformat="%Y%m%d",
        datetime=2,
        open=3,
        high=4,
        low=5,
        close=6,
        volume=10,
        reverse=True,
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(7000)

    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    cerebro.broker.setcommission(commission=0.003)

    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    cerebro.run()

    profits = cerebro.runstrats[0][0].params.profits
    print(np.mean(profits))

    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    cerebro.plot()
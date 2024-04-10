from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List 
import string

import pandas as pd
import numpy as np
import statistics as stats
import math 
import jsonpickle

import collections
import copy

INF = int(1e9)

class Trader:
    # order_depths: Dict[Symbol, OrderDepth]

    position = {'STARFRUIT' : 0, 'AMETHYSTS' : 0}

    # number of historical mid_price used to predict new mid_price
    starfruit_dim = 5
    starfruit_cache = []
    POSITION_LIMIT = {'STARFRUIT' : 20, 'AMETHYSTS' : 0}

    def calc_next_price_starfruit(self):
        # bananas cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price

        coef = [0.16179295, 0.14453001, 0.20387022, 0.16503886, 0.31240748]
        intercept = 61.6762187870645
        nxt_price = intercept
        for i, val in enumerate(self.starfruit_cache):
            nxt_price += val * coef[i]

        return int(round(nxt_price))
        

    def save_position(self, state:TradingState):
        '''
        Save the current position in every instrument.
        '''
        for key, val in state.position.items():
            self.position[key] = val


    def run(self, state: TradingState):

        orders: list[Order] = []

        # Initialize the method output dict as an empty dict
        result = {'AMETHYSTS' : [], 'STARFRUIT': []}     

        # get highest ask
        if len(order_depth.sell_orders):
            best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
        
        # get lowest bid
        if len(order_depth.buy_orders):
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]

        self.starfruit_cache.append((best_bid+best_ask)/2)
        

        if len(self.starfruit_cache) == self.starfruit_dim:
            starfruit_price = self.calc_next_price_starfruit()

        # if negative positions
        if self.position['STARFRUIT'] < 0:
            # buy
            orders.append(Order('STARFRUIT', starfruit_price+1, self.POSITION_LIMIT['STARFRUIT']))
            # sell
            orders.append(Order('STARFRUIT', starfruit_price-1, -self.POSITION_LIMIT['STARFRUIT']-self.position['STARFRUIT']))
        
        # if positive position
        if self.position['STARFRUIT'] >= 0:
            # buy
            orders.append(Order('STARFRUIT', starfruit_price+1, self.POSITION_LIMIT['STARFRUIT']-self.position['STARFRUIT']))
            # sell
            orders.append(Order('STARFRUIT', starfruit_price-1, self.POSITION_LIMIT['STARFRUIT']))

        for product in ["STARFRUIT"]:
            result[product] += orders


        # clear cache from one value if full and cache the new mid value
        if len(self.starfruit_cache) == self.starfruit_dim:
            self.starfruit_cache.pop(0)


        traderData ="SAMPLE"
        conversions = 1

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
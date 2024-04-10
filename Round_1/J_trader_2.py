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
    
    def extract_best_order_price(self, order_depth, side):
        '''
        order_depth: state.order_depths[product]
        '''
        # get highest ask
        if len(order_depth.sell_orders) != 0 and side == 'sell':
            best_ask, best_ask_amount = list(order_depth.sell_orders.items())[-1]
            return best_ask
        
        # get lowest bid
        if len(order_depth.buy_orders) != 0 and side == 'buy':
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[-1]
            return best_bid
        
    def compute_orders_regression(self, product, order_depth, acc_bid, acc_ask, LIMIT):
        orders: list[Order] = []

        best_sell_pr = self.extract_best_order_price(order_depth, side='sell')
        best_buy_pr  = self.extract_best_order_price(order_depth, side='buy')

        cpos = self.position[product]

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid) # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask)
        # bid_pr = acc_bid
        # sell_pr = acc_ask

        if cpos < LIMIT:
            num = LIMIT - cpos
            orders.append(Order(product, bid_pr, num))
            cpos += num
        
        cpos = self.position[product]

        if cpos > -LIMIT:
            num = -LIMIT-cpos
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders

    def save_position(self, state:TradingState):
        '''
        Save the current position in every instrument.
        '''
        for key, val in state.position.items():
            self.position[key] = val


    def run(self, state: TradingState):

        # Initialize the method output dict as an empty dict
        result = {'AMETHYSTS' : [], 'STARFRUIT': []}     

        self.save_position(state)   

        # extract best bid and best ask from current order book
        bs_starfruit = self.extract_best_order_price(state.order_depths["STARFRUIT"], side='sell')
        bb_starfruit = self.extract_best_order_price(state.order_depths["STARFRUIT"], side='buy')

        self.starfruit_cache.append((bs_starfruit+bb_starfruit)/2)
        
        # calculate own order prices
        starfruit_lb = -INF
        starfruit_ub = INF
        if len(self.starfruit_cache) == self.starfruit_dim:
            starfruit_lb = self.calc_next_price_starfruit()-1
            starfruit_ub = self.calc_next_price_starfruit()+1
        
        acc_bid = {'STARFRUIT' : starfruit_lb} # we want to buy at slightly below
        acc_ask = {'STARFRUIT' : starfruit_ub} # we want to sell at slightly above

        for product in ["STARFRUIT"]:
            order_depth: OrderDepth = state.order_depths[product]
            orders = self.compute_orders_regression(product, order_depth, acc_bid[product], acc_ask[product], self.POSITION_LIMIT[product])
            result[product] += orders


        # clear cache from one value if full and cache the new mid value
        if len(self.starfruit_cache) == self.starfruit_dim:
            self.starfruit_cache.pop(0)


        traderData ="SAMPLE"
        conversions = 1

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
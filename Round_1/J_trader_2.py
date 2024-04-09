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
        if len(order_depth.sell_orders) != 0 and side == 'sell':
            best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
            return best_ask
                
        if len(order_depth.buy_orders) != 0 and side == 'buy':
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
            return best_bid    
        
    def compute_orders_regression(self, product, order_depth, acc_bid, acc_ask, LIMIT):
        orders: list[Order] = []
        osell = collections.OrderedDict(sorted(order_depth.sell_orders.items()))
        obuy = collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True))

        best_sell_pr = self.extract_best_order_price(order_depth, side='sell')
        best_buy_pr  = self.extract_best_order_price(order_depth, side='buy')

        cpos = self.position[product]

        for ask, vol in osell.items():
            if ((ask <= acc_bid) or ((self.position[product]<0) and (ask == acc_bid+1))) and cpos < LIMIT:
                order_for = min(-vol, LIMIT - cpos)
                cpos += order_for
                assert(order_for >= 0)
                orders.append(Order(product, ask, order_for))

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid) # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask)

        if cpos < LIMIT:
            num = LIMIT - cpos
            orders.append(Order(product, bid_pr, num))
            cpos += num
        
        cpos = self.position[product]
        

        for bid, vol in obuy.items():
            if ((bid >= acc_ask) or ((self.position[product]>0) and (bid+1 == acc_ask))) and cpos > -LIMIT:
                order_for = max(-vol, -LIMIT-cpos)
                # order_for is a negative number denoting how much we will sell
                cpos += order_for
                assert(order_for <= 0)
                orders.append(Order(product, bid, order_for))

        if cpos > -LIMIT:
            num = -LIMIT-cpos
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders

    def print_position(self):
        '''
        Prints all instrument positions.
        '''
        print("Our position:")
        for key, val in self.position.items():
            print(f'{key} position: {val}')

    def save_position(self, state:TradingState):
        '''
        Save the current position in every instrument.
        '''
        for key, val in state.position.items():
            self.position[key] = val

    def print_own_trades(self, state:TradingState):
        '''
        Print own trades of last iteration.
        '''
        print("Own trades:")
        for product in state.own_trades.keys():
            for trade in state.own_trades[product]:
                if trade.timestamp == state.timestamp-100:
                    print(f'We traded {product}, {trade.buyer}, {trade.seller}, {trade.quantity}, {trade.price}')

    # line 130, in print_others_trades\\n    for trade in state.own_trades[product] error
    def print_others_trades(self, state:TradingState):
        '''
        Print bot trades of last iteration.
        '''
        print("Others trades:")
        for product in state.market_trades.keys():
            for trade in state.own_trades[product]:
                if trade.timestamp == state.timestamp-100:
                    print(f'Bots traded {product}, {trade.buyer}, {trade.seller}, {trade.quantity}, {trade.price}')

    def print_market_orders(self, result):
        '''
        Print our marke orders of current iteration.
        '''
        for product in result.keys():
            for order in result[product]:
                print(order)

    def run(self, state: TradingState):

        # Initialize the method output dict as an empty dict
        result = {'AMETHYSTS' : [], 'STARFRUIT': []}        

        # extract best bid and best ask from current order book
        bs_starfruit = self.extract_best_order_price(state.order_depths["STARFRUIT"], side='sell')
        bb_starfruit = self.extract_best_order_price(state.order_depths["STARFRUIT"], side='buy')

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
        self.starfruit_cache.append((bs_starfruit+bb_starfruit)/2)

        traderData ="SAMPLE"
        conversions = 1

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
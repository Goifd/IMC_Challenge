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

import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Trade, TradingState
# from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any





class Trader:
    # order_depths: Dict[Symbol, OrderDepth]
    POSITION_LIMIT = {'STARFRUIT' : 20, 'AMETHYSTS' : 20, 'CHOCOLATE':250, 'STRAWBERRIES':350,'ROSES':60,'GIFT_BASKET':60}

    # basket caches
    CHOC_cache = []
    theor_CHOC_cache = []
    CHOC_diff_cache = []
    CHOC_rolling_diff_cache = []
    CHOC_rolling_dev_diff_cache = []    

    def run(self, state: TradingState):
        # basket:         
        # dev_signal = 1.5 or 1 or 1.5
        # average_len = 30 or 20 or 40
        

        # trading params
        dev_signal = 1.5
        average_len = 30
        # buy/sell price, quantity (order sizing)

        BT_orders: List[Order] = []
        ROSES_orders: List[Order] = []
        CHOC_orders: List[Order] = []
        STRAW_orders: List[Order] = []
        result = {'AMETHYSTS' : [], 'STARFRUIT': [], 'ORCHIDS':[], 'CHOCOLATE':[], 'STRAWBERRIES':[], 'ROSES':[],'GIFT_BASKET':[]}   

        # GET MARKET DATA
        if len(state.order_depths["ROSES"].sell_orders) != 0:
            ROSES_best_ask, ROSES_best_ask_amount = list(state.order_depths["ROSES"].sell_orders.items())[0] 
        if len(state.order_depths["ROSES"].buy_orders) != 0:
            ROSES_best_bid, ROSES_best_bid_amount = list(state.order_depths["ROSES"].buy_orders.items())[0]

        if len(state.order_depths["CHOCOLATE"].sell_orders) != 0:
            CHOCOLATE_best_ask, CHOCOLATE_best_ask_amount = list(state.order_depths["CHOCOLATE"].sell_orders.items())[0] 
        if len(state.order_depths["CHOCOLATE"].buy_orders) != 0:
            CHOCOLATE_best_bid, CHOCOLATE_best_bid_amount = list(state.order_depths["CHOCOLATE"].buy_orders.items())[0]

        if len(state.order_depths["STRAWBERRIES"].sell_orders) != 0:
            STRAWBERRIES_best_ask, STRAWBERRIES_best_ask_amount = list(state.order_depths["STRAWBERRIES"].sell_orders.items())[0] 
        if len(state.order_depths["STRAWBERRIES"].buy_orders) != 0:
            STRAWBERRIES_best_bid, STRAWBERRIES_best_bid_amount = list(state.order_depths["STRAWBERRIES"].buy_orders.items())[0]
        
        if len(state.order_depths["GIFT_BASKET"].sell_orders) != 0:
            GIFT_BASKET_best_ask, GIFT_BASKET_best_ask_amount = list(state.order_depths["GIFT_BASKET"].sell_orders.items())[0] 
        if len(state.order_depths["GIFT_BASKET"].buy_orders) != 0:
            GIFT_BASKET_best_bid, GIFT_BASKET_best_bid_amount = list(state.order_depths["GIFT_BASKET"].buy_orders.items())[0]

        # 6 strawberries, 4 chocolate, 1 rose
        CHOC_theor_ask = int(round((GIFT_BASKET_best_ask-4*CHOCOLATE_best_ask-ROSES_best_ask)/6))
        CHOC_theor_bid = int(round((GIFT_BASKET_best_bid-4*CHOCOLATE_best_bid-ROSES_best_bid)/6))

        CHOC_theor_mid = (CHOC_theor_ask+CHOC_theor_bid)/2
        CHOC_mid = (STRAWBERRIES_best_ask+STRAWBERRIES_best_bid)/2

        self.CHOC_cache.append(CHOC_mid)
        self.theor_CHOC_cache.append(CHOC_theor_mid)

        diff = CHOC_theor_mid-CHOC_mid
        self.CHOC_diff_cache.append(diff)

        rolling = np.mean(self.CHOC_diff_cache)
        self.CHOC_rolling_diff_cache.append(rolling)

        rolling_dev = np.std(self.CHOC_diff_cache)*dev_signal
        self.CHOC_rolling_dev_diff_cache.append(rolling_dev)        


        # ------------------------------- STAT ARB ALGO -------------------------------

        # BASKET
        # if len(self.rolling_diff_cache)==average_len:
        #     # prices will converge again
        #     if diff>(rolling+rolling_dev):
        #             # sell basket
        #             BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_ask-1, -20))

        #             # # buy individuals
        #             # ROSES_orders.append(Order("ROSES", ROSES_best_bid, 10))
        #             # STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid, 20))
        #             # CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_bid, 40))
                
        #     # prices will diverge
        #     if (rolling-rolling_dev) > diff:
        #         # buy basket
        #         BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_bid+1, 20))

                # # sell indi
                # ROSES_orders.append(Order("ROSES", ROSES_best_ask, -10))
                # STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask, -60))
                # CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_ask, -40))


        # CHOCOLATE
        
        if len(self.CHOC_rolling_diff_cache)==average_len:
            # prices will converge again
            if diff>(rolling+rolling_dev):
                STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid, 20))
                
            # prices will diverge
            if (rolling-rolling_dev)>diff:
                STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask, -20))

        result["GIFT_BASKET"] = BT_orders
        result["ROSES"] = ROSES_orders
        result["CHOCOLATE"] = CHOC_orders
        result["STRAWBERRIES"] = STRAW_orders

        if len(self.CHOC_rolling_diff_cache)==average_len:
            self.CHOC_rolling_diff_cache.pop(0)
            self.CHOC_cache.pop(0)
            self.CHOC_diff_cache.pop(0)

        trader_data ="SAMPLE"
        conversions=1

        # returns a list of orders that the algo sends to the market
        return result, conversions, trader_data
    
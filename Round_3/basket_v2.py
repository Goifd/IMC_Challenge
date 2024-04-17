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
    basket_cache = []
    theor_basket_cache = []
    diff_cache = []
    rolling_diff_cache = []
    rolling_dev_diff_cache = []

    choch_diff_cache = []
    rose_diff_cache = []
    straw_diff_cache = []

    

    def run(self, state: TradingState):
        # basket:         
        # dev_signal = 1.5 or 1 or 1.5
        # average_len = 30 or 20 or 40
        

        # trading params
        dev_signal = 0.5
        average_len = 20
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

        rose_mid = (ROSES_best_ask+ROSES_best_bid)/2

        if len(state.order_depths["CHOCOLATE"].sell_orders) != 0:
            CHOCOLATE_best_ask, CHOCOLATE_best_ask_amount = list(state.order_depths["CHOCOLATE"].sell_orders.items())[0] 
        if len(state.order_depths["CHOCOLATE"].buy_orders) != 0:
            CHOCOLATE_best_bid, CHOCOLATE_best_bid_amount = list(state.order_depths["CHOCOLATE"].buy_orders.items())[0]
        
        choc_mid = (CHOCOLATE_best_ask+CHOCOLATE_best_bid)/2

        if len(state.order_depths["STRAWBERRIES"].sell_orders) != 0:
            STRAWBERRIES_best_ask, STRAWBERRIES_best_ask_amount = list(state.order_depths["STRAWBERRIES"].sell_orders.items())[0] 
        if len(state.order_depths["STRAWBERRIES"].buy_orders) != 0:
            STRAWBERRIES_best_bid, STRAWBERRIES_best_bid_amount = list(state.order_depths["STRAWBERRIES"].buy_orders.items())[0]

        straw_mid = (STRAWBERRIES_best_ask+STRAWBERRIES_best_bid)/2
        
        if len(state.order_depths["GIFT_BASKET"].sell_orders) != 0:
            GIFT_BASKET_best_ask, GIFT_BASKET_best_ask_amount = list(state.order_depths["GIFT_BASKET"].sell_orders.items())[0] 
        if len(state.order_depths["GIFT_BASKET"].buy_orders) != 0:
            GIFT_BASKET_best_bid, GIFT_BASKET_best_bid_amount = list(state.order_depths["GIFT_BASKET"].buy_orders.items())[0]

        

        # 6 strawberries, 4 chocolate, 1 rose
        GF_theor_ask = 6*STRAWBERRIES_best_ask+4*CHOCOLATE_best_ask+ROSES_best_ask
        GF_theor_bid = 6*STRAWBERRIES_best_bid+4*CHOCOLATE_best_bid+ROSES_best_bid

        GF_theor_mid = (GF_theor_ask+GF_theor_bid)/2
        GF_mid = (GIFT_BASKET_best_ask+GIFT_BASKET_best_bid)/2

        self.basket_cache.append(GF_mid)
        self.theor_basket_cache.append(GF_theor_mid)

        diff = GF_mid-GF_theor_mid
        self.diff_cache.append(diff)

        rose_diff = GF_mid-rose_mid
        choc_diff = GF_mid-choc_mid
        straw_diff = GF_mid-straw_mid

        self.rose_diff_cache.append(rose_diff)
        self.choch_diff_cache.append(choc_diff)
        self.straw_diff_cache.append(straw_diff)

        rose_dev = abs(np.std(self.rose_diff_cache)/np.mean(self.rose_diff_cache))
        choc_dev = abs(np.std(self.choch_diff_cache)/np.mean(self.choch_diff_cache))
        straw_dev = abs(np.std(self.straw_diff_cache)/np.mean(self.straw_diff_cache))

        rolling = np.mean(self.diff_cache)
        self.rolling_diff_cache.append(rolling)

        rolling_dev = np.std(self.diff_cache)*dev_signal
        self.rolling_dev_diff_cache.append(rolling_dev)        


        # ------------------------------- STAT ARB ALGO -------------------------------

        # BASKET
        if len(self.rolling_diff_cache)==average_len:
            # prices will converge again
            if diff>(rolling+rolling_dev):
                # sell basket
                basket_pos=0
                if 'GIFT_BASKET' in state.position.keys():
                    basket_pos = state.position["GIFT_BASKET"]
                max_ask_quant = -60 - basket_pos
                max_bid_quant = 60 - basket_pos
                BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_ask-1, max(-20,max_ask_quant)))
                
                # if(rose_dev>choc_dev and rose_dev>straw_dev):
                #     ROSES_orders.append(Order("ROSES", ROSES_best_bid+1, 10))
                # if(choc_dev> rose_dev and choc_dev>straw_dev):
                #     CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_bid+1, 40))
                # if(straw_dev>rose_dev and straw_dev>choc_dev):
                #     STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid+1, 20))
                    
                
            # prices will diverge
            if (rolling-rolling_dev) > diff:
                # buy basket
                basket_pos=0
                if 'GIFT_BASKET' in state.position.keys():
                    basket_pos = state.position["GIFT_BASKET"]
                max_ask_quant = -60 - basket_pos
                max_bid_quant = 60 - basket_pos
                BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_bid+1, min(20, max_bid_quant)))
                # identify which instrument causes the deviation
                # if(rose_dev>choc_dev and rose_dev>straw_dev):
                #     ROSES_orders.append(Order("ROSES", ROSES_best_ask-1, -10))
                # if(choc_dev> rose_dev and choc_dev>straw_dev):
                #     CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_ask-1, -40))
                # if(straw_dev>rose_dev and straw_dev>choc_dev):
                #     STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask-1, -20))



        result["GIFT_BASKET"] = BT_orders
        result["ROSES"] = ROSES_orders
        result["CHOCOLATE"] = CHOC_orders
        result["STRAWBERRIES"] = STRAW_orders

        if len(self.rolling_diff_cache)==average_len:
            self.rolling_diff_cache.pop(0)
            self.basket_cache.pop(0)
            self.diff_cache.pop(0)
            self.choch_diff_cache.pop(0)
            self.rose_diff_cache.pop(0)
            self.straw_diff_cache.pop(0)

        trader_data ="SAMPLE"
        conversions=1

        # returns a list of orders that the algo sends to the market
        return result, conversions, trader_data
    
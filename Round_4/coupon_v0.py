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
    COC_cache = []
    COUPON_cache = []

    def black_scholes_price(self, S, K, t, r, sigma, option_type='call'):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        d2 = d1 - sigma * np.sqrt(t)
        if option_type == 'call':
            price = S * stats.NormalDist().cdf(d1) - K * np.exp(-r * t) * stats.NormalDist().cdf(d2)
        else:
            price = K * np.exp(-r * t) * stats.NormalDist().cdf(-d2) - S * stats.NormalDist().cdf(-d1)
        return price

    def black_scholes_delta(self, S, K, t, r, sigma, option_type='call'):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
        if option_type == 'call':
            delta = stats.NormalDist().cdf(d1)
        else:
            delta = stats.NormalDist().cdf(d1) - 1
        return delta
    

    def run(self, state: TradingState):

        COC_orders: List[Order] = []
        COUPON_orders: List[Order] = []

        result = {'AMETHYSTS' : [], 'STARFRUIT': [], 'ORCHIDS':[], 'CHOCOLATE':[], 'STRAWBERRIES':[], 'ROSES':[],'GIFT_BASKET':[], 'COCONUT':[], 'COCONUT_COUPON':[]}   

        # GET MARKET DATA
        if len(state.order_depths["COCONUT"].sell_orders) != 0:
            COC_best_ask, COC_best_ask_amount = list(state.order_depths["COCONUT"].sell_orders.items())[0] 
        if len(state.order_depths["COCONUT"].buy_orders) != 0:
            COC_best_bid, COC_best_bid_amount = list(state.order_depths["COCONUT"].buy_orders.items())[0]

        COC_mid = (COC_best_ask+COC_best_bid)/2

        COUPON_best_bid = 0
        if len(state.order_depths["COCONUT_COUPON"].sell_orders) != 0:
            COUPON_best_ask, COUPON_best_ask_amount = list(state.order_depths["COCONUT_COUPON"].sell_orders.items())[0] 
        if len(state.order_depths["COCONUT_COUPON"].buy_orders) != 0:
            COUPON_best_bid, COUPON_best_bid_amount = list(state.order_depths["COCONUT_COUPON"].buy_orders.items())[0]
        
        COUPON_mid = (COUPON_best_ask+COUPON_best_bid)/2
    
        # ------------------------------- MARKET MAKING --------------------------------
        COUPON_pos = 0
        COC_pos = 0

        if 'COCONUT_COUPON' in state.position.keys():
            COUPON_pos = state.position["COCONUT_COUPON"]
        if 'COCONUT' in state.position.keys():
            COC_pos = state.position["COCONUT"]

        price = self.black_scholes_price(COC_mid,10000,247/365,0,0.1933)
        delta = self.black_scholes_delta(COC_mid,10000,247/365,0,0.1933)
        total_delta = int(round(COUPON_pos * delta))

        # take into account existing position
        required_quantity = -total_delta - COC_pos
        # take into account position limit
        position_limit = 300
        if abs(required_quantity) > position_limit:
            required_quantity = np.sign(required_quantity) * position_limit  

        # hedge
        if required_quantity > 0:
            volume = required_quantity
            if (COC_pos+required_quantity)>=300:
                volume = 299-COC_pos
            COC_orders.append(Order("COCONUT", COC_best_ask, volume))
        elif required_quantity < 0:
            volume = required_quantity
            if (COC_pos+required_quantity)<=-300:
                volume = -299-COC_pos
            COC_orders.append(Order("COCONUT", COC_best_bid, volume))

        # send buy and sell orders for coupon
        if price>(COUPON_mid+3):
            volume = 20
            if (COUPON_pos+20)>=600:
                volume = 599-COUPON_pos
            COUPON_orders.append(Order("COCONUT_COUPON", COUPON_best_ask, volume))
            
        if price<(COUPON_mid-3):
            volume = -20
            if (COUPON_pos-20)<=-600:
                volume = -599-COUPON_pos
            COUPON_orders.append(Order("COCONUT_COUPON", COUPON_best_bid, volume))
            
        

        result["COCONUT"] = COC_orders
        result["COCONUT_COUPON"] = COUPON_orders

        trader_data ="SAMPLE"
        conversions=1

        # returns a list of orders that the algo sends to the market
        return result, conversions, trader_data
    
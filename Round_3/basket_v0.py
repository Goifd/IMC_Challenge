from Round_3.datamodel import OrderDepth, UserId, TradingState, Order
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

    # number of historical mid_price used to predict new mid_price
    starfruit_dim = 4
    starfruit_cache = []
    POSITION_LIMIT = {'STARFRUIT' : 20, 'AMETHYSTS' : 20, 'CHOCOLATE':250, 'STRAWBERRIES':350,'ROSES':60,'GIFT_BASKET':60}

    

    def run(self, state: TradingState):
        BT_orders: List[Order] = []
        ROSES_orders: List[Order] = []
        CHOC_orders: List[Order] = []
        STRAW_orders: List[Order] = []
        result = {'AMETHYSTS' : [], 'STARFRUIT': [], 'ORCHIDS':[], 'CHOCOLATE':[], 'STRAWBERRIES':[], 'ROSES':[],'GIFT_BASKET':[]}   
        # get the prices
        # ROSES
        # CHOCOLATE
        # STRAWBERRIES
        # GIFT_BASKET

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
        GF_theor_ask = 6*STRAWBERRIES_best_ask+4*CHOCOLATE_best_ask+ROSES_best_ask
        GF_theor_bid = 6*STRAWBERRIES_best_bid+4*CHOCOLATE_best_bid+ROSES_best_bid

        basket_pos = 0
        # check result of previous iteration, settle it on neigh market
        if 'GIFT_BASKET' in state.position.keys():
            basket_pos = state.position["GIFT_BASKET"]
            ROSES_pos = 0
            STRAW_pos = 0
            CHOC_pos = 0
            if 'ROSES' in state.position.keys():
                ROSES_pos = state.position['ROSES']

            if 'STRAWBERRIES' in state.position.keys():
                STRAW_pos = state.position['STRAWBERRIES']

            if 'CHOCOLATE' in state.position.keys():
                CHOC_pos = state.position['CHOCOLATE']

            # calculate hedge order sizes
            ROSES_hedge = min(-basket_pos-ROSES_pos, 59, key=abs)
            STRAW_hedge = min(-basket_pos*6-STRAW_pos, 349, key=abs)
            CHOC_hedge = min(-basket_pos*4-CHOC_pos, 249, key=abs)
            # hedge basket position
            if basket_pos < 0: # we buy to hedge
                ROSES_orders.append(Order("ROSES", ROSES_best_ask, ROSES_hedge))
                STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask, STRAW_hedge))
                CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_ask, CHOC_hedge))
            elif basket_pos > 0: # we sell to hedge
                ROSES_orders.append(Order("ROSES", ROSES_best_bid, ROSES_hedge))
                STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid, STRAW_hedge))
                CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_bid, CHOC_hedge))
        


        max_ask_quant = -60 - basket_pos
        max_bid_quant = 60 - basket_pos

        # best_bid = max(GF_theor_bid, GIFT_BASKET_best_bid)-1
        # best_ask = min(GF_theor_ask, GIFT_BASKET_best_ask)+1

        mid_price = int(round((GIFT_BASKET_best_ask+GIFT_BASKET_best_bid)/2))
        best_bid = GIFT_BASKET_best_bid
        best_ask = GIFT_BASKET_best_ask

        BT_orders.append(Order("GIFT_BASKET", mid_price-3, max_bid_quant))
        BT_orders.append(Order("GIFT_BASKET", mid_price+3, max_ask_quant))


        result["GIFT_BASKET"] = BT_orders
        result["ROSES"] = ROSES_orders
        result["CHOCOLATE"] = CHOC_orders
        result["STRAWBERRIES"] = STRAW_orders

        traderData ="SAMPLE"
        conversions=1

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
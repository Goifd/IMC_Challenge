from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Trade, TradingState
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
    starfruit_dim = 4
    starfruit_cache = []
    POSITION_LIMIT = {'STARFRUIT' : 20, 'AMETHYSTS' : 0}

    # basket caches
    basket_cache = []
    theor_basket_cache = []
    diff_cache = []
    rolling_diff_cache = []
    rolling_dev_diff_cache = []

    choch_diff_cache = []
    rose_diff_cache = []
    straw_diff_cache = []
    

    def calc_next_price_starfruit(self):
        # bananas cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price

        # coef = [0.16179295, 0.14453001, 0.20387022, 0.16503886, 0.31240748]
        # intercept = 61.6762187870645
        coef = [0.1871, 0.2132, 0.2599, 0.3393]
        intercept =  2.0597
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
            # best_ask = next(iter(order_depth.sell_orders.items()))
            return best_ask
        
        # get lowest bid
        if len(order_depth.buy_orders) != 0 and side == 'buy':
            best_bid, best_bid_amount = list(order_depth.buy_orders.items())[-1]
            # best_bid = next(iter(order_depth.buy_orders.items()))
            return best_bid
        
    def compute_orders_regression(self, product, order_depth, acc_bid, acc_ask, LIMIT):
        orders: list[Order] = []

        best_sell_pr = self.extract_best_order_price(order_depth, side='sell')
        best_buy_pr  = self.extract_best_order_price(order_depth, side='buy')

        cpos = self.position[product]

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1
        adjustment = 0 # int((-self.position["STARFRUIT"])/10)
        bid_pr = min(undercut_buy, acc_bid)+adjustment # we will shift this by 1 to beat this price
        sell_pr = max(undercut_sell, acc_ask)+adjustment
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
        

        # trading params
        dev_signal = 0.5
        average_len = 20
        # buy/sell price, quantity (order sizing)
        BT_orders: List[Order] = []


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

        # ----------------------------------------------------------- ROUND 1 -----------------------------------------------------

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

        # -------------------------------------------
        orders: List[Order] = []
        ask_price = 0
        bid_price = 0
        
        if state.position != {}:
            buy_value, buy_quant = next(iter(state.order_depths["AMETHYSTS"].buy_orders.items()))
            sell_value, sell_quant = next(iter(state.order_depths["AMETHYSTS"].sell_orders.items()))

            ask_quant = -19 - state.position["AMETHYSTS"]
            bid_quant = 19 - state.position["AMETHYSTS"]

            adjustment = 0 # int((-self.position["AMETHYSTS"])/14)

            if state.position["AMETHYSTS"] > -19:
                orders.append(Order("AMETHYSTS", 10002, ask_quant+adjustment))
            if state.position["AMETHYSTS"] < 19:
                orders.append(Order("AMETHYSTS", 9998, bid_quant+adjustment))
        elif state.position == {}:
                orders.append(Order("AMETHYSTS", 9999, 2))
                orders.append(Order("AMETHYSTS", 10001, -2))
        result["AMETHYSTS"] = orders
        # ------------------------------------------------------
        conversions = 0
        orders_orchid: list[Order] = []
        best_ask = INF
        best_bid = -INF
        if len(state.order_depths["ORCHIDS"].sell_orders) != 0:
            best_ask, best_ask_amount = list(state.order_depths["ORCHIDS"].sell_orders.items())[0] 
        if len(state.order_depths["ORCHIDS"].buy_orders) != 0:
            best_bid, best_bid_amount = list(state.order_depths["ORCHIDS"].buy_orders.items())[0]

        # check result of previous iteration, settle it on neigh market
        if 'ORCHIDS' in state.position.keys():
            orchid_pos = state.position["ORCHIDS"]
            max_ask_quant = -99 - orchid_pos
            max_bid_quant = 99 - orchid_pos

            conversions = -orchid_pos

        neigh_bid = state.observations.conversionObservations['ORCHIDS'].bidPrice
        neigh_ask = state.observations.conversionObservations['ORCHIDS'].askPrice
        imp_tar = state.observations.conversionObservations['ORCHIDS'].importTariff
        exp_tar = state.observations.conversionObservations['ORCHIDS'].exportTariff
        trans_fees = state.observations.conversionObservations['ORCHIDS'].transportFees
        sunlight = state.observations.conversionObservations['ORCHIDS'].sunlight
        humidity = state.observations.conversionObservations['ORCHIDS'].humidity

        # check if I can buy on island and sell to neighbours profitably
        profit = neigh_bid-best_ask-exp_tar-trans_fees
        if profit > 0:
            orders_orchid.append(Order("ORCHIDS", best_ask, 99))

        # check if I can buy from neighbours and sell on island profitably
        profit = best_bid-neigh_ask-imp_tar-trans_fees
        if profit > 0:
            orders_orchid.append(Order("ORCHIDS", best_bid, -99))


        result["ORCHIDS"] = orders_orchid

        # --------------------------------------------------------------
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
        # result["ROSES"] = ROSES_orders
        # result["CHOCOLATE"] = CHOC_orders
        # result["STRAWBERRIES"] = STRAW_orders

        if len(self.rolling_diff_cache)==average_len:
            self.rolling_diff_cache.pop(0)
            self.basket_cache.pop(0)
            self.diff_cache.pop(0)
            self.choch_diff_cache.pop(0)
            self.rose_diff_cache.pop(0)
            self.straw_diff_cache.pop(0)


        traderData ="SAMPLE"

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
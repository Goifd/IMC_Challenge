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
from Round_3.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders),
            conversions,
            "",
            "",
        ]))

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing["symbol"], listing["product"], listing["denomination"]])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append([
                    trade.symbol,
                    trade.price,
                    trade.quantity,
                    trade.buyer,
                    trade.seller,
                    trade.timestamp,
                ])

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sunlight,
                observation.humidity,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[:max_length - 3] + "..."

logger = Logger()


class Trader:
    # order_depths: Dict[Symbol, OrderDepth]
    POSITION_LIMIT = {'STARFRUIT' : 20, 'AMETHYSTS' : 20, 'CHOCOLATE':250, 'STRAWBERRIES':350,'ROSES':60,'GIFT_BASKET':60}

    # basket caches
    basket_cache = []
    theor_basket_cache = []
    diff_cache = []
    rolling_diff_cache = []
    rolling_dev_diff_cache = []

    buy_cache_time = []
    buy_cache_price = []
    sell_cache_time = []
    sell_cache_price = []

    in_trade_1 = False
    in_trade_2 = False
    entry_price = 0

    

    def run(self, state: TradingState):
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
        GF_theor_ask = 6*STRAWBERRIES_best_ask+4*CHOCOLATE_best_ask+ROSES_best_ask
        GF_theor_bid = 6*STRAWBERRIES_best_bid+4*CHOCOLATE_best_bid+ROSES_best_bid

        GF_theor_mid = (GF_theor_ask+GF_theor_bid)/2
        GF_mid = (GIFT_BASKET_best_ask+GIFT_BASKET_best_bid)/2

        self.basket_cache.append(GF_mid)
        self.theor_basket_cache.append(GF_theor_mid)

        diff = GF_mid-GF_theor_mid
        self.diff_cache.append(diff)

        rolling = np.mean(self.diff_cache)
        self.rolling_diff_cache.append(rolling)

        rolling_dev = np.std(self.diff_cache)/2
        self.rolling_dev_diff_cache.append(rolling_dev)
        


        # ------------------------------- STAT ARB ALGO -------------------------------

        if len(self.rolling_diff_cache)==40:
            # diff > rolling diff -> buy basket sell individual until price reverses
            if diff>rolling and not self.in_trade_2:
                if not self.in_trade_1: # get into trade
                    self.in_trade_1 = True
                    self.entry_price = diff
                    # buy basket -> only go to best bid not to best ask
                    BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_ask, 10))

                    self.buy_cache_time.append(state.timestamp)
                    self.buy_cache_price.append(GIFT_BASKET_best_ask)

                    # sell individuals
                    ROSES_orders.append(Order("ROSES", ROSES_best_bid, -10))
                    STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid, -60))
                    CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_bid, -40))
                    
                    #print('Get into diff>rolling diff trade at: ', GIFT_BASKET_best_bid+1, ' diff: ' , diff, ' rollingd diff: ', rolling)
                
                if self.in_trade_1 and (rolling+rolling_dev) < diff: # reversal happened -> get out of trade
                    self.in_trade_1 = False
                    # sell basket
                    BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_bid, -10))

                    self.sell_cache_time.append(state.timestamp)
                    self.sell_cache_price.append(GIFT_BASKET_best_bid)

                    # buy individuals
                    ROSES_orders.append(Order("ROSES", ROSES_best_ask, 10))
                    STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask, 60))
                    CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_ask, 40))
                    #print('Get out of trade diff>rolling diff trade at: ', GIFT_BASKET_best_ask-1, ' diff: ' , diff, ' rolling diff: ', rolling)

                self.entry_price = diff

            # diff < rolling diff -> sell basket buy individual until price reverses
            elif rolling>diff and not self.in_trade_1: # get into trade
                if not self.in_trade_2:
                    self.in_trade_2 = True
                    self.entry_price = diff
                    # sell basket
                    BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_bid, -10))

                    self.sell_cache_time.append(state.timestamp)
                    self.sell_cache_price.append(GIFT_BASKET_best_bid)

                    # buy individuals
                    ROSES_orders.append(Order("ROSES", ROSES_best_ask, 10))
                    STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_ask, 60))
                    CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_ask, 40))
                    #print('Get into trade diff<rolling diff trade at: ', GIFT_BASKET_best_ask-1, ' diff: ' , diff, ' rolling diff: ', rolling)

                if self.in_trade_2 and (rolling-rolling_dev) > diff: # reversal happened -> get out of trade
                    self.in_trade_2 = False
                    # buy basket
                    BT_orders.append(Order("GIFT_BASKET", GIFT_BASKET_best_ask, 10))

                    self.buy_cache_time.append(state.timestamp)
                    self.buy_cache_price.append(GIFT_BASKET_best_ask)
                    # sell individuals
                    ROSES_orders.append(Order("ROSES", ROSES_best_bid, -10))
                    STRAW_orders.append(Order("STRAWBERRIES", STRAWBERRIES_best_bid, -60))
                    CHOC_orders.append(Order("CHOCOLATE", CHOCOLATE_best_bid, -40))
                    #print('Get out of diff<rolling diff trade at: ', GIFT_BASKET_best_bid+1, ' diff: ' , diff, ' rollingd diff: ', rolling)

                self.entry_price = diff
            



        result["GIFT_BASKET"] = BT_orders
        result["ROSES"] = ROSES_orders
        result["CHOCOLATE"] = CHOC_orders
        result["STRAWBERRIES"] = STRAW_orders

        if len(self.rolling_diff_cache)==40:
            self.rolling_diff_cache.pop(0)
            self.basket_cache.pop(0)
            self.diff_cache.pop(0)

        trader_data ="SAMPLE"
        conversions=1

        #logger.flush(state, result, conversions, trader_data)

        if state.timestamp == 99900:
            print(self.buy_cache_time)
            print(self.buy_cache_price)

            print(self.sell_cache_time)
            print(self.sell_cache_price)

        # returns a list of orders that the algo sends to the market
        return result, conversions, trader_data
    
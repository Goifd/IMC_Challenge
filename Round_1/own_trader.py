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
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
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

    position = {'STARFRUIT' : 0, 'AMETHYSTS' : 0}

    # number of historical mid_price used to predict new mid_price
    starfruit_dim = 4
    starfruit_cache = []
    starfruit_ask_cache = []
    starfruit_bid_cache = []
    POSITION_LIMIT = {'STARFRUIT' : 19, 'AMETHYSTS' : 0}

    def calc_next_price_starfruit(self):
        # bananas cache stores price from 1 day ago, current day resp
        # by price, here we mean mid price

        coef = [0.1871, 0.2132, 0.2599, 0.3393]
        intercept =  2.0597
        nxt_price = intercept
        for i, val in enumerate(self.starfruit_cache):
            nxt_price += val * coef[i]

        return int(round(nxt_price))
    
    def calc_next_askbid_starfruit(self):

        # ask coefs
        ask_coef = [0.2117, 0.2195, 0.2557, 0.3126]
        ask_intercept =  2.9417
        nxt_ask = ask_intercept
        for i, val in enumerate(self.starfruit_ask_cache):
            nxt_ask += val * ask_coef[i]

        # bid coefs
        bid_coef = [0.2130, 0.2262, 0.2547, 0.3055]
        bid_intercept =  3.2342
        nxt_bid = bid_intercept
        for i, val in enumerate(self.starfruit_bid_cache):
            nxt_bid += val * bid_coef[i]

        return int(round(nxt_ask)), int(round(nxt_bid))
        

    def save_position(self, state:TradingState):
        '''
        Save the current position in every instrument.
        '''
        for key, val in state.position.items():
            self.position[key] = val


    def run(self, state: TradingState):

        orders: list[Order] = []
        result = {'AMETHYSTS' : [], 'STARFRUIT': []}  
        self.save_position(state)   

        best_ask=0
        best_bid=0

        # get highest ask
        if len(state.order_depths["STARFRUIT"].sell_orders):
            best_ask, best_ask_amount = list(state.order_depths["STARFRUIT"].sell_orders.items())[0] 
        # get lowest bid
        if len(state.order_depths["STARFRUIT"].buy_orders):
            best_bid, best_bid_amount = list(state.order_depths["STARFRUIT"].buy_orders.items())[0]

        self.starfruit_cache.append((best_bid+best_ask)/2)
        self.starfruit_ask_cache.append(best_ask)
        self.starfruit_bid_cache.append(best_bid)

        starfruit_price = 0
        ask_price = 0
        bid_price = 0

        

        if len(self.starfruit_cache) == self.starfruit_dim:
            starfruit_price = self.calc_next_price_starfruit()
            ask_price, bid_price = self.calc_next_askbid_starfruit()
        
        ask_quant = -19 - self.position["STARFRUIT"]
        bid_quant = 19 - self.position["STARFRUIT"]
        adjustment = int((-self.position["STARFRUIT"])/10)
        # /12 -> 1000
        # /11 -> 984
        # /10 -> 1097
        # /9 -> 1034
        # /8 -> 844 
        # /7 -> 744
        # /6 -> -210
        # without 767

        # worst_sell, best_ask_amount = list(state.order_depths["STARFRUIT"].sell_orders.items())[-1]
        # worst_buy, best_bid_amount = list(state.order_depths["STARFRUIT"].buy_orders.items())[-1] 

        # worst_sell -= 1
        # worst_buy += 1

        # ask_price = max( worst_sell, ask_price)
        # bid_price = min(worst_buy, bid_price)

        if self.position["STARFRUIT"] > -19:
            orders.append(Order("STARFRUIT", ask_price+adjustment, ask_quant))
        if self.position["STARFRUIT"] < 19:
            orders.append(Order("STARFRUIT", bid_price+adjustment, bid_quant))


        if len(self.starfruit_cache) == self.starfruit_dim:
            for product in ["STARFRUIT"]:
                result[product] += orders


        # clear cache from one value if full and cache the new mid value
        if len(self.starfruit_cache) == self.starfruit_dim:
            self.starfruit_cache.pop(0)
            self.starfruit_ask_cache.pop(0)
            self.starfruit_bid_cache.pop(0)


        traderData = ""
        conversions = 0

        logger.flush(state, result, conversions, traderData)

        # returns a list of orders that the algo sends to the market
        return result, conversions, traderData
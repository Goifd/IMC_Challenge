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
    
    def run(self, state: TradingState):

        orders: list[Order] = []
        result = {'AMETHYSTS' : [], 'STARFRUIT': [], 'ORCHIDS': []} 
        trader_data = ""
        conversions = 0  

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

        

        # get neigh market data
        neigh_bid = state.observations.conversionObservations['ORCHIDS'].bidPrice
        neigh_ask = state.observations.conversionObservations['ORCHIDS'].askPrice
        imp_tar = state.observations.conversionObservations['ORCHIDS'].importTariff
        exp_tar = state.observations.conversionObservations['ORCHIDS'].exportTariff
        trans_fees = state.observations.conversionObservations['ORCHIDS'].transportFees

        # check if I can buy on island and sell to neighbours profitably
        profit = neigh_bid-best_ask-exp_tar-trans_fees
        if profit > 0:
            orders.append(Order("ORCHIDS", best_ask, 99))

        # check if I can buy from neighbours and sell on island profitably
        profit = best_bid-neigh_ask-imp_tar-trans_fees
        if profit > 0:
            orders.append(Order("ORCHIDS", best_bid, -99))


        result["ORCHIDS"] = orders

        logger.flush(state, result, conversions, trader_data)

        # returns a list of orders that the algo sends to the market
        return result, conversions, trader_data
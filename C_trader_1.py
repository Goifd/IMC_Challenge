from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

class Trader:

    def run(self, state: TradingState):
        # Only method required. It takes all buy and sell orders for all symbols as an input, and outputs a list of orders to be sent
        print("traderData: " + state.traderData + "\n")
        print("Observations: " + str(state.observations) + "\n")
        result = {}
        # First, gather all unique prices from both buy and sell orders

        all_prices = set(state.order_depths['AMETHYSTS'].buy_orders.keys()) | set(state.order_depths['AMETHYSTS'].sell_orders.keys())

        orders: List[Order] = []
        ask_price = 0
        bid_price = 0
        if state.position != {}:
                buy_value, buy_quant = next(iter(state.order_depths["AMETHYSTS"].buy_orders.items()))
                sell_value, sell_quant = next(iter(state.order_depths["AMETHYSTS"].sell_orders.items()))
                print(f"undercutting bid price @ : {buy_value}")
                print(f"undercutting ask price @ : {sell_value}")
                ask_quant = -19 - state.position["AMETHYSTS"]
                bid_quant = 19 - state.position["AMETHYSTS"]
                if state.position["AMETHYSTS"] > -19:
                        orders.append(Order("AMETHYSTS", 10003, ask_quant))
                        all_prices.add(ask_price)
                if state.position["AMETHYSTS"] < 19:
                        orders.append(Order("AMETHYSTS", 9997, bid_quant))
                        all_prices.add(bid_price)
                temp_store = state.position["AMETHYSTS"]
                print(f"Bid Price @ {bid_price} Quantity @ {bid_quant}")
                print(f"Ask Price @ {ask_price} Quantity @ {ask_quant}")
        elif state.position == {}:
                orders.append(Order("AMETHYSTS", 9999, 2))
                orders.append(Order("AMETHYSTS", 10001, -2))
        print(state.own_trades.get("AMETHYSTS", "No trades found for AMETHYSTS"))
        result["AMETHYSTS"] = orders


        # Sort the prices from high to low
        sorted_prices = sorted(all_prices, reverse=True)

        # Prepare the display data
        display_data = []
        for price in sorted_prices:
        # Get the quantity for buy orders at this price, or '-' if no buy order exists
                if price == bid_price:
                       buy_quantity = 19 - state.position["AMETHYSTS"]
                else:
                       buy_quantity = state.order_depths['AMETHYSTS'].buy_orders.get(price, '-')
        # Get the quantity for sell orders at this price, or '-' if no sell order exists

                if price == ask_price:
                        sell_quantity = -19 - state.position["AMETHYSTS"]
                else:
                        sell_quantity_raw = state.order_depths['AMETHYSTS'].sell_orders.get(price, '-')
                        sell_quantity = abs(sell_quantity_raw) if isinstance(sell_quantity_raw, int) else sell_quantity_raw

        # Append a tuple of the buy quantity, price, and sell quantity
                display_data.append((buy_quantity, price, sell_quantity))

        # Print the header
        print(f"{'Buy Quantity':<15} | {f'Price of {'AMETHYSTS'}':<10} | {'Sell Quantity':<15}")

        print("-" * 42)
        print(state.position)

        # Now, print each row
        for buy_qty, price, sell_qty in display_data:
                print(f"{str(buy_qty):<15} | {price:<10} | {str(sell_qty):<15}")


        traderData = "AMETHYSTS" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 1
        return result, conversions, traderData
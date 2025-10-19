
import pandas as pd


data =  {'e': 'outboundAccountPosition', 'E': 1711041463007, 'u': 1711041463007, 'B': [{'a': 'BTC', 'f': '0.18344000', 'l': '0.00000000'}, {'a': 'USDT', 'f': '62873.00788380', 'l': '0.00000000'}]}
data2 = {'e': 'executionReport',
         'E': 1711041391403,
         's': 'BTCUSDT',
         'c': 'gAzyZu6WAO7wA4CzJo8DPH',
         'S': 'BUY',
         'o': 'LIMIT',
         'f': 'GTC',
         'q': '0.00451000',
         'p': '66552.45000000',
         'P': '0.00000000',
         'F': '0.00000000',
         'g': -1,
         'C': '',
         'x': 'NEW',
         'X': 'NEW',
         'r': 'NONE',
         'i': 3646073,
         'l': '0.00000000',
         'z': '0.00000000',
         'L': '0.00000000',
         'n': '0',
         'N': None,
         'T': 1711041391403,
         't': -1,
         'I': 8239619,
         'w': True,
         'm': False,
         'M': False,
         'O': 1711041391403,
         'Z': '0.00000000',
         'Y': '0.00000000',
         'Q': '0.00000000',
         'W': 1711041391403,
         'V': 'EXPIRE_MAKER'}
data3 = {'symbol': 'BTCUSDT',
         'orderId': 3646073,
         'orderListId': -1,
         'clientOrderId': 'gAzyZu6WAO7wA4CzJo8DPH',
         'transactTime': 1711041391403,
         'price': '66552.45000000',
         'origQty': '0.00451000',
         'executedQty': '0.00451000',
         'cummulativeQuoteQty': '300.14562310',
         'status': 'FILLED',
         'timeInForce': 'GTC',
         'type': 'LIMIT',
         'side': 'BUY',
         'workingTime': 1711041391403,
         'fills': [{'price': '66550.81000000', 'qty': '0.00301000', 'commission': '0.00000000', 'commissionAsset': 'BTC', 'tradeId': 954099},
                   {'price': '66551.79000000', 'qty': '0.00150000', 'commission': '0.00000000', 'commissionAsset': 'BTC', 'tradeId': 954100}],
         'selfTradePreventionMode': 'EXPIRE_MAKER'}
data3.pop('fills', None)

data_frame = pd.DataFrame({key: [value] for key, value in data2.items()}).drop(columns=['E','c','o','f','P','F','g','C','X','r','i','l','z','L','n','N','T','t','I','w','m','M','O','Z','Y','Q','W','V'])
data_frame = pd.DataFrame(data['B'])
data_frame = pd.DataFrame({key: [value] for key, value in data3.items()}).drop(columns=['orderId','orderListId','clientOrderId','transactTime','cummulativeQuoteQty','timeInForce','workingTime','selfTradePreventionMode'])
print(data_frame)
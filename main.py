from transformers import AutoTokenizer, AutoModelForCausalLM,pipeline,BitsAndBytesConfig 
import torch
import re
from alpaca.trading.client import TradingClient 
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import requests
import json
import time 
import yfinance as yf
from datetime import datetime



url = "https://api.polygon.io/v2/reference/news?limit=10&apiKey=YOUR_API_KEY"
tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Llama-8B")
model = AutoModelForCausalLM.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Llama-8B",torch_dtype="auto", quantization_config=BitsAndBytesConfig(load_in_8bit=True))  
device = "cuda" if torch.cuda.is_available() else "cpu"
news = requests.get(url).text
news_collect = json.loads(news)

key = 'ENTER YOUR KEY'
secret = 'ENTER YOUR API'
trading_client = TradingClient(key, secret)

trade_status = True
stocks = []
stocks_neg = []

def sent_getter():
        for x in range(2):
            news = news_collect["results"][x-1]["description"]
            tickers = news_collect["results"][x-1]["tickers"]
            messages = f"You are to roleplay as a Professional Stock Advisor (for entertainment purposes) and analyze the sentiment of a given news headline. Your response must respond with either [POSITIVE] or [NEGATIVE] after </think> to clearly indicate sentiment. Keep your explanation concise—under 200 words—and focus only on the key factors influencing the sentiment +{news}"
            inputs = tokenizer(messages, return_tensors="pt").to("cuda")
            generated_ids = model.generate(**inputs, max_length=850)
            outputs = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
            res = re.findall(r"\[(.*?)\]", str(outputs))
            final_sentiment = res[-1]
            if final_sentiment == "POSITIVE":
                print(tickers[x-1])
                stocks.append(tickers[x-1])
            elif final_sentiment == "NEGATIVE":
                stocks_neg.append(tickers[x-1])

def buy_start():  
    while trade_status:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        if current_time == "10:30:00" or current_time == "12:00:00" or  current_time == "14:30:00":
            stocks.clear()
            sent_getter() 
        if len(stocks) == 0:
            sell_start() 
        
        main_ticker = yf.Ticker(stocks[0])
        data = main_ticker.history(interval='1m',period='5d')

        data['EMA12'] = data["Close"].ewm(span=12,adjust=False).mean()
        data['EMA26'] = data["Close"].ewm(span=26,adjust=False).mean()
        data['MACD'] = data['EMA26']-data['EMA12']
        data['Signal'] = data["MACD"].ewm(span=9,adjust=False).mean()
        data["RSI"] = ta.rsi(data["Close"])

        if data.iloc[-1]["MACD"]>data.iloc[-1]["Signal"] or data.iloc[-1]["RSI"]>50:
                market_order_data = MarketOrderRequest(
                symbol=stocks[0], qty=5, side=OrderSide.BUY, time_in_force=TimeInForce.DAY
                )
                buy = trading_client.submit_order(market_order_data)
                print("Buy order submitted.")
        elif data.iloc[-1]["MACD"]<data.iloc[-1]["Signal"] or data.iloc[-1]["RSI"]<50:
            market_order_data = MarketOrderRequest(
            symbol=stocks[0], qty=5, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
            trading_client.submit_order(market_order_data)
            print("Sell order submitted.")
        time.sleep(60) 

def sell_start():
    
    while trade_status:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        if current_time == "10:30:00" or current_time == "12:00:00" or current_time == "14:30:00":
            stocks_neg.clear()
            sent_getter()
        if len(stocks_neg) == 0:
            buy_start()
        main_ticker = yf.Ticker(stocks_neg[0])
        data = main_ticker.history(interval='1m',period='5d')

        data['EMA12'] = data["Close"].ewm(span=12,adjust=False).mean()
        data['EMA26'] = data["Close"].ewm(span=26,adjust=False).mean()
        data['MACD'] = data['EMA26']-data['EMA12']
        data['Signal'] = data["MACD"].ewm(span=9,adjust=False).mean()
        data["RSI"] = ta.rsi(data["Close"])

        if data.iloc[-1]["MACD"]<data.iloc[-1]["Signal"] or data.iloc[-1]["RSI"]<50:
                market_order_data = MarketOrderRequest(
                symbol=stocks[0], qty=5, side=OrderSide.SELL, time_in_force=TimeInForce.DAY
                )
                trading_client.submit_order(market_order_data)
                print("Sell order submitted.")
        elif data.iloc[-1]["MACD"]>data.iloc[-1]["Signal"] or data.iloc[-1]["RSI"]>50:
            market_order_data = MarketOrderRequest(
            symbol=stocks[0], qty=5, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
            trading_client.submit_order(market_order_data)
            print("Buy order submitted.")
        time.sleep(60)    

sent_getter()

original_length_pos = len(stocks)
original_length_neg = len(stocks_neg)

if original_length_pos>1:
    buy_start()
elif original_length_neg:
    sell_start()

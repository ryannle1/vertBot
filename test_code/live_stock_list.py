# Living List of stock that the user would like to monitor 
import pandas as pd
import yfinance as yf

# 1. Ask user what stocks to monitor
user_input = input("Enter stock symbols to monitor (comma-separated, e.g., AAPL,MSFT,GOOG): ")
stock_list = [symbol.strip().upper() for symbol in user_input.split(",")]

# 2. Download stock data using yfinance
data = yf.download(stock_list, period="1d", interval="1m", group_by='ticker', threads=True)

# 3. Display latest data
for ticker in stock_list:
    print(f"\nLatest data for {ticker}:")
    if ticker in data:
        print(data[ticker].tail(5))  # Show last 5 rows
    else:
        print("No data found or ticker might be invalid.")


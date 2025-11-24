import os
import tushare as ts

# Get Tushare token from environment
token = os.getenv('TUSHARE_TOKEN')
if not token:
    print("Error: TUSHARE_TOKEN not found in environment variables")
    exit(1)

# Initialize Tushare
ts.set_token(token)
pro = ts.pro_api()

# Test news API
symbol = '000002.SZ'  # Vanke A
print(f"Testing Tushare news API for {symbol}")

try:
    # Get news for the stock
    # Tushare news interface: news(src='sina', start_date='', end_date='', code='')
    df = pro.news(src='sina', code=symbol, start_date='20251101', end_date='20251124')
    
    if df is not None and not df.empty:
        print(f"\nFound {len(df)} news items:")
        print(df.head())
        print("\nColumns:", df.columns.tolist())
    else:
        print("No news found")
        
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying alternative news API...")
    
    try:
        # Try major_news interface
        df = pro.major_news(src='sina', start_date='20251101', end_date='20251124')
        if df is not None and not df.empty:
            print(f"\nFound {len(df)} major news items:")
            print(df.head())
    except Exception as e2:
        print(f"Alternative API also failed: {e2}")

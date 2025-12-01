#!/usr/bin/env python3
"""
Inspect AkShare stock_info functions for columns and sample data
"""

import akshare as ak
import pandas as pd

def inspect_function(func_name, func):
    print(f"\n=== {func_name} ===")
    try:
        df = func()
        if df is None or df.empty:
            print("Empty DataFrame")
            return
        print(f"Shape: {df.shape}")
        print("Columns:", list(df.columns))
        print("\nSample data:")
        print(df.head(3).to_string(index=False))
        # Check for time-related columns
        time_cols = [col for col in df.columns if any(word in col for word in ['时间', 'date', 'time', '发布'])]
        if time_cols:
            print(f"\nPotential time columns: {time_cols}")
            for col in time_cols:
                sample = df[col].dropna().head(1).iloc[0] if not df[col].dropna().empty else "No data"
                print(f"  {col}: {sample}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Inspecting AkShare stock info functions...\n")
    
    inspect_function("stock_info_global_ths", ak.stock_info_global_ths)
    inspect_function("stock_info_global_futu", ak.stock_info_global_futu)
    inspect_function("stock_info_broker_sina", ak.stock_info_broker_sina)

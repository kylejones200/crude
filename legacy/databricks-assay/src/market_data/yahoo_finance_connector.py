"""
Yahoo Finance Data Connector for Real-Time Crude Oil Prices

This module provides functionality to fetch real-time crude oil prices
from Yahoo Finance and integrate them with the crude assay analytics platform.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import time
from dataclasses import dataclass
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CrudePrice:
    """Data class for crude oil price information."""
    crude_id: str
    ticker: str
    current_price: float
    currency: str
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    market_status: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None


class YahooFinanceConnector:
    """
    Connector for fetching real-time crude oil prices from Yahoo Finance.
    """
    
    # Mapping of crude oil types to Yahoo Finance tickers
    CRUDE_TICKERS = {
        # Major Crude Oil Futures
        'WTI': 'CL=F',           # WTI Crude Oil Futures
        'BRENT': 'BZ=F',         # Brent Crude Oil Futures
        
        # Energy ETFs and Stocks
        'USO': 'USO',            # United States Oil Fund
        'UCO': 'UCO',            # ProShares Ultra Bloomberg Crude Oil
        'SCO': 'SCO',            # ProShares UltraShort Bloomberg Crude Oil
        'OIL': 'OIL',            # iPath Series B S&P GSCI Crude Oil Total Return Index ETN
        'USL': 'USL',            # United States 12 Month Oil Fund
        
        # Oil Company Stocks (as price proxies)
        'XOM': 'XOM',            # Exxon Mobil
        'CVX': 'CVX',            # Chevron
        'BP': 'BP',              # BP plc
        'RDS.A': 'SHEL',         # Shell
        'TOT': 'TTE',            # TotalEnergies
        'COP': 'COP',            # ConocoPhillips
        'EOG': 'EOG',            # EOG Resources
        'SLB': 'SLB',            # Schlumberger
        
        # Regional/Alternative Crude Proxies
        'GAZP.ME': 'GAZP.ME',    # Gazprom (Russian energy proxy)
        'PTR': 'PTR',            # PetroChina (Chinese energy proxy)
        'SNP': 'SNP',            # China Petroleum & Chemical Corp
    }
    
    # Mapping crude IDs to Yahoo Finance tickers
    CRUDE_ID_TO_TICKER = {
        # Direct futures mapping
        'WTI': 'CL=F',
        'BRENT': 'BZ=F',
        
        # Proxy mappings based on geographic/company relationships
        'ARB': 'CL=F',           # Use WTI as proxy for Arab Light
        'DUBAI': 'BZ=F',         # Use Brent as proxy for Dubai
        'MAYA': 'CL=F',          # Use WTI as proxy for Maya (geographically closer)
        'URALS': 'BZ=F',         # Use Brent as proxy for Urals
        'MARS': 'CL=F',          # Use WTI for Mars (US Gulf)
        'SAHARA': 'BZ=F',        # Use Brent for Sahara Blend
        'KUWAIT': 'BZ=F',        # Use Brent for Middle East crudes
        'IRANIAN_LIGHT': 'BZ=F', # Use Brent for Middle East crudes
        'CANADIAN_HEAVY': 'CL=F', # Use WTI for North American crudes
        'VENEZUELAN_HEAVY': 'CL=F', # Use WTI for Western Hemisphere
        'NIGERIAN_LIGHT': 'BZ=F',   # Use Brent for West African crudes
        'RUSSIAN_EXPORT': 'BZ=F',   # Use Brent for Russian crudes
        'NORTH_SEA_EKOFISK': 'BZ=F', # Use Brent for North Sea crudes
        'MEXICO_MAYA': 'CL=F',      # Use WTI for Mexican crudes
        'BRAZIL_MARLIM': 'CL=F',    # Use WTI for Latin American crudes
    }
    
    # Price adjustment factors for different crude types vs benchmarks
    PRICE_ADJUSTMENTS = {
        # Premium/discount vs WTI (for WTI-based proxies)
        'ARB': -1.50,            # Arab Light typically trades at discount to WTI
        'MAYA': -12.00,          # Maya Heavy significant discount due to gravity/sulfur
        'MARS': -1.00,           # Mars slight discount to WTI
        'CANADIAN_HEAVY': -15.00, # Heavy oil sands significant discount
        'VENEZUELAN_HEAVY': -18.00, # Heavy crude substantial discount
        'MEXICO_MAYA': -11.00,    # Maya heavy discount
        
        # Premium/discount vs Brent (for Brent-based proxies)
        'DUBAI': -0.75,          # Dubai slight discount to Brent
        'URALS': -2.50,          # Urals discount due to logistics/quality
        'SAHARA': +1.25,         # Sahara Blend premium for quality
        'KUWAIT': -1.25,         # Kuwait slight discount
        'IRANIAN_LIGHT': -2.00,  # Iran discount due to sanctions risk
        'NIGERIAN_LIGHT': +0.50, # Nigerian light sweet premium
        'RUSSIAN_EXPORT': -3.00, # Russian export blend discount
        'NORTH_SEA_EKOFISK': +0.25, # North Sea slight premium
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_crude_prices(self, crude_ids: List[str] = None, 
                        include_benchmark_data: bool = True) -> Dict[str, CrudePrice]:
        """
        Fetch current crude oil prices for specified crude IDs.
        
        Args:
            crude_ids: List of crude IDs to fetch prices for. If None, fetches all available.
            include_benchmark_data: Whether to include additional market data
            
        Returns:
            Dictionary mapping crude_id to CrudePrice objects
        """
        if crude_ids is None:
            crude_ids = list(self.CRUDE_ID_TO_TICKER.keys())
        
        prices = {}
        
        # Get unique tickers to minimize API calls
        tickers_needed = set()
        for crude_id in crude_ids:
            if crude_id in self.CRUDE_ID_TO_TICKER:
                tickers_needed.add(self.CRUDE_ID_TO_TICKER[crude_id])
        
        # Fetch ticker data
        ticker_data = {}
        for ticker in tickers_needed:
            try:
                ticker_info = yf.Ticker(ticker)
                info = ticker_info.info
                history = ticker_info.history(period='1d', interval='1m')
                
                if not history.empty:
                    current_price = history['Close'].iloc[-1]
                    volume = int(history['Volume'].iloc[-1]) if not pd.isna(history['Volume'].iloc[-1]) else 0
                    day_high = history['High'].max()
                    day_low = history['Low'].min()
                    
                    # Calculate change from previous close
                    if len(history) > 1:
                        prev_close = history['Close'].iloc[-2]
                        change = current_price - prev_close
                        change_percent = (change / prev_close) * 100 if prev_close != 0 else 0
                    else:
                        change = 0
                        change_percent = 0
                    
                    ticker_data[ticker] = {
                        'price': current_price,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': volume,
                        'day_high': day_high,
                        'day_low': day_low,
                        'info': info,
                        'timestamp': datetime.now()
                    }
                    
                    logger.info(f"Successfully fetched data for {ticker}: ${current_price:.2f}")
                    
            except Exception as e:
                logger.error(f"Error fetching data for ticker {ticker}: {e}")
                continue
        
        # Map ticker data to crude IDs
        for crude_id in crude_ids:
            if crude_id in self.CRUDE_ID_TO_TICKER:
                ticker = self.CRUDE_ID_TO_TICKER[crude_id]
                
                if ticker in ticker_data:
                    data = ticker_data[ticker]
                    
                    # Apply price adjustment if available
                    adjusted_price = data['price']
                    if crude_id in self.PRICE_ADJUSTMENTS:
                        adjusted_price += self.PRICE_ADJUSTMENTS[crude_id]
                    
                    prices[crude_id] = CrudePrice(
                        crude_id=crude_id,
                        ticker=ticker,
                        current_price=adjusted_price,
                        currency='USD',
                        change=data['change'],
                        change_percent=data['change_percent'],
                        volume=data['volume'],
                        timestamp=data['timestamp'],
                        market_status=data['info'].get('marketState', 'UNKNOWN'),
                        day_high=data['day_high'],
                        day_low=data['day_low']
                    )
                else:
                    logger.warning(f"No price data available for crude {crude_id} (ticker: {ticker})")
        
        return prices
    
    def get_historical_prices(self, crude_ids: List[str], 
                             period: str = '30d',
                             interval: str = '1d') -> pd.DataFrame:
        """
        Fetch historical price data for crude oils.
        
        Args:
            crude_ids: List of crude IDs
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with historical prices
        """
        historical_data = []
        
        # Get unique tickers
        tickers_needed = set()
        for crude_id in crude_ids:
            if crude_id in self.CRUDE_ID_TO_TICKER:
                tickers_needed.add(self.CRUDE_ID_TO_TICKER[crude_id])
        
        for ticker in tickers_needed:
            try:
                ticker_obj = yf.Ticker(ticker)
                history = ticker_obj.history(period=period, interval=interval)
                
                if not history.empty:
                    # Find crude IDs that use this ticker
                    related_crudes = [cid for cid, t in self.CRUDE_ID_TO_TICKER.items() 
                                    if t == ticker and cid in crude_ids]
                    
                    for crude_id in related_crudes:
                        crude_history = history.copy()
                        
                        # Apply price adjustments
                        if crude_id in self.PRICE_ADJUSTMENTS:
                            adjustment = self.PRICE_ADJUSTMENTS[crude_id]
                            for col in ['Open', 'High', 'Low', 'Close']:
                                if col in crude_history.columns:
                                    crude_history[col] += adjustment
                        
                        crude_history['crude_id'] = crude_id
                        crude_history['ticker'] = ticker
                        crude_history.reset_index(inplace=True)
                        
                        historical_data.append(crude_history)
                        
            except Exception as e:
                logger.error(f"Error fetching historical data for {ticker}: {e}")
                continue
        
        if historical_data:
            return pd.concat(historical_data, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def get_market_summary(self) -> Dict:
        """
        Get overall crude oil market summary.
        
        Returns:
            Dictionary with market summary information
        """
        summary = {}
        
        try:
            # Get WTI and Brent as main benchmarks
            wti = yf.Ticker('CL=F')
            brent = yf.Ticker('BZ=F')
            
            wti_info = wti.info
            brent_info = brent.info
            
            wti_history = wti.history(period='1d')
            brent_history = brent.history(period='1d')
            
            if not wti_history.empty:
                summary['WTI'] = {
                    'price': wti_history['Close'].iloc[-1],
                    'change': wti_history['Close'].iloc[-1] - wti_history['Open'].iloc[0],
                    'volume': int(wti_history['Volume'].iloc[-1]),
                    'high': wti_history['High'].max(),
                    'low': wti_history['Low'].min()
                }
            
            if not brent_history.empty:
                summary['Brent'] = {
                    'price': brent_history['Close'].iloc[-1],
                    'change': brent_history['Close'].iloc[-1] - brent_history['Open'].iloc[0],
                    'volume': int(brent_history['Volume'].iloc[-1]),
                    'high': brent_history['High'].max(),
                    'low': brent_history['Low'].min()
                }
            
            # Calculate spread
            if 'WTI' in summary and 'Brent' in summary:
                summary['WTI_Brent_Spread'] = summary['WTI']['price'] - summary['Brent']['price']
            
            summary['timestamp'] = datetime.now()
            summary['market_status'] = wti_info.get('marketState', 'UNKNOWN')
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def update_price_file(self, crude_ids: List[str] = None, 
                         output_file: str = None) -> str:
        """
        Update the prices CSV file with current market data.
        
        Args:
            crude_ids: List of crude IDs to update
            output_file: Output CSV file path
            
        Returns:
            Path to updated file
        """
        if output_file is None:
            output_file = 'resources/sample_data/live_prices.csv'
        
        prices = self.get_crude_prices(crude_ids)
        
        # Convert to DataFrame format compatible with existing system
        price_data = []
        
        # Add standard products with live crude-based pricing
        if 'WTI' in prices and 'BRENT' in prices:
            wti_price = prices['WTI'].current_price
            brent_price = prices['BRENT'].current_price
            avg_crude_price = (wti_price + brent_price) / 2
            
            # Estimate product prices based on crude prices
            # These are typical crack spreads that can be adjusted
            price_data.extend([
                {'product': 'LIGHTS', 'price_usd_bbl': avg_crude_price + 8.50},  # Gasoline premium
                {'product': 'MIDDLES', 'price_usd_bbl': avg_crude_price + 5.25}, # Diesel premium  
                {'product': 'HEAVIES', 'price_usd_bbl': avg_crude_price - 2.75}  # Fuel oil discount
            ])
        
        # Add individual crude prices
        for crude_id, price_obj in prices.items():
            price_data.append({
                'crude_id': crude_id,
                'price_usd_bbl': round(price_obj.current_price, 2),
                'change': round(price_obj.change, 2),
                'change_percent': round(price_obj.change_percent, 2),
                'volume': price_obj.volume,
                'timestamp': price_obj.timestamp.isoformat(),
                'market_status': price_obj.market_status
            })
        
        df = pd.DataFrame(price_data)
        
        # Ensure output directory exists
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        df.to_csv(output_file, index=False)
        logger.info(f"Updated prices saved to {output_file}")
        
        return output_file


def main():
    """Demo script for the Yahoo Finance connector."""
    
    connector = YahooFinanceConnector()
    
    print("🔄 Fetching real-time crude oil prices from Yahoo Finance...")
    
    # Test with a subset of crude IDs
    test_crudes = ['WTI', 'BRENT', 'ARB', 'MAYA', 'URALS', 'SAHARA']
    
    # Get current prices
    prices = connector.get_crude_prices(test_crudes)
    
    print(f"\n📊 CURRENT CRUDE OIL PRICES ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 70)
    
    for crude_id, price_obj in prices.items():
        change_symbol = "📈" if price_obj.change >= 0 else "📉"
        print(f"{crude_id:15s}: ${price_obj.current_price:7.2f} "
              f"{change_symbol} {price_obj.change:+6.2f} ({price_obj.change_percent:+5.1f}%)")
    
    # Get market summary
    print(f"\n🌍 MARKET SUMMARY")
    print("=" * 30)
    summary = connector.get_market_summary()
    
    if 'WTI' in summary:
        wti = summary['WTI']
        print(f"WTI Crude:   ${wti['price']:7.2f} ({wti['change']:+6.2f})")
    
    if 'Brent' in summary:
        brent = summary['Brent']  
        print(f"Brent Crude: ${brent['price']:7.2f} ({brent['change']:+6.2f})")
    
    if 'WTI_Brent_Spread' in summary:
        spread = summary['WTI_Brent_Spread']
        print(f"WTI-Brent Spread: ${spread:+6.2f}")
    
    # Update price file
    print(f"\n💾 Updating price file...")
    updated_file = connector.update_price_file(test_crudes)
    print(f"✅ Prices updated in: {updated_file}")
    
    # Get some historical data
    print(f"\n📈 Fetching 7-day historical data...")
    historical = connector.get_historical_prices(['WTI', 'BRENT'], period='7d')
    
    if not historical.empty:
        print(f"✅ Retrieved {len(historical)} historical data points")
        print("\nSample historical data:")
        print(historical[['Datetime', 'crude_id', 'Close']].head())
    
    print(f"\n🎯 Yahoo Finance integration complete!")


if __name__ == "__main__":
    main()

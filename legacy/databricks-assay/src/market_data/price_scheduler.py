"""
Automated Price Update Scheduler

This module provides scheduled updates of crude oil prices from Yahoo Finance,
integrating with the crude assay analytics platform.
"""

import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading
import json
import os

from .yahoo_finance_connector import YahooFinanceConnector


class PriceScheduler:
    """
    Scheduler for automated crude oil price updates.
    """
    
    def __init__(self, config_path: str = None):
        self.connector = YahooFinanceConnector()
        self.config_path = config_path or "conf/price_scheduler_config.json"
        self.config = self.load_config()
        self.is_running = False
        self.scheduler_thread = None
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> Dict:
        """Load scheduler configuration."""
        default_config = {
            "update_frequency_minutes": 15,
            "market_hours_only": True,
            "market_open_hour": 9,
            "market_close_hour": 17,
            "weekend_updates": False,
            "crude_ids": [
                "WTI", "BRENT", "ARB", "MAYA", "URALS", "SAHARA",
                "CANADIAN_HEAVY", "NIGERIAN_LIGHT", "RUSSIAN_EXPORT"
            ],
            "output_files": {
                "live_prices": "resources/sample_data/live_prices.csv",
                "historical_prices": "resources/sample_data/historical_prices.csv",
                "market_summary": "resources/sample_data/market_summary.json"
            },
            "price_change_threshold": 2.0,  # Alert if price changes > 2%
            "enable_alerts": True
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    config.setdefault(key, value)
                return config
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
                return default_config
        else:
            # Save default config
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def is_market_hours(self) -> bool:
        """Check if current time is during market hours."""
        if not self.config["market_hours_only"]:
            return True
        
        now = datetime.now()
        
        # Skip weekends if configured
        if not self.config["weekend_updates"] and now.weekday() >= 5:
            return False
        
        # Check market hours
        market_open = self.config["market_open_hour"]
        market_close = self.config["market_close_hour"]
        
        return market_open <= now.hour < market_close
    
    def update_prices(self):
        """Update crude oil prices from Yahoo Finance."""
        if not self.is_market_hours():
            self.logger.info("Outside market hours, skipping price update")
            return
        
        try:
            self.logger.info("Starting scheduled price update...")
            
            # Get current prices
            crude_ids = self.config["crude_ids"]
            prices = self.connector.get_crude_prices(crude_ids)
            
            if not prices:
                self.logger.warning("No prices retrieved from Yahoo Finance")
                return
            
            # Update price files
            live_prices_file = self.config["output_files"]["live_prices"]
            self.connector.update_price_file(crude_ids, live_prices_file)
            
            # Get market summary
            market_summary = self.connector.get_market_summary()
            summary_file = self.config["output_files"]["market_summary"]
            
            # Save market summary
            os.makedirs(os.path.dirname(summary_file), exist_ok=True)
            with open(summary_file, 'w') as f:
                json.dump(market_summary, f, indent=2, default=str)
            
            # Check for significant price changes
            if self.config["enable_alerts"]:
                self.check_price_alerts(prices)
            
            self.logger.info(f"Successfully updated {len(prices)} crude prices")
            
        except Exception as e:
            self.logger.error(f"Error updating prices: {e}")
    
    def check_price_alerts(self, prices: Dict):
        """Check for significant price changes and log alerts."""
        threshold = self.config["price_change_threshold"]
        
        for crude_id, price_obj in prices.items():
            if abs(price_obj.change_percent) >= threshold:
                alert_type = "🚨 PRICE ALERT" if abs(price_obj.change_percent) >= threshold * 2 else "⚠️  Price Change"
                self.logger.warning(
                    f"{alert_type}: {crude_id} changed {price_obj.change_percent:+.1f}% "
                    f"to ${price_obj.current_price:.2f}"
                )
    
    def start_scheduler(self):
        """Start the price update scheduler."""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        frequency = self.config["update_frequency_minutes"]
        
        # Schedule regular updates
        schedule.every(frequency).minutes.do(self.update_prices)
        
        # Schedule market summary updates (less frequent)
        schedule.every().hour.do(self.update_market_summary)
        
        # Daily historical data update
        schedule.every().day.at("18:00").do(self.update_historical_data)
        
        self.is_running = True
        
        # Run initial update
        self.logger.info(f"Starting price scheduler with {frequency} minute updates")
        self.update_prices()
        
        # Start scheduler in separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Price scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the price update scheduler."""
        self.is_running = False
        schedule.clear()
        self.logger.info("Price scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.is_running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def update_market_summary(self):
        """Update market summary information."""
        try:
            market_summary = self.connector.get_market_summary()
            summary_file = self.config["output_files"]["market_summary"]
            
            os.makedirs(os.path.dirname(summary_file), exist_ok=True)
            with open(summary_file, 'w') as f:
                json.dump(market_summary, f, indent=2, default=str)
            
            self.logger.info("Market summary updated")
            
        except Exception as e:
            self.logger.error(f"Error updating market summary: {e}")
    
    def update_historical_data(self):
        """Daily update of historical price data."""
        try:
            self.logger.info("Updating historical price data...")
            
            crude_ids = self.config["crude_ids"]
            historical = self.connector.get_historical_prices(
                crude_ids, period='30d', interval='1d'
            )
            
            if not historical.empty:
                hist_file = self.config["output_files"]["historical_prices"]
                os.makedirs(os.path.dirname(hist_file), exist_ok=True)
                historical.to_csv(hist_file, index=False)
                self.logger.info(f"Historical data updated: {len(historical)} records")
            
        except Exception as e:
            self.logger.error(f"Error updating historical data: {e}")
    
    def get_status(self) -> Dict:
        """Get scheduler status information."""
        return {
            "is_running": self.is_running,
            "update_frequency_minutes": self.config["update_frequency_minutes"],
            "market_hours_only": self.config["market_hours_only"],
            "is_market_hours": self.is_market_hours(),
            "crude_ids_tracked": len(self.config["crude_ids"]),
            "next_run": str(schedule.next_run()) if schedule.next_run() else None,
            "config_path": self.config_path
        }


def create_price_scheduler_service():
    """Create and return a price scheduler service instance."""
    return PriceScheduler()


if __name__ == "__main__":
    # Demo/test the scheduler
    scheduler = PriceScheduler()
    
    print("🔧 Price Scheduler Demo")
    print("=" * 30)
    
    # Show current status
    status = scheduler.get_status()
    print("Current Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Run a single update
    print("\n🔄 Running single price update...")
    scheduler.update_prices()
    
    # Show scheduler can be started (but don't actually run continuously)
    print("\n✅ Price scheduler ready to use")
    print("   To start continuous updates: scheduler.start_scheduler()")
    print("   To stop updates: scheduler.stop_scheduler()")

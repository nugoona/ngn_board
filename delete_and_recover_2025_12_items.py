import os
from google.cloud import bigquery
from datetime import datetime, timedelta
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# BigQuery client
client = bigquery.Client()

def delete_december_2025_items():
    """Delete daily_cafe24_items data for December 2025"""
    delete_query = """
    DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE payment_date >= '2025-12-01'
      AND payment_date <= '2025-12-31'
      AND LOWER(company_name) = 'piscess'
    """
    
    logging.info("Deleting daily_cafe24_items data for December 2025 (piscess)...")
    try:
        query_job = client.query(delete_query)
        query_job.result()
        logging.info("Successfully deleted December 2025 data")
        return True
    except Exception as e:
        logging.error(f"Failed to delete data: {e}")
        return False

def main():
    logging.info("=" * 80)
    logging.info("Starting December 2025 daily_cafe24_items data recovery")
    logging.info("=" * 80)
    
    # Delete existing data
    if not delete_december_2025_items():
        logging.error("Failed to delete existing data. Aborting.")
        return
    
    # Import and run recover script
    logging.info("Running recover_2025_12_items.py...")
    try:
        import recover_2025_12_items
        # Iterate through all days in December 2025
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2025, 12, 31)
        current_date = start_date
        day_count = 0
        total_days = 31
        
        while current_date <= end_date:
            day_count += 1
            date_str = current_date.strftime("%Y-%m-%d")
            logging.info(f"[{day_count}/{total_days}] Processing {date_str}...")
            
            try:
                recover_2025_12_items.execute_bigquery_for_date(date_str)
                logging.info(f"Completed {date_str}")
            except Exception as e:
                logging.error(f"Error processing {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        logging.info("=" * 80)
        logging.info("December 2025 data recovery completed!")
        logging.info("=" * 80)
        
    except Exception as e:
        logging.error(f"Error running recover script: {e}")

if __name__ == "__main__":
    main()


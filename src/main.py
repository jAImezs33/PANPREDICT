import os
import pandas as pd
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA
# from prophet import Prophet
import holidays
import requests
import logging
import pickle

# Define confidence levels for forecasting
CONFIDENCE_LEVELS = [90]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

def load_data(csv_path: str) -> pd.DataFrame:
    """Loads sales data from a CSV file."""
    logging.info(f"Loading data from {csv_path}...")
    try:
        # First try with semicolon separator (common in Spanish locales)
        try:
            df = pd.read_csv(
                csv_path,
                sep=';',
                parse_dates=['fecha'],
                dayfirst=True  # Assuming DD/MM/YYYY format, common in Spain
            )
        except Exception as e:
            # If semicolon fails, try with comma separator
            logging.info("Trying with comma separator...")
            df = pd.read_csv(
                csv_path,
                sep=',',
                parse_dates=['fecha'],
                dayfirst=True
            )
        
        # Handle different column name variations
        column_map = {}
        
        # Check for date column
        if 'fecha' not in df.columns and 'date' in df.columns:
            column_map['date'] = 'fecha'
        
        # Check for product column
        if 'articulo' in df.columns:
            pass  # Already using correct column name
        elif 'producto' in df.columns:
            column_map['producto'] = 'articulo'
        elif 'product' in df.columns:
            column_map['product'] = 'articulo'
            
        # Check for quantity column
        if 'unidades' in df.columns:
            pass  # Already using correct column name
        elif 'cantidad' in df.columns:
            column_map['cantidad'] = 'unidades'
        elif 'quantity' in df.columns:
            column_map['quantity'] = 'unidades'
        
        # Rename columns if needed
        if column_map:
            df = df.rename(columns=column_map)
        
        # Basic validation
        if not all(col in df.columns for col in ['fecha', 'articulo', 'unidades']):
            logging.error("CSV must contain date ('fecha'), product ('articulo' or 'producto'), and quantity ('unidades' or 'cantidad') columns.")
            logging.error(f"Found columns: {df.columns.tolist()}")
            return pd.DataFrame()
            
        logging.info(f"Successfully loaded {len(df)} rows.")
        return df
    except FileNotFoundError:
        logging.error(f"Error: The file was not found at {csv_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading the data: {e}")
        return pd.DataFrame()

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the raw sales data into the format required by StatsForecast."""
    logging.info("Preprocessing data...")
    if df.empty:
        logging.warning("Input DataFrame is empty. Skipping preprocessing.")
        return pd.DataFrame()
    
    try:
        # Make a copy to avoid modifying the original
        df = df.copy()
        
        # Standardize column names (case insensitive)
        column_map = {}
        date_cols = ['fecha', 'date', 'fechas', 'fecha_venta']
        product_cols = ['articulo', 'producto', 'product', 'item', 'descripcion']
        qty_cols = ['unidades', 'cantidad', 'quantity', 'ventas', 'sales']
        
        # Find matching columns (case insensitive)
        df_columns_lower = [str(col).lower() for col in df.columns]
        
        # Map date column
        for col in date_cols:
            if col in df_columns_lower:
                column_map[df.columns[df_columns_lower.index(col)]] = 'ds'
                break
                
        # Map product column
        for col in product_cols:
            if col in df_columns_lower:
                column_map[df.columns[df_columns_lower.index(col)]] = 'unique_id'
                break
                
        # Map quantity column
        for col in qty_cols:
            if col in df_columns_lower:
                column_map[df.columns[df_columns_lower.index(col)]] = 'y'
                break
        
        # Apply column renaming
        df = df.rename(columns=column_map)
        
        # Check if we have all required columns
        required_cols = ['ds', 'unique_id', 'y']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logging.error(f"Missing required columns after mapping: {missing_cols}")
            logging.error(f"Available columns: {df.columns.tolist()}")
            return pd.DataFrame()
        
        # Convert date to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(df['ds']):
            # Try different date formats
            date_formats = [
                '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', 
                '%Y/%m/%d', '%d-%m-%Y', '%Y%m%d',
                '%d/%m/%y', '%m/%d/%y', '%d-%m-%y'
            ]
            
            for fmt in date_formats:
                try:
                    df['ds'] = pd.to_datetime(df['ds'], format=fmt, errors='raise')
                    logging.info(f"Successfully parsed dates with format: {fmt}")
                    break
                except Exception as e:
                    continue
            else:
                # If no format worked, try without format (pandas will try to infer)
                try:
                    df['ds'] = pd.to_datetime(df['ds'], errors='raise')
                    logging.info("Successfully parsed dates with pandas inference")
                except Exception as e:
                    logging.error(f"Could not parse dates. Error: {e}")
                    return pd.DataFrame()
        
        # Ensure numeric values for sales (handle commas as decimal separators)
        if not pd.api.types.is_numeric_dtype(df['y']):
            df['y'] = df['y'].astype(str).str.replace(',', '.').astype(float, errors='ignore')
        
        # Convert to numeric, coercing errors to NaN
        df['y'] = pd.to_numeric(df['y'], errors='coerce')
        
        # Drop any rows with missing values
        initial_rows = len(df)
        df = df.dropna(subset=['ds', 'unique_id', 'y'])
        
        if len(df) < initial_rows:
            logging.warning(f"Dropped {initial_rows - len(df)} rows with missing values")
        
        # Ensure unique_id is string and strip whitespace
        df['unique_id'] = df['unique_id'].astype(str).str.strip()
        
        # Sort by date and unique_id
        df = df.sort_values(['unique_id', 'ds'])
        
        # Handle duplicate date-product combinations by summing quantities
        if df.duplicated(subset=['unique_id', 'ds']).any():
            logging.info("Found duplicate date-product combinations. Aggregating quantities...")
            df = df.groupby(['unique_id', 'ds'], as_index=False)['y'].sum()
        
        # Ensure we have at least 2 data points per product
        product_counts = df['unique_id'].value_counts()
        valid_products = product_counts[product_counts >= 2].index
        df = df[df['unique_id'].isin(valid_products)]
        
        if df.empty:
            logging.error("No valid data left after preprocessing. Need at least 2 data points per product.")
            return pd.DataFrame()
            
        # Ensure y is integer (since we can't sell fractions of items)
        df['y'] = df['y'].round().astype(int)
        
        # Ensure positive values
        df = df[df['y'] > 0]
        
        # Sort by product and date
        df = df.sort_values(['unique_id', 'ds'])
        
        logging.info(f"Preprocessing complete. Data shape: {df.shape}")
        logging.info(f"Products: {df['unique_id'].nunique()}")
        logging.info(f"Date range: {df['ds'].min().date()} to {df['ds'].max().date()}")
        
        # Ensure we only return the required columns in the correct order
        result = df[['unique_id', 'ds', 'y']].copy()
        return result.reset_index(drop=True)
        
    except Exception as e:
        logging.error(f"Error during preprocessing: {str(e)}", exc_info=True)
        return pd.DataFrame()
    logging.info("Data preprocessing complete.")
    return df_melted

def create_features_df(start_date, end_date, unique_ids: list) -> pd.DataFrame:
    """Creates exogenous features like holidays for the given date range."""
    logging.info(f"Creating features from {start_date.date()} to {end_date.date()}...")
    dates = pd.date_range(start_date, end_date, freq='D')
    df = pd.DataFrame({'ds': dates})

    # --- Holiday Feature ---
    es_holidays = holidays.Spain(prov='CT')
    df['holiday'] = df['ds'].isin([date for date, name in es_holidays.items()]).astype(int)
    logging.info(f"Added holiday feature. Found {df['holiday'].sum()} holidays.")

    # --- Create unique_id for all combinations ---
    if not unique_ids:
        logging.error("Cannot create features: unique_ids list is empty.")
        return pd.DataFrame()
    
    # Combine features with unique_ids
    final_features_df = pd.concat([df.assign(unique_id=uid) for uid in unique_ids], ignore_index=True)

    # --- Defensive fix: ensure only expected columns are returned in the correct order ---
    final_features_df = final_features_df[['unique_id', 'ds', 'holiday']]

    logging.info(f"Created features dataframe with shape {final_features_df.shape}")
    return final_features_df

def train_and_forecast(df: pd.DataFrame, X_df: pd.DataFrame, h: int, retrain: bool = False) -> pd.DataFrame:
    """Trains a time series model and returns the forecast."""
    logging.info("Training model and generating forecast...")
    
    # For very small datasets, we'll use a simpler model
    min_days_for_seasonality = 14  # Minimum days to attempt weekly seasonality
    
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    model_path = "models/statsforecast_model.pkl"
    
    # Check if we have enough data for seasonality
    days_of_data = df['ds'].nunique()
    use_seasonality = days_of_data >= min_days_for_seasonality
    
    logging.info(f"Days of data: {days_of_data}, Using seasonality: {use_seasonality}")
    
    # Initialize model
    if use_seasonality:
        models = [AutoARIMA(season_length=7)]  # Weekly seasonality
    else:
        models = [AutoARIMA(season_length=1)]  # No seasonality for small datasets
    
    # Initialize StatsForecast
    sf = StatsForecast(
        df=df,
        models=models,
        freq='D',  # Daily frequency
        n_jobs=-1  # Use all available cores
    )
    
    # Train model
    try:
        sf.fit()
        logging.info("Model trained successfully.")
    except Exception as e:
        logging.error(f"Error during model training: {e}")
        # Fallback to simple average if model training fails
        logging.info("Falling back to simple moving average...")
        # Calculate simple moving average
        forecast_df = df.groupby('unique_id')['y'].mean().reset_index()
        forecast_df['yhat'] = forecast_df['y']
        forecast_df['yhat_lower'] = forecast_df['y'] * 0.9  # 10% lower bound
        forecast_df['yhat_upper'] = forecast_df['y'] * 1.1  # 10% upper bound
        
        # Create date range for forecast
        last_date = df['ds'].max()
        date_range = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=h, freq='D')
        
        # Create forecast DataFrame
        forecast = pd.DataFrame({
            'ds': np.tile(date_range, len(forecast_df)),
            'unique_id': np.repeat(forecast_df['unique_id'], len(date_range)),
            'yhat': np.repeat(forecast_df['yhat'], len(date_range)),
            'yhat_lower': np.repeat(forecast_df['yhat_lower'], len(date_range)),
            'yhat_upper': np.repeat(forecast_df['yhat_upper'], len(date_range))
        })
        
        return forecast
    
    try:
        # Generate forecast
        logging.info(f"Generating {h}-day forecast...")
        forecast = sf.predict(h=h, level=CONFIDENCE_LEVELS)
        
        # For small datasets, ensure we have reasonable bounds
        if not use_seasonality:
            # Calculate simple moving average as fallback
            avg_sales = df.groupby('unique_id')['y'].mean()
            
            # Update forecast with moving average if predictions are unreasonable
            for product in avg_sales.index:
                if product in forecast.index:
                    forecast.loc[product, 'yhat'] = avg_sales[product]
                    forecast.loc[product, 'yhat_lower'] = avg_sales[product] * 0.9
                    forecast.loc[product, 'yhat_upper'] = avg_sales[product] * 1.1
        
        # Rename columns to be more descriptive
        forecast = forecast.rename(columns={
            'AutoARIMA': 'yhat',
            'AutoARIMA-lo-90': 'yhat_lower',
            'AutoARIMA-hi-90': 'yhat_upper'
        })
        
        return forecast.reset_index()
    except Exception as e:
        logging.error(f"Error during forecasting: {e}")
        # Fallback to simple average if forecasting fails
        logging.info("Falling back to simple average forecast...")
        forecast_df = df.groupby('unique_id')['y'].mean().reset_index()
        forecast_df['yhat'] = forecast_df['y']
        forecast_df['yhat_lower'] = forecast_df['y'] * 0.9  # 10% lower bound
        forecast_df['yhat_upper'] = forecast_df['y'] * 1.1  # 10% upper bound
        
        # Create date range for forecast
        last_date = df['ds'].max()
        date_range = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=h, freq='D')
        
        # Create forecast DataFrame
        forecast = pd.DataFrame({
            'ds': np.tile(date_range, len(forecast_df)),
            'unique_id': np.repeat(forecast_df['unique_id'], len(date_range)),
            'yhat': np.repeat(forecast_df['yhat'], len(date_range)),
            'yhat_lower': np.repeat(forecast_df['yhat_lower'], len(date_range)),
            'yhat_upper': np.repeat(forecast_df['yhat_upper'], len(date_range))
        })
        
        return forecast
    return final_forecast

def save_to_gsheets(forecast_df: pd.DataFrame, sheet_id: str):
    """Saves the forecast data to a Google Sheet."""
    logging.info(f"Saving forecast to Google Sheet ID: {sheet_id}")
    try:
        # --- Authentication ---
        # The GOOGLE_SERVICE_ACC_JSON env var should contain the JSON content
        creds_json_str = os.getenv('GOOGLE_SERVICE_ACC_JSON')
        if not creds_json_str:
            logging.error("GOOGLE_SERVICE_ACC_JSON environment variable not set.")
            return

        import json
        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)

        # --- Open Sheet and Worksheet ---
        spreadsheet = client.open_by_key(sheet_id)
        sheet_name = "Pronóstico"
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            logging.info(f"Found existing worksheet: '{sheet_name}'")
            worksheet.clear()
            logging.info("Cleared existing data.")
        except gspread.WorksheetNotFound:
            logging.info(f"Worksheet '{sheet_name}' not found, creating it...")
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")

        # --- Prepare Data for Writing ---
        # Pivot the forecast data to wide format
        forecast_wide = forecast_df.pivot(index='ds', columns='unique_id', values='yhat')
        forecast_wide = forecast_wide.reset_index().rename(columns={'ds': 'Fecha'})
        forecast_wide['Fecha'] = forecast_wide['Fecha'].dt.strftime('%Y-%m-%d')

        # --- Write to Sheet ---
        headers = [forecast_wide.columns.values.tolist()]
        data_to_write = forecast_wide.values.tolist()
        worksheet.update('A1', headers + data_to_write)

        logging.info(f"Successfully wrote {len(data_to_write)} rows to '{sheet_name}'.")
        # Note: Sparklines are best added via Google Apps Script or manually setting formulas.
        # A simple formula could be: =SPARKLINE(B2:I2)

    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"Spreadsheet with ID '{sheet_id}' not found. Check permissions and ID.")
    except Exception as e:
        logging.error(f"An error occurred while writing to Google Sheets: {e}")

def main():
    """Main function to run the forecast pipeline."""
    logging.info("Pan-Predict 90 process started.")

    # --- Configuration ---
    # In a real scenario, these would come from command-line arguments
    csv_path = "data/ventas.csv" # Example path
    google_sheet_id = os.getenv("GOOGLE_SHEET_ID")
    retrain_model = False # Example flag

    # --- ETL & Modeling Pipeline ---
    raw_data = load_data(csv_path)
    if raw_data.empty:
        logging.error("No data loaded. Exiting.")
        return

    processed_data = preprocess_data(raw_data)
    if processed_data.empty:
        logging.error("Data preprocessing resulted in an empty dataframe. Exiting.")
        return

    # Create features for the historical period and the forecast horizon
    HORIZON = 8
    start_date = processed_data['ds'].min()
    end_date = processed_data['ds'].max() + pd.Timedelta(days=HORIZON)
    features_df = create_features_df(start_date, end_date)

    # The features dataframe must have unique_id and ds to be merged correctly
    # Let's create a complete exogenous dataframe for all series
    unique_ids = processed_data['unique_id'].unique()
    X_df_full = pd.DataFrame()
    for uid in unique_ids:
        temp_df = features_df.copy()
        temp_df['unique_id'] = uid
        X_df_full = pd.concat([X_df_full, temp_df])

    forecast = train_and_forecast(processed_data, X_df=X_df_full, h=HORIZON, retrain=retrain_model)

    # --- Output ---
    if not forecast.empty and google_sheet_id:
        save_to_gsheets(forecast, google_sheet_id)
    else:
        logging.warning("Forecast is empty or Google Sheet ID is not configured. Skipping save.")

    logging.info("Pan-Predict 90 process finished.")

if __name__ == "__main__":
    main()

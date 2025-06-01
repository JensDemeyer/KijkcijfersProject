
import pandas as pd
import numpy as np
import re
from datetime import datetime
import pickle
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import joblib

def preprocess_input_data(input_df, holidays_path='./Data/CleanData/holidays_clean.csv', 
                         school_holidays_path='./Data/CleanData/school_holidays_clean.csv'):
    """
    Preprocess the input data in the same way as the training data was processed
    """
    # Load holidays data
    df_holidays = pd.read_csv(holidays_path, delimiter=';')
    df_holidays['date'] = pd.to_datetime(df_holidays['date'])
    
    df_school_holidays = pd.read_csv(school_holidays_path, delimiter=';')
    df_school_holidays['start_date'] = pd.to_datetime(df_school_holidays['start_date'])
    df_school_holidays['end_date'] = pd.to_datetime(df_school_holidays['end_date'])

    # Convert dates and times
    input_df['Datum'] = pd.to_datetime(input_df['Datum'], dayfirst=True)
    input_df['Start'] = pd.to_datetime(input_df['Start'], format='%H:%M:%S').dt.time
    
    # Convert duration to minutes
    def convert_duration(dur_str):
        h, m, s = map(int, dur_str.split(':'))
        return h * 60 + m + s / 60
    
    input_df['duration_min'] = input_df['Duur'].apply(convert_duration)
    
    # Create features
    input_df['weekday'] = input_df['Datum'].dt.dayofweek
    input_df['month'] = input_df['Datum'].dt.month
    input_df['hour'] = input_df['Start'].apply(lambda x: x.hour)
    
    # Minutes since midnight
    input_df['minutes_since_midnight'] = input_df['Start'].apply(lambda x: x.hour * 60 + x.minute)
    
    # Check if holiday
    def check_holiday(date):
        if date in df_holidays['date'].values:
            return 1
        for _, row in df_school_holidays.iterrows():
            if row['start_date'] <= date <= row['end_date']:
                return 1
        return 0
    
    input_df['is_holiday'] = input_df['Datum'].apply(check_holiday)
    input_df['is_weekend'] = input_df['weekday'].apply(lambda x: 1 if x >= 5 else 0)
    
    # Prime time feature (18:30 - 22:00)
    input_df['is_primetime'] = input_df['Start'].apply(
        lambda x: 1 if (18, 30) <= (x.hour, x.minute) <= (22, 0) else 0
    )
    
    # News program feature
    news_keywords = ['journaal', 'nieuws', 'sportweekend']
    news_pattern = re.compile('|'.join(news_keywords), flags=re.IGNORECASE)
    input_df['is_news'] = input_df['Programma'].apply(lambda x: 1 if news_pattern.search(str(x)) else 0)
    
    # Select and rename columns to match training data
    processed_df = input_df[['Zender', 'minutes_since_midnight', 'duration_min', 
                            'weekday', 'month', 'hour', 'is_primetime', 
                            'is_weekend', 'is_holiday', 'is_news']]
    
    processed_df = processed_df.rename(columns={'Zender': 'channel'})
    
    return processed_df

def main():

    model = joblib.load('best_xgb_model.pkl')

    # Read input data
    input_file = 'Input_voor_examen_VOORBEELD.csv'
    try:
        input_df = pd.read_csv(input_file, delimiter=';', encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return
    
    # Preprocess the input data
    processed_data = preprocess_input_data(input_df)
    
    # Make predictions
    predictions = model.predict(processed_data)
    
    # Add predictions to original dataframe
    input_df['Voorspelde_Kijkcijfers'] = predictions.round().astype(int)
    
    # Save results
    output_file = 'voorspellingen_kijkcijfers.csv'
    input_df.to_csv(output_file, index=False, sep=';')
    
    print(f"Voorspellingen succesvol opgeslagen in {output_file}")
    print("Voorspellingen:")
    print(input_df[['Programma', 'Zender', 'Datum', 'Start', 'Voorspelde_Kijkcijfers']])

if __name__ == "__main__":
    main()


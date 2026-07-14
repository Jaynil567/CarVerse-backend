import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

def train():
    csv_path = "./public/car_details.csv"
    model_output = "./pricing_model.joblib"
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Cannot train model.")
        return False
        
    print(f"Loiisv_path...")
    df = pd.read_csv(csv_path)
    
    # Select features that a seller can easily input
    features = [
        'KM', 
        'Fuel Type', 
        'Manufacturing Year', 
        'No of Owners', 
        'Transmission', 
        'Engine Capacity (cc)', 
        'Mileage (kmpl)', 
        'Seating Capacity'
    ]
    target = 'Old Car Price (Lakh)'
    
    # Drop rows with missing values in key columns
    df = df.dropna(subset=features + [target])
    
    X = df[features]
    y = df[target]
    
    print(f"Dataset shape: {X.shape}. Training Random Forest Model...")
    
    # Categorical and numerical columns
    categorical_cols = ['Fuel Type', 'No of Owners', 'Transmission']
    numerical_cols = ['KM', 'Manufacturing Year', 'Engine Capacity (cc)', 'Mileage (kmpl)', 'Seating Capacity']
    
    # Preprocessor using ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
        ])
    
    # Random Forest Regressor Pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])
    
    # Split data for evaluation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Fit the pipeline
    model_pipeline.fit(X_train, y_train)
    
    # Evaluate
    train_score = model_pipeline.score(X_train, y_train)
    test_score = model_pipeline.score(X_test, y_test)
    print(f"Model trained. R^2 Training Score: {train_score:.4f}, R^2 Test Score: {test_score:.4f}")
    
    # Print feature coefficients / importances (from the regressor)
    # Save the pipeline
    joblib.dump(model_pipeline, model_output)
    print(f"Model pipeline saved successfully to {model_output}")
    return True

if __name__ == "__main__":
    train()

"""
Crude Assay Regression Models

This module provides machine learning models for predicting crude oil properties
and valuations based on assay characteristics like API gravity, sulfur content,
and distillation cut yields.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split, cross_val_score
import pickle
import json
from typing import Dict, List, Tuple, Optional
import os


class CrudeAssayRegressor:
    """
    Advanced regression models for crude assay property prediction.
    
    Supports multiple model types:
    - Linear regression for baseline predictions  
    - Polynomial features for capturing non-linear relationships
    - Random Forest for complex interactions
    - Ridge regression for regularized predictions
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.polynomial_features = {}
        self.feature_names = ['api_gravity', 'sulfur_content', 'light_cuts', 'middle_cuts', 'heavy_cuts']
        self.target_names = ['gross_value', 'netback_value', 'quality_score', 'processing_index']
        
        # Product price assumptions (can be updated dynamically)
        self.product_prices = {
            'lights': 88.0,
            'middles': 82.0, 
            'heavies': 75.0
        }
        
        # Freight assumptions by region
        self.freight_rates = {
            'ME': 2.5,  # Middle East
            'WAF': 1.8,  # West Africa  
            'USG': 0.5,  # US Gulf
            'default': 2.0
        }
    
    def generate_synthetic_data(self, n_samples: int = 500) -> pd.DataFrame:
        """
        Generate synthetic but realistic crude assay data for training.
        
        Args:
            n_samples: Number of synthetic samples to generate
            
        Returns:
            DataFrame with assay properties and derived targets
        """
        np.random.seed(42)  # For reproducibility
        
        data = []
        
        for i in range(n_samples):
            # Generate correlated assay properties
            
            # API gravity: realistic distribution from 15-45°API
            api = np.random.beta(2, 2) * 30 + 15
            
            # Sulfur content: inversely correlated with API (light crudes tend to be sweeter)
            sulfur_base = 5.0 - (api - 15) / 30 * 4.0  # Base relationship
            sulfur = max(0.1, sulfur_base + np.random.normal(0, 0.8))
            sulfur = min(5.0, sulfur)
            
            # Distillation cuts: realistic yields that sum to 1.0
            # Light cuts correlate with API gravity
            light_base = 0.15 + (api - 15) / 30 * 0.3
            light = max(0.15, min(0.55, light_base + np.random.normal(0, 0.08)))
            
            # Heavy cuts anti-correlate with API
            heavy_base = 0.45 - (api - 15) / 30 * 0.25
            heavy = max(0.05, min(0.45, heavy_base + np.random.normal(0, 0.08)))
            
            # Middle cuts: remainder to sum to 1.0
            middle = max(0.25, min(0.65, 1.0 - light - heavy))
            
            # Normalize to exactly 1.0
            total = light + middle + heavy
            light /= total
            middle /= total  
            heavy /= total
            
            # Calculate realistic derived properties
            gross_value = self._calculate_gross_value(light, middle, heavy)
            
            # Add realistic noise to gross value
            gross_value += np.random.normal(0, 1.5)
            
            # Netback with variable freight costs
            region_freight = np.random.choice([1.5, 2.0, 2.5, 3.0], p=[0.3, 0.4, 0.2, 0.1])
            netback_value = gross_value - region_freight
            
            # Quality score based on API and sulfur
            quality_score = self._calculate_quality_score(api, sulfur)
            quality_score += np.random.normal(0, 0.5)  # Add noise
            quality_score = max(0, min(10, quality_score))
            
            # Processing index with complex interactions
            processing_index = self._calculate_processing_index(api, sulfur, light, middle, heavy)
            processing_index += np.random.normal(0, 3.0)  # Add noise
            processing_index = max(0, min(100, processing_index))
            
            data.append({
                'api_gravity': api,
                'sulfur_content': sulfur, 
                'light_cuts': light,
                'middle_cuts': middle,
                'heavy_cuts': heavy,
                'gross_value': gross_value,
                'netback_value': netback_value,
                'quality_score': quality_score,
                'processing_index': processing_index
            })
        
        return pd.DataFrame(data)
    
    def _calculate_gross_value(self, light: float, middle: float, heavy: float) -> float:
        """Calculate gross value based on cut yields and product prices."""
        return (light * self.product_prices['lights'] + 
                middle * self.product_prices['middles'] + 
                heavy * self.product_prices['heavies'])
    
    def _calculate_quality_score(self, api: float, sulfur: float) -> float:
        """Calculate quality score from API and sulfur content."""
        api_score = min(10, api / 4.0)
        sulfur_score = max(0, 10 - sulfur * 2.5)
        return (api_score + sulfur_score) / 2
    
    def _calculate_processing_index(self, api: float, sulfur: float, light: float, 
                                   middle: float, heavy: float) -> float:
        """Calculate processing complexity index."""
        api_factor = api * 1.2
        sulfur_penalty = sulfur * 10
        light_bonus = light * 60
        middle_bonus = middle * 45
        heavy_penalty = heavy * 25
        
        return api_factor - sulfur_penalty + light_bonus + middle_bonus - heavy_penalty
    
    def train_models(self, data: pd.DataFrame) -> Dict[str, Dict]:
        """
        Train multiple regression models for each target variable.
        
        Args:
            data: Training data with features and targets
            
        Returns:
            Dictionary with model performance metrics
        """
        X = data[self.feature_names]
        results = {}
        
        for target in self.target_names:
            y = data[target]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Initialize scalers and models for this target
            self.scalers[target] = StandardScaler()
            self.polynomial_features[target] = PolynomialFeatures(degree=2, include_bias=False)
            
            # Scale features
            X_train_scaled = self.scalers[target].fit_transform(X_train)
            X_test_scaled = self.scalers[target].transform(X_test)
            
            # Create polynomial features
            X_train_poly = self.polynomial_features[target].fit_transform(X_train_scaled)
            X_test_poly = self.polynomial_features[target].transform(X_test_scaled)
            
            # Train multiple model types
            models_to_train = {
                'linear': LinearRegression(),
                'ridge': Ridge(alpha=1.0),
                'polynomial': LinearRegression(),
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
            }
            
            target_results = {}
            
            for model_name, model in models_to_train.items():
                if model_name == 'polynomial':
                    model.fit(X_train_poly, y_train)
                    y_pred = model.predict(X_test_poly)
                else:
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                
                # Calculate metrics
                r2 = r2_score(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                
                # Cross-validation score
                if model_name == 'polynomial':
                    cv_scores = cross_val_score(model, X_train_poly, y_train, cv=5)
                else:
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
                
                target_results[model_name] = {
                    'r2_score': r2,
                    'mae': mae,
                    'cv_mean': cv_scores.mean(),
                    'cv_std': cv_scores.std()
                }
            
            # Store the best performing model (by R² score)
            best_model_name = max(target_results.keys(), 
                                key=lambda k: target_results[k]['r2_score'])
            
            self.models[target] = {
                'model': models_to_train[best_model_name],
                'type': best_model_name,
                'performance': target_results[best_model_name]
            }
            
            results[target] = target_results
        
        return results
    
    def predict(self, api_gravity: float, sulfur_content: float, 
               light_cuts: float, middle_cuts: float, heavy_cuts: float) -> Dict[str, float]:
        """
        Make predictions for all targets given assay inputs.
        
        Args:
            api_gravity: API gravity in degrees
            sulfur_content: Sulfur content in weight percent
            light_cuts: Light fraction yield (0-1)
            middle_cuts: Middle distillate yield (0-1)  
            heavy_cuts: Heavy fraction yield (0-1)
            
        Returns:
            Dictionary with predicted values for all targets
        """
        # Normalize cuts to sum to 1.0
        total_cuts = light_cuts + middle_cuts + heavy_cuts
        light_cuts /= total_cuts
        middle_cuts /= total_cuts
        heavy_cuts /= total_cuts
        
        # Prepare input features
        features = np.array([[api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts]])
        
        predictions = {}
        
        for target in self.target_names:
            if target not in self.models:
                # Fallback calculations if model not trained
                if target == 'gross_value':
                    predictions[target] = self._calculate_gross_value(light_cuts, middle_cuts, heavy_cuts)
                elif target == 'netback_value':
                    gross = self._calculate_gross_value(light_cuts, middle_cuts, heavy_cuts)
                    predictions[target] = gross - self.freight_rates['default']
                elif target == 'quality_score':
                    predictions[target] = self._calculate_quality_score(api_gravity, sulfur_content)
                elif target == 'processing_index':
                    predictions[target] = self._calculate_processing_index(
                        api_gravity, sulfur_content, light_cuts, middle_cuts, heavy_cuts
                    )
                continue
            
            # Scale features
            features_scaled = self.scalers[target].transform(features)
            
            # Make prediction based on model type
            model_info = self.models[target]
            model = model_info['model']
            model_type = model_info['type']
            
            if model_type == 'polynomial':
                features_poly = self.polynomial_features[target].transform(features_scaled)
                prediction = model.predict(features_poly)[0]
            else:
                prediction = model.predict(features_scaled)[0]
            
            predictions[target] = float(prediction)
        
        return predictions
    
    def save_models(self, filepath: str):
        """Save trained models to disk."""
        model_data = {
            'models': {},
            'scalers': {},
            'polynomial_features': {},
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'product_prices': self.product_prices,
            'freight_rates': self.freight_rates
        }
        
        # Extract model information (sklearn objects need special handling)
        for target in self.models:
            model_data['models'][target] = {
                'type': self.models[target]['type'],
                'performance': self.models[target]['performance']
            }
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model_data': model_data,
                'sklearn_models': self.models,
                'sklearn_scalers': self.scalers,
                'sklearn_poly_features': self.polynomial_features
            }, f)
    
    def load_models(self, filepath: str):
        """Load trained models from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.models = data['sklearn_models']
        self.scalers = data['sklearn_scalers'] 
        self.polynomial_features = data['sklearn_poly_features']
        
        model_data = data['model_data']
        self.feature_names = model_data['feature_names']
        self.target_names = model_data['target_names']
        self.product_prices = model_data['product_prices']
        self.freight_rates = model_data['freight_rates']
    
    def get_model_summary(self) -> Dict:
        """Get summary of trained models and their performance."""
        summary = {
            'feature_names': self.feature_names,
            'target_names': self.target_names,
            'models': {}
        }
        
        for target in self.models:
            model_info = self.models[target]
            summary['models'][target] = {
                'type': model_info['type'],
                'r2_score': model_info['performance']['r2_score'],
                'mae': model_info['performance']['mae'],
                'cv_mean': model_info['performance']['cv_mean'],
                'cv_std': model_info['performance']['cv_std']
            }
        
        return summary


def main():
    """Demo script showing model training and prediction."""
    # Initialize regressor
    regressor = CrudeAssayRegressor()
    
    # Generate synthetic training data  
    print("Generating synthetic crude assay data...")
    training_data = regressor.generate_synthetic_data(n_samples=1000)
    
    print(f"Generated {len(training_data)} samples")
    print("\nSample data:")
    print(training_data.head())
    
    print("\nTraining regression models...")
    results = regressor.train_models(training_data)
    
    print("\nModel Performance Summary:")
    print("=" * 50)
    
    for target, target_results in results.items():
        print(f"\n{target.upper()}:")
        for model_name, metrics in target_results.items():
            print(f"  {model_name:15s}: R² = {metrics['r2_score']:.3f}, "
                  f"MAE = {metrics['mae']:.2f}, CV = {metrics['cv_mean']:.3f}±{metrics['cv_std']:.3f}")
    
    # Test predictions with sample crudes
    print("\n" + "=" * 50)
    print("SAMPLE PREDICTIONS")
    print("=" * 50)
    
    sample_crudes = {
        'Arab Light': {'api': 33.0, 'sulfur': 1.8, 'light': 0.35, 'middle': 0.45, 'heavy': 0.20},
        'West African': {'api': 36.5, 'sulfur': 0.25, 'light': 0.40, 'middle': 0.45, 'heavy': 0.15},
        'Mars': {'api': 29.0, 'sulfur': 2.0, 'light': 0.25, 'middle': 0.45, 'heavy': 0.30},
        'WTI': {'api': 39.6, 'sulfur': 0.24, 'light': 0.45, 'middle': 0.40, 'heavy': 0.15}
    }
    
    for crude_name, props in sample_crudes.items():
        predictions = regressor.predict(
            props['api'], props['sulfur'], props['light'], 
            props['middle'], props['heavy']
        )
        
        print(f"\n{crude_name}:")
        print(f"  API: {props['api']}°, Sulfur: {props['sulfur']}%")
        print(f"  Cuts: L={props['light']:.1%}, M={props['middle']:.1%}, H={props['heavy']:.1%}")
        print(f"  Predictions:")
        for target, value in predictions.items():
            if 'value' in target:
                print(f"    {target:20s}: ${value:6.2f}/bbl")
            else:
                print(f"    {target:20s}: {value:6.1f}")
    
    # Save models
    model_path = "/Users/k.jones/Desktop/assay/models/crude_regression_models.pkl"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    regressor.save_models(model_path)
    print(f"\nModels saved to: {model_path}")
    
    # Save model summary as JSON
    summary_path = "/Users/k.jones/Desktop/assay/models/model_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(regressor.get_model_summary(), f, indent=2)
    print(f"Model summary saved to: {summary_path}")


if __name__ == "__main__":
    main()

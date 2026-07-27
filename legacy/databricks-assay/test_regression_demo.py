#!/usr/bin/env python3
"""
Quick test script for the crude assay regression demo.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.regression_models import CrudeAssayRegressor
    print("✅ Successfully imported regression models")
    
    # Test model creation and training
    regressor = CrudeAssayRegressor()
    print("✅ Successfully created CrudeAssayRegressor")
    
    # Generate small amount of test data
    print("📊 Generating test data...")
    test_data = regressor.generate_synthetic_data(n_samples=100)
    print(f"✅ Generated {len(test_data)} synthetic samples")
    
    # Display sample data
    print("\n📋 Sample data:")
    print(test_data.head())
    
    # Train models on small dataset
    print("\n🧠 Training models...")
    results = regressor.train_models(test_data)
    print("✅ Models trained successfully!")
    
    # Display model performance
    print("\n📈 Model Performance:")
    for target, target_results in results.items():
        best_model = max(target_results.keys(), 
                        key=lambda k: target_results[k]['r2_score'])
        best_r2 = target_results[best_model]['r2_score']
        print(f"  {target:20s}: {best_model:15s} (R² = {best_r2:.3f})")
    
    # Test predictions with sample crudes
    print("\n🧪 Testing predictions...")
    
    sample_crudes = {
        'Arab Light': {'api': 33.0, 'sulfur': 1.8, 'light': 0.35, 'middle': 0.45, 'heavy': 0.20},
        'WTI': {'api': 39.6, 'sulfur': 0.24, 'light': 0.45, 'middle': 0.40, 'heavy': 0.15}
    }
    
    for crude_name, props in sample_crudes.items():
        predictions = regressor.predict(
            props['api'], props['sulfur'], props['light'], 
            props['middle'], props['heavy']
        )
        
        print(f"\n{crude_name}:")
        print(f"  Input: API={props['api']}°, S={props['sulfur']}%, Cuts={props['light']:.0%}/{props['middle']:.0%}/{props['heavy']:.0%}")
        for target, value in predictions.items():
            if 'value' in target:
                print(f"  {target:20s}: ${value:6.2f}/bbl")
            else:
                print(f"  {target:20s}: {value:6.1f}")
    
    print("\n✅ All tests passed! Regression demo is working correctly.")
    print("\n🚀 To run the full demo with web interface:")
    print("   python run_regression_demo.py")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

except Exception as e:
    print(f"❌ Test failed: {e}")
    sys.exit(1)

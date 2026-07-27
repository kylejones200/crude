"""
Streamlit Dashboard for Crude Assay Analytics

Interactive dashboard for exploring crude oil analytics, regression models,
and market data integration in Databricks.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Configure page
st.set_page_config(
    page_title="🛢️ Crude Assay Analytics",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4e79;
    }
    .sidebar-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Try to import Databricks-specific modules
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    DATABRICKS_MODE = True
except:
    DATABRICKS_MODE = False
    st.warning("⚠️ Running in local mode. Some features require Databricks environment.")


@st.cache_data
def load_sample_data():
    """Load sample data for demonstration."""
    
    # Sample crude assay data
    sample_crudes = {
        'crude_id': ['WTI', 'BRENT', 'ARB', 'MAYA', 'URALS', 'SAHARA', 'CANADIAN_HEAVY', 'NIGERIAN_LIGHT'],
        'name': ['West Texas Intermediate', 'Brent', 'Arab Light', 'Maya Heavy', 'Urals', 'Sahara Blend', 'Canadian Heavy', 'Nigerian Light'],
        'api': [39.6, 38.3, 33.0, 22.0, 31.7, 44.1, 20.5, 37.4],
        'sulfur_wt': [0.24, 0.37, 1.8, 3.4, 1.3, 0.10, 3.8, 0.14],
        'current_price': [78.45, 82.30, 76.20, 66.50, 74.80, 84.60, 63.25, 81.45],
        'quality_score': [9.2, 8.8, 7.4, 4.2, 7.1, 9.6, 3.8, 9.0],
        'processing_index': [25.4, 28.2, 45.6, 78.9, 52.3, 18.7, 85.4, 22.1],
        'enhanced_gross_value': [89.2, 88.5, 84.7, 71.2, 82.1, 92.8, 68.4, 87.9],
        'crude_category': ['Light Sweet', 'Light Sweet', 'Medium Sour', 'Heavy Sour', 'Medium Sour', 'Light Sweet', 'Heavy Sour', 'Light Sweet']
    }
    
    return pd.DataFrame(sample_crudes)


@st.cache_data  
def load_databricks_data():
    """Load data from Databricks Delta tables."""
    
    if not DATABRICKS_MODE:
        return load_sample_data()
    
    try:
        # Load from gold analytics table
        df = spark.table("gold_crude_analytics").toPandas()
        return df
    except Exception as e:
        st.error(f"Error loading Databricks data: {e}")
        return load_sample_data()


def create_market_overview():
    """Create market overview section."""
    
    st.markdown("## 📊 Market Overview")
    
    # Sample market data
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="WTI Crude",
            value="$78.45",
            delta="+1.23 (+1.59%)",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="Brent Crude", 
            value="$82.30",
            delta="+0.85 (+1.04%)",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="WTI-Brent Spread",
            value="$3.85",
            delta="+0.38",
            delta_color="normal"
        )
    
    with col4:
        st.metric(
            label="Active Crudes",
            value="50+",
            delta="Live pricing",
            delta_color="off"
        )


def create_crude_explorer(df):
    """Create crude oil explorer section."""
    
    st.markdown("## 🔍 Crude Oil Explorer")
    
    # Sidebar filters
    with st.sidebar:
        st.markdown("### 🎛️ Filters")
        
        # API gravity filter
        api_range = st.slider(
            "API Gravity Range",
            min_value=float(df['api'].min()),
            max_value=float(df['api'].max()),
            value=(float(df['api'].min()), float(df['api'].max())),
            step=0.5
        )
        
        # Sulfur content filter
        sulfur_range = st.slider(
            "Sulfur Content Range (%)",
            min_value=float(df['sulfur_wt'].min()),
            max_value=float(df['sulfur_wt'].max()),
            value=(float(df['sulfur_wt'].min()), float(df['sulfur_wt'].max())),
            step=0.1
        )
        
        # Crude category filter
        categories = st.multiselect(
            "Crude Categories",
            options=df['crude_category'].unique(),
            default=df['crude_category'].unique()
        )
    
    # Filter data
    filtered_df = df[
        (df['api'] >= api_range[0]) & (df['api'] <= api_range[1]) &
        (df['sulfur_wt'] >= sulfur_range[0]) & (df['sulfur_wt'] <= sulfur_range[1]) &
        (df['crude_category'].isin(categories))
    ]
    
    # Display filtered results
    st.markdown(f"### Showing {len(filtered_df)} crude oils")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Scatter plot: API vs Quality Score
        fig = px.scatter(
            filtered_df,
            x='api',
            y='quality_score', 
            size='enhanced_gross_value',
            color='crude_category',
            hover_name='name',
            hover_data=['current_price', 'sulfur_wt'],
            title="API Gravity vs Quality Score",
            labels={'api': 'API Gravity (°API)', 'quality_score': 'Quality Score (0-10)'}
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top crudes by quality score
        top_crudes = filtered_df.nlargest(5, 'quality_score')
        st.markdown("### 🏆 Top Quality Crudes")
        
        for idx, crude in top_crudes.iterrows():
            with st.container():
                st.markdown(f"**{crude['name']}**")
                st.markdown(f"Quality: {crude['quality_score']:.1f} | API: {crude['api']:.1f}° | S: {crude['sulfur_wt']:.2f}%")
                st.markdown("---")


def create_regression_analysis(df):
    """Create regression analysis section."""
    
    st.markdown("## 🧠 Regression Analysis")
    
    tab1, tab2, tab3 = st.tabs(["📈 Price Predictions", "🎯 Quality Models", "⚙️ Processing Analysis"])
    
    with tab1:
        st.markdown("### Enhanced Valuation vs Market Price")
        
        # Scatter plot: Enhanced value vs current price
        fig = px.scatter(
            df,
            x='current_price',
            y='enhanced_gross_value',
            size='quality_score',
            color='crude_category',
            hover_name='name',
            title="Market Price vs Enhanced Valuation Model",
            labels={'current_price': 'Current Market Price ($/bbl)', 
                   'enhanced_gross_value': 'Enhanced Gross Value ($/bbl)'}
        )
        
        # Add diagonal line for reference
        min_price = min(df['current_price'].min(), df['enhanced_gross_value'].min())
        max_price = max(df['current_price'].max(), df['enhanced_gross_value'].max())
        fig.add_trace(
            go.Scatter(
                x=[min_price, max_price],
                y=[min_price, max_price],
                mode='lines',
                name='Perfect Correlation',
                line=dict(dash='dash', color='gray')
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Value enhancement analysis
        df['value_enhancement'] = df['enhanced_gross_value'] - df['current_price']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Enhanced value distribution
            fig = px.histogram(
                df,
                x='value_enhancement',
                nbins=20,
                title="Value Enhancement Distribution",
                labels={'value_enhancement': 'Enhancement ($/bbl)', 'count': 'Number of Crudes'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top value enhancers
            top_enhanced = df.nlargest(5, 'value_enhancement')
            st.markdown("#### 🚀 Top Value Enhanced Crudes")
            
            for idx, crude in top_enhanced.iterrows():
                st.markdown(
                    f"**{crude['name']}**: +${crude['value_enhancement']:.2f}/bbl "
                    f"({crude['value_enhancement']/crude['current_price']*100:.1f}%)"
                )
    
    with tab2:
        st.markdown("### Quality Score Regression")
        
        # API vs Quality Score regression
        fig = px.scatter(
            df,
            x='api',
            y='quality_score',
            color='sulfur_wt',
            size='enhanced_gross_value',
            hover_name='name',
            title="API Gravity vs Quality Score (colored by Sulfur Content)",
            labels={'api': 'API Gravity (°API)', 'quality_score': 'Quality Score (0-10)', 'sulfur_wt': 'Sulfur (wt%)'}
        )
        
        # Add regression line
        from sklearn.linear_model import LinearRegression
        X = df['api'].values.reshape(-1, 1)
        y = df['quality_score'].values
        reg = LinearRegression().fit(X, y)
        
        x_line = np.linspace(df['api'].min(), df['api'].max(), 100)
        y_line = reg.predict(x_line.reshape(-1, 1))
        
        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_line,
                mode='lines',
                name=f'Regression Line (R² = {reg.score(X, y):.3f})',
                line=dict(color='red', width=2)
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Model performance metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("R² Score", f"{reg.score(X, y):.3f}")
        
        with col2:
            mae = np.mean(np.abs(reg.predict(X) - y))
            st.metric("Mean Abs Error", f"{mae:.2f}")
        
        with col3:
            rmse = np.sqrt(np.mean((reg.predict(X) - y)**2))
            st.metric("RMSE", f"{rmse:.2f}")
    
    with tab3:
        st.markdown("### Processing Complexity Analysis")
        
        # Processing index vs crude properties
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('API Gravity vs Processing Index', 'Sulfur Content vs Processing Index')
        )
        
        # API vs Processing Index
        fig.add_trace(
            go.Scatter(
                x=df['api'],
                y=df['processing_index'],
                mode='markers',
                name='API vs Processing',
                marker=dict(size=8, color='blue', opacity=0.7),
                text=df['name'],
                hovertemplate='<b>%{text}</b><br>API: %{x:.1f}°<br>Processing Index: %{y:.1f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Sulfur vs Processing Index
        fig.add_trace(
            go.Scatter(
                x=df['sulfur_wt'],
                y=df['processing_index'],
                mode='markers',
                name='Sulfur vs Processing',
                marker=dict(size=8, color='red', opacity=0.7),
                text=df['name'],
                hovertemplate='<b>%{text}</b><br>Sulfur: %{x:.2f}%<br>Processing Index: %{y:.1f}<extra></extra>'
            ),
            row=1, col=2
        )
        
        fig.update_xaxes(title_text="API Gravity (°API)", row=1, col=1)
        fig.update_xaxes(title_text="Sulfur Content (wt%)", row=1, col=2)
        fig.update_yaxes(title_text="Processing Index", row=1, col=1)
        fig.update_yaxes(title_text="Processing Index", row=1, col=2)
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def create_optimization_insights(df):
    """Create optimization insights section."""
    
    st.markdown("## ⚙️ Optimization Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💰 Value-Based Optimization")
        
        # Top value crudes
        top_value = df.nlargest(10, 'enhanced_gross_value')
        
        fig = px.bar(
            top_value,
            x='enhanced_gross_value',
            y='name',
            color='quality_score',
            orientation='h',
            title="Top 10 Crude Oils by Enhanced Value",
            labels={'enhanced_gross_value': 'Enhanced Gross Value ($/bbl)', 'name': 'Crude Oil'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🏭 Processing-Based Selection")
        
        # Processing efficiency (high value, low complexity)
        df['efficiency_ratio'] = df['enhanced_gross_value'] / (df['processing_index'] + 1)  # +1 to avoid division by zero
        
        top_efficient = df.nlargest(10, 'efficiency_ratio')
        
        fig = px.bar(
            top_efficient,
            x='efficiency_ratio',
            y='name',
            color='crude_category',
            orientation='h',
            title="Top 10 Most Processing-Efficient Crudes",
            labels={'efficiency_ratio': 'Value/Processing Ratio', 'name': 'Crude Oil'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Optimization recommendations
    st.markdown("### 🎯 Optimization Recommendations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🏆 Premium Blend")
        premium = df[df['quality_score'] >= 8.0].nsmallest(3, 'current_price')
        for idx, crude in premium.iterrows():
            st.markdown(f"• **{crude['name']}** - ${crude['current_price']:.2f}/bbl")
    
    with col2:
        st.markdown("#### ⚖️ Balanced Blend")
        balanced = df[(df['quality_score'] >= 6.0) & (df['processing_index'] <= 60)].nsmallest(3, 'current_price')
        for idx, crude in balanced.iterrows():
            st.markdown(f"• **{crude['name']}** - ${crude['current_price']:.2f}/bbl")
    
    with col3:
        st.markdown("#### 💵 Economic Blend")  
        economic = df.nsmallest(3, 'current_price')
        for idx, crude in economic.iterrows():
            st.markdown(f"• **{crude['name']}** - ${crude['current_price']:.2f}/bbl")


def create_data_summary(df):
    """Create data summary section."""
    
    with st.sidebar:
        st.markdown("### 📊 Data Summary")
        st.markdown(f"**Total Crudes**: {len(df)}")
        st.markdown(f"**Avg API Gravity**: {df['api'].mean():.1f}°")
        st.markdown(f"**Avg Sulfur Content**: {df['sulfur_wt'].mean():.2f}%")
        st.markdown(f"**Avg Quality Score**: {df['quality_score'].mean():.1f}")
        
        st.markdown("### 🏷️ Categories")
        category_counts = df['crude_category'].value_counts()
        for category, count in category_counts.items():
            st.markdown(f"• {category}: {count}")


def main():
    """Main dashboard function."""
    
    # Header
    st.markdown('<h1 class="main-header">🛢️ Crude Assay Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading crude oil data..."):
        df = load_databricks_data()
    
    if df.empty:
        st.error("No data available. Please check your data sources.")
        return
    
    # Data summary sidebar
    create_data_summary(df)
    
    # Market overview
    create_market_overview()
    
    st.markdown("---")
    
    # Crude explorer
    create_crude_explorer(df)
    
    st.markdown("---")
    
    # Regression analysis
    create_regression_analysis(df)
    
    st.markdown("---")
    
    # Optimization insights
    create_optimization_insights(df)
    
    # Footer
    st.markdown("---")
    st.markdown("### 🔧 Dashboard Info")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Mode**: {'Databricks' if DATABRICKS_MODE else 'Local'}")
    
    with col2:
        st.markdown(f"**Data Points**: {len(df)}")
    
    with col3:
        st.markdown(f"**Last Updated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()

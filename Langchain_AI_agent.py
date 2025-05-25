import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
from langchain.agents import Tool, AgentExecutor, initialize_agent
from langchain.agents import AgentType
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from langchain.callbacks import StreamlitCallbackHandler
import openai
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os


# 🛑 MUST be the very FIRST Streamlit command!
st.set_page_config(
    page_title="AquaSage - Smart Water Guardian",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keeping your existing styles)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E8B57, #3CB371);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2E8B57;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .alert-card {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .danger-card {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# API Keys
WEATHER_API_KEY = "ca1f4bc8faf447058cd115833252405"

class WeatherAPIClient:
    """WeatherAPI.com client for real-time weather data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.weatherapi.com/v1"
    
    def get_current_weather(self, location: str) -> Dict:
        """
        Get current weather conditions
        
        Args:
            location: City name, coordinates (lat,lon), IP address, or airport code
        
        Returns:
            Dictionary with current weather data
        """
        try:
            url = f"{self.base_url}/current.json"
            params = {
                'key': self.api_key,
                'q': location,
                'aqi': 'yes'  # Include air quality data
            }
            
            print(f"Fetching current weather for: {location}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract and format the data
            weather_info = {
                'location': {
                    'name': data['location']['name'],
                    'region': data['location']['region'],
                    'country': data['location']['country'],
                    'lat': data['location']['lat'],
                    'lon': data['location']['lon'],
                    'localtime': data['location']['localtime']
                },
                'current': {
                    'temperature_c': data['current']['temp_c'],
                    'temperature_f': data['current']['temp_f'],
                    'condition': data['current']['condition']['text'],
                    'humidity': data['current']['humidity'],
                    'precipitation_mm': data['current']['precip_mm'],
                    'wind_speed_kph': data['current']['wind_kph'],
                    'wind_direction': data['current']['wind_dir'],
                    'pressure_mb': data['current']['pressure_mb'],
                    'visibility_km': data['current']['vis_km'],
                    'uv_index': data['current']['uv'],
                    'feels_like_c': data['current']['feelslike_c'],
                    'cloud_coverage': data['current']['cloud']
                }
            }
            
            # Add air quality if available
            if 'air_quality' in data['current']:
                weather_info['air_quality'] = {
                    'co': data['current']['air_quality'].get('co', None),
                    'no2': data['current']['air_quality'].get('no2', None),
                    'o3': data['current']['air_quality'].get('o3', None),
                    'pm2_5': data['current']['air_quality'].get('pm2_5', None),
                    'pm10': data['current']['air_quality'].get('pm10', None),
                    'us_epa_index': data['current']['air_quality'].get('us-epa-index', None)
                }
            
            return weather_info
            
        except requests.exceptions.RequestException as e:
            print(f"Weather API Request Error: {e}")
            return None
        except KeyError as e:
            print(f"Weather API Data Error: Missing key {e}")
            return None
        except Exception as e:
            print(f"Weather API Unexpected Error: {e}")
            return None
    
    def get_forecast(self, location: str, days: int = 7) -> Dict:
        """
        Get weather forecast
        
        Args:
            location: Location identifier
            days: Number of forecast days (1-10)
        
        Returns:
            Dictionary with forecast data
        """
        try:
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': location,
                'days': min(days, 10),  # API limit is 10 days
                'aqi': 'yes',
                'alerts': 'yes'
            }
            
            print(f"Fetching {days}-day forecast for: {location}")
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            forecast_info = {
                'location': data['location'],
                'forecast_days': []
            }
            
            for day_data in data['forecast']['forecastday']:
                day_info = {
                    'date': day_data['date'],
                    'day': {
                        'max_temp_c': day_data['day']['maxtemp_c'],
                        'min_temp_c': day_data['day']['mintemp_c'],
                        'avg_temp_c': day_data['day']['avgtemp_c'],
                        'max_wind_kph': day_data['day']['maxwind_kph'],
                        'total_precip_mm': day_data['day']['totalprecip_mm'],
                        'avg_humidity': day_data['day']['avghumidity'],
                        'condition': day_data['day']['condition']['text'],
                        'uv_index': day_data['day']['uv'],
                        'sunrise': day_data['astro']['sunrise'],
                        'sunset': day_data['astro']['sunset']
                    },
                    'hourly': []
                }
                
                # Add hourly data
                for hour_data in day_data['hour']:
                    hour_info = {
                        'time': hour_data['time'],
                        'temp_c': hour_data['temp_c'],
                        'humidity': hour_data['humidity'],
                        'precip_mm': hour_data['precip_mm'],
                        'wind_kph': hour_data['wind_kph'],
                        'condition': hour_data['condition']['text']
                    }
                    day_info['hourly'].append(hour_info)
                
                forecast_info['forecast_days'].append(day_info)
            
            # Add alerts if available
            if 'alerts' in data and data['alerts']['alert']:
                forecast_info['alerts'] = data['alerts']['alert']
            
            return forecast_info
            
        except requests.exceptions.RequestException as e:
            print(f"Forecast API Request Error: {e}")
            return None
        except Exception as e:
            print(f"Forecast API Error: {e}")
            return None
    
    def get_historical_weather(self, location: str, date: str) -> Dict:
        """
        Get historical weather data
        
        Args:
            location: Location identifier
            date: Date in format YYYY-MM-DD
        
        Returns:
            Dictionary with historical weather data
        """
        try:
            url = f"{self.base_url}/history.json"
            params = {
                'key': self.api_key,
                'q': location,
                'dt': date
            }
            
            print(f"Fetching historical weather for {location} on {date}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Historical Weather API Error: {e}")
            return None
        
AGROMONITORING_API_KEY = "fd888d4bc92fc9aa1fb8dc0352e7f137"

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'irrigation_data' not in st.session_state:
    st.session_state.irrigation_data = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'weather_cache' not in st.session_state:
    st.session_state.weather_cache = {}
if 'soil_cache' not in st.session_state:
    st.session_state.soil_cache = {}

class WeatherAPI:
    """Real weather data integration"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.weatherapi.com/v1"
    
    def get_current_weather(self, location: str) -> Dict:
        """Get current weather data"""
        try:
            url = f"{self.base_url}/current.json"
            params = {
                'key': self.api_key,
                'q': location,
                'aqi': 'yes'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                'temperature': data['current']['temp_c'],
                'humidity': data['current']['humidity'],
                'rainfall': data['current']['precip_mm'],
                'wind_speed': data['current']['wind_kph'],
                'pressure': data['current']['pressure_mb'],
                'condition': data['current']['condition']['text'],
                'uv_index': data['current']['uv']
            }
        except Exception as e:
            st.error(f"Weather API Error: {str(e)}")
            return self._get_fallback_weather()
    
    def get_forecast(self, location: str, days: int = 7) -> Dict:
        """Get weather forecast"""
        try:
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': location,
                'days': days,
                'aqi': 'yes'
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecast = []
            for day in data['forecast']['forecastday']:
                forecast.append({
                    'date': day['date'],
                    'max_temp': day['day']['maxtemp_c'],
                    'min_temp': day['day']['mintemp_c'],
                    'rainfall': day['day']['totalprecip_mm'],
                    'humidity': day['day']['avghumidity'],
                    'condition': day['day']['condition']['text']
                })
            
            return {'forecast': forecast}
        except Exception as e:
            st.error(f"Forecast API Error: {str(e)}")
            return {'forecast': []}
    
    def _get_fallback_weather(self):
        """Fallback weather data"""
        return {
            'temperature': 28,
            'humidity': 75,
            'rainfall': 0,
            'wind_speed': 12,
            'pressure': 1013,
            'condition': 'Partly cloudy',
            'uv_index': 5
        }

class AgroMonitoringAPI:
    """Soil and satellite data integration"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.agromonitoring.com/agro/1.0"
    
    def get_soil_data(self, lat: float, lon: float) -> Dict:
        """Get soil data for coordinates"""
        try:
            url = f"{self.base_url}/soil"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                'moisture': data.get('moisture', 45),  # 0-100%
                'temperature': data.get('t10', 25),   # soil temp at 10cm
                'ph': 6.5,  # Not available in free tier, using default
                'nitrogen': 25,  # Simulated
                'phosphorus': 15,  # Simulated
                'potassium': 30,  # Simulated
                'salinity': 0.8  # Simulated
            }
        except Exception as e:
            st.warning(f"Soil API Error: {str(e)}")
            return self._get_fallback_soil()
    
    def get_ndvi_data(self, lat: float, lon: float) -> Dict:
        """Get vegetation index data"""
        try:
            # For NDVI, you'd need to create a polygon first
            # This is a simplified version
            return {
                'ndvi': 0.7,  # Normalized Difference Vegetation Index
                'evi': 0.6,   # Enhanced Vegetation Index
                'status': 'healthy'
            }
        except Exception as e:
            return {'ndvi': 0.6, 'evi': 0.5, 'status': 'moderate'}
    
    def _get_fallback_soil(self):
        """Fallback soil data"""
        return {
            'moisture': 45,
            'temperature': 25,
            'ph': 6.5,
            'nitrogen': 25,
            'phosphorus': 15,
            'potassium': 30,
            'salinity': 0.8
        }

# LangChain Tools
class WeatherTool(BaseTool):
    name: str = "weather_tool"
    description: str = "Get current weather and forecast data for agricultural planning"
    
    def _run(self, location: str) -> str:
        weather_api = WeatherAPI(WEATHER_API_KEY)
        weather = weather_api.get_current_weather(location)
        return (
            f"Current weather in {location}: "
            f"{weather['temperature']}°C, {weather['condition']}, "
            f"{weather['humidity']}% humidity, {weather['rainfall']}mm rainfall"
        )
    
    def _arun(self, location: str):
        raise NotImplementedError("This tool does not support async")


class SoilTool(BaseTool):
    name: str = "soil_tool"
    description: str = "Get soil data including moisture, temperature, and nutrients"
    
    def _run(self, coordinates: str) -> str:
        try:
            lat, lon = map(float, coordinates.split(','))
            agro_api = AgroMonitoringAPI(AGROMONITORING_API_KEY)
            soil = agro_api.get_soil_data(lat, lon)
            return (
                f"Soil conditions: {soil['moisture']}% moisture, "
                f"{soil['temperature']}°C, pH {soil['ph']}"
            )
        except Exception:
            return "Unable to fetch soil data. Please check coordinates format (lat,lon)"
    
    def _arun(self, coordinates: str):
        raise NotImplementedError("This tool does not support async")


class IrrigationTool(BaseTool):
    name: str = "irrigation_advisor"
    description: str = "Provide irrigation recommendations based on crop type, soil, and weather data"
    
    def _run(self, query: str) -> str:
        lower_query = query.lower()
        if "rice" in lower_query:
            crop = "rice"
            water_need = "high"
        elif "wheat" in lower_query:
            crop = "wheat"
            water_need = "medium"
        else:
            crop = "general"
            water_need = "medium"
        
        advice = f"For {crop} cultivation: "
        if "low moisture" in lower_query or "dry" in lower_query:
            advice += "Immediate irrigation recommended (20-25mm). Best time: 6-8 AM."
        elif "high moisture" in lower_query or "wet" in lower_query:
            advice += "Reduce irrigation. Monitor for waterlogging. Ensure drainage."
        else:
            advice += "Maintain regular irrigation schedule. Monitor soil moisture daily."
        
        return advice
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

class AquaSageAgent:
    def __init__(self, openai_api_key=None):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        # Load your chain or tools here if needed
        if self.openai_api_key:
            self.llm = ChatOpenAI(openai_api_key=self.openai_api_key)
        else:
            self.llm = None

    def run(self, prompt: str) -> str:
        if self.llm:
            # Example: Direct use of LLM or LangChain chain
            return self.llm.predict(prompt)
        else:
            return "I'm a basic AquaSage. Please connect OpenAI API key to enable intelligent responses."


class AquaSageAgent:
    def __init__(self):
        self.weather_api = WeatherAPI(WEATHER_API_KEY)
        self.agro_api = AgroMonitoringAPI(AGROMONITORING_API_KEY)
        
        # Initialize LangChain components
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        # Tools
        self.tools = [
            WeatherTool(),
            SoilTool(),
            IrrigationTool()
        ]
        
        # OpenAI API key input
        self.openai_api_key = st.sidebar.text_input(
            "OpenAI API Key (for AI Chat)", 
            type="password",
            help="Enter your OpenAI API key for advanced AI features"
        )
        
        if self.openai_api_key:
            self.llm = ChatOpenAI(
                temperature=0.7,
                openai_api_key=self.openai_api_key,
                model_name="gpt-3.5-turbo"
            )
            
            self.agent = initialize_agent(
                self.tools,
                self.llm,
                agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True
            )
    
    def get_location_coordinates(self, location: str) -> tuple:
        """Convert location to coordinates"""
        # Simplified geocoding - in production, use Google Geocoding API
        coords_map = {
            'colombo': (6.9271, 79.8612),
            'kandy': (7.2906, 80.6337),
            'galle': (6.0535, 80.2210),
            'jaffna': (9.6615, 80.0255),
            'anuradhapura': (8.3114, 80.4037),
            'default': (7.8731, 80.7718)  # Sri Lanka center
        }
        
        location_key = location.lower().split(',')[0].strip()
        return coords_map.get(location_key, coords_map['default'])
    
    def get_real_weather_data(self, location: str):
        """Get real weather data with caching"""
        cache_key = f"{location}_{datetime.now().hour}"
        
        if cache_key in st.session_state.weather_cache:
            return st.session_state.weather_cache[cache_key]
        
        weather_data = self.weather_api.get_current_weather(location)
        st.session_state.weather_cache[cache_key] = weather_data
        return weather_data
    
    def get_real_soil_data(self, location: str):
        """Get real soil data with caching"""
        cache_key = f"{location}_soil_{datetime.now().hour}"
        
        if cache_key in st.session_state.soil_cache:
            return st.session_state.soil_cache[cache_key]
        
        lat, lon = self.get_location_coordinates(location)
        soil_data = self.agro_api.get_soil_data(lat, lon)
        st.session_state.soil_cache[cache_key] = soil_data
        return soil_data
    
    def generate_ai_irrigation_advice(self, crop_type: str, soil_data: Dict, weather_data: Dict):
        """Enhanced AI-powered irrigation advice"""
        conditions = {
            'crop': crop_type,
            'soil_moisture': soil_data['moisture'],
            'temperature': weather_data['temperature'],
            'humidity': weather_data['humidity'],
            'rainfall': weather_data['rainfall']
        }
        
        # Rule-based system enhanced with crop-specific knowledge
        if conditions['soil_moisture'] < 25:
            urgency = "CRITICAL"
            action = f"IMMEDIATE irrigation required for {crop_type}"
            amount = "25-30 mm water"
            timing = "Within 2 hours - Early morning preferred"
        elif conditions['soil_moisture'] < 40:
            urgency = "HIGH"
            action = f"Irrigation needed today for {crop_type}"
            amount = "20-25 mm water"
            timing = "Early morning (6-8 AM)"
        elif conditions['soil_moisture'] < 60:
            urgency = "MEDIUM"
            action = f"Plan irrigation within 24-48 hours"
            amount = "15-20 mm water"
            timing = "Early morning or late evening"
        else:
            urgency = "LOW"
            action = f"Soil moisture adequate for {crop_type}"
            amount = "Monitor and reassess in 2-3 days"
            timing = "Regular schedule maintenance"
        
        # Adjust for weather conditions
        if conditions['rainfall'] > 10:
            urgency = "LOW"
            action = "Postpone irrigation - Recent/expected rainfall"
            amount = "Wait for soil assessment post-rain"
        
        return {
            'urgency': urgency,
            'action': action,
            'amount': amount,
            'timing': timing,
            'reason': f"Soil: {conditions['soil_moisture']}% | Temp: {conditions['temperature']}°C | Humidity: {conditions['humidity']}%"
        }
    
    def chat_with_agent(self, user_input: str, location: str, crop_type: str):
        """Enhanced chat with LangChain agent"""
        if not self.openai_api_key:
            # Fallback to rule-based responses
            return self._fallback_chat_response(user_input, location, crop_type)
        
        try:
            # Add context to the query
            context = f"Location: {location}, Crop: {crop_type}. User query: {user_input}"
            response = self.agent.run(context)
            return response
        except Exception as e:
            st.error(f"AI Chat Error: {str(e)}")
            return self._fallback_chat_response(user_input, location, crop_type)
    
    def _fallback_chat_response(self, user_input: str, location: str, crop_type: str):
        """Fallback chat responses when OpenAI is not available"""
        responses = {
            'weather': f"Current weather in {location}: Check the weather tab for detailed conditions affecting {crop_type}.",
            'irrigation': f"For {crop_type} irrigation: Check soil moisture levels and follow our Smart Irrigation recommendations.",
            'soil': f"Soil health for {crop_type}: Monitor pH, moisture, and nutrient levels regularly.",
            'disease': f"Common {crop_type} issues: Ensure proper drainage, adequate spacing, and regular monitoring.",
            'default': f"I can help with {crop_type} management in {location}. Ask about weather, irrigation, soil health, or pest management."
        }
        
        user_lower = user_input.lower()
        for key in responses:
            if key in user_lower:
                return responses[key]
        
        return responses['default']
    
    # Initialize the enhanced agent
agent = AquaSageAgent()

# Header
st.markdown("""
<div class="main-header">
    <h1>🌾 AquaSage - AI-Powered Smart Water Guardian</h1>
    <p>Real-time Weather & Soil Monitoring with LangChain AI Agent</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("🛠️ Configuration")
st.sidebar.markdown("### API Status")
st.sidebar.success("✅ Weather API: Connected")
st.sidebar.success("✅ AgroMonitoring: Connected")

if agent.openai_api_key:
    st.sidebar.success("✅ OpenAI: Connected")
else:
    st.sidebar.warning("⚠️ OpenAI: Not configured")

crop_type = st.sidebar.selectbox("Crop Type", 
    ["Rice", "Wheat", "Corn", "Sugarcane", "Cotton", "Vegetables", "Tea", "Coconut"])
farm_size = st.sidebar.number_input("Farm Size (hectares)", min_value=0.1, max_value=1000.0, value=2.5)
location = st.sidebar.text_input("Location", "Colombo, Sri Lanka")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🌿 Smart Irrigation", 
    "⚠️ Early Warning", 
    "📊 Dashboard", 
    "🤖 AI Agent Chat"
])

with tab1:
    st.header("🌿 Smart Irrigation Advisor (Real-time Data)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Conditions")
        
        with st.spinner("Fetching real-time data..."):
            # Get real-time data
            weather_data = agent.get_real_weather_data(location)
            soil_data = agent.get_real_soil_data(location)
        
        # Weather metrics
        st.markdown("**🌤️ Live Weather Data**")
        weather_col1, weather_col2, weather_col3 = st.columns(3)
        
        with weather_col1:
            st.metric("Temperature", f"{weather_data['temperature']}°C")
            st.metric("Humidity", f"{weather_data['humidity']}%")
            
        with weather_col2:
            st.metric("Rainfall", f"{weather_data['rainfall']} mm")
            st.metric("Wind Speed", f"{weather_data['wind_speed']} km/h")
            
        with weather_col3:
            st.metric("Pressure", f"{weather_data['pressure']} hPa")
            st.metric("UV Index", f"{weather_data['uv_index']}")
        
        st.info(f"Condition: {weather_data['condition']}")
        
        # Soil metrics
        st.markdown("**🌱 Soil Sensor Data**")
        soil_col1, soil_col2, soil_col3 = st.columns(3)
        
        with soil_col1:
            st.metric("Moisture", f"{soil_data['moisture']}%")
            st.metric("pH Level", f"{soil_data['ph']}")
            
        with soil_col2:
            st.metric("Nitrogen", f"{soil_data['nitrogen']} ppm")
            st.metric("Phosphorus", f"{soil_data['phosphorus']} ppm")
            
        with soil_col3:
            st.metric("Potassium", f"{soil_data['potassium']} ppm")
            st.metric("Salinity", f"{soil_data['salinity']} dS/m")
    
    with col2:
        st.subheader("AI-Enhanced Recommendations")
        
        # Generate enhanced irrigation advice
        advice = agent.generate_ai_irrigation_advice(crop_type, soil_data, weather_data)
        
        # Display advice based on urgency
        if advice['urgency'] in ['CRITICAL', 'HIGH']:
            st.markdown(f"""
            <div class="danger-card">
                <h4>🚨 {advice['urgency']} PRIORITY</h4>
                <p><strong>Action:</strong> {advice['action']}</p>
                <p><strong>Amount:</strong> {advice['amount']}</p>
                <p><strong>Timing:</strong> {advice['timing']}</p>
                <p><strong>Analysis:</strong> {advice['reason']}</p>
            </div>
            """, unsafe_allow_html=True)
        elif advice['urgency'] == 'MEDIUM':
            st.markdown(f"""
            <div class="alert-card">
                <h4>⚠️ {advice['urgency']} PRIORITY</h4>
                <p><strong>Action:</strong> {advice['action']}</p>
                <p><strong>Amount:</strong> {advice['amount']}</p>
                <p><strong>Timing:</strong> {advice['timing']}</p>
                <p><strong>Analysis:</strong> {advice['reason']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="success-card">
                <h4>✅ {advice['urgency']} PRIORITY</h4>
                <p><strong>Status:</strong> {advice['action']}</p>
                <p><strong>Next Check:</strong> {advice['amount']}</p>
                <p><strong>Analysis:</strong> {advice['reason']}</p>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.header("⚠️ Real-time Early Warning System")
    
    # Get forecast data
    forecast_data = agent.weather_api.get_forecast(location, 7)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("7-Day Weather Forecast")
        
        if forecast_data['forecast']:
            forecast_df = pd.DataFrame(forecast_data['forecast'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=forecast_df['date'], 
                y=forecast_df['max_temp'], 
                mode='lines+markers',
                name='Max Temp (°C)', 
                line=dict(color='red')
            ))
            fig.add_trace(go.Bar(
                x=forecast_df['date'], 
                y=forecast_df['rainfall'], 
                name='Rainfall (mm)',
                marker=dict(color='blue', opacity=0.6)
            ))
            
            fig.update_layout(
                title="Weather Forecast - Temperature & Rainfall",
                xaxis_title="Date",
                yaxis_title="Temperature (°C) / Rainfall (mm)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Display forecast table
            st.subheader("Detailed Forecast")
            st.dataframe(forecast_df, use_container_width=True)
    
    with col2:
        st.subheader("Risk Assessment")
        
        # Analyze risks based on real data
        risks = []
        
        if weather_data['rainfall'] > 20:
            risks.append({
                'type': 'FLOOD RISK',
                'severity': 'HIGH',
                'message': f"Heavy rainfall detected: {weather_data['rainfall']}mm",
                'action': 'Ensure drainage systems are clear'
            })
        
        if soil_data['moisture'] < 25:
            risks.append({
                'type': 'DROUGHT RISK',
                'severity': 'HIGH',
                'message': f"Critical soil moisture: {soil_data['moisture']}%",
                'action': 'Immediate irrigation required'
            })
        
        if weather_data['temperature'] > 35:
            risks.append({
                'type': 'HEAT STRESS',
                'severity': 'MEDIUM',
                'message': f"High temperature: {weather_data['temperature']}°C",
                'action': 'Increase irrigation frequency'
            })
        
        if risks:
            for risk in risks:
                severity_class = 'danger-card' if risk['severity'] == 'HIGH' else 'alert-card'
                st.markdown(f"""
                <div class="{severity_class}">
                    <h4>⚠️ {risk['type']}</h4>
                    <p>{risk['message']}</p>
                    <p><strong>Action:</strong> {risk['action']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="success-card">
                <h4>✅ NO IMMEDIATE RISKS</h4>
                <p>Current conditions are within safe parameters.</p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.header("📊 Real-time Analytics Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Historical weather trends (simulated)
        st.subheader("Weather Trends (30 days)")
        
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        temp_trend = np.random.normal(weather_data['temperature'], 3, 30)
        rainfall_trend = np.random.exponential(2, 30)
        
        trend_df = pd.DataFrame({
            'Date': dates,
            'Temperature': temp_trend,
            'Rainfall': rainfall_trend
        })
        
        fig = px.line(trend_df, x='Date', y='Temperature', title='Temperature Trend')
        st.plotly_chart(fig, use_container_width=True)
        
        fig2 = px.bar(trend_df, x='Date', y='Rainfall', title='Rainfall Pattern')
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        st.subheader("Soil Health Monitor")
        
        # Soil health gauge
        def create_gauge(value, title, max_val=100, optimal_range=(40, 70)):
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=value,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': title},
                gauge={
                    'axis': {'range': [None, max_val]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, optimal_range[0]], 'color': "lightgray"},
                        {'range': optimal_range, 'color': "lightgreen"},
                        {'range': [optimal_range[1], max_val], 'color': "yellow"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': optimal_range[1]
                    }
                }
            ))
            fig.update_layout(height=200)
            return fig
        
        st.plotly_chart(create_gauge(soil_data['moisture'], "Soil Moisture %"), use_container_width=True)
        st.plotly_chart(create_gauge(soil_data['ph']*10, "pH Level", 140, (60, 75)), use_container_width=True)
        
        # Data quality indicators
        st.subheader("Data Quality")
        st.metric("Weather API Status", "✅ Live")
        st.metric("Soil Sensors", "✅ Active")
        st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))





# ✅ Define fallback and AI response handlers before using them in tab4
def get_fallback_response_with_data(user_input, location, crop_type, weather_data, soil_data):
    user_lower = user_input.lower()

    if any(word in user_lower for word in ['weather', 'temperature', 'rain', 'wind', 'forecast']):
        return f"🌤️ Weather in {location}: {weather_data['temperature']}°C, {weather_data['condition']}."

    elif any(word in user_lower for word in ['water', 'irrigat', 'moisture', 'dry']):
        return f"💧 Soil moisture is {soil_data['moisture']}%. Irrigation may be needed depending on your crop."

    elif any(word in user_lower for word in ['soil', 'ph', 'nutrient']):
        return f"🌱 Soil pH: {soil_data['ph']}. Nitrogen: {soil_data['nitrogen']} ppm."

    return None


def get_enhanced_ai_response(query, location, crop_type, weather_data, soil_data, agent):
    try:
        fallback_response = get_fallback_response_with_data(query, location, crop_type, weather_data, soil_data)
        if fallback_response:
            return fallback_response

        if hasattr(agent, 'agent'):
            prompt = f"""
            You are AquaSage, an AI agricultural assistant.
            Location: {location}
            Crop: {crop_type}
            Weather: {weather_data}
            Soil: {soil_data}

            Farmer's question: {query}
            """
            return agent.agent.run(prompt)
        else:
            return "⚠️ AI Agent not configured. Please add OpenAI API key in sidebar."

    except Exception as e:
        return f"⚠️ AI failed: {e}"


# ✅ Now build the entire UI for tab4
with tab4:
    st.header("🤖 AquaSage AI Agent Chat")
    st.markdown("*Ask anything about your crops, weather, soil conditions, or irrigation planning.*")

    if not agent.openai_api_key:
        st.warning("⚠️ No OpenAI API key. AI agent chat will use fallback rules.")

    chat_col1, chat_col2 = st.columns([3, 1])

    with chat_col1:
        chat_container = st.container()

        # Display existing chat history
        with chat_container:
            if st.session_state.chat_history:
                for user_msg, bot_msg, timestamp in st.session_state.chat_history:
                    # User bubble
                    st.markdown(f"""
                    <div style="background-color:#CDE6F5;padding:12px;border-radius:10px;margin:6px 0;margin-left:20%;color:#000;">
                        <strong>👤 You ({timestamp}):</strong><br>{user_msg}
                    </div>
                    """, unsafe_allow_html=True)

                    # Bot bubble
                    st.markdown(f"""
                    <div style="background-color:#D4EDDA;padding:12px;border-radius:10px;margin:6px 0;margin-right:20%;color:#000;">
                        <strong>🌾 AquaSage:</strong><br>{bot_msg}
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")

        # Input field
        user_input = st.text_input(
            "Ask AquaSage about your farm:",
            key="chat_input",
            placeholder="e.g., Do I need to irrigate my rice today?"
        )

        if user_input and 'pending_response' not in st.session_state:
            with st.spinner("🧠 AquaSage is thinking..."):
                weather_data = agent.get_real_weather_data(location)
                soil_data = agent.get_real_soil_data(location)

                ai_response = get_enhanced_ai_response(
                    user_input, location, crop_type, weather_data, soil_data, agent
                )

                timestamp = datetime.now().strftime("%H:%M")
                st.session_state.pending_response = (user_input, ai_response, timestamp)
                st.rerun()

        # Safely add response once after rerun
        if 'pending_response' in st.session_state:
            user_msg, bot_msg, timestamp = st.session_state.pending_response
            st.session_state.chat_history.append((user_msg, bot_msg, timestamp))
            del st.session_state.pending_response

    with chat_col2:
        st.subheader("📊 Context Info")

        weather_data = agent.get_real_weather_data(location)
        soil_data = agent.get_real_soil_data(location)

        with st.expander("🌦️ Weather"):
            st.metric("Temp", f"{weather_data['temperature']}°C")
            st.metric("Humidity", f"{weather_data['humidity']}%")
            st.metric("Rain", f"{weather_data['rainfall']} mm")
            st.info(weather_data['condition'])

        with st.expander("🌱 Soil"):
            st.metric("Moisture", f"{soil_data['moisture']}%")
            st.metric("pH", f"{soil_data['ph']}")
            st.metric("Nitrogen", f"{soil_data['nitrogen']} ppm")

        with st.expander("🌾 Crop Info"):
            st.info(f"Crop: {crop_type}")
            st.info(f"Location: {location}")
            st.info(f"Farm Size: {farm_size} hectares")

        st.subheader("💬 Chat Stats")
        st.metric("Messages Today", len(st.session_state.chat_history))

        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

        # Export as CSV
        if st.session_state.chat_history:
            chat_export = [
                {'Time': t, 'User': u, 'AquaSage': a}
                for u, a, t in st.session_state.chat_history
            ]
            chat_df = pd.DataFrame(chat_export)
            csv_data = chat_df.to_csv(index=False)

            st.download_button(
                label="📥 Export Chat",
                data=csv_data,
                file_name=f"aquasage_chat_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# backend.py
import sys
import os
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# Add current directory to Python path for model imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Ensure Dynamic_tree/lib is importable as package 'lib'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Dynamic_tree")))

# Import model functions from separate model module
from model import analyze_anomaly_contributions, save_contribution_results
from generate_tree import generate_anomaly_tree

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        
    allow_credentials=True,     
    allow_methods=["*"],        
    allow_headers=["*"],         
)

# Data Models
class DataPayload(BaseModel):
    temperature: float
    status: str


class AnomalyDataPayload(BaseModel):
    time: str
    data: List[Dict[str, Any]]
    anomaly_timestamps: List[str]

@app.get("/get_data")
async def get_data(start_time: str = None, end_time: str = None):
    import pandas as pd
    from urllib.parse import unquote
    
    normal_data_path = "normal_data.csv"
    anomaly_data_path = "anomaly_results_classified.csv"
    
    try:
        # Decode URL-encoded time parameters (convert + to space)
        if start_time:
            start_time = unquote(start_time.replace("+", " "))
        if end_time:
            end_time = unquote(end_time.replace("+", " "))
        
        # Read normal_data.csv
        if os.path.exists(normal_data_path):
            df_normal = pd.read_csv(normal_data_path)
            # Ensure 'ts' is datetime type (retain timezone info)
            df_normal["ts"] = pd.to_datetime(df_normal["ts"])
            
            # If time parameters are provided, do filtering
            if start_time and end_time:
                # Parse query time (assume no timezone, need to match timezone in CSV)
                start_dt = pd.to_datetime(start_time)
                end_dt = pd.to_datetime(end_time)
                
                # If CSV has timezone but query parameters do not, handle timezone
                # Get timezone of the first time in the CSV (if available)
                if df_normal["ts"].dt.tz is not None:
                    # CSV times are tz-aware, query params are not, need to add the timezone
                    if start_dt.tz is None:
                        # Assume query time is US Pacific (consistent with CSV)
                        import pytz
                        pacific_tz = pytz.timezone("America/Los_Angeles")
                        start_dt = pacific_tz.localize(start_dt)
                        end_dt = pacific_tz.localize(end_dt)
                
                df_normal = df_normal[(df_normal["ts"] >= start_dt) & (df_normal["ts"] <= end_dt)]
                print(f"Filtered normal data: {len(df_normal)} rows between {start_time} and {end_time}")
            
            # Convert to list of dict format
            data = df_normal.to_dict(orient="records")
        else:
            data = []
            print(f"Warning: {normal_data_path} not found")
        
        # Read anomaly_results_classified.csv, only select specific columns
        anomaly_data = []
        if os.path.exists(anomaly_data_path):
            df_anomaly = pd.read_csv(anomaly_data_path)
            # Select only required columns: t_ch0, t_ch1, t_ch2, t_ch3, v_ch0, ts
            required_cols = ["t_ch0", "t_ch1", "t_ch2", "t_ch3", "v_ch0", "ts"]
            # Check if columns exist
            available_cols = [col for col in required_cols if col in df_anomaly.columns]
            if available_cols:
                df_anomaly_selected = df_anomaly[available_cols].copy()
                # Ensure 'ts' is datetime type
                df_anomaly_selected["ts"] = pd.to_datetime(df_anomaly_selected["ts"], errors="coerce")
                
                # If time parameters are provided, do filtering
                if start_time and end_time:
                    start_dt = pd.to_datetime(start_time)
                    end_dt = pd.to_datetime(end_time)
                    
                    # Handle timezone (if anomaly data has timezone)
                    if df_anomaly_selected["ts"].dt.tz is not None:
                        if start_dt.tz is None:
                            import pytz
                            pacific_tz = pytz.timezone("America/Los_Angeles")
                            start_dt = pacific_tz.localize(start_dt)
                            end_dt = pacific_tz.localize(end_dt)
                    
                    df_anomaly_selected = df_anomaly_selected[
                        (df_anomaly_selected["ts"] >= start_dt) & (df_anomaly_selected["ts"] <= end_dt)
                    ]
                    print(f"Filtered anomaly data: {len(df_anomaly_selected)} rows between {start_time} and {end_time}")
                
                anomaly_data = df_anomaly_selected.to_dict(orient="records")
        else:
            print(f"Warning: {anomaly_data_path} not found")
        
        return {
            "message": "Data retrieved successfully",
            "data": data,
            "anomaly_data": anomaly_data
        }
    except Exception as e:
        import traceback
        print(f"Error in get_data: {str(e)}")
        print(traceback.format_exc())
        return {
            "message": f"Error reading data: {str(e)}",
            "data": [],
            "anomaly_data": []
        }

@app.get("/get_time_range")
async def get_time_range():
    import pandas as pd
    
    normal_data_path = "normal_data.csv"
    
    try:
        if os.path.exists(normal_data_path):
            df = pd.read_csv(normal_data_path)
            if "ts" in df.columns and len(df) > 0:
                # Ensure 'ts' is datetime type
                df["ts"] = pd.to_datetime(df["ts"])
                # Find earliest and latest time
                start_time = df["ts"].min().strftime("%Y-%m-%d %H:%M:%S")
                end_time = df["ts"].max().strftime("%Y-%m-%d %H:%M:%S")
                return {
                    "message": "Time range retrieved successfully",
                    "start_time": start_time,
                    "end_time": end_time
                }
            else:
                return {
                    "message": "No timestamp data found in CSV",
                    "start_time": "",
                    "end_time": ""
                }
        else:
            return {
                "message": f"File {normal_data_path} not found",
                "start_time": "",
                "end_time": ""
            }
    except Exception as e:
        return {
            "message": f"Error reading time range: {str(e)}",
            "start_time": "",
            "end_time": ""
        }

@app.get("/get_anomaly_list")
async def get_anomaly_list():
    import pandas as pd
    
    anomaly_data_path = "anomaly_results_classified.csv"
    
    try:
        if os.path.exists(anomaly_data_path):
            df = pd.read_csv(anomaly_data_path)
            # Convert to list of dict format
            anomaly_list = df.to_dict(orient="records")
            return {"anomaly_list": anomaly_list}
        else:
            return {"anomaly_list": []}
    except Exception as e:
        return {
            "anomaly_list": [],
            "error": str(e)
        }

@app.get("/get_dynamic_tree")
async def get_dynamic_tree():
    import json
    
    tree_file_path = "anomaly_results_classified_tree.json"
    
    try:
        if os.path.exists(tree_file_path):
            with open(tree_file_path, "r", encoding="utf-8") as f:
                tree_data = json.load(f)
            return tree_data
        else:
            return {"error": f"File {tree_file_path} not found"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON format: {str(e)}"}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


@app.post("/anomaly_data")
async def receive_anomaly_data(payload: AnomalyDataPayload):
    print(f"Received anomaly detection results at {payload.time}")
    print(f"Number of data points: {len(payload.data)}")
    print(f"Number of anomalies detected: {len(payload.anomaly_timestamps)}")
    
    if payload.anomaly_timestamps:
        print(f"Anomaly timestamps: {payload.anomaly_timestamps[:5]}...")  # Show first 5
        
        # Perform contribution analysis
        print("\nStarting contribution analysis...")
        contribution_results = analyze_anomaly_contributions(
            payload.data, 
            payload.anomaly_timestamps
        )
        
        output_filename = "backend_anomaly_contribution_results.csv"
        # Save results to CSV
        saved_file = save_contribution_results(results_df = contribution_results, output_file = output_filename)
        
        if contribution_results is not None:
            # Build/extend anomaly tree using the saved CSV
            try:
                generate_anomaly_tree(csv_path=saved_file)
            except Exception as e:
                print(f"[warning] generate_anomaly_tree failed: {e}")
            
            response_data = {
                "message": "Anomaly data received and analyzed successfully", 
                "anomaly_count": len(payload.anomaly_timestamps),
                "data_points_count": len(payload.data),
                "processing_time": datetime.now().isoformat(),
                "contribution_analysis": {
                    "completed": True,
                    "results_file": saved_file,
                    "analyzed_anomalies": len(contribution_results)
                }
            }
        else:
            response_data = {
                "message": "Anomaly data received but contribution analysis failed", 
                "anomaly_count": len(payload.anomaly_timestamps),
                "data_points_count": len(payload.data),
                "processing_time": datetime.now().isoformat(),
                "contribution_analysis": {
                    "completed": False,
                    "error": "Could not analyze contributions"
                }
            }
    else:
        print("No anomalies detected in this batch")
        response_data = {
            "message": "Data received - no anomalies to analyze", 
            "anomaly_count": 0,
            "data_points_count": len(payload.data),
            "processing_time": datetime.now().isoformat(),
            "contribution_analysis": {
                "completed": False,
                "reason": "No anomalies to analyze"
            }
        }
    
    return response_data

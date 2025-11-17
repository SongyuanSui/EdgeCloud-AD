#!/usr/bin/env python3
"""
Anomaly detection script that reads last 2 hours of data from TDengine instead of CSV,
and uses Pacific Time consistently.
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Input, LSTM, RepeatVector, TimeDistributed, Dense
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
import taos
import pytz


# ===========================
# TDengine connection config
# ===========================
DB_NAME = "data"
TABLE_NAME = "realtime_data"
TD_HOST = "localhost"
TD_USER = "root"
TD_PASS = "taosdata"
TD_PORT = 6030
PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Window size for LSTM AutoEncoder
WINDOW_SIZE = 30


def read_data_last_2_hours():
    """
    Read data from TDengine for the most recent two hours (using Pacific Time window).
    For example, if now is 22:30 PDT, read data from 20:30 PDT ~ 22:30 PDT.
    """
    # Current time (Pacific Time)
    now_local = datetime.now(PACIFIC_TZ)
    start_time = now_local - timedelta(hours=2)

    now_str = now_local.strftime("%Y-%m-%d %H:%M:%S")
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"⏱  Querying data from {start_str} to {now_str} (Pacific Time)")

    # Connect to TDengine and explicitly specify timezone=Pacific Time
    conn = taos.connect(
        host=TD_HOST,
        user=TD_USER,
        password=TD_PASS,
        port=TD_PORT,
        timezone="America/Los_Angeles",
    )
    cursor = conn.cursor()
    cursor.execute(f"USE {DB_NAME}")

    # Time range query
    cursor.execute(f"""
        SELECT ts,
               t_ch0,
               t_ch1,
               t_ch2,
               t_ch3,
               v_ch0
        FROM {TABLE_NAME}
        WHERE ts >= '{start_str}'
          AND ts <= '{now_str}'
        ORDER BY ts
    """)

    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    if not rows:
        print("❌ No data found in the last 2 hours.")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=colnames)

    # Ensure ts is datetime (the driver already returns tz-aware, Pacific Time)
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    # We no longer localize or convert
    # df["ts"] is already Pacific Time (with tzinfo), use it directly
    # If you want to remove tzinfo to ease later comparisons, you can create a naive copy:
    df["ts_naive"] = df["ts"].dt.tz_localize(None)

    print(f"✅ Loaded {len(df)} rows from TDengine ({DB_NAME}.{TABLE_NAME})")
    print(df.head(5))
    return df


def detect_anomalies():
    """Main function for anomaly detection using last 2 hours of data"""
    # 1. Read the latest two hours of data from TDengine
    df = read_data_last_2_hours()
    if df is None or df.empty:
        print("No data available in the last 2 hours. Exiting.")
        return

    # All subsequent calculations use ts_naive (timezone-naive datetime) to avoid pandas complaints about tz-aware/tz-naive comparisons
    df["ts_work"] = df["ts_naive"]

    print("First 10 rows of data:")
    print(df[["ts_work", "t_ch0", "t_ch1", "t_ch2", "t_ch3", "v_ch0"]].head(10))

    # 2. Take only the numeric columns (remove timestamp columns)
    df_numeric = df.drop(columns=["ts", "ts_naive", "ts_work"], errors="ignore")

    print(f"NaN values before cleaning: {df_numeric.isnull().sum().sum()}")

    df_numeric = df_numeric.replace([np.inf, -np.inf], np.nan).dropna()

    # Keep the row indices aligned after dropping any invalid numeric rows
    df = df.loc[df_numeric.index].reset_index(drop=True)
    df_numeric = df_numeric.reset_index(drop=True)

    print(f"Data shape after cleaning: {df_numeric.shape}")
    if df_numeric.empty:
        print("After cleaning, no valid numeric rows remain. Exiting.")
        return

    # 3. Normalize (MinMax scaling)
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(df_numeric)

    # 4. Create sliding window sequences
    def create_sequences(data, window_size):
        sequences = []
        for i in range(len(data) - window_size + 1):
            seq = data[i:i + window_size]
            sequences.append(seq)
        return np.array(sequences)

    X_seq = create_sequences(data_scaled, WINDOW_SIZE)
    
    if len(X_seq) == 0:
        print(f"Not enough data points for window size {WINDOW_SIZE}. Need at least {WINDOW_SIZE} rows.")
        return

    print(f"X_seq shape: {X_seq.shape}")

    # 5. Build the LSTM AutoEncoder model
    timesteps = X_seq.shape[1]
    n_features = X_seq.shape[2]

    input_layer = Input(shape=(timesteps, n_features))
    encoded = LSTM(64, activation='tanh')(input_layer)
    repeat = RepeatVector(timesteps)(encoded)
    decoded = LSTM(64, activation='tanh', return_sequences=True)(repeat)
    output_layer = TimeDistributed(Dense(n_features))(decoded)

    autoencoder = Model(inputs=input_layer, outputs=output_layer)
    autoencoder.compile(optimizer=Adam(learning_rate=0.001), loss='mse')

    # 6. Train the model
    autoencoder.fit(
        X_seq, X_seq,
        epochs=50,
        batch_size=32,
        shuffle=True,
        validation_split=0.1,
        verbose=1,
    )

    # 7. Compute reconstruction error
    X_pred = autoencoder.predict(X_seq)
    mse_seq = np.mean(np.power(X_seq - X_pred, 2), axis=(1, 2))

    # 8. Map sequence-level anomaly scores back to the original data points
    # Initialize all pointwise anomaly scores as 0
    anomaly_scores = np.zeros(len(df))
    
    # For each sliding window, assign its MSE score to all data points covered by that window
    for i in range(len(mse_seq)):
        for j in range(WINDOW_SIZE):
            if i + j < len(anomaly_scores):
                # Take the max value so if a point appears in multiple sliding windows, its score accumulates the largest anomaly value
                anomaly_scores[i + j] = max(anomaly_scores[i + j], mse_seq[i])
    
    df["anomaly_score"] = anomaly_scores

    # 9. Anomaly thresholding (use the 99th percentile as cutoff)
    threshold = np.percentile(mse_seq, 99)
    df["is_anomaly"] = df["anomaly_score"] > threshold

    # # 8. Focus only on the middle period (exclude the first/last 30 minutes)
    # actual_start_time = df["ts_work"].min()
    # actual_end_time = df["ts_work"].max()
    # middle_start = actual_start_time + timedelta(minutes=30)
    # middle_end = actual_end_time - timedelta(minutes=30)

    # df_middle = df[(df["ts_work"] >= middle_start) & (df["ts_work"] < middle_end)]
    # anomaly_times = df_middle[df_middle["is_anomaly"] == True]["ts_work"].tolist()
    anomaly_times = df[df["is_anomaly"] == True]["ts_work"].tolist()

    # If no anomalies are detected, skip further processing
    if not anomaly_times:
        print("✅ No anomalies detected.")
        return

    # 9. Prepare output - ensure the format matches the requirement
    df_out = df.copy()
    # For the output, use Pacific Time string for ts (column), rename to "ts"
    df_out["ts"] = df["ts_work"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Only keep columns required: t_ch0, t_ch1, t_ch2, t_ch3, v_ch0, ts
    required_columns = ["t_ch0", "t_ch1", "t_ch2", "t_ch3", "v_ch0", "ts"]
    df_to_send = df_out[required_columns].copy()

    output_data = {
        "time": datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "data": df_to_send.to_dict(orient="records"),
        "anomaly_timestamps": [
            t.strftime("%Y-%m-%d %H:%M:%S") for t in anomaly_times
        ],
    }

    # 10. Print / Save / Send
    print(f"⚠️ Detected {len(anomaly_times)} anomalies.")
    print(f"First 10 anomaly times: {anomaly_times[:10]}")

    with open("anomaly_detection_output.json", "w") as f:
        json.dump(output_data, f, indent=2)
    print("✅ Saved anomaly_detection_output.json")

    print("\nSending results to backend...")
    success = send_anomaly_results_to_backend(output_data)
    if success:
        print("✅ Successfully sent anomaly detection results to backend!")
    else:
        print("⚠️ Failed to send anomaly results to backend.")


def send_anomaly_results_to_backend(output_data):
    """Send anomaly detection results to backend API."""
    url = "http://18.222.143.225:8000/anomaly_data"
    try:
        print(f"Sending anomaly detection results to {url}")
        print(f"Sending {len(output_data['anomaly_timestamps'])} anomalies and {len(output_data['data'])} data points")
        response = requests.post(url, json=output_data)
        response.raise_for_status()
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending to backend: {e}")
        return False


if __name__ == "__main__":
    # Run this script every one hour
    detect_anomalies()

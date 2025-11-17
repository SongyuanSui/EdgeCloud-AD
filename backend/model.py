"""
Anomaly Detection Model and Contribution Analysis

This module contains the DeeplogLSTM model implementation and functions
for analyzing anomaly contributions.
"""

import pandas as pd
import numpy as np
import warnings
from typing import List, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.utils import check_array
from sklearn.utils.validation import check_is_fitted
from pyod.utils.stat_models import pairwise_distances_no_broadcast
from pyod.models.base import BaseDetector
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM
from tensorflow.keras.losses import MSE

warnings.filterwarnings("ignore")


class DeeplogLstm(BaseDetector):
    """
    Deep LSTM-based anomaly detection model for contribution analysis.
    """
    
    def __init__(self, hidden_size: int = 64, optimizer: str = 'adam', loss=MSE, preprocessing=True,
                 epochs: int = 16, batch_size: int = 256, dropout_rate: float = 0.1,
                 l2_regularizer: float = 0.1, validation_size: float = 0.1,
                 window_size: int = 1, stacked_layers: int = 1, verbose: int = 1, contamination: int = 0.0001):

        super(DeeplogLstm, self).__init__(contamination=contamination)
        self.hidden_size = hidden_size
        self.loss = loss
        self.optimizer = optimizer
        self.epochs = epochs
        self.batch_size = batch_size
        self.dropout_rate = dropout_rate
        self.l2_regularizer = l2_regularizer
        self.validation_size = validation_size
        self.window_size = window_size
        self.stacked_layers = stacked_layers
        self.preprocessing = preprocessing
        self.verbose = verbose
        self.dropout_rate = dropout_rate
        self.contamination = contamination

    def _build_model(self):
        """Build and compile the LSTM model."""
        model = Sequential()
        model.add(LSTM(self.hidden_size, input_shape=(self.window_size, self.n_features_),
                       return_sequences=True, dropout=self.dropout_rate))
        for layer in range(self.stacked_layers):
            return_seq = layer != self.stacked_layers - 1
            model.add(LSTM(self.hidden_size, return_sequences=return_seq, dropout=self.dropout_rate))
        model.add(Dense(self.n_features_))
        model.compile(loss=self.loss, optimizer=self.optimizer)
        return model

    def fit(self, X: np.ndarray, y=None):
        """Train the LSTM model."""
        X = check_array(X)
        self._set_n_classes(y)
        self.n_samples_, self.n_features_ = X.shape
        X_train, Y_train = self._preprocess_data_for_LSTM(X)
        self.model_ = self._build_model()
        self.history_ = self.model_.fit(X_train, Y_train, epochs=self.epochs,
                                        batch_size=self.batch_size, validation_split=self.validation_size,
                                        verbose=self.verbose).history
        pred_scores = np.zeros(X.shape)
        pred_scores[self.window_size:] = self.model_.predict(X_train)
        Y_train_for_decision_scores = np.zeros(X.shape)
        Y_train_for_decision_scores[self.window_size:] = Y_train
        self.decision_scores_ = pairwise_distances_no_broadcast(Y_train_for_decision_scores, pred_scores)
        self._process_decision_scores()
        return self

    def _preprocess_data_for_LSTM(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess data for LSTM."""
        if self.preprocessing:
            self.scaler_ = StandardScaler()
            X_norm = self.scaler_.fit_transform(X)
        else:
            X_norm = np.copy(X)
        X_data, Y_data = [], []
        for idx in range(X.shape[0] - self.window_size):
            X_data.append(X_norm[idx:idx + self.window_size])
            Y_data.append(X_norm[idx + self.window_size])
        return np.asarray(X_data), np.asarray(Y_data)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Compute anomaly scores."""
        check_is_fitted(self, ['model_', 'history_'])
        X = check_array(X)
        X_norm, Y_norm = self._preprocess_data_for_LSTM(X)
        pred_scores = np.zeros(X.shape)
        pred_scores[self.window_size:] = self.model_.predict(X_norm)
        Y_norm_for_decision_scores = np.zeros(X.shape)
        Y_norm_for_decision_scores[self.window_size:] = Y_norm
        return pairwise_distances_no_broadcast(Y_norm_for_decision_scores, pred_scores)


def fit_model_and_compute_scores(X_train: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
    """
    Compute overall and feature-wise anomaly scores.
    
    Args:
        X_train: Training data array
        
    Returns:
        Tuple of (overall_scores, feature_scores_list)
    """
    print("Training overall anomaly detection model...")
    transformer = DeeplogLstm(contamination=0.00005)
    transformer.fit(X_train)
    overall_score = transformer.decision_function(X_train)
    overall_score = overall_score / max(overall_score)  # Normalize
    
    print("Training individual feature models...")
    scores = []
    for feat in range(X_train.shape[1]):
        print(f"  Training model for feature {feat + 1}/{X_train.shape[1]}")
        small_transformer = DeeplogLstm(contamination=0.00005)
        train_x = np.array([X_train[:, feat]]).T
        small_transformer.fit(train_x)
        score = small_transformer.decision_function(train_x)
        score = np.nan_to_num(score / max(score))  # Normalize feature score
        scores.append(score)
    
    print("Model training completed.")
    return overall_score, scores


def analyze_anomaly_contributions(data, anomaly_times):
    """
    Analyze anomaly contributions using the backend model.
    
    Args:
        data: List of dictionaries containing sensor data
        anomaly_times: List of anomaly timestamps
        
    Returns:
        DataFrame with contribution analysis results or None if failed
    """
    try:
        print("Starting anomaly contribution analysis...")
        
        # Convert data to DataFrame
        df = pd.DataFrame(data)
        df['ts'] = pd.to_datetime(df['ts']).round('s')
        df = df.dropna()
        
        print(f"Processing {len(df)} data points")
        
        # Identify numerical columns (exclude non-numeric, metadata, and computed columns)
        exclude_cols = ['ts', 'Timestamp', 'Device', 'deviceid', 'anomaly_score', 'is_anomaly']
        numerical_cols = [col for col in df.columns 
                         if df[col].dtype in ['float64', 'int64'] and col not in exclude_cols]
        
        print(f"Numerical columns for analysis: {numerical_cols}")
        
        if not numerical_cols:
            print("ERROR: No numerical columns found for analysis")
            return None
        
        # Prepare data for model
        X_train = np.array(df[numerical_cols])
        print(f"Training data shape: {X_train.shape}")
        
        # Compute contribution scores using the backend model
        overall_score, feature_scores = fit_model_and_compute_scores(X_train)
        
        # Convert anomaly times to datetime
        anomaly_times = [pd.to_datetime(t).round('s') for t in anomaly_times]
        print(f"Looking for {len(anomaly_times)} anomaly timestamps")
        
        # Find indices of anomaly timestamps in the dataframe
        anomaly_indices = df[df['ts'].isin(anomaly_times)].index.tolist()
        
        if anomaly_indices:
            print(f"SUCCESS: Found {len(anomaly_indices)} matching anomaly points")
            
            # Create result dataframe with anomaly data
            result_df = df.loc[anomaly_indices].copy()
            
            # Add contribution scores for each feature
            for i, feature_name in enumerate(numerical_cols):
                result_df[f'contribution_{feature_name}'] = feature_scores[i][anomaly_indices]
            
            # Add overall anomaly score
            result_df['overall_anomaly_score'] = overall_score[anomaly_indices]
            
            print("Contribution analysis completed successfully")
            return result_df
        else:
            print("ERROR: No matching anomaly timestamps found in data")
            return None
            
    except Exception as e:
        print(f"ERROR in contribution analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_contribution_results(results_df, output_file='backend_anomaly_contribution_results.csv'):
    """
    Save contribution analysis results to CSV file.
    
    Args:
        results_df: DataFrame with contribution analysis results
        output_file: Output CSV filename
        
    Returns:
        Filename if successful, None if failed
    """
    if results_df is not None:
        results_df.to_csv(output_file, index=False)
        print(f"Contribution analysis results saved to {output_file}")
        
        # Print summary
        print("\n" + "="*50)
        print("BACKEND CONTRIBUTION ANALYSIS RESULTS")
        print("="*50)
        print(f"Total anomaly points: {len(results_df)}")
        print(f"Time range: {results_df['ts'].min()} to {results_df['ts'].max()}")
        
        # Show top contributing features for each anomaly
        contribution_cols = [col for col in results_df.columns if col.startswith('contribution_')]
        
        for idx, row in results_df.iterrows():
            # Get top 3 contributing features
            contributions = {col.replace('contribution_', ''): row[col] 
                           for col in contribution_cols}
            top_contributors = sorted(contributions.items(), 
                                    key=lambda x: abs(x[1]), reverse=True)[:3]
            
        return output_file
    else:
        print("No results to save")
        return None

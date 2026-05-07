import pandas as pd
import numpy as np
import pytest
from core.anomaly_detection import AnomalyDetectionEngine

def test_percentage_deviation():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 100, 100, 150], index=['2023-01', '2023-02', '2023-03', '2023-04'])
    anomalies = engine.detect_percentage_deviation(series, baseline_window=3, threshold=0.2)
    assert len(anomalies) == 1
    assert anomalies[0]['period'] == '2023-04'
    assert anomalies[0]['deviation'] == 0.5
    assert anomalies[0]['severity'] == 'Critical'

def test_z_score_anomaly():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 105, 95, 100, 98, 102, 300])
    anomalies = engine.detect_z_score_anomalies(series, threshold=2.0)
    assert len(anomalies) == 1
    assert anomalies[0]['actual_value'] == 300

def test_moving_average_anomaly():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 100, 100, 150])
    anomalies = engine.detect_moving_average_anomalies(series, window=3, threshold=0.2)
    assert len(anomalies) == 1
    assert anomalies[0]['deviation'] == 0.5

def test_short_series_safe_handling():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 100])
    assert engine.detect_percentage_deviation(series, baseline_window=3) == []
    assert engine.detect_z_score_anomalies(series) == []
    assert engine.detect_moving_average_anomalies(series, window=3) == []

def test_nan_safe_handling():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 100, np.nan, 100, 200])
    anomalies = engine.detect_percentage_deviation(series, baseline_window=3, threshold=0.2)
    assert len(anomalies) >= 0  # Should run without crashing

def test_summarize_anomalies():
    engine = AnomalyDetectionEngine()
    series = pd.Series([100, 100, 100, 300], index=['1', '2', '3', '4'])
    df = engine.summarize_anomalies('MRR', series)
    assert not df.empty
    assert df['metric'].iloc[0] == 'MRR'

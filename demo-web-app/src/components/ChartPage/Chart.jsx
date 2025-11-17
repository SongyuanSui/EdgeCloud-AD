import { useState } from 'react';
import React from "react";
import './Chart.css';
import Modal from '../Modal';
import AnomalyDetail from './AnomalyDetail';
import AnomalyReport from './AnomalyReport';
//import ScatterChart from "./visualization/ScatterChart";
import LineChart from '../visualization/LineChart';

const Chart = ({ deviceId, data, anomalies, rawAnomalies, channelAliasMap, chartUnitSetting, isLoading }) => {
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [showDetail, setShowDetail] = useState(false);
    const [showReport, setShowReport] = useState(false);

    const toggleDetail = () => {
        setShowDetail(!showDetail);
    };

    const toggleReport = () => {
        setShowReport(!showReport);
    };

    return (
        <div className="chart">
            {isLoading ? (
                <div className="spinner-container">
                    <div className="spinner"></div>
                </div>
            ) : (
                <>
                    <Modal show={showDetail} onClose={toggleDetail}>
                        {selectedIndex !== -1 && rawAnomalies[selectedIndex] ? (
                            <AnomalyDetail AnomalyPoint={rawAnomalies[selectedIndex]} channelAliasMap={channelAliasMap} toggleReport={toggleReport}></AnomalyDetail>
                        ) : (
                            <p>No anomaly selected.</p>
                        )}
                    </Modal>
                    <Modal show={showReport} onClose={toggleReport}>
                        <AnomalyReport />
                    </Modal>
                    <div className="scatter-chart">
                        <LineChart deviceId={deviceId} channelData={data} anomalies={anomalies} chartUnitSetting={chartUnitSetting} setSelectedIndex={setSelectedIndex} toggleDetail={toggleDetail} />
                        {/* <ScatterChart deviceId={deviceId} channelData={data} anomalies={anomalies} setSelectedIndex={setSelectedIndex} toggleDetail={toggleDetail} /> */}
                    </div>
                </>
            )}
        </div>
    )
};

export default Chart;
import React, { useState } from "react";
import './MainPage.css';
import DataDashboard from "../../components/DataDashboard";
import { AnomalyPage } from "../AnomalyPage/AnomalyPage";

export const MainPage = () => {
    const [activeTab, setActiveTab] = useState('visualization');

    const handleTabClick = (tab) => {
        setActiveTab(tab);
    };

    return (
        <div className="main-page-container">
            <div className="tab-header">
                <button 
                    className={`tab-button ${activeTab === 'visualization' ? 'tab-active' : ''}`}
                    onClick={() => handleTabClick('visualization')}
                >
                    Visualization
                </button>
                <button 
                    className={`tab-button ${activeTab === 'anomaly' ? 'tab-active' : ''}`}
                    onClick={() => handleTabClick('anomaly')}
                >
                    Anomaly Detection
                </button>
            </div>
            
            <div className="tab-content">
                {activeTab === 'visualization' && <DataDashboard />}
                {activeTab === 'anomaly' && <AnomalyPage />}
            </div>
        </div>
    );
};

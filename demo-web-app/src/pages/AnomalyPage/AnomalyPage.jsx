import React from "react";
import "./AnomalyPage.css";

import AnomalyExplorer from "../../components/AnomalyExplorerStandalone.jsx";

export const AnomalyPage = () => {
  return (
    <div className="anomaly-page-container">
      <div className="anomaly-content">
        {/* Title block */}
        <h2>Anomaly Detection &amp; Exploration</h2>

        {/* Card: List / Graph / Drilldown explorer */}
        <div className="anomaly-explorer-section">
          <div className="anomaly-explorer-header">
            <h3 className="anomaly-explorer-title">
              Root Cause &amp; Contribution Analysis
            </h3>
            <p className="anomaly-explorer-desc">
              Browse anomalies, inspect contributions, and see grouped
              behavior by domain. Use List or Graph view.
            </p>
          </div>

          <AnomalyExplorer />
        </div>
      </div>
    </div>
  );
};

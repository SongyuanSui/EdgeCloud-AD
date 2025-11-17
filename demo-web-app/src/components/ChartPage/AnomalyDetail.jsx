import React, { useState, useEffect } from "react";
import BarChart from "../visualization/BarChart";
import './AnomalyDetail.css'

const generateContributionListForAnomaly = (anomaly, channelAliasMap) => {
    const contributionList = [];

    Object.keys(channelAliasMap).forEach((channel) => {
        const contribution = `c_${channel}`;

        if (anomaly[contribution] !== null && anomaly[contribution] !== undefined) {
            contributionList.push({
                channelName: channelAliasMap[channel],
                contributionScore: anomaly[contribution],
            });
        }
    });

    contributionList.sort((a, b) => b.contributionScore - a.contributionScore);

    return contributionList;
};

const AnomalyDetail = ({ AnomalyPoint, channelAliasMap, toggleReport }) => {


    const [contributionList, setContributionList] = useState([]);
    useEffect(() => {
        if (AnomalyPoint) {
            const processedContributionList = generateContributionListForAnomaly(AnomalyPoint, channelAliasMap);
            setContributionList(processedContributionList);
        }

    }, [AnomalyPoint, channelAliasMap]);

    const clickOpenReport = () => {
        window.open('https://autoedge.ai/assets/PDF/DatasetReport.pdf', '_blank');
    };

    const clickUploadReport = () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.click();
    };

    return (
        <div className="detail-container" style={{ background: "#f9f9fc", borderRadius: 16, border: "1px solid #ececf0", boxShadow: "0 4px 10px #e0e2e8", padding: 32, display: "flex", flexDirection: "column", maxWidth: 370 }}>
            <div style={{ height: '100%', overflowY: 'auto', width: '100%' }}>
                <div style={{ marginBottom: 22 }}>
                    <span style={{
                        fontWeight: 600,
                        fontSize: 24,
                        color: "#252d37",
                        fontFamily: "'Segoe UI', Arial, sans-serif",
                        letterSpacing: 0.5,
                        display: "block",
                        marginBottom: 6
                    }}>
                        Anomaly Details
                    </span>
                    <div style={{ fontWeight: 400, fontSize: 14, color: "#637381", marginBottom: 10 }}>
                        <span style={{ fontWeight: 600, color: "#1e88e5" }}>Timestamp:</span> {AnomalyPoint.ts}
                    </div>
                </div>
                <div>
                    {
                        Object.entries(AnomalyPoint)
                            .filter(([key]) => key !== 'ts' && key !== 'deviceid' && key[0] !== 'c' && key !== 'label')
                            .map(([key, value]) => (
                                <div
                                    key={key}
                                    style={{
                                        borderBottom: "1px solid #ececec",
                                        padding: "7px 0 5px 0",
                                        display: 'flex',
                                        alignItems: 'center',
                                        fontFamily: "'Segoe UI', Arial, sans-serif"
                                    }}
                                >
                                    <span style={{
                                        minWidth: 140,
                                        color: "#49516d",
                                        fontWeight: 500,
                                        fontSize: 15
                                    }}>
                                        {channelAliasMap[key] || key}:
                                    </span>
                                    <span style={{
                                        color: "#1e293b",
                                        fontWeight: 400,
                                        fontSize: 15,
                                        marginLeft: 10
                                    }}>
                                        {typeof value === 'number' ? value.toFixed(3) : value}
                                    </span>
                                </div>
                            ))
                    }
                </div>
            </div>
        </div>
    );
}

export default AnomalyDetail;
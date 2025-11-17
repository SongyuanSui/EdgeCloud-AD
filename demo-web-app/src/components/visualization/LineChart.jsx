import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  ScatterController,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  ScatterController
);

const LineChart = ({ deviceId, channelData, anomalies, chartUnitSetting, setSelectedIndex, toggleDetail }) => {
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    if (Object.keys(channelData).length === 0) {
      setChartData(null);
    } else if (channelData && Object.keys(channelData).length > 0) {
      const datasets = Object.keys(channelData).flatMap((channel, index) => {

        const dataPoints = channelData[channel].map(point => ({
          x: new Date(point.x),
          y: point.y
        }));

        const anomalyPoints = anomalies[channel]?.map(point => ({
          x: new Date(point.x),
          y: point.y
        })) || [];

        return [
          {
            type: 'line',
            label: `${channel}`,
            data: dataPoints,
            backgroundColor: `rgba(${75 + index * 40}, ${192 - index * 30}, ${132 + index * 20}, 1)`,
            borderColor: `rgba(${75 + index * 40}, ${192 - index * 30}, ${132 + index * 20}, 1)`,
            fill: false,
            order: 2,
            tension: 0.2,
            borderWidth: 1,
            yAxisID: chartUnitSetting["axisMap"][channel] === 1 ? 'y1' : 'y',
          },
          {
            type: 'scatter',
            label: `${channel} - Anomalies`,
            data: anomalyPoints,
            backgroundColor: `rgba(255, 0, 0, 1)`,
            pointRadius: 4,
            borderColor: 'rgba(255, 0, 0, 1)',
            fill: false,
            order: 1,
            hoverRadius: 6,
            yAxisID: chartUnitSetting["axisMap"][channel] === 1 ? 'y1' : 'y',
          }
        ];
      });

      setChartData({
        datasets: datasets,
      });
    }
  }, [deviceId, channelData, anomalies, chartUnitSetting]);
  const options = {
    scales: {
      x: {
        type: 'time',
        time: {
          unit: 'minute',
        },
        title: {
          display: true,
          text: 'Timestamp',
          font: {
            size: 16,
            weight: 'bold',
          },
        },
        ticks: {
          font: {},
          color: "#000",
        },
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: chartUnitSetting["chartUnits"].length > 0 ? chartUnitSetting["chartUnits"][0] : '', 
          font: {
            size: 16,
            weight: 'bold',
          },
        },
        ticks: {
          font: {},
          color: "#000",
          callback: function(value) {
            const unit = chartUnitSetting["chartUnits"][0] === 'Temperature' ? '°F' : ' ';
            // Round to 1 decimal place to avoid floating-point precision issues
            const roundedValue = Math.round(value * 10) / 10;
            return `${roundedValue}${unit}`; 
          },
        },
      },
      y1: chartUnitSetting["chartUnits"].length === 2
        ? {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: chartUnitSetting["chartUnits"][1], 
              font: {
                size: 16,
                weight: 'bold',
              },
            },
            grid: {
              drawOnChartArea: false, 
            },
            ticks: {
              font: {},
              color: "#000",
              callback: function(value) {
                const unit = chartUnitSetting["chartUnits"][1] === 'Temperature' ? '°F' : ' ';
                // Round to 1 decimal place to avoid floating-point precision issues
                const roundedValue = Math.round(value * 10) / 10;
                return `${roundedValue}${unit}`; 
              },
            },

          }
        : undefined, 
    },
    plugins: {
      legend: {
        labels: {
          font: {
            size: 14,
          },
          color: '#000',
        },
      },
    },
    onClick: (event, elements) => {
      if (elements.length > 0) {
        const firstElement = elements[0];
        const datasetIndex = firstElement.datasetIndex;
        const dataIndex = firstElement.index;
        if (datasetIndex % 2) {
          setSelectedIndex(dataIndex);
          toggleDetail();
        }
        console.log(`Clicked on dataset index: ${datasetIndex}, data index: ${dataIndex}`);
      }
    },
  };
  

  return (
    <div>
      <h2>{deviceId}</h2>
      {chartData ? <Line data={chartData} options={options} /> : <p>No data available or no channel selected</p>}
    </div>
  );
};

export default LineChart;

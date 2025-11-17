import React, { useEffect, useState } from 'react';
import { Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

const ScatterChart = ({ deviceId, channelData, anomalies, setSelectedIndex, toggleDetail }) => {
  const [chartData, setChartData] = useState(null);
  

  useEffect(() => {

    if (Object.keys(channelData).length === 0) {
      setChartData(null);
    }
    else if (channelData && Object.keys(channelData).length > 0) {
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
            label: `${channel}`,
            data: dataPoints,
            backgroundColor: `rgba(${75 + index * 40}, ${192 - index * 30}, ${132 + index * 20}, 0.8)`,
            order: 2,
          },
          {
            label: `${channel} - Anomalies`,
            data: anomalyPoints,
            backgroundColor: `rgba(255, 0, 0, 1)`,
            pointRadius: 4,
            order: 1,
            hoverRadius: 6,
          }
        ];
      });

      setChartData({
        datasets: datasets,
      });
    }
  }, [deviceId, channelData, anomalies]);

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
        },
      },
      y: {
        title: {
          display: true,
          text: 'Fahrenheit',
        },
      },
    },
    
    onClick: (event, elements) => {
      if (elements.length > 0) {
        const firstElement = elements[0];
        const datasetIndex = firstElement.datasetIndex;
        const dataIndex = firstElement.index;
        if(datasetIndex%2)
        {
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
      {chartData ? <Scatter data={chartData} options={options} /> : <p>No data available or no channel selected</p>}
    </div>
  );
};

export default ScatterChart;

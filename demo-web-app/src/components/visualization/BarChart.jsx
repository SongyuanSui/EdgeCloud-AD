import React from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';


ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);



const BarChart = ({ contributionList }) => {
 
  const topContributions = contributionList.slice(0, 4);

 
  const labels = topContributions.map(item => item.channelName);
  const dataValues = topContributions.map(item => item.contributionScore);

  
  const data = {
    labels,
    datasets: [
      {
        label: 'Top 4 Contributing Factors',
        data: dataValues, 
        categoryPercentage: 1,
        barPercentage: 0.5,
        backgroundColor: [
          'rgba(150, 0, 10, 0.5)',
          'rgba(54, 162, 235, 0.5)',
          'rgba(255, 206, 86, 0.5)',
          'rgba(75, 192, 192, 0.5)',
        ],
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      x: {},
      y: {
        beginAtZero: true,
      },
    },
  };

  return <Bar data={data} options={options} />;
};

export default BarChart;
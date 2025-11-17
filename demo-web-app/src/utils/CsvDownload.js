
const generateCsvString = (data, channelAliasMap) => {
    const headers = ['Timestamp', 'Device', 't_ch0', 't_ch1', 't_ch2', 't_ch3', 't_ch4', 't_ch5', 't_ch6', 't_ch7', 'v_ch0', 'v_ch1', 'v_ch2', 'v_ch3', 'v_ch4', 'v_ch5', 'v_ch6', 'v_ch7'];
    const processedHeaders = headers.map(header => 
        channelAliasMap[header] ? channelAliasMap[header] : header
    );

    let csvString = processedHeaders.join(',') + '\n';

    data.forEach((row) => {
        csvString += row.join(',') + '\n';
    });

    return csvString;
};


export const triggerDownload = (data, filename, channelAliasMap) => {
    const csvString = generateCsvString(data, channelAliasMap);
    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
};
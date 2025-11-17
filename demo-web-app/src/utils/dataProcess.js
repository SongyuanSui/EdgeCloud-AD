
export const processDataPoints = (rawData, selectedChannels, channelAliasMap, maxPoints) => {

    if (rawData && Array.isArray(rawData)) {


        const channelData = selectedChannels.reduce((acc, channel) => {
            const filteredData = rawData
                .map(row => ({
                    x: new Date(row.ts),
                    y: parseFloat(row[channel]),
                }));


            const sampledData = maxPoints && filteredData.length > maxPoints
                ? sampleData(filteredData, maxPoints)
                : filteredData;

            acc[channelAliasMap[channel]] = sampledData;
            return acc;
        }, {});

        return channelData

    } else {

        return {}
    }
};



const sampleData = (data, maxPoints) => {
    const step = Math.ceil(data.length / maxPoints);
    return data.filter((_, index) => index % step === 0);
};

export const formatTimeString = (timestamp) => {
    const parts = timestamp.split(":");
    if (parts.length === 2) {
        return `${timestamp}:00`;
    }
    return timestamp;

};

export const generateChartUnitsSetting = (selectedChannels, channelAliasMap) => {
    if (selectedChannels.length === 0) {
        return {};
    }

    let chartUnits = [];

    const hasTemperature = selectedChannels.some((channel) => channel.startsWith('t_'));
    const hasPressure = selectedChannels.some((channel) => channel.startsWith('v_'));
    

    if (hasTemperature && hasPressure) {
        chartUnits = ['Temperature', 'Voltage'];
    } else if (hasTemperature) {
        chartUnits = ['Temperature'];
    } else if (hasPressure) {
        chartUnits = ['Voltage'];
    };

    const axisMap = Object.fromEntries(
        Object.entries(channelAliasMap).map(([key, value]) => {
          if (key.startsWith('t_')) {
            return [value, chartUnits.indexOf('Temperature')];
          } else if (key.startsWith('v_')) {
            return [value, chartUnits.indexOf('Voltage')];
          }
          return [value, 0]; 
        })
    );
    
    return { chartUnits, axisMap };
    
};

export const formatDataToTableInChat = (data) => {
    let columns = Object.keys(data[0]);
    
    // Move ts column to front if it exists
    if (columns.includes('ts')) {
        columns = ['ts', ...columns.filter(col => col !== 'ts' && col !== 'deviceid')];
    }

    const colWidths = columns.map(col => 
        Math.max(col.length, ...data.map(row => String(row[col]).length))
    );

    const formatRow = row => 
        "| " + columns.map((col, i) => String(row[col]).padEnd(colWidths[i])).join(" | ") + " |";

    const header = formatRow(Object.fromEntries(columns.map(col => [col, col])));
    
    const separator = "+-" + colWidths.map(w => "-".repeat(w)).join("-+-") + "-+";

    const rows = data.map(formatRow);

    return [separator, header, separator, ...rows, separator].join("\n");
}
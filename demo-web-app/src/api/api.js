import axios from 'axios';

const SERVER_IP = "18.222.143.225:8000";
const CONNECTION = "http";


export const getTimeRange =  async () => {
    try {
        const response = await axios
            .get(`${CONNECTION}://${SERVER_IP}/get_time_range`);
        return response;
    } catch (error) {
        console.error('Error fetching time range:', error);
        throw error;
    }
};

export const getData = async (start_time, end_time) => {
    try {
        const response = await axios
            .get(`${CONNECTION}://${SERVER_IP}/get_data`, {
                params: {
                    start_time: start_time,
                    end_time: end_time
                }
            });
        return response;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
};

export const getAnomalyList = async () => {
    try {
        const response = await axios
            .get(`${CONNECTION}://${SERVER_IP}/get_anomaly_list`);
        return response;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
};

export const getDynamicTree = async () => {
    try {
        const response = await axios
            .get(`${CONNECTION}://${SERVER_IP}/get_dynamic_tree`);
        return response;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
};
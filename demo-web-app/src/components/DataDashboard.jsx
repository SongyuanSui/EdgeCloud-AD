import React from "react";
import Chart from "./ChartPage/Chart";
import { useState, useEffect } from "react";
import './DataDashboard.css'
import { processDataPoints, formatTimeString, generateChartUnitsSetting } from "../utils/dataProcess";
import { getData, getTimeRange} from "../api/api";
import OutlinedInput from '@mui/material/OutlinedInput';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import ListItemText from '@mui/material/ListItemText';
import Select from '@mui/material/Select';
import Checkbox from '@mui/material/Checkbox';
import { useNotification } from '../context/NotificationContext';


const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 6.2 + ITEM_PADDING_TOP,
      width: 400,
    },
  },
};

const DataDashboard = () => {
  const [rawData, setRawData] = useState([]);
  const [rawAnomalies, setRawAnomalies] = useState([]);
  const [deviceId, setDeviceId] = useState("");
  const [data, setData] = useState({});
  const [anomalies, setAnomalies] = useState({});
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [lastStartTime, setLastStartTime] = useState("");
  const [lastEndTime, setLastEndTime] = useState("");
  const [channels, setChannels] = useState([]);
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [isDeviceSelected, setIsDeviceSelected] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState({id: 1, identifier: 'edge_device1', name: 'edge_device_1'});
  const [isLoading, setIsLoading] = useState(false);
  const [channelAliasMap, setChannelAliasMap] = useState({});
  const [chartUnitSetting, setChartUnitSetting] = useState({
    axisMap: {},
    chartUnits: [],
  });

  const MAX_POINTS = 500;

  const showNotification = useNotification();


  const handleDeviceChange = (event) => {
    const selectedIdentifier = event.target.value;
    const selectedDevice = devices.find(device => device.identifier === selectedIdentifier);
    setSelectedDevice(selectedDevice);
  };

  const handleChannelChange = (event) => {
    const {
      target: { value },
    } = event;

    setSelectedChannels(
      // On autofill we get a stringified value.
      Array.isArray(value) ? value : []
    );
  };

  const checkTimeRange = () => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const daysDifference = (end - start) / (1000 * 60 * 60 * 24);

    if (daysDifference > 14) {
      showNotification(
        'Loading data for more than 14 days may take longer or time out. If a timeout occurs, please try a shorter time range.',
        'warning',
        6000
      );
    }
  };

  const handleDrawClick = () => {
    if (selectedChannels.length === 0) {
      showNotification('Please select at least one channel', 'warning');
      return;
    }

    checkTimeRange();

    if (startTime !== lastStartTime || endTime !== lastEndTime) {
      setIsLoading(true);

      getData(formatTimeString(startTime), formatTimeString(endTime)).then((response) => {
        setRawData(response.data.data);
        setRawAnomalies(response.data.anomaly_data);
        console.log('data', response.data.data);
        console.log('anomaly', response.data.anomaly_data)
        const channelData = processDataPoints(response.data.data, selectedChannels, channelAliasMap, MAX_POINTS);
        const anomaliesData = processDataPoints(response.data.anomaly_data, selectedChannels, channelAliasMap);
        setData(channelData);
        setAnomalies(anomaliesData);
      })
        .catch((error) => {
          if (error.message === 'Network Error') {
            showNotification('Data loading timed out. Please try selecting a smaller time range.', 'error', 5000);
          }
          else if (!error.response || error.response.status !== 401) {
            const errorMessage = error.response?.data?.error ||
              error.response?.data?.details ||
              'Failed to load data. Please try again later.';
            showNotification(errorMessage, 'error');
          }
          else {
            showNotification('Failed to load data', 'error');
          }
          console.error('Error:', error);
        }).finally(() => {
          setIsLoading(false);
          setLastStartTime(startTime);
          setLastEndTime(endTime);
        });

    } else {
      const channelData = processDataPoints(rawData, selectedChannels, channelAliasMap, MAX_POINTS);
      const anomaliesData = processDataPoints(rawAnomalies, selectedChannels, channelAliasMap);
      setData(channelData);
      setAnomalies(anomaliesData);
    }
    setChartUnitSetting(generateChartUnitsSetting(selectedChannels, channelAliasMap));

  };

  const getDeviceList = () => {
    setDevices([{id: 1, identifier: 'edge_device1', name: 'edge_device_1'}]);
  };

  useEffect(() => {
    getDeviceList();

    getTimeRange()
      .then(response => {
        const { start_time, end_time } = response.data;
        setStartTime(formatTimeString(start_time));
        setEndTime(formatTimeString(end_time));
      })
      .catch(error => {
        showNotification('Failed to fetch time range.', 'error');
        console.error('Error fetching time range:', error);
      });
    setIsDeviceSelected(true);
    setDeviceId('edge_device_1');
    // setChannels(['t_ch0', 't_ch1', 't_ch2', 't_ch3', 'v_ch1']);
    // setChannelAliasMap({
    //   't_ch0': 'temperature_channel_1',
    //   't_ch1': 'temperature_channel_2',
    //   't_ch2': 'temperature_channel_3',
    //   't_ch3': 'temperature_channel_4',
    //   'v_ch1': 'voltage_channel_1',
    //   });
    setChannels([
      'aimp', 'amud', 'arnd', 'asin1', 'asin2', 'adbr', 'adfl',
      'bed1', 'bed2', 'bfo1', 'bfo2', 'bso1', 'bso2', 'bso3',
      'ced1', 'cfo1', 'cso1'
    ]);
    setChannelAliasMap({
      'aimp': 'aimp',
      'amud': 'amud',
      'arnd': 'arnd',
      'asin1': 'asin1',
      'asin2': 'asin2',
      'adbr': 'adbr',
      'adfl': 'adfl',
      'bed1': 'bed1',
      'bed2': 'bed2',
      'bfo1': 'bfo1',
      'bfo2': 'bfo2',
      'bso1': 'bso1',
      'bso2': 'bso2',
      'bso3': 'bso3',
      'ced1': 'ced1',
      'cfo1': 'cfo1',
      'cso1': 'cso1',
    });
  }, []);

  return (
    <div className="navi-tab-container">

      {true &&
        <div className="control-bar">
          <div className="device-select-container">
            <div className="text">
              Devices
            </div>
            <select value={selectedDevice?.identifier || ''} onChange={handleDeviceChange}>
              <option value="" disabled className="device-select">Select a device</option>
              {devices.map((device, index) => (
                <option key={device.identifier} value={device.identifier}>
                  {device.name}
                </option>
              ))}
            </select>
          </div>

          {isDeviceSelected && (
            <div className="draw-settings">
              <div className="time-inputs">
                <div className="text">
                  Start Time
                </div>
                <input className="time-input"
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  step="1"
                />

                <p className="text">
                  End Time
                </p>
                <input className="time-input"
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  step="1"
                />
              </div>
              <div className="channels-buttons-container">
                <div className="channel-select-container">
                  <div className="text">
                    Channels
                  </div>
                  {/* <div className="channel-select">
                    <select
                      value={selectedChannels}
                      onChange={handleChannelChange}
                    >
                      <option value="" disabled> Select</option>
                      {channels.map(channel => (
                        <option key={channel} value={channel}>
                          {channelAliasMap[channel]}
                        </option>
                      ))}
                    </select>
                  </div> */}
                  <FormControl sx={{ width: 400, textAlign: "center" }}>
                    <Select
                      labelId="demo-multiple-checkbox-label"
                      id="demo-multiple-checkbox"
                      multiple
                      displayEmpty
                      value={selectedChannels}
                      onChange={handleChannelChange}
                      input={
                        <OutlinedInput
                          sx={{
                            '& .MuiOutlinedInput-notchedOutline': {
                              display: 'none',
                            },
                            color: 'black',
                            padding: '10px 10px',
                            border: 'none',
                            borderRadius: '10px',
                            fontSize: '16px',
                            fontFamily: "'Arial', sans-serif",
                            fontWeight: 'bold',
                            boxShadow: '0px 4px 6px rgba(0, 0, 0, 0.1)',
                            width: '400px',
                            height: '40px',
                            cursor: 'pointer',
                          }}
                        />
                      }
                      renderValue={(selected) => {
                        if (selected.length === 0) {
                          return <b>Select Channels</b>;
                        }

                        return selected.map((item) => channelAliasMap[item]).join(', ');
                      }
                      }
                      MenuProps={MenuProps}
                    >
                      {channels.map((channel) => (
                        <MenuItem key={channel} value={channel}>
                          <Checkbox checked={selectedChannels.includes(channel)} />
                          <ListItemText primary={channelAliasMap[channel]} />
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </div>

                <button className="draw-button" disabled={isLoading} onClick={handleDrawClick}>Plot</button>
              </div>


            </div>
          )}


        </div>
      }

      {/* Content pages which share the device selector and control bar. The content of the pages are different based on the active tab. */}
      {
        <div className="tab-content">

          {true &&
            (
              isDeviceSelected
                ? <Chart
                  deviceId={deviceId}
                  data={data} anomalies={anomalies}
                  rawAnomalies={rawAnomalies}
                  channelAliasMap={channelAliasMap}
                  chartUnitSetting={chartUnitSetting}
                  isLoading={isLoading}>
                </Chart>
                : <p>Please select a device first</p>
            )
          }

        </div>
      }


    </div>
  );


};

export default DataDashboard;

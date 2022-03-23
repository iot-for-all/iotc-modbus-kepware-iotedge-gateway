# **Introduction**
In this step-by-step workshop you will connect modbus device(s) with IoT Central application via KEPServerEx and an IoT Edge Gateway

## **Scenarios**
modbus devices connected to IoT Central via IoT Edge Gateway using the following patterns:
- [Opaque](#opaque-pattern): In this pattern IoT Edge Gateway is only device known in the cloud

&nbsp;
## Opaque pattern
In this pattern IoT Edge Gateway is the only device known in the cloud. All capabilities are part of that one device.

1. Setup and run [modbus Simulator and KEPServerEx](deviceenv.md)
2. Build and publish [opaque custom IoT Edge module](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/tree/main/edge-gateway-modules/ptc-opaque/README.md)
3. Setup [IoT Central application](iotcentral.md)
4. Deploy an [IoT Edge enabled Linux VM](edgevm.md)
5. Confim that IoT Edge device status shows _"Provisioned"_ in your IoT Central application
    
    [<img src=./assets/02_device_status.png heigth="60%" width="60%">](/assets/02_device_status.png)
6. [IoT Edge Gateway commands to handle modbus CRUD](commands.md)
7. [Configure KEPServerEX and connect](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/tree/main/app/README.md)
    - First call **file** command to set the configuration
    - then call **connect** command to get IoT Edge Gateway connected to KEPServerEX
8. click on IoT Edge Gateway device and select _"Raw data"_ tab and verify the telemetry is flowing

    [<img src=./assets/03_device_rawdata.png heigth="60%" width="60%">](/assets/03_device_rawdata.png)

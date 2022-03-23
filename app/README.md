# Configure IoT Edge Gateway module

## Prerequisite:
- Install Python 3.7 or higher from [here](https://www.python.org/downloads/)
- Install pip from [here](https://www.makeuseof.com/tag/install-pip-for-python/)

## Generate the configuration payload
1. Copy the [provided folder](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/tree/master/app) to your development machine and open it in VSCode
2. Install necessary packages by executing the following commans:
    ```python
    pip install -r requirements.txt
    ```
3. Open the **ptc01.json** file and replace the following placeholders with the actual values:
    - <YOUR_WIN_VM_PUBLIC_IP>
    - <YOUR_PTC_USER_ID>
    - <YOUR_PTC_USER_PASSWORD>
4. Run **com_input_gen.py** either from within Visual Studio Code or the command line with:
    ```
    python com_input_gen.py
    ```

Running the above code will create an **output.json** file. Copy the content of it and paste into command's payload as discribe below:

## Connect, disconnect, disable instructions
You're using IoT Centralfeature **"model-less command"** to execute Direct Methods on IoT Edge Gateway.
1. In your IoT Central application, click on your IoT Edge Gateway device to go to device detail page
2. On device detail page click on **Manage device** tab then select **Command**

   [<img src=../assets/15_model_less_command.png heigth="60%" width="60%">](/assets/15_model_less_command.png)

3. Using _"model-less command"_, you could send the following commands to IoT Edge Gateway module **"plc_ptc_crud"**:
    - **file**: setup the configuration file in IoT Edge Gateway module <br />
        - **Method name**: file
        - **Module name**: plc_ptc_crud
        - **Payload**: Copy the content of **output.json** file and paste

         It will create entry in twin's reported properties like:
         ```json
         {
             "ptc": {
                 "ptc01": {
                     "config": "/files/ptc01.json",
                     "enabled": false
                 }
             }
         }
         ```
    - **connect**: Toggles the **enabled** flag to true so the module could setup the device and connect <br />
        - **Method name**: connect
        - **Module name**: plc_ptc_crud
        - **Payload**: [{"assetId": "ptc01"}]
    - **disconnect**: Removes the configuration and disconnects the device<br />
        - **Method name**: disconnect
        - **Module name**: plc_ptc_crud
        - **Payload**: [{"assetId": "ptc01"}]
    - **disable**: disconnects the device and changed the **enabled** flag to false<br />
        - **Method name**: disable
        - **Module name**: plc_ptc_crud
        - **Payload**: [{"assetId": "ptc01"}]



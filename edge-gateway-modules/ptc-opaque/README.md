# IoT Edge Gateway custom module

## Prerequisite:
- Install Python 3.7 or higher from [here](https://www.python.org/downloads/)
- Need an [Azure Container Registry(ACR)](https://portal.azure.com/#create/Microsoft.ContainerRegistry). Our example uses ACR. Please create one if you don't have already and note the _"Login server"_, _"Registry name"_, _"User name"_, and _"password"_. You need them when you're building and publishing your module
- Install Docker in your development machine from [docker.com](https://www.docker.com/products/docker-desktop)
- In your development machine run the following command: _"docker login -u <YOUR_DOCKER_USER_NAME> -p <YOUR_DOCKER_PASSWORD>"_

## Build and publish OPAQUE module
1. Copy the [provided solution](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/tree/main/edge-gateway-modules/ptc-opaque) to your development machine and open it in VSCode
2. Install vscode extension [Azure IoT Tools](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.azure-iot-tools)
3. in [.env file](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/blob/main/edge-gateway-modules/ptc-opaque/.env#L2-L4) replace all instance of:
    - <YOUR_ACR_REGISTRY_NAME> with your ACR _"Registry name"_
    - <YOUR_ACR_REGISTRY_PASSWORD> with your ACR _"password"_
4. Right click on [deployment.template.json](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/blob/main/edge-gateway-modules/ptc-opaque/deployment.template.json) in your vscode solution and select _"Build and Push IoT Edge Solution"_. If successful, you should see the _"plc_ptc_crud"_ package in your ACR Repositories
    - If you see the following **unauthorized** error pushing the module to ACR

      [<img src=../../assets/29_acr_push_err.png heigth="25%" width="25%">](/assets/29_acr_push_err.png)

      Open the command prompt and execute the following azure CLI commands:
      ```shell
      az login
      az acr login -n <YOUR_ACR_NAME> --expose-token
      docker login <YOUR_ACR_NAME>.azurecr.io --username 00000000-0000-0000-0000-000000000000 --password <EXPOSE_TOKEN_FROM_ABOVE_RUN>
      ```
5. Use the [config/deployment.amd64.json](https://github.com/iot-for-all/iotc-modbus-kepware-iotedge-gateway/blob/main/edge-gateway-modules/ptc-opaque/config/deployment.amd64.json) file to create IoT Edge Gateway device template in your IoT Central application

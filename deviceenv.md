# modbus Simulator and KEPServer setup

## To setup Simulator

1.  Go to step #3, If you'd like to use an existing Windows VM
2.  Create Windows Virtual Machine using the following CLI commands:

    ```shell
    	#!/bin/bash
    	az login

    	# Setup account subscription
    	az account set --subscription <YOUR_SUBSCRIPTION_NAME>

    	# Make sure resource group exists
    	az group create \
    		--name <YOUR_RESOURCE_GROUP_NAME> \
    		--location <AZURE_REGION>

    	# Create a new VM running Windows
    	az vm create \
    		--resource-group <YOUR_RESOURCE_GROUP_NAME> \
    		--name <YOUR_VM_NAME> \
    		--image Win2019Datacenter \
    		--public-ip-sku Standard \
    		--admin-username <YOUR_USER_NAME> \
    		--admin-password <YOUR_PASSWORD>
    ```

3.  Open your VM in Azure portal click on **"Networking"** and check the following ports for being opened or not:
    - Open port 5020 for modbus client/server to connect and communicate if it's not open
      ```shell
      	# Open port 5020 for modbus connection
      	# Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection.
      	az vm open-port \
      		--port 5020 \
      		--resource-group <YOUR_RESOURCE_GROUP_NAME> \
      		--name <YOUR_VM_NAME> \
      		--priority <RULE_PRIORITY>

		# Open port 9000 for modbus simulator API calls you'll use to set registery values
      	# Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection.
      	az vm open-port \
      		--port 9000 \
      		--resource-group <YOUR_RESOURCE_GROUP_NAME> \
      		--name <YOUR_VM_NAME> \
      		--priority <RULE_PRIORITY>
      ```
    - Open port 3389 for RDP connection if it's not open
      ` shell # Open port 3389 for RDP connection (Remote Desktop) # Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection. az vm open-port \ --port 3389 \ --resource-group <YOUR_RESOURCE_GROUP_NAME> \ --name <YOUR_VM_NAME> \ --priority <RULE_PRIORITY> `
      [<img src=../assets/18_sim_server_ports.png heigth="60%" width="60%">](/assets/18_sim_server_ports.png)
4.  Connect to the Windows Virtual Machine using publicIpAddress returned in the output from your VM
    ```shell
    	mstsc /v:<VM_PUBLIC_IP_ADDRESS>
    ```
5.  Turn off Windows defender for _"Guest or public network"_ (Please note, defender should not be disabled in production. We're turning it off for the sake of this exercise)

    - Go to **"Control Panel --> System and Security --> Windows Defender Firewall"** and click on _"Turn Windows Defender Firewall on or off"_

      [<img src=./assets/19_server_vm_defender.png heigth="60%" width="60%">](/assets/19_server_vm_defender.png)

    - On the next page select the _"Turn off Windows Defender Firewall"_ radio button under _"Public network settings"_ section then click _"Ok"_ button

      [<img src=./assets/20_server_vm_defender_off.png heigth="60%" width="60%">](/assets/20_server_vm_defender_off.png)

    - Verify the _"Guest or public networks"_ section looks like below:

      [<img src=./assets/21_server_vm_defender_off_mode.png heigth="60%" width="60%">](/assets/21_server_vm_defender_off_mode.png)

6.  Install **Unserver** modbus simulator in Windows VM from [here](https://unserver.xyz/docs/unslave/)
7.  Replace the content of modbus simulator config.json with the following json
    ```json
    {
		"version": "3.0.3",
		// mode: "RTU" | "TCP"
		"mode": "TCP",
		"port": {
			"name": "COM1",
			"baudRate": 19200,
			"dataBits": 8,
			"parity": "none",
			"stopBits": 1
		},
		"frameDelay": null,
		"tcpPort": 5020,
		"slaves": {
			"1": {
				"isOnline": false,
				"registers": {
					"HR0": 1,
					"HR1": 2,
					"HR2": 3,
					"HR10": "0x0A",
					"HR11": "0x0B",
					"HR12": "0x0C",
					"HR13": "0xFFFF",
					"HR14": "0x1234",
					"HR999": { "exception": 3 },
					"IR1": 1,
					"IR2": 2,
					"C0": false,
					"C1": true,
					"DI1": true,
					"DI2": false
				}
			},
			"2": {
				"isOnline": true,
				"registers": {
					"HR0": 11,
					"HR1": 12,
					"HR2": 13,
					"HR10": 1234,
					"HR11": 5678
				}
			}
		},
		"api": {
			"enable": true,
			"port": 9000
		}
	}
    ```
8. Run the modbus simulator from a shell
    ```shell
    	unslave.exe
    ```
9. Observe the modbus simulator waiting for client to connect plus note the ports that needs to get open

	  [<img src=./assets/22_modbus_sim_run.png heigth="50%" width="50%">](/assets/22_modbus_sim_run.png)
10. Download and Install free version of **KEPServerEx** in Windows VM from [here](https://www.kepware.com/en-us/products/kepserverex/)
11. Open **KEPServer Administration** and **KEPServer Configuration** tools

	  [<img src=./assets/23_ptc_server_open.png heigth="20%" width="20%">](/assets/23_ptc_server_open.png)
12. On task bar right click on **KEPServer** icon and select **Settings**

	  [<img src=./assets/24_ptc_settings_open.png heigth="20%" width="20%">](/assets/24_ptc_settings_open.png)
13. Select **Configuration API Service** tab, Enable plus note the ports being used for configuration API

	  [<img src=./assets/25_ptc_settings_api_config.png heigth="50%" width="50%">](/assets/25_ptc_settings_api_config.png)
14. Select **User Manager** tab, add an Administrator user. You'll be using this user calling configuration API

	  [<img src=./assets/27_ptc_user_add.png heigth="50%" width="50%">](/assets/27_ptc_user_add.png)
15. On task bar right click on **KEPServer** icon and select **OPC UA Configuration**

      [<img src=./assets/26_ptc_opcua_open.png heigth="20%" width="20%">](/assets/26_ptc_opcua_open.png)
16. On OPC UA Configuration Manager select **Server Endpoints** then check the **Enabled** box and note the OPC UA ports, plus **Edit** and set **Security** to **None** if it is set to anything other than None

	  [<img src=./assets/28_ptc_opcua_config.png heigth="50%" width="50%">](/assets/28_ptc_opcua_config.png)
17. In the Kepserver Config tool, right click on **Project**, select **OPCUA**, set **Allow anonymous login** to **Yes**, and click on **OK** button

	  [<img src=./assets/30_ptc_opcua_config_security.png heigth="50%" width="50%">](/assets/30_ptc_opcua_config_security.png)
18. Open ports for KEPServerEx configuration API and OPC UA connections
      ```shell
      	# Open KEPServerEX configuration API port noted in step # 13 (default should be 57412)
      	# Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection.
      	az vm open-port \
      		--port 57412 \
      		--resource-group <YOUR_RESOURCE_GROUP_NAME> \
      		--name <YOUR_VM_NAME> \
      		--priority <RULE_PRIORITY>

		# Open KEPServerEX OPC UA port noted in step # 16 (default should be 49320)
      	# Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection.
      	az vm open-port \
      		--port 49320 \
      		--resource-group <YOUR_RESOURCE_GROUP_NAME> \
      		--name <YOUR_VM_NAME> \
      		--priority <RULE_PRIORITY>
      ```


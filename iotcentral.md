# IoT Central Application Setup

1. Create an [IoT Central application](https://apps.azureiotcentral.com/build)
2. Click on **"Create app"**

    [<img src=./assets/05_central_app_create.png heigth="60%" width="60%">](/assets/05_central_app_create.png)
3. Fill up the required information and click **"Create"**

    [<img src=./assets/06_central_app_create.png heigth="60%" width="60%">](/assets/06_central_app_create.png)
4. Click on **"Device template"** then **"+ New"**start creating an IoT Edge device template 

    [<img src=./assets/07_device_template.png heigth="60%" width="60%">](/assets/07_device_template.png)
5. On the **"Select type"** page click on **"Azure IoT Edge"** tile

    [<img src=./assets/08_device_template_type.png heigth="60%" width="60%">](/assets/08_device_template_type.png)
6. Click **"Next: Customize"** and provide a name in **"Device template name"** textbox, ckeck _"This is a gateway device"_ checkbox, and click on **"Browse"** button to upload the [deployment.amd64.json (opaque)](/edge-gateway-modules/ptc-opaque/config/deployment.amd64.json) then click **"Next: Review"**

    [<img src=./assets/09_device_template_upload.png heigth="60%" width="60%">](/assets/09_device_template_upload.png)
7. Click on **"Create"** button on **"Review"** page
8. On the next page click on **"Relationships"**

    [<img src=./assets/10_device_template_rel.png heigth="60%" width="60%">](/assets/10_device_template_rel.png)
9. Set the relationship by clicking on **"+ Add relationship"**, put "any" word in all 3 textboxes (Display name, Name, and Target), then click on **"Save"**, and finally **"Publish"**

    [<img src=./assets/11_device_template_pub.png heigth="60%" width="60%">](/assets/11_device_template_pub.png)
10. Click on **"Devices"**, select the template you just created, and click on **"Create a device"** button to register an IoT Edge Gateway device to your application

    [<img src=./assets/12_device_template_select.png heigth="60%" width="60%">](/assets/12_device_template_select.png)
11. On the **"Create a new device"** page fill up the display name, Device ID, make sure your device template is seleted in **"Device template"** dropdown, finally click on **"Create"**

    [<img src=./assets/13_device_reg.png heigth="60%" width="60%">](/assets/13_device_reg.png)
12. Go to device explorer page and confirm the device status shows as _"Registered"_

    [<img src=./assets/14_device_created.png heigth="60%" width="60%">](/assets/14_device_created.png)
13. Click on device you just registered above and open _"Connect"_ tab

    [<img src=./assets/04_device_connect_tab.png heigth="60%" width="60%">](/assets/04_device_connect_tab.png)
14. Note the **"ID scope"**, **"Device ID"**, and **"Primary key"** values. You need them later to configure IoT Edge runtime 1.2

    [<img src=./assets/01_device_connect.png heigth="60%" width="60%">](/assets/01_device_connect.png)
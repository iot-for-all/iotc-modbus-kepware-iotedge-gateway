# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
from asyncio.tasks import sleep
import json
import time
import uuid
import math
import random
import base64
import os
import sys
sys.path.insert(0, "..")
import asyncio
from datetime import datetime, timedelta

import requests
from requests.auth import HTTPBasicAuth

from opcua import Client, ua
from azure.iot.device import Message, MethodResponse
from azure.iot.device.aio import IoTHubModuleClient


try:  
    # python 3.4
    from asyncio import JoinableQueue as Queue
except:  
    # python 3.5
    from asyncio import Queue

# global counters
TWIN_CALLBACKS = 0
RECEIVED_MESSAGES = 0
PAUSE_IN_SECOND = 15
PUBLISH_INTERVAL_MS = 500
OPAQUE = False

module_client = None
asset_dict = {}
root_node_dict = {}
startTimer = time.process_time()

multipart_msg_schema = '{{"data": "{}"}}'
config_chunks = {}
async def file_processor(method_request):
    method_name = method_request.name
    payload = method_request.payload
    multi_part = payload.get("multipart-message")
    id = payload.get("id")
    assetId = payload.get("assetId")
    part = payload.get("part")
    maxPart = payload.get("maxPart")
    data = payload.get("data")
    print ("file_processor: DirectMethod: {}".format(method_name))
    print ("\tmultipart-message: {}\n\tid: {}\n\tassetId: {}\n\tpart: {}\n\tmaxPart: {}".format(multi_part, id, assetId, part, maxPart))
    if data and multi_part and multi_part == "yes":
        id = payload.get("id")
        print("file_processor: multi part message received: {}".format(id))
        config = config_chunks.get(id)
        if config == None:
            print("file_processor: setting config_chunks: {}".format(id))
            config_chunks[id] = {}
            config_chunks[id].update({"assetId": payload.get("assetId")})
            config_chunks[id].update({"maxPath": payload.get("maxPart")})
            config_chunks[id].update({"parts": {}})
        
        config = config_chunks.get(id)
        print("file_processor: Processing part: {}".format(payload.get("part")))
        parts = config.get("parts")
        parts.update({payload.get("part"): data})
        
        # check to see if all the file parts are available
        if len(parts) == int(config.get("maxPath")):
            print("file_processor: Recieved all parts: {}".format(config.get("maxPath")))
            encodedData = ""
            for key, value in parts.items():
                print("- Processing chunk: {}".format(key))
                encodedData = encodedData + value
            
            decodedData = base64.b64decode(encodedData)
            
            # write to disk
            fileName = "/files/{}.json".format(config.get("assetId"))
            print("file_processor: Creating config file: {}".format(fileName))
            file = open(fileName, "wb")
            file.write(decodedData)
            file.close()
            print("file_processor: Cleaning up cached chunks . . .")
            print("file_processor: Update reported properties for asset: {}".format(config.get("assetId")))
            await reported_properties_update(assetId=config.get("assetId"), config_file=fileName, enabled=False)
            config_chunks.pop(id)

    res = {}
    res.update({ assetId: { "status": 201, "data": "Processed id: '{}', part: '{}' of '{}'".format(id, part, maxPart)}})
    payload = {"result": True, "data": res}  # set response payload
    status = 207
    
    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("executed file")


def message_handler(message):
    print("Message received on INPUT 1")
    print("the data in the message received was ")
    print(message.data)
    print("custom properties are")
    print(message.custom_properties)
            

# Send a file over the IoT Hub transport to IoT Central
async def send_config_content(filepath, data):
    file_size_kb = len(data) / 1024

    # encode the data with base64 for transmission as a JSON string
    data_base64 = base64.b64encode(data).decode("ASCII")

    max_msg_size = 255 * 1024
    msg_template_size = len(multipart_msg_schema)
    max_content_size = max_msg_size - msg_template_size
    
    max_parts = int(math.ceil(len(data_base64) / max_content_size))
    id = uuid.uuid4()
    part = 1
    index = 0

    # chunk the file payload into 255KB chunks to send to IoT central over MQTT (could also be AMQP or HTTPS)
    status = 200
    status_message = "completed"
    for i in range(max_parts):
        data_chunk = data_base64[index:index + max_content_size]
        index = index + max_content_size
        
        payload = multipart_msg_schema.format(data_chunk)
        if module_client and module_client.connected:
            print("Start sending multi-part message: %s" % (payload))
            msg = Message(payload)
            
            # standard message properties
            msg.content_type = "application/json";  # when we support binary payload this should be changed to application/octet-stream
            msg.content_encoding = "utf-8"; # encoding for the payload utf-8 for JSON and can be left off for binary data

            # custom message properties
            msg.custom_properties["multipart-message"] = "yes";  # indicates this is a multi-part message that needs special processing
            msg.custom_properties["id"] = id;   # unique identity for the multi-part message we suggest using a UUID
            msg.custom_properties["filepath"] = filepath; # file path for the final file, the path will be appended to the base recievers path
            msg.custom_properties["part"] = str(part);   # part N to track ordring of the parts
            msg.custom_properties["maxPart"] = str(max_parts);   # maximum number of parts in the set
            compression_value = "none"
            msg.custom_properties["compression"] = compression_value;   # use value 'deflate' for compression or 'none'/remove this property for no compression
            
            try:
                await module_client.send_message_to_output(msg, "output1")
                print("completed sending multi-part message")
            except Exception as err:
                status_message = "Received exception during send_message. Exception: " + err
                print(status_message)
                status = 500
            
        part = part + 1

    # send a config status message to IoT Central over MQTT
    payload = f'{{"filename": "{filepath}", "filepath": "{filepath}", "status": {status}, "message": "{status_message}", "size": {file_size_kb}}}'
    msg = Message(payload)
            
    # standard message properties
    msg.content_type = "application/json";  # when we support binary payload this should be changed to application/octet-stream
    msg.content_encoding = "utf-8"; # encoding for the payload utf-8 for JSON and can be left off for binary data

    await module_client.send_message_to_output(msg, "output1")
    print("completed sending config status message")

            
async def reported_properties_update(assetId, config_file, enabled):
    reported = {
        "ptc": {
            assetId: {
                "config": config_file,
                "enabled": enabled
            }
        }
    }

    print("reported_properties_update: {}".format(json.dumps(reported)))
    await module_client.patch_twin_reported_properties(reported)
    print("reported_properties_update: Updated reported properties for ptc: {}".format(assetId))

# update modbus registry values to simulate an active PLC
async def set_registers(plc_url, id, tags, secret):
    for tag in tags:
        register = tag.get("servermain.TAG_ADDRESS")
        if register == "400001":
            register = "HR0"
        elif register == "400003":
            register = "HR2"
        elif register == "400011":
            register = "HR10"

        value = random.randint(0, 32768)
        print ("set_registers: {}/slaves/{}/registers/{} value: {}".format(plc_url, id, register, value))
        res = requests.put("{}/slaves/{}/registers/{}".format(plc_url, id, register), json = {"value": value}, auth = secret)
        print(res.raise_for_status())


# KepServerEx channel setup
async def setup_channel(url, channel, tagList, basicAuth):
    print("setup_channel: start . . .")
    print("  - post_url: {}".format(url))
    payload = {}
    for k, v in channel.items():
        if k == "device":
            continue
        payload.update({ k: v })
        
    name = channel.get("common.ALLTYPES_NAME")
    get_url = "{}/{}".format(url, name)
    res = requests.get(get_url, auth = basicAuth)
    if res.status_code == 404:
        res = requests.post(url, json = payload, auth = basicAuth)
    elif res.status_code == 200:
        projectId = json.loads(res.text).get("PROJECT_ID")
        payload.update({"PROJECT_ID": projectId})
        res = requests.put(get_url, json = payload, auth = basicAuth)

    print(res.raise_for_status())
    print("  - get_url: {}".format(get_url))
    res = requests.get(get_url, auth = basicAuth)
    
    device = channel.get("device")
    device_url = "{}/devices".format(get_url)
    print("Setting up device: {}/{}".format(device_url, device.get("common.ALLTYPES_NAME")))
    await setup_device(device_url, device, tagList, basicAuth)
    print("setup_channel: end . . .")


# KepServerEx device setup
async def setup_device(url, device, tagList, basicAuth):
    print("setup_device: start . . .")
    print("  - post_url: {}".format(url))
    payload = {}
    for k, v in device.items():
        if k == "tags" or k == "tagGroups":
            continue
        payload.update({ k: v })
    
    name = device.get("common.ALLTYPES_NAME")
    get_url = "{}/{}".format(url, name)
    res = requests.get(get_url, auth = basicAuth)
    if res.status_code == 404:
        res = requests.post(url, json = payload, auth = basicAuth)
    elif res.status_code == 200:
        projectId = json.loads(res.text).get("PROJECT_ID")
        payload.update({"PROJECT_ID": projectId})
        res = requests.put(get_url, json = payload, auth = basicAuth)

    print(res.raise_for_status())
    print("  - get_url: {}".format(get_url))
    res = requests.get(get_url, auth = basicAuth)
    
    tags = device.get("tags")
    if tags and len(tags) > 0:
        tagList.extend(tags)
        for tag in tags:
            tag_url = "{}/tags".format(get_url)
            print("Setting up tag: {}/{}".format(tag_url, tag.get("common.ALLTYPES_NAME")))
            await setup_tag(tag_url, tag, basicAuth)
            
    tagGroups = device.get("tagGroups")
    if tagGroups and len(tagGroups) > 0:
        for tagGroup in tagGroups:
            tag_group_url = "{}/tag_groups".format(get_url)
            print("Setting up tagGroups: {}/{}".format(tag_group_url, tagGroup.get("common.ALLTYPES_NAME")))
            await setup_tag_group(tag_group_url, tagGroup, tagList, basicAuth)
    
    print("setup_device: end . . .")


# KepServerEx tag setup
async def setup_tag(url, tag, basicAuth):
    print("setup_tags: start . . .")
    print("  - post_url: {}".format(url))
    payload = {}
    for k, v in tag.items():
        payload.update({k: v})
        
    name = tag.get("common.ALLTYPES_NAME")
    get_url = "{}/{}".format(url, name)
    res = requests.get(get_url, auth = basicAuth)
    if res.status_code == 404:
        res = requests.post(url, json = payload, auth = basicAuth)
    elif res.status_code == 200:
        projectId = json.loads(res.text).get("PROJECT_ID")
        payload.update({"PROJECT_ID": projectId})
        res = requests.put(get_url, json = payload, auth = basicAuth)
        
    print(res.raise_for_status())
    print("  - get_url: {}".format(get_url))
    res = requests.get(get_url, auth = basicAuth)
    print("setup_tags: end . . .")


# KepServerEx tag_group setup
async def setup_tag_group(url, tag_group, tagList, basicAuth):
    print("setup_tag_groups: start . . .")
    print("  - post_url: {}".format(url))
    payload = {}
    for k, v in tag_group.items():
        if k == "tags" or k == "tagGroups":
            continue
        payload.update({k: v})
    name = tag_group.get("common.ALLTYPES_NAME")
    get_url = "{}/{}".format(url, name)
    res = requests.get(get_url, auth = basicAuth)
    if res.status_code == 404:
        res = requests.post(url, json = payload, auth = basicAuth)
    
    print(res.raise_for_status())
    print("  - get_url: {}".format(get_url))
    res = requests.get(get_url, auth = basicAuth)
    tags = tag_group.get("tags")
    if tags and len(tags) > 0:
        tagList.extend(tags)
        for tag in tags:
            tag_url = "{}/tags".format(get_url)
            print("Setting up tag: {}/{}".format(tag_url, tag.get("common.ALLTYPES_NAME")))
            await setup_tag(tag_url, tag, basicAuth)
            
    tagGroups = tag_group.get("tagGroups")
    if tagGroups and len(tagGroups) > 0:
        for tagGroup in tagGroups:
            tag_group_url = "{}/tag_groups".format(get_url)
            print("Setting up tagGroups: {}/{}".format(tag_group_url, tagGroup.get("common.ALLTYPES_NAME")))
            await setup_tag_group(tag_group_url, tagGroup, basicAuth)
    
    print("setup_tag_groups: end . . .")


# define behavior for receiving a twin patch
async def twin_patch_handler(patch):
    print("the data in the desired properties patch was: {}".format(patch))
    # print("set default publishing interval in desired properties")
    # send new reported properties
    if 'publishInterval' in patch:
        print("Reporting desired changes {}".format(patch))
        reported = { "publishInterval": patch['publishInterval'] }
        await module_client.patch_twin_reported_properties(reported)
        print("Reported twin patch")
        pubInterval = patch["publishInterval"]
        if len(asset_dict) > 0:
            for k, config in asset_dict.items():
                if config == None:
                    continue
                else:
                    print("changing publishing interval to %d ms" % pubInterval)
                    await config.publish_interval_update(pubInterval)
    print("Patched twin")


# Define behavior for handling methods
async def method_request_handler(method_request):
    # print("Method request payload received: {}".format(method_request.payload))
    print("method_request_handler: {}".format(method_request.name))
    # Determine how to respond to the method request based on the method name
    if method_request.name == "file":
        await file_processor(method_request)
    elif method_request.name == "connect":
        await connect_method_handler(method_request)
    elif method_request.name == "disconnect":
        await disconnect_method_handler(method_request)
    elif method_request.name == "disable":
        await disable_method_handler(method_request)
    elif method_request.name == "config":
        await config_method_handler(method_request)
    elif method_request.name == "filter":
        await filter_method_handler(method_request)
    elif method_request.name == "pubInterval":
        await pubInterval_method_handler(method_request)
    else:
        payload = {"result": False, "data": "unknown method"}  # set response payload
        status = 400  # set return status code
        print("executed unknown method: " + method_request.name)

        # Send the response
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await module_client.send_method_response(method_response)


async def connect_method_handler(method_request):
    result = True
    data = {}
    twin = await module_client.get_twin()
    reported_properties = twin["reported"]
    ptc = reported_properties.get("ptc")
    if ptc != None:
        print("connect_method_handler: started . . .")
        reported = {}
        reported["ptc"] = {}
        for item in method_request.payload:
            assetId = item["assetId"]
            if assetId in ptc:
                print("connect_method_handler: Enabling PTC asset: {}".format(assetId))
                reported["ptc"][assetId] = {}
                reported["ptc"][assetId].update({"enabled": True})
                try:
                    await module_client.patch_twin_reported_properties(reported)
                    data.update({ assetId: { "status": 201, "data": "Scheduled connection to PTC asset '{}'".format(assetId)}})
                except:
                    data.update({ assetId: { "status": 400, "data": "Failed to schedule connection to PTC asset '{}'".format(assetId)}})
            else:
                print("connect_method_handler: Not found reported properties for ptc asset: {}".format(assetId))
    else:
        print("connect_method_handler: Not found reported properties for ptc . . .")
    
    payload = {"result": result, "data": data}  # set response payload
    status = 207
    
    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("executed connect")


async def disconnect_method_handler(method_request):
    print("disconnect_method_handler: started . . .")
    result = True
    data = {}
    
    twin = await module_client.get_twin()
    reported_properties =twin["reported"] 
    ptc = reported_properties.get("ptc")
    if ptc != None:
        reported = {}
        reported["ptc"] = {}
        for item in method_request.payload:
            assetId = item["assetId"]
            asset = ptc.get(assetId)
            if asset != None:
                filePath = asset.get("config")
                print("disconnect_method_handler: Removing PTC asset config %s from reported properties" % assetId)
                reported["ptc"].update({ assetId: None })
                print("disconnect_method_handler: {}".format(reported))
                await module_client.patch_twin_reported_properties(reported)
                os.remove(filePath)
            
            config = asset_dict.get(assetId)
            if config == None:
                print("disconnect_method_handler: Found no config to apply disconnect for %s" % assetId)
                data.update({assetId: { "status": 404, "data": "Found no config to apply disconnect for '{}'".format(assetId)}})
                result = False
            else:
                print("disconnect_method_handler: disconnect asset: %s" % assetId)
                try:
                    subscription = config.subscription
                    handles = config.handles
                    if subscription != None and handles != None and len(handles) > 0:
                        subscription.unsubscribe(handles)
                        await sleep(5)
                except Exception as e:
                    print("disconnect_method_handler: Failed to unsubscribe monitor: {}".format(e))

                asset_dict.pop(assetId, None)
                data.update({assetId: { "status": 200, "data": "Disconnect PTC asset '{}'".format(assetId)}})
    
    payload = {"result": result, "data": data}  # set response payload
    status = 207

    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("disconnect_method_handler: executed disconnect")
    
    
async def disable_method_handler(method_request):
    print("disable_method_handler: started . . .")
    result = True
    data = {}
    
    twin = await module_client.get_twin()
    reported_properties =twin["reported"] 
    ptc = reported_properties.get("ptc")
    if ptc != None:
        reported = {}
        reported["ptc"] = {}
        for item in method_request.payload:
            assetId = item["assetId"]
            if ptc.get(assetId) != None:
                print("disable_method_handler: Disabling PTC asset config %s from reported properties" % assetId)
                reported["ptc"][assetId] = {}
                reported["ptc"][assetId].update({"enabled": False})
                await module_client.patch_twin_reported_properties(reported)
            
            config = asset_dict.get(assetId)
            if config == None:
                print("disable_method_handler: Found no config to apply disconnect for %s" % assetId)
                data.update({assetId: { "status": 404, "data": "Found no config to apply disable for '{}'".format(assetId)}})
                result = False
            else:
                print("disable_method_handler: disable asset: %s" % assetId)
                try:
                    subscription = config.subscription
                    handles = config.handles
                    if subscription != None and handles != None and len(handles) > 0:
                        subscription.unsubscribe(handles)
                        await sleep(5)
                except Exception as e:
                    print("disable_method_handler: Failed to unsubscribe monitor: {}".format(e))

                asset_dict.pop(assetId, None)
                data.update({assetId: { "status": 200, "data": "Disable PTC asset '{}'".format(assetId)}})
    
    payload = {"result": result, "data": data}  # set response payload
    status = 207

    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("disable_method_handler: executed disable")
    
    
async def config_method_handler(method_request):
    print("config_method_handler: started . . .")
    result = True
    data = {}
    config_array = {}
    config_array["nodes"] = []
    filepath = method_request.payload.get("filepath")
    if len(asset_dict) <= 0:
        print("config_method_handler: Found no client to retrieve the config")
        payload = {"result": False, "data": "config"}
        status = 404
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await module_client.send_method_response(method_response)
        print("executed config")
        return

    for key, config in asset_dict.items():
        if config == None:
            data.update({config.assetId: { "status": 404, "data": "No config found for PTC asset '{}'".format(key)}})
            result = False
        else:
            print("config_method_handler: Processing asset config %s" % config.assetId)
            print("config_method_handler: Variable nodes: {}".format(config.variable_nodes))
            rootNode = root_node_dict.get(config.assetId)
            if rootNode == None:
                rootNode = "Widget_Maker_1000"
            config_array["nodes"].append({"assetId": config.assetId, "serverUrl": config.url, "nodes": config.hirarchy})
            data.update({config.assetId: { "status": 200, "data": "Got PTC asset '{}' config".format(key)}})
    
    payload = {"result": result, "data": data}
    status = 207
    
    try:
        print("      {}".format(config_array))
        config_str = json.dumps(config_array)
        config = config_str.encode("ASCII")
    
        await send_config_content(filepath, config)
        print("config_method_handler: completed sending config message")
    except Exception as e:
        print("config_method_handler: Failed to send config message: {}".format(e))
        payload = {"result": False, "data": data}
        status = 400

    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("config_method_handler: executed config")


async def filter_method_handler(method_request):
    if len(asset_dict) == 0:
        print("filter_method_handler: Found no client to apply the filter")
        payload = {"result": False, "data": "filter"}
        status = 404
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await module_client.send_method_response(method_response)
        print("filter_method_handler: executed filter")
        return
    
    global startTimer
    result = True
    data = {}
    reported_properties = {}
    reported_properties["ptc"] = {}
    for item in method_request.payload:
        assetId = item["assetId"]
        config = asset_dict.get(assetId)
        if config == None:
            print("filter_method_handler: Found no config to apply filter for %s" % assetId)
            data.update({config.assetId: { "status": 404, "data": "Found no config to apply filter for '{}'".format(assetId)}})
            result = False
        else:
            print("filter_method_handler: Applying filter to %s" % assetId)
            filter = item.get("filter")
            if filter == None:
                print("filter_method_handler: Found no config to apply filter for %s" % assetId)
                data.update({config.assetId: { "status": 400, "data": "Missing filter for '{}'".format(assetId)}})
                result = False
                    
            pubInterval = item.get("publishInterval")
            if pubInterval == None:
                pubInterval = config.publishInterval
                if pubInterval == None:
                    pubInterval = PUBLISH_INTERVAL_MS
            
            startTimer = time.process_time()
            action = filter["action"]
            if action == "reset":
                print("filter_method_handler: Reseting nodeid filter on asset %s" % config.assetId)
                await config.reset_subscription_filter()
                
                entry = { "url": config.url, "publishInterval": pubInterval, "filter": None }
                reported_properties["ptc"].update({ config.assetId: entry })
                print("filter_method_handler: Removing reported ptc filter section {}".format(entry))
                data.update({config.assetId: { "status": 200, "data": "Reseted filter on asset '{}'".format(assetId)}})
            else:
                print("filter_method_handler: Apply filter mode %s" % action)
                nodes = filter.get("nodes")
                if nodes == None or len(nodes) <= 0:
                    print("filter_method_handler: Cannot apply empty filter for %s" % assetId)
                    continue
            
                print("filter_method_handler: Filter nodes: {}".format(nodes))
                await config.apply_subscription_filter({ "action": action, "nodes": nodes})
            
                entry = { "url": config.url, "publishInterval": pubInterval, "filter": { "action": action, "nodes": nodes} }
                reported_properties["ptc"].update({ config.assetId: entry })
                print("filter_method_handler: Setting reported ptc to {}".format(entry))
                data.update({config.assetId: { "status": 200, "data": "Applied filter on asset '{}'".format(assetId)}})
    
    if len(reported_properties["ptc"]) > 0:
        print("filter_method_handler: Set the state in reported properties")
        await module_client.patch_twin_reported_properties(reported_properties)
    
    payload = {"result": result, "data": data}  # set response payload
    status = 207
    
    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("filter_method_handler: executed filter")


async def pubInterval_method_handler(method_request):
    if len(asset_dict) == 0:
        print("pubInterval_method_handler: Found no client to apply publish interval")
        payload = {"result": False, "data": "pubInterval"}
        status = 404
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await module_client.send_method_response(method_response)
        print("pubInterval_method_handler: executed pubInterval")
        return
    
    global startTimer
    result = True
    data = {}
    reported_properties = {}
    reported_properties["ptc"] = {}
    for item in method_request.payload:
        assetId = item["assetId"]
        config = asset_dict.get(assetId)
        if config == None:
            print("pubInterval_method_handler: Found no config to apply publish interval for %s" % assetId)
            data.update({config.assetId: { "status": 404, "data": "Found no config to apply publish interval for '{}'".format(assetId)}})
            result = False
        else:
            print("pubInterval_method_handler: Applying publish interval to %s" % assetId)        
            pubInterval = item.get("publishInterval")
            if pubInterval == None:
                pubInterval = config.publishInterval
                if pubInterval == None:
                    pubInterval = PUBLISH_INTERVAL_MS
            
            startTimer = time.process_time()
            print("pubInterval_method_handler: changing publishing interval for server %s to %d ms" % (assetId, pubInterval))
            await config.publish_interval_update(pubInterval)
            
            entry = { "publishInterval": pubInterval }
            reported_properties["ptc"].update({ config.assetId: entry })
            print("pubInterval_method_handler: Setting reported ptc to {}".format(entry))
            data.update({config.assetId: { "status": 200, "data": "Changed publish interval on asset '{}'".format(assetId)}})
    
    if len(reported_properties["ptc"]) > 0:
        print("pubInterval_method_handler: Set the state in reported properties")
        await module_client.patch_twin_reported_properties(reported_properties)
    
    payload = {"result": result, "data": data}  # set response payload
    status = 207
    
    # Send the response
    method_response = MethodResponse.create_from_method_request(method_request, status, payload)
    await module_client.send_method_response(method_response)
    print("pubInterval_method_handler: executed pubInterval")


class PtcConfig(object):
    def __init__(self, assetId, url, ptc_client, variable_nodes, hirarchy, ptc_config, tags) -> None:
        self.assetId = assetId
        self.secrets = None
        self.cert = None
        self.certKey = None
        self.modelId = None
        self.url = url
        self.ptc_client = ptc_client
        self.variable_nodes = variable_nodes
        self.hirarchy = hirarchy
        self.ptc = ptc_config
        self.tags = tags
        self.incoming_queue = []
        self.publishInterval = None
        self.subscription = None
        self.handles = []
        self.filtered_nodes = []
        self.registrationId = assetId
        if len(variable_nodes) > 0:
            for variable_node in variable_nodes:
                self.filtered_nodes.append(variable_node)
    
    
    async def publish_interval_update(self, publishInterval):
        if self.publishInterval != publishInterval:
            self.publishInterval = publishInterval
            await self.apply_subscription_filter({ "action": "include", "nodes": self.filtered_nodes })
            
            
    async def apply_subscription(self, run_filter):
        if run_filter:
            print("apply_subscription: filtered")
            await self.apply_subscription_filter(self.filtered_nodes)
        else:
            print("apply_subscription: all")
            # use subscription to get values
            handler = SubsriptionHandler(self)
            self.subscription = self.ptc_client.create_subscription(self.publishInterval, handler)
            for node in self.variable_nodes:
                print("apply_subscription: 1 {}".format(node))
                node = self.ptc_client.get_node(node)
                print("apply_subscription: 2 {}".format(node))
                self.handles.append(self.subscription.subscribe_data_change(node))


    async def apply_subscription_filter(self, filter):
        action = filter.get("action")
        nodes = filter.get("nodes")
        if action == None:
            print("apply_subscription_filter: Filter 'action' cannot be empty . . .")
            return
        
        if action == 'reset':
            return await self.reset_subscription_filter()
        
        if nodes != None and len(nodes) > 0:
            filteredNodes = []
            for variable_node in self.variable_nodes:
                if variable_node in nodes:
                    if  action == 'include':
                        filteredNodes.append(variable_node)
                else:
                    if action == 'exclude':
                        filteredNodes.append(variable_node)
                
            handles = []
            if len(self.handles) > 0:
                self.subscription.unsubscribe(self.handles)
            
            handler = SubsriptionHandler(self)
            self.subscription = self.ptc_client.create_subscription(self.publishInterval, handler)
            for filteredNode in filteredNodes:
                node = self.ptc_client.get_node(filteredNode)
                handles.append(self.subscription.subscribe_data_change(node))
                
            self.handles = handles
            self.filtered_nodes = filteredNodes

            
    async def reset_subscription_filter(self):
        filteredNodes = []
        for variable_node in self.variable_nodes:
            filteredNodes.append(variable_node)
                
        handles = []
        if len(self.handles) > 0:
            self.subscription.unsubscribe(self.handles)
            
        handler = SubsriptionHandler(self)
        self.subscription = self.ptc_client.create_subscription(self.publishInterval, handler)
        for filteredNode in filteredNodes:
            node = self.ptc_client.get_node(filteredNode)
            handles.append(self.subscription.subscribe_data_change(node))
        
        self.handles = handles
        self.filtered_nodes = filteredNodes


class SubsriptionHandler(object):
    def __init__(self, config):
        self.config = config
    
     
    def datachange_notification(self, node, val, data):
        # don't try and do anything with the node as network calls to the server are not allowed outside of the main thread - so we just queue it
        incomingQueue = self.config.incoming_queue
        if incomingQueue != None:
            incomingQueue.append({"registrationId": self.config.registrationId, "secrets": self.config.secrets, "cert": self.config.cert, "certKey": self.config.certKey, "modelId": self.config.modelId, "source_time_stamp": data.monitored_item.Value.SourceTimestamp.strftime("%m/%d/%Y, %H:%M:%S"), "nodeid": node, "value": val})


    def event_notification(self, event):
        print("event_notification: Python: New event", event)


def json_dump_struct(struct_value):
    value = "{"
    first = True
    for sub_var in struct_value.ua_types:
        if not first:
            value = value + ", "
        else:
            first = False
        value = value + f'"{sub_var[0]}":'
        if type(getattr(struct_value, sub_var[0])) == int or type(getattr(struct_value, sub_var[0])) == float or type(getattr(struct_value, sub_var[0])) == bool:
            value = value + str(getattr(struct_value, sub_var[0]))
        elif str(type(getattr(struct_value, sub_var[0]))) == "string":
            value = value + f'"{getattr(struct_value, sub_var[0])}"'
        elif str(type(getattr(struct_value, sub_var[0]))).startswith("<class"):
            value = value + json_dump_struct(getattr(struct_value, sub_var[0]))
    return value + "}"


async def send_to_upstream(data, customProperties):
    if module_client and module_client.connected:
        nodeid = f'"{data["nodeid"]}"'
        name = f'"{data["name"]}"'
        timestamp = f'"{data["source_time_stamp"]}"'
        valueKey = "value"

        if type(data["value"]) == int or type(data["value"]) == float or type(data["value"]) == bool:
            value = data["value"]
        elif str(type(data["value"])) == "string":
            value = f'"{data["value"]}"'
        elif str(type(data["value"])).startswith("<class"):
            value = json_dump_struct(data["value"])
            valueKey = "valueObject"

        payload = '{ "nodeid": %s, "name": %s, "source_time_stamp": %s, %s: %s}' % (nodeid, name, timestamp, valueKey, value)

        print("      %s" % (payload))
        msg = Message(payload)
        msg.content_type = "application/json"
        msg.content_encoding = "utf-8"
        for k, v in customProperties.items():
            if v != None:
                msg.custom_properties[k] = v
    
        try:
            await module_client.send_message_to_output(msg, "output1")
            print("send_to_upstream: completed sending message")
        except asyncio.TimeoutError:
            print("send_to_upstream: call to send message timed out")


async def incoming_queue_processor():
    global startTimer
    startTimer = time.process_time()
    regUpdateTimer = time.process_time()
    while True:
        try:
            if len(asset_dict) > 0:
                for key, value in asset_dict.items():
                    if value == None:
                        print("incoming_queue_processor: asset_dict value is empty . . .")
                        continue
                        
                    queue = value.incoming_queue
                    client = value.ptc_client
                    if queue == None or client == None:
                        print("incoming_queue_processor: None queue or client . . .")
                        continue
                        
                    if len(queue) > 0:
                        data = queue.pop(0)
                        data["name"] = client.get_node(data["nodeid"]).get_display_name().Text
                        registrationId = data.get("registrationId")
                        properties = {}
                        properties["registrationId"] = registrationId
                        properties["modelId"] = data.get("modelId")
                        if data.get("cert") != None:
                            properties["cert"] = data["cert"]
                        if data.get("certKey") != None:
                            properties["certKey"] = data["certKey"]

                        properties["secrets"] = data.get("secrets")
                        if registrationId == None:
                            print("===>> [{}] {} - {}".format(data["source_time_stamp"], data["name"], data["value"]))
                        else:
                            print("===>> {}: [{}] {} - {}".format(registrationId, data["source_time_stamp"], data["name"], data["value"]))
                            
                        await send_to_upstream(data, properties)
  
                if time.process_time() - regUpdateTimer > 3:
                    regUpdateTimer = time.process_time()
                    for key, value in asset_dict.items():
                        ptc_config = value.ptc
                        channel = ptc_config.get("channel")
                        device = channel.get("device")
                        usrpwd = ptc_config.get("secrets")
                        usr = usrpwd.get("usr")
                        pwd = usrpwd.get("pwd")
                        secret = HTTPBasicAuth(usr, pwd)
                        try:
                            await set_registers(ptc_config.get("plc_url"), device.get("servermain.DEVICE_ID_DECIMAL"), value.tags, secret)
                        except Exception as ex:
                            print("incoming_queue_processor: set_registers failed: {}".format(ex))
                
            if time.process_time() - startTimer > 10:
                startTimer = time.process_time()
                await ping()
                
        except Exception as e:
            print("incoming_queue_processor: Processing incoming queue failed with exception: {}".format(e))


def walk_variables(object, variable_nodes, hirarchy, indent):
    objName = object.get_display_name().Text
    print("{}- {}".format(" " * indent, objName))
    hirarchy[objName] = {}
    children = object.get_children()
    for child in children:
        name = child.get_display_name().Text
        if name.startswith("_"):
            continue
        
        childClass = child.get_node_class()
        if childClass == ua.NodeClass.Object:
            walk_variables(child, variable_nodes, hirarchy[objName], indent + 2)
        elif childClass == ua.NodeClass.Variable:
            variable_nodes.append(child.nodeid.to_string())
            if hirarchy[objName].get("tags") == None:
                hirarchy[objName]["tags"] = []
            
            hirarchy[objName]["tags"].append({ 'nodeId': child.nodeid.to_string(), 'tag': child.get_display_name().Text, "type": child.get_data_type_as_variant_type().name})
            print("{}  - {} {} {}".format(" " * indent, child.nodeid.to_string(), child.get_display_name().Text, child.get_data_type_as_variant_type().name))

   
async def ptc_client_connect(value, assetId):
    global root_node_dict
    ptc_client_url = value.get("url")
    modelId = value.get("modelId")
    pubInterval = value.get("publishInterval")
    if pubInterval == None:
        pubInterval = PUBLISH_INTERVAL_MS

    filter = value.get("filter")
    if filter != None and filter.get("action") == None:
        print("ptc_client_connect: Skipping filter since required 'filter.action' is missing")
        filter = None
                   
    ptc_config = value.get("ptc")
    ptc_api_url = ptc_config.get("url")
    channel = ptc_config.get("channel")
    channelName = "2:{}".format(channel.get("common.ALLTYPES_NAME"))
    device = channel.get("device")
    deviceName = "2:{}".format(device.get("common.ALLTYPES_NAME"))
    
    tagList = []
    try:
        # connect PTC to PLC
        secrets = ptc_config.get("secrets")
        basicAuth = HTTPBasicAuth(secrets["usr"], secrets["pwd"])
        channel_url = "{}/config/v1/project/channels".format(ptc_api_url)
        print("Setting up channel: {}/{}".format(channel_url, channel.get("common.ALLTYPES_NAME")))
        await setup_channel(channel_url, channel, tagList, basicAuth)
        print ( "ptc_client_connect: %s" % (ptc_client_url))
        ptc_client = Client(ptc_client_url)
        
        # connect to the OPC-UA server
        ptc_client.session_timeout = 600000
        ptc_client.connect()
        print("ptc_client_connect: connected to PTC asset")
    except Exception as e:
        print("ptc_client_connect: Connection to PTC asset failed with exception: {}".format(e))
        return
    
    ptc_client.load_type_definitions()
    root = ptc_client.get_root_node()

    # walk the objects and variable tree
    variable_nodes = []
    hirarchy = {}
    print("ptc_client_connect: CRUD search path: {}.{}".format(channelName, deviceName))
    channelNode = root.get_child(["0:Objects"]).get_child([channelName])
    print("  - {}".format(channelNode.get_display_name().Text))
    hirarchy[channelNode.get_display_name().Text] = {}
    dev = channelNode.get_child([deviceName])
    walk_variables(dev, variable_nodes, hirarchy[channelNode.get_display_name().Text], 4)
            
    config = PtcConfig(assetId, ptc_client_url, ptc_client, variable_nodes, hirarchy, ptc_config, tagList)
    asset_dict.update({assetId: config})
    
    config.modelId = modelId
    config.publishInterval = pubInterval
    config.registrationId = None if OPAQUE else assetId
    run_filter = False
    if filter != None:
        run_filter = True
    
    await config.apply_subscription(run_filter)


async def ping():
    try:
        print("ping: PTC assets . . .")
        twin = await module_client.get_twin()
        reported = twin["reported"]
        if 'ptc' in reported and len(reported['ptc']) > 0:
            for key, value in reported['ptc'].items():
                enabled = value.get("enabled")
                if not enabled:
                    print("ping: Skipping disabled PTC asset %s" % key)
                    continue

                config = asset_dict.get(key)
                if config == None:
                    print("ping: Not found PTC asset '%s' in cache . . ." % key)
                    # config file to load
                    filePath = value.get("config")
                    f = open(file=filePath, mode="r")
                    assetConfig = f.read()
                    print("ping: assetConfig: \n{}".format(assetConfig))
                    print("ping: Connecting to PTC asset %s" % key)
                    await ptc_client_connect(json.loads(assetConfig), key)
                else:
                    print("ping: Found active PTC asset %s" % key)
                #     try:
                #         print("ping: Sending hello message to PTC asset %s" % key)
                #         config.ptc_client.send_hello()
                #     except Exception as e:
                #         print("ping:  PTC asset '{}' failed with exception {}".format(key, e))
                #         print("ping: Trying to re-connect to PTC asset %s" % key)
                #         await ptc_client_connect(value.get("ptc"), key)
    except Exception as ex:
        print("ping: failed with exception {}".format(ex))
        pass
        
    print("ping: PTC assets completed . . .")


async def main():
    try:
        if not sys.version >= "3.5.3":
            raise Exception( "The sample requires python 3.5.3+. Current version of Python: %s" % sys.version )
        print ( "IotEdge module Client for Processing PTC messages" )

        # The client object is used to interact with your Azure IoT hub.
        global module_client
        global startTimer
        global PUBLISH_INTERVAL_MS
        global OPAQUE
        
        module_client = IoTHubModuleClient.create_from_edge_environment()

        # connect the client.
        await module_client.connect()
        
        if os.getenv("opaque", "false") == "true":
            OPAQUE = True
            
        print("Opaque: {}".format(OPAQUE))
        
        twin = await module_client.get_twin()
        desired = twin["desired"]
        print("Twin properties desired:")
        print("{}".format(desired))
        if 'publishInterval' in desired and desired['publishInterval'] > 10:
            PUBLISH_INTERVAL_MS = desired['publishInterval']
                
        # set the message handler on the module
        module_client.on_message_received = message_handler
        
        # set the twin patch handler on the module
        module_client.on_twin_desired_properties_patch_received = twin_patch_handler
        
        # Set the method request handler on the module
        module_client.on_method_request_received = method_request_handler
       
        tasks = []
        tasks.append(asyncio.create_task(incoming_queue_processor()))
        await asyncio.gather(*tasks)

        print ( "Disconnecting . . .")

        # Finally, disconnect
        await module_client.disconnect()

    except Exception as e:
        print ( "Unexpected error {}".format(e))
        raise
        
if __name__ == "__main__":
    asyncio.run(main())
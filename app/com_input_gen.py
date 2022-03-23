import base64
import uuid
import json
import asyncio

async def main():
    print("started . . .")
    
    input = "ptc01.json"
    output = "output.json"
    assetId = "ptc01"
    
    fin = open(file=input, mode="rb")
    data = fin.read()
    fin.close()

    id = uuid.uuid4()
    payload = {}
    payload["data"] = base64.b64encode(data).decode("ASCII")
    payload["multipart-message"] = "yes"    # indicates this is a multi-part message that needs special processing
    payload["id"] = str(id)                 # unique identity for the multi-part message we suggest using a UUID
    payload["assetId"] = assetId            # file path for the final file, the path will be appended to the base recievers path
    payload["part"] = str(1)                # part N to track ordring of the parts
    payload["maxPart"] = str(1)             # maximum number of parts in the set
    
    fout = open(file=output, mode="w")
    fout.write(json.dumps(payload))
    fout.close()
    
    print("completed . . .")


# start the main routine
if __name__ == "__main__":
    asyncio.run(main())
import aiohttp
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
import blockchain
import asyncio
from fastapi.websockets import WebSocketDisconnect, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class BlockType(BaseModel):
    index: int
    timestamp: str
    data: str
    proof: str
    previous_hash: str


blockchain = blockchain.Blockchain()  # type: ignore

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')

# Create a set to store connected websockets
connected_websockets = set()
blocked_hashes = set()

# create a list of nodes
blockchain_nodes = ["http://localhost:8001", "http://localhost:8002"]

# endpoint to mine a block and add file to blockchain


@app.post("/mine_block/")
async def mine_block(file: UploadFile = File(...)):
    # Read the contents of the uploaded file
    file_content = await file.read()

    # Save the file to a temporary location
    temp_file_path = f"temp/{file.filename}"
    os.makedirs("temp", exist_ok=True)
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(file_content)

    file_hash = blockchain.calculate_file_hash(temp_file_path)
    if file_hash in blocked_hashes:
        return {"status": "Ransomware"}
    # send file to the ransomware detection endpoint
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field("file", open(temp_file_path, "rb"))
        # form_data.add_field("is_ransomware", "true")
        # Calculate the hash of the file
        async with session.post("http://localhost:5000/upload-json", data=form_data) as response:
            print(response)
            if response.status != 200:
                raise HTTPException(status_code=500, detail="Error in ransomware detection")
            is_ransomware = (await response.json()).get('is_ransomware')
            # print("is_ransomware:", is_ransomware)
            if is_ransomware == "yes":
                blocked_hashes.add(file_hash)
                # Notify other nodes about the file hash
                for node in blockchain_nodes:
                    print(f"Notifying node {node}")
                    try:
                        async with session.post(f"{node}/notify_file_hash/{file_hash}") as notify_response:
                            if notify_response.status != 200:
                                raise HTTPException(status_code=500, detail="Error notifying nodes about file hash")
                    except aiohttp.ClientConnectorError:
                        print(f"node {node} is not running")
                        pass
                # return the file hash and it's status
                return {"file_hash": file_hash, "status": "Ransomware"}
            else:
                block = blockchain.mine_block(file_hash)
                for node in blockchain_nodes:
                    print(f"Notifying node {node}")
                    try:
                        async with session.post(f"{node}/update_chain", json=block) as update_resp:
                            if update_resp.status != 200:
                                raise HTTPException(status_code=500, detail="Error updating nodes chain")
                    except aiohttp.ClientConnectorError:
                        print(f"node {node} is not running")
                        pass
                print(block)
                return {"status": "Not ransomware", "block": block}



@app.post("/update_chain/")
async def update_chain(block: BlockType):
    print(block)
    blockchain.add_block(block)
    return {"message": "Chain updated"}


@app.get("/blockchain/")
async def get_blockchain():
    chain = blockchain.get_chain()
    return chain

# endpoint to see if the chain is valid


@app.get("/validate/")
async def is_blockchain_valid():
    is_valid = blockchain.is_chain_valid()
    return is_valid


@app.post("/notify_file_hash/{file_hash}")
async def notify_file_hash(file_hash):
    # todo: reach body
    # send the message to connected clients via websockets
    message = {"file_hash": file_hash}
    blocked_hashes.add(file_hash)
    print(f"Sending file_has {file_hash} to connected clients")
    await asyncio.gather(*[websocket.send_json(message) for websocket in connected_websockets])
    return {"message": "File hash received"}


@app.get("/")
async def index(request: Request):
    # render ws.html template
    blocked_hashes_text = "\n".join(blocked_hashes) + "\n"
    return templates.TemplateResponse("ws.html", {"request": request, "blocked_hashes": blocked_hashes_text})

# WebSocket endpoint


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected", websocket)
    connected_websockets.add(websocket)
    try:
        while True:
            # Wait for messages from the client
            message = await websocket.receive_text()
    except WebSocketDisconnect:
        print("Client disconnected", websocket)
        # Remove the websocket from the set of connected websockets
        connected_websockets.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    # uvicorn main:app --port 8000 --reload
    uvicorn.run(app, host="localhost", port=8000)

from flask import Flask, request, jsonify
import threading
import json
import time
import requests



app = Flask(__name__)
lock = threading.Lock()
request_queue = []

def send_request_to_container(container_id, container_info, incoming_request_data):
    """
    Sends a request to a container on a worker instance.

    Args:
        container_id (str): The identifier of the container (e.g., "container1").
        container_info (dict): Information about the container, including its IP and port.
        incoming_request_data (dict): The data to be sent to the container.
    """
    container_ip = container_info['ip']
    container_port = container_info['port']

    # Construct the URL to the container's endpoint (assuming '/run_model' is the endpoint for processing requests)
    container_url = f"http://{container_ip}:{container_port}/run_model"

    try:
        print(f"Sending request to {container_id} at {container_url} with data: {incoming_request_data}...")
        
        # Send the POST request to the container's API
        response = requests.post(container_url, json=incoming_request_data)

        # Check if the request was successful
        if response.status_code == 200:
            print(f"Request successfully processed by {container_id}. Response: {response.json()}")
        else:
            print(f"Error: Container {container_id} responded with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send request to {container_id} at {container_url}: {e}")

def update_container_status(container_id, status):
    with lock:
        with open("status.json", "r") as f:
            data = json.load(f)
        data[container_id]["status"] = status
        with open("status.json", "w") as f:
            json.dump(data, f)

def process_request(incoming_request_data):
    with lock:
        with open("status.json", "r") as f:
            data = json.load(f)
        free_container = None
        for container_id, container_info in data.items():
            if container_info["status"] == "free":
                free_container = container_id
                break

    if free_container:
        update_container_status(free_container, "busy")
        send_request_to_container(free_container, data[free_container], incoming_request_data)
        update_container_status(free_container, "free")
    else:
        request_queue.append(incoming_request_data)

@app.route("/new_request", methods=["POST"])
def new_request():
    incoming_request_data = request.json
    threading.Thread(target=process_request, args=(incoming_request_data,)).start()
    return jsonify({"message": "Request received and processing started."})

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=80)

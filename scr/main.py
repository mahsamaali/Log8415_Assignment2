#aws library
import boto3
#import vpc,subnet_id,create_security_group
from netwrok_connection import get_vpc,get_subnet_by_vpc_and_az,create_security_group
#keypair and creat isntaces
from create_instances import create_key_pair,create_instances,create_ebs_volumes,attach_volume_to_instance

#buid docker image
from dockers import build_images
#deployement FAST API
from deploy_flaskApp import setup_ml_app,set_up_orchestrator

import  os
import json
import time

from send_request import test_orchestrator

#terminate ressources
from terminate_resources import delete_all_load_balancers,delete_all_target_groups,terminate_all_instances,delete_all_volumes


# Creating an EC2 client
ec2 = boto3.client('ec2',region_name='us-east-1')


#buid docker images
dockerfiles = {
        "container1": "Dockerfile_1",
    }
try:
        # Check if container1.tar.gz exists
    if not os.path.exists('./container1.tar.gz'):
        raise FileNotFoundError("container1.tar.gz not found")

    print("container1.tar.gz is present locally.")

except FileNotFoundError as e:
        # If any tar file is missing, build the images
        print(e)
        print("Building Docker images since they are not found locally...")
        build_images(dockerfiles)

#1. get VPC
vpc_id=get_vpc(ec2=ec2)


#2. get subnet_id
availability_zone = 'us-east-1e'
subnet_ids_data=get_subnet_by_vpc_and_az(ec2=ec2,vpc_id= vpc_id, availability_zone=availability_zone)
print(subnet_ids_data[0]['SubnetId'])

subnet_id_1=subnet_ids_data[0]['SubnetId']
#3. create security_group
securiy_group_id=create_security_group(ec2=ec2,vpc_id=vpc_id)

#4. create keypair
#name of keypair
key_name = 'my-key-pair'
#path of keypair
key_file = f"./{key_name}.pem"
create_key_pair(ec2=ec2,key_name=key_name,key_file=key_file)

#5. create instance:

#ubuntu ami
ami_id = 'ami-0e86e20dae9224db8'


#CPU type
instance_type_large='t2.large'
#number of instances
nb_instances_large=5


###############################Worker Part###############################################
# Step 1: Create an EBS Volume
volume_ids = create_ebs_volumes(ec2=ec2, availability_zone=availability_zone, volume_size=10,num_volumes=nb_instances_large)

# Step2: Create instances 

all_instances_data =create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=securiy_group_id,
                                    instance_type=instance_type_large, 
                                    num_instances=nb_instances_large,
                                    availability_zone=availability_zone)



for (instance_id, public_ip), volume_id in zip(all_instances_data, volume_ids):
    # Step 3: Attach the EBS volume to the first instance 
    attach_volume_to_instance(ec2=ec2, instance_id=instance_id, volume_id=volume_id,device_name='/dev/sdf')
     
# Assign the first instance as orchestrator
orchestrator_instance_data = all_instances_data[0]
orchestrator_ip = orchestrator_instance_data[1]
#Assign for workers
workers_ips=[]
worker_instances_data = all_instances_data[1:]
all_containers_status = {}  # Dictionary to hold the status of all containers across all workers
container_count=1

for (instance_id, public_ip), volume_id in zip(worker_instances_data, volume_ids):

    workers_ips.append(public_ip)
    #Step 4: Install docker; Transfer Docker Image; run containers 
    worker_containers_info = setup_ml_app(
            ip_address=public_ip,
            username='ubuntu',
            private_key_path=key_file,
            container_start_port=8000,
        )
    # Add each container's info to the global dictionary with unique container names (container1, container2, etc.)
    for container_name, container_info in worker_containers_info.items():
        all_containers_status[f"container{container_count}"] = container_info
        container_count += 1

    # Print the container information for debugging purposes
    print(json.dumps(worker_containers_info, indent=4))

# Step5: Save all container status information to a JSON file (e.g., status.json)
with open('status.json', 'w') as status_file:
    json.dump(all_containers_status, status_file, indent=4)


###############################End Of WorkerPart###############################################
#1. Build image of orchestrator with JSON file
dockerfiles = {
        "orchestrator": "Dockerfile_2",
    }
build_images(dockerfiles)


#2.Set up  orchestrator and Install  docker and transfer image and run container
set_up_orchestrator(ip_address=orchestrator_ip, username='ubuntu', private_key_path=key_file)


#test logic
test_orchestrator(orchestrator_ip=orchestrator_ip, num_requests=1000, max_workers=1000)

#15. Terminate ressources
terminate_all_instances()
time.sleep(260)
delete_all_volumes()

print("All  EC2 instances have been deleted.")
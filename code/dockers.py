import subprocess
import os

def build_images(dockerfiles):
    """
    Dynamically builds Docker images and saves them as compressed tar.gz files.

    Args:
        dockerfiles (dict): A dictionary where the key is the image name and the value is the Dockerfile path.
                            For example: {"container1": "Dockerfile_1", "container2": "Dockerfile_2"}
    """
    for image_name, dockerfile_path in dockerfiles.items():
        # Build the Docker image dynamically using the Dockerfile
        print(f"Building Docker image {image_name} using {dockerfile_path}...")
        build_command = ["docker", "build", "-f", dockerfile_path, "-t", image_name, "."]
        result = subprocess.run(build_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print(f"Error building Docker image {image_name}: {result.stderr.decode('utf-8')}")
            continue
        
        print(f"Successfully built Docker image {image_name}")

        # Save the Docker image directly as a compressed tar.gz file
        tar_gz_file = f"{image_name}.tar.gz"
        print(f"Saving Docker image {image_name} as compressed {tar_gz_file}...")

        try:
            # Save the Docker image and compress it
            with open(tar_gz_file, "wb") as f_out:
                save_command = ["docker", "save", image_name]
                gzip_command = ["gzip"]
                save_process = subprocess.Popen(save_command, stdout=subprocess.PIPE)
                gzip_process = subprocess.Popen(gzip_command, stdin=save_process.stdout, stdout=f_out)
                save_process.stdout.close()  # Allow save_process to receive a SIGPIPE if gzip_process exits
                gzip_process.communicate()   # Wait for gzip to finish

                if gzip_process.returncode == 0:
                    print(f"Compressed Docker image saved as {tar_gz_file}")
                else:
                    print(f"Error saving compressed Docker image {image_name}")
        except Exception as e:
            print(f"Failed to save compressed Docker image {image_name}: {e}")



# #buid docker images
# dockerfiles = {
#         "orchestrator": "Dockerfile_2",
#     }
# try:
#         # Check if container1.tar.gz exists
#     if not os.path.exists('./container2.tar.gz'):
#         raise FileNotFoundError("container1.tar.gz not found")

#     print("container1.tar.gz is present locally.")

# except FileNotFoundError as e:
#         # If any tar file is missing, build the images
#         print(e)
#         print("Building Docker images since they are not found locally...")
#         build_images(dockerfiles)


import json
from typing import Optional
import tyro
import dataclasses
import base64
import copy
import tempfile
import os
import logging
import requests


import uuid
import boto3


@dataclasses.dataclass(kw_only=True)
class AwsSpotInstanceRequest:
    """Request to launch an AWS spot instance."""

    launch_template: str
    """Path to the launch template JSON file."""

    user_data: str
    """Path to the user data shell script file."""

    instance_name: str
    """What to name the instance that is launched."""

    fleet_type: str = "request"
    """Options are "request" or "maintain"."""

    instance_types: list[str] = dataclasses.field(
        default_factory=lambda: ["p5.48xlarge", "p5en.48xlarge"]
    )

    ami_id: str = "ami-06b5b6fef1daf63ed"

    key_name: str = "Eltayeb-AWS"

    shutdown_on_finish: bool = True
    """Shutdown the instance when the job is finished."""
    terminate_fleet_on_finish_controller: Optional[str] = "http://52.23.181.222:7451"
    """IP/dns address of controller. If supplied request the controller to 
    terminate the fleet when the job is finished."""

    def __post_init__(self):
        if not self.launch_template.endswith(".json"):
            raise ValueError("Launch template path must be a JSON file.")
        if not self.user_data.endswith(".sh"):
            raise ValueError("User data path must be a shell script file.")
        assert (
            len(self.instance_types) > 0
        ), "At least one instance type must be specified."

        assert self.fleet_type in [
            "request",
            "maintain",
        ], "Fleet type must be either 'request' or 'maintain'."

        if self.terminate_fleet_on_finish_controller and self.fleet_type == "request":
            logging.warning(
                "Fleet type is 'request' but terminate_fleet_on_finish_controller is set. "
                "This does not make sense and fleet will terminate on shutdown anyway."
            )

        if not self.shutdown_on_finish:
            logging.warning(
                "Shutdown on finish is set to False. This means the instance will not shut down "
                "after the job is finished. Make sure to terminate the fleet manually."
            )


def preprocess_user_data(
    user_data: str,
    terminate_fleet_on_finish_controller: Optional[str],
    shutdown_on_finish: bool,
    job_uuid: str,
) -> str:
    """Preprocess the user data script to add termination commands.

    Args:
        user_data (str): The original user data script.
        terminate_fleet_on_finish_controller (str): The URL of the termination controller. If provided,
            a command to request fleet termination will be added to the end script.
        shutdown_on_finish (bool): If True, a command to shut down the instance will be added to
            the end of the script.

    Assumes user data is a bash script."""
    if terminate_fleet_on_finish_controller:
        terminate_command = (
            f"wget {terminate_fleet_on_finish_controller}/terminate_fleet/{job_uuid}"
        )
        user_data = "\n".join(
            [
                user_data,
                f"echo 'Requesting fleet termination on finish to {terminate_fleet_on_finish_controller}'",
                terminate_command,
            ]
        )

    if shutdown_on_finish:
        shutdown_command = "shutdown now"
        user_data = "\n".join(
            [
                user_data,
                f"echo 'Shutting down instance on finish'",
                shutdown_command,
            ]
        )

    return user_data


def check_termination_controller_status(
    terminate_fleet_on_finish_controller: Optional[str] = None,
) -> bool:
    """Check the status of the termination controller."""
    if terminate_fleet_on_finish_controller is None:
        logging.info("Termination controller URL is not provided.")
        return True

    logging.info(
        f"Checking termination controller status at {terminate_fleet_on_finish_controller}"
    )
    try:
        response = requests.get(terminate_fleet_on_finish_controller + "/status")
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error checking termination controller status: {e}")
        return False


if __name__ == "__main__":
    args = tyro.cli(AwsSpotInstanceRequest)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


    with open(args.user_data, "r") as f:
        user_data = f.read()

    with open(args.launch_template, "r") as f:
        launch_template = json.load(f)

    job_uuid = str(uuid.uuid4())

    if check_termination_controller_status(
        args.terminate_fleet_on_finish_controller
    ):
        logging.info(
            f"Termination controller at {args.terminate_fleet_on_finish_controller} is reachable."
        )
    else:
        logging.error(
            f"Termination controller at {args.terminate_fleet_on_finish_controller} is not reachable. "
            "Exiting without launching the fleet."
        )
        exit(1)

    user_data = preprocess_user_data(
        user_data,
        args.terminate_fleet_on_finish_controller,
        args.shutdown_on_finish,
        job_uuid=job_uuid,
    )
    user_data_b64 = base64.b64encode(user_data.encode("utf-8"))

    # Remove padding from base64 string
    while user_data_b64.endswith(b"="):
        user_data_b64 = user_data_b64[:-1]

    launch_template["LaunchSpecifications"][0]["UserData"] = user_data_b64.decode(
        "utf-8"
    )
    launch_template["LaunchSpecifications"][0]["InstanceType"] = args.instance_types[0]
    launch_template["LaunchSpecifications"][0]["ImageId"] = args.ami_id
    launch_template["LaunchSpecifications"][0]["KeyName"] = args.key_name

    launch_template["LaunchSpecifications"][0]["TagSpecifications"][0]["Tags"].append(
        {"Key": "Name", "Value": args.instance_name}
    )

    launch_template["TagSpecifications"][0]["Tags"].append(
        {"Key": "Name", "Value": args.instance_name}
    )

    for instance_type in args.instance_types[1:]:
        new_launch_spec = copy.deepcopy(launch_template["LaunchSpecifications"][0])
        new_launch_spec["InstanceType"] = instance_type
        launch_template["LaunchSpecifications"].append(new_launch_spec)

    launch_template["Type"] = args.fleet_type

    tmpdir = tempfile.mkdtemp()
    final_launch_template_path = os.path.join(tmpdir, "launch_template.json")
    with open(os.path.join(tmpdir, "launch_template.json"), "w") as f:
        json.dump(launch_template, f, indent=4)
    print(f"Final launch template: {final_launch_template_path}")

    ec2_client = boto3.client("ec2")

    response = ec2_client.request_spot_fleet(SpotFleetRequestConfig=launch_template)
    print("Spot fleet request submitted successfully.")
    fleet_id = response["SpotFleetRequestId"]
    print(f"Spot fleet request ID: {fleet_id}")

    if args.terminate_fleet_on_finish_controller:
        print(
            f"Terminate fleet on finish controller: {args.terminate_fleet_on_finish_controller}"
        )
        addresss = f"{args.terminate_fleet_on_finish_controller}/register_job/{job_uuid}/{fleet_id}"
        # Ensure 'requests' is imported at the top of the file: import requests
        try:
            print(f"Sending GET request to: {addresss}")
            response = requests.get(addresss)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            print(f"Controller response status: {response.status_code}")
            print(f"Controller response body: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending request to controller: {e}")

        print(f"Job UUID: {job_uuid}")
        print(f"Register job address: {addresss}")

import json
import tyro
import dataclasses
import base64
import copy
import tempfile
import os
import subprocess

@dataclasses.dataclass(kw_only=True)
class AwsSpotInstanceRequest:
    """Request to launch an AWS spot instance."""

    launch_template_path: str
    user_data_path: str

    instance_types: list[str] = dataclasses.field(
        default_factory=lambda: ["p5.48xlarge", "p5en.48xlarge"]
    )

    ami_id: str = "ami-06b5b6fef1daf63ed"

    key_name: str = "Eltayeb-AWS"

    def __post_init__(self):
        if not self.launch_template_path.endswith(".json"):
            raise ValueError("Launch template path must be a JSON file.")
        if not self.user_data_path.endswith(".sh"):
            raise ValueError("User data path must be a shell script file.")
        assert len(self.instance_types) > 0, "At least one instance type must be specified."

if __name__ == "__main__":
    args = tyro.cli(AwsSpotInstanceRequest)

    with open(args.user_data_path, "r") as f:
        user_data = f.read()

    with open(args.launch_template_path, "r") as f:
        launch_template = json.load(f)
    user_data_b64 = base64.b64encode(user_data.encode("utf-8"))
    
    # Remove padding from base64 string
    while user_data_b64.endswith(b"="):
        user_data_b64 = user_data_b64[:-1]


    launch_template["LaunchSpecifications"][0]["UserData"] = user_data_b64.decode("utf-8")
    launch_template["LaunchSpecifications"][0]["InstanceType"] = args.instance_types[0]
    launch_template["LaunchSpecifications"][0]["ImageId"] = args.ami_id
    launch_template["LaunchSpecifications"][0]["KeyName"] = args.key_name

    for instance_type in args.instance_types[1:]:
        new_launch_spec = copy.deepcopy(launch_template["LaunchSpecifications"][0])
        new_launch_spec["InstanceType"] = instance_type
        launch_template["LaunchSpecifications"].append(new_launch_spec)
    
    tmpdir = tempfile.mkdtemp()
    final_launch_template_path = os.path.join(tmpdir, "launch_template.json")
    with open(os.path.join(tmpdir, "launch_template.json"), "w") as f:
        json.dump(launch_template, f, indent=4)
    print(f"Final launch template: {final_launch_template_path}")

    subprocess.run(
        [
            "aws",
            "ec2",
            "request-spot-fleet",
            f"--spot-fleet-request-config=file://{final_launch_template_path}",
        ],
        check=True,
        stdout=None, # Inherit stdout from parent (print to console)
        stderr=None, # Inherit stderr from parent (print to console)
    )
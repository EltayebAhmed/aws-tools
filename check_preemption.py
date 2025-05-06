import boto3
import pprint
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone

def check_fleet_preemption(spot_fleet_request_id: str) -> Dict[str, List[Dict]]:
    """
    Check if instances in a Spot Fleet have been terminated by Amazon (preempted).
    
    Args:
        spot_fleet_request_id: The ID of the Spot Fleet request (e.g., 'sfr-12345678-1234-5678-1234-567890abcdef')
        
    Returns:
        A dictionary with lists of preempted and non-preempted instances with their details
    """
    ec2_client = boto3.client('ec2')
    
    # Initialize results dictionary
    results = {
        "preempted_instances": [],
        "non_preempted_instances": [],
        "active_instances": []
    }
    
    try:
        # Get spot instance requests associated with this fleet
        response = ec2_client.describe_spot_fleet_request_history(
            SpotFleetRequestId=spot_fleet_request_id,
            StartTime=datetime(2020, 1, 1, tzinfo=timezone.utc), # Example: fixed start date
        )
        
        # Preemption status codes that indicate Amazon terminated the instance
        preemption_codes = [
            'instance-terminated-by-price',
            'instance-terminated-capacity-not-available',
            'instance-terminated-capacity-oversubscribed',
            'instance-terminated-by-service'
        ]
        # print(response)
        # pprint.pprint([(i, x.get('EventSubType'), x['EventType']) for i, x  in enumerate(response['HistoryRecords'])])
        instance_chages = [x for x in response['HistoryRecords'] if x['EventType'] in ['instanceChange']]#, 'spotInstanceRequestChange']]
        instance_ids = [x['EventInformation']['InstanceId'] for x in instance_chages]
        print(instance_ids)
        
        # Print events associated with each instance
        for i, instance_id in enumerate(instance_ids):
            specific_response = ec2_client.describe_instance_status(
            InstanceIds=[instance_id],
            )

            print(specific_response)

        # print(instance_chages)
        # Process each spot instance request
        for request in response.get('SpotInstanceRequests', []):
            instance_id = request.get('InstanceId')
            status_code = request.get('Status', {}).get('Code')
            status_message = request.get('Status', {}).get('Message', '')
            
            instance_info = {
                'instance_id': instance_id,
                'status_code': status_code,
                'status_message': status_message,
                'request_id': request.get('SpotInstanceRequestId')
            }

            print(instance_info)
            
            # Check if instance is terminated and why
            if status_code in preemption_codes:
                results["preempted_instances"].append(instance_info)
            elif status_code == 'instance-terminated-by-user' or status_code == 'request-canceled-and-instance-terminated':
                # User-initiated termination is not considered preemption
                results["non_preempted_instances"].append(instance_info)
            elif status_code == 'fulfilled' and instance_id:
                # Check if the instance is still running
                results["active_instances"].append(instance_info)
        # Get additional fleet history for more context
        # Use a reasonable start time, e.g., 30 days ago, or adjust as needed
        start_time = datetime(2020, 1, 1, tzinfo=timezone.utc) # Example: fixed start date
        # Or dynamically calculate, e.g., 30 days ago:
        # from datetime import timedelta
        # start_time = datetime.now(timezone.utc) - timedelta(days=30)

        history_response = ec2_client.describe_spot_fleet_request_history(
            SpotFleetRequestId=spot_fleet_request_id,
            StartTime=start_time
        )

        # Add fleet history events to the result for reference
        # Add fleet history events to the result for reference
        results["fleet_history"] = history_response.get('HistoryRecords', [])
        
        return results
        
    except Exception as e:
        logging.error(f"Error checking fleet preemption: {e}")
        raise

# Example usage
if __name__ == "__main__":
    # Replace with your actual Spot Fleet Request ID
    # fleet_id = "sfr-bf9342d7-eba4-4f99-b8c2-9606db34d855"
    # fleet_id = "sfr-6ef8768e-eee6-4b23-81fa-da5b2e583ce7"
    # fleet_id = "sfr-6ef8768e-eee6-4b23-81fa-da5b2e583ce7"
    # fleet_id = "sfr-73d62f92-c829-4574-88ea-942f99f97d3b"
    # fleet_id = "sfr-18305655-bc55-4d35-8305-2923d2c47004"
    # fleet_id = "sfr-220a2c8f-4847-471e-9140-0bac886f3dc8"


    # fleet_id = "sfr-918882c9-0e46-402e-bd5e-78f4e74fd0b5"
    fleet_ids = [
        "sfr-fc41a748-97e3-4521-890a-75497ded3a97",
"sfr-be0c8cda-df44-465d-a79f-625f84824ded",
"sfr-918882c9-0e46-402e-bd5e-78f4e74fd0b5",
"sfr-1f6b1cfa-19d6-4761-b06e-d16ce92e1863",
"sfr-e94cdd1b-a172-4d2b-8204-0598fe827e88",
"sfr-42a0eb08-2fba-4b74-a170-dfcf65800db0",
"sfr-cf9b3b1c-4761-41fa-8128-dd3864e72471",
"sfr-897b7808-a073-4836-9615-c99bc4b6a89a",
"sfr-09c73d7e-4cb6-4e3d-8dde-6e6d713c4fbe",
"sfr-5d7702c4-9ce5-4ad4-bc6f-539d0c9cead8",
"sfr-a9988cf8-9556-4d71-958a-7229587a6e89",
"sfr-18ca76f3-9d2b-4da2-942d-2b459a6d26ea",
"sfr-3c3e590b-2ac3-4ae8-928c-c211bdb2f057",
"sfr-afa4d685-c260-4d89-bfc3-6be4faef1b84",
"sfr-fd4818eb-6f40-498d-90a8-906a67e0f0b1",
"sfr-8a6fe189-57de-49e2-861d-39fb94e5f2c7",
"sfr-733c88d0-cef7-4533-afdd-8a3fd01e2cfd",
"sfr-bf9342d7-eba4-4f99-b8c2-9606db34d855",
"sfr-6ef8768e-eee6-4b23-81fa-da5b2e583ce7",
"sfr-38083a75-4a3e-4a35-97b0-431ed2c80e67",
"sfr-862c43f4-b388-4495-b5aa-5211f90d4575",
"sfr-f97e3bd4-335b-4dbe-abd2-eb07e6bc3735",
"sfr-73d62f92-c829-4574-88ea-942f99f97d3b",
"sfr-8b3093bd-21e3-4186-bc5b-2f74bc8a980a",
"sfr-1ad04d81-70b5-4748-958b-fdbbb8e7ed48",
"sfr-18305655-bc55-4d35-8305-2923d2c47004",
"sfr-2471c50b-23df-453c-b1ea-246338c95a5f",
"sfr-bf721a6f-1ce7-4269-b256-70ec5c25edda",
"sfr-220a2c8f-4847-471e-9140-0bac886f3dc8",
"sfr-b1b0965c-2089-4aef-afa2-68796e8fb81d",
    ]
    for fleet_id in fleet_ids:
        try:
            result = check_fleet_preemption(fleet_id)
            
            # Print summary
            # print(f"Fleet ID: {fleet_id}")
            # print(f"Preempted instances: {len(result['preempted_instances'])}")
            # for instance in result['preempted_instances']:
            #     print(f"  - {instance['instance_id']}: {instance['status_message']}")
                
            # print(f"\nNon-preempted terminated instances: {len(result['non_preempted_instances'])}")
            # print(f"Active instances: {len(result['active_instances'])}")
            
        except Exception as e:
            print(f"Error: {e}")
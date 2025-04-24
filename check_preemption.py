import boto3
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
        response = ec2_client.describe_spot_instance_requests(
            Filters=[
                {
                    'Name': 'spot-fleet-request-id',
                    'Values': [spot_fleet_request_id]
                }
            ]
        )
        
        # Preemption status codes that indicate Amazon terminated the instance
        preemption_codes = [
            'instance-terminated-by-price',
            'instance-terminated-capacity-not-available',
            'instance-terminated-capacity-oversubscribed',
            'instance-terminated-by-service'
        ]
        
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
    fleet_id = "sfr-220a2c8f-4847-471e-9140-0bac886f3dc8"
    try:
        result = check_fleet_preemption(fleet_id)
        
        # Print summary
        print(f"Fleet ID: {fleet_id}")
        print(f"Preempted instances: {len(result['preempted_instances'])}")
        for instance in result['preempted_instances']:
            print(f"  - {instance['instance_id']}: {instance['status_message']}")
            
        print(f"\nNon-preempted terminated instances: {len(result['non_preempted_instances'])}")
        print(f"Active instances: {len(result['active_instances'])}")
        
    except Exception as e:
        print(f"Error: {e}")
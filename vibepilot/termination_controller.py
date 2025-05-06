import datetime
import logging
import os
import sqlite3

import boto3
from flask import Flask, abort, jsonify

# initialize Flask app
app = Flask(__name__)

# Configure logging
now = datetime.datetime.now()
timestamp = now.strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(
    os.path.dirname(__file__), f"termination_controller_{timestamp}.log"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),  # Also log to console
    ],
)

# set up SQLite DB in same folder
DB_PATH = os.path.join(os.path.dirname(__file__), "termination_controller.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    """
CREATE TABLE IF NOT EXISTS jobs (
    uuid TEXT PRIMARY KEY,
    fleet_id TEXT NOT NULL
)
"""
)
conn.commit()


def terminate_spot_fleet(fleet_id: str):
    """Stub: terminate a spot fleet by ID."""
    logging.info(f"Attempting to terminate spot fleet: {fleet_id}")
    # TODO: Add proper error handling for boto3 calls
    ec2 = boto3.client("ec2", region_name="us-east-1")
    try:
        response = ec2.cancel_spot_fleet_requests(
            SpotFleetRequestIds=[fleet_id], TerminateInstances=True
        )
        logging.info(
            f"Successfully cancelled spot fleet request {fleet_id}. Response: {response}"
        )
    except Exception as e:
        logging.error(f"Failed to terminate spot fleet {fleet_id}: {e}")
        # Re-raise the exception to be caught by the caller route
        raise e


@app.route("/register_job/<job_uuid>/<fleet_id>")
def register_job(job_uuid, fleet_id):
    """Register a new job UUID and its fleet ID."""
    logging.info(
        f"Received registration request for job {job_uuid} with fleet {fleet_id}"
    )
    try:
        conn.execute(
            "INSERT OR REPLACE INTO jobs (uuid, fleet_id) VALUES (?, ?)",
            (job_uuid, fleet_id),
        )
        conn.commit()
        logging.info(f"Successfully registered job {job_uuid} with fleet {fleet_id}")
    except Exception as e:
        logging.error(f"Error registering job {job_uuid}: {e}")
        abort(500, str(e))
    return jsonify({"status": "registered", "uuid": job_uuid, "fleet_id": fleet_id})


@app.route("/terminate_fleet/<job_uuid>")
def terminate_fleet(job_uuid):
    """Lookup fleet_id by job_uuid and terminate the fleet."""
    logging.info(f"Received termination request for job {job_uuid}")
    cur = conn.execute("SELECT fleet_id FROM jobs WHERE uuid = ?", (job_uuid,))
    row = cur.fetchone()
    if not row:
        logging.warning(f"No job found for UUID {job_uuid} during termination request.")
        abort(404, f"No job found for UUID {job_uuid}")
    fleet_id = row[0]
    logging.info(f"Found fleet ID {fleet_id} for job {job_uuid}")
    try:
        terminate_spot_fleet(fleet_id)
        logging.info(
            f"Successfully initiated termination for fleet {fleet_id} (job {job_uuid})"
        )
    except NotImplementedError:
        logging.error(
            f"Termination function not implemented for fleet {fleet_id} (job {job_uuid})"
        )
        abort(501, "terminate_spot_fleet not implemented")
    except Exception as e:
        logging.error(f"Error terminating fleet {fleet_id} (job {job_uuid}): {e}")
        abort(500, str(e))
    return jsonify({"status": "terminated", "uuid": job_uuid, "fleet_id": fleet_id})


@app.route("/status")
def status():
    """Health check endpoint."""
    logging.info("Health check requested.")
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    logging.info("Starting termination controller server...")
    # listen on port 7451 for controller endpoints
    app.run(host="0.0.0.0", port=7451)

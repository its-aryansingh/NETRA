"""
NETRA Demo Reset Script.
Terminates demo instances tagged netra:managed=true and cleans up demonstration state.
"""

import argparse
import logging
import os
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("netra.reset")

REGION = os.getenv("AWS_REGION", "ap-south-1")


def reset_real_aws(session: boto3.Session) -> None:
    """Finds all running instances tagged netra:managed=true and terminates them."""
    ec2 = session.client("ec2", region_name=REGION)
    logger.info("Discovering managed demo instances in %s...", REGION)

    try:
        resp = ec2.describe_instances(
            Filters=[
                {"Name": "tag:netra:managed", "Values": ["true"]},
                {"Name": "instance-state-name", "Values": ["running", "pending", "stopped"]},
            ]
        )

        instance_ids = []
        for resv in resp.get("Reservations", []):
            for inst in resv.get("Instances", []):
                instance_ids.append(inst["InstanceId"])

        if not instance_ids:
            logger.info("No active demo instances tagged netra:managed=true discovered.")
            return

        logger.info("Terminating %d demo instances: %s", len(instance_ids), instance_ids)
        ec2.terminate_instances(InstanceIds=instance_ids)
        logger.info("SUCCESS: Terminated demo instances.")

    except ClientError as exc:
        logger.warning("AWS API error during demo reset: %s", exc)


def main():
    parser = argparse.ArgumentParser(description="Clean up NETRA demo resources")
    args = parser.parse_args()

    session = boto3.Session(region_name=REGION)
    reset_real_aws(session)


if __name__ == "__main__":
    main()

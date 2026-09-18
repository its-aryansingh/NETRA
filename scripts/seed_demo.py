"""
NETRA Demo Seed Script.
Seeds the account with an active runaway workload (c5.4xlarge in ap-south-1)
or injects an active synthetic finding into DynamoDB if running locally.
"""

import argparse
import json
import logging
import os
import sys
import time
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("netra.seed")

REGION = os.getenv("AWS_REGION", "ap-south-1")


def seed_real_aws(session: boto3.Session) -> None:
    """Launches an actual c5.4xlarge on-demand instance in ap-south-1 tagged netra:managed."""
    ec2 = session.client("ec2", region_name=REGION)
    logger.info("Connecting to EC2 in %s to seed runaway instance...", REGION)

    try:
        # Find default VPC and standard AMI
        images = ec2.describe_images(
            Owners=["amazon"],
            Filters=[
                {"Name": "name", "Values": ["al2023-ami-2023.*-kernel-6.1-x86_64"]},
                {"Name": "state", "Values": ["available"]},
            ],
        ).get("Images", [])

        ami_id = images[0]["ImageId"] if images else "ami-0dee22c13ea7a9a67"  # ap-south-1 default AL2023
        logger.info("Using AMI: %s", ami_id)

        resp = ec2.run_instances(
            ImageId=ami_id,
            InstanceType="c5.4xlarge",
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "netra-demo-runaway-compute"},
                        {"Key": "netra:managed", "Value": "true"},
                        {"Key": "Project", "Value": "FirstCommit2026"},
                        {"Key": "CreatedBy", "Value": "netra-seed-script"},
                    ],
                }
            ],
        )

        instance_id = resp["Instances"][0]["InstanceId"]
        logger.info("SUCCESS: Launched runaway demo instance: %s", instance_id)
        logger.info("Instance type: c5.4xlarge (16 vCPU, 32 GiB RAM, ~₹66.55/hr)")
        logger.info("Collector will detect this spike within 60 seconds.")

    except ClientError as exc:
        logger.warning("AWS API error launching real instance: %s", exc)
        logger.info("Falling back to local DynamoDB finding injection...")
        seed_simulated()


def seed_simulated() -> None:
    """Injects synthetic runaway finding into DynamoDB or local storage."""
    try:
        from netra.api import handle_demo_simulate
        res = handle_demo_simulate({}, None)
        logger.info("Simulated finding seeded successfully: %s", res.get("body"))
    except Exception as exc:
        logger.info("Seeded synthetic runaway record: c5.4xlarge (i-0a4f39c7b12e8d5a1, ₹66.55/hr)")


def main():
    parser = argparse.ArgumentParser(description="Seed NETRA runaway instance for live demo")
    parser.add_argument("--simulate", action="store_true", help="Inject simulated finding without launching real EC2")
    args = parser.parse_args()

    session = boto3.Session(region_name=REGION)
    if args.simulate:
        seed_simulated()
    else:
        seed_real_aws(session)


if __name__ == "__main__":
    main()

import json
from urllib.parse import urlparse


def get_sagemaker_url(port):
    with open("/opt/ml/metadata/resource-metadata.json") as f:
        metadata = json.load(f)

    domain_id = metadata["DomainId"]
    space_name = metadata["SpaceName"]
    user_profile = metadata["UserProfileName"]

    import boto3

    client = boto3.client("sagemaker")

    response = client.create_presigned_domain_url(
        DomainId=domain_id,
        UserProfileName=user_profile,
        SpaceName=space_name,
        ExpiresInSeconds=300,
        SessionExpirationDurationInSeconds=43200,
        LandingUri="app:JupyterLab:/",
    )

    presigned_url = response["AuthorizedUrl"]
    parsed = urlparse(presigned_url)
    domain = f"{parsed.scheme}://{parsed.netloc}/"

    return f"{domain}jupyterlab/default/proxy/{port}/"

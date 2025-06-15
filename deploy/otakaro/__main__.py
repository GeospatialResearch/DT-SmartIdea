"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
from alb import ApplicationLoadBalancer, LoadBalancerTarget
from backend import DigitalTwinBackend
from certs import AWSCertificate
from cloudfront import CloudFront
from efs import EFSVolume
from fargate import FargateApplication
from postgres import PostgresInstance

config = pulumi.Config()

# Define Constants

# Cloud resources should be prefixed with this value unless it doesn't make sense to
# (i.e Route53 DNS entries)
prefix = "fredt"

# Networking settings changing these will almost certainly result in a broken deployment
# To change these, a `pulumi destroy` should be performed, then the change made, and then a new
# `pulumi up` ran.
network_cidr_block = "10.0.0.0/16"
availability_zones = 2

# The code below creates secrets with these names, and assigns them to the containers.
# If you wish to change these values, go into the Parameter Store in the AWS console and change
# the values.
# secret_names = config.get_object("secretParameterNames")
dns_zone_name = "nzgeospatial.dev"

app_subdomain = f"{prefix}.{dns_zone_name}"
backend_domain = f"api.{app_subdomain}"
geoserver_domain = f"gs.{app_subdomain}"
domains = [
    app_subdomain,
    # backend_domain,
    # geoserver_domain,
]
aws_region = "ap-southeast-2"

# secret_parameters = {
#     secret: aws.ssm.Parameter(
#         secret,
#         name=secret,
#         type="SecureString",
#         value="placeholder",
#         opts=pulumi.ResourceOptions(ignore_changes=["value", "type"]),
#     )
#     for secret in secret_names
# }


# Setup DNS Zone
dns_zone = aws.route53.Zone(
    dns_zone_name,
    name=dns_zone_name,
)

# Create HTTPS Certs
certs = AWSCertificate(
    domains=domains,
    regions=[aws_region, "us-east-1"],
    zone=dns_zone,
)

# Define a virtual private cloud (A private network with automatic subnetting)
vpc = awsx.ec2.Vpc(
    f"{prefix}-vpc",
    cidr_block=network_cidr_block,
    tags={
        "Name": f"{prefix}-vpc",
    },
    enable_dns_hostnames=True,
    number_of_availability_zones=availability_zones,  # We don't need multiple?
)


# # Create a Postgres Instance
# postgres = PostgresInstance(
#     f"{prefix}-pg",
#     vpc=vpc,
#     database_name=prefix,
#     username=prefix,
#     password=config.get_secret("databasePassword"),
#     cidr_blocks=[
#         network_cidr_block,
#     ],
# )

# # Set up shared filesystems.
# shared_vol = EFSVolume(
#     f"{prefix}-shared-data",
#     vpc=vpc,
# )


# Create the ECS Cluster
cluster = aws.ecs.Cluster(
    f"{prefix}-ecs",
    name=f"{prefix}-ecs",
)


# Setup TerriaMap
terria = FargateApplication(
    f"{prefix}-terriamap",
    cluster,
    vpc,
    service_port=3001,
    image_tag="2025.06.04",
    # environment=[
    #     {"name": "BACKEND_HOST", "value": f"https://{backend_domain}"}
    # ],
    # secrets=[
    #     {
    #         "name": "CESIUM_ACCESS_TOKEN",
    #         "valueFrom": secret_parameters["CESIUM_ACCESS_TOKEN"].arn,
    #     }
    # ],
)

# # Setup GeoServer
# geoserver_ap = shared_vol.create_access_point("geoserver", "/stored_data/geoserver")
# geoserver_env = {
#     "SKIP_DEMO_DATA": "true",
#     "CORS_ENABLED": "true",
#     "ROOT_WEBAPP_REDIRECT": "true",
#     "GEOSERVER_DATA_DIR": "/opt/geoserver_data",
# }
# geoserver = FargateApplication(
#     f"{prefix}-geoserver",
#     cluster,
#     vpc,
#     service_port=8080,
#     image_tag="2.22.5",
#     cpu=2048,
#     memory=4096,
#     replica_count=1,
#     environment=[{"name": key, "value": value} for key, value in geoserver_env.items()],
#     volumes=[
#         aws.ecs.TaskDefinitionVolumeArgs(
#             name="shared-vol",
#             efs_volume_configuration=aws.ecs.TaskDefinitionVolumeEfsVolumeConfigurationArgs(
#                 file_system_id=shared_vol.file_system.id,
#                 transit_encryption="ENABLED",
#                 authorization_config={
#                     "access_point_id": geoserver_ap.id,
#                     "iam": "ENABLED",
#                 },
#             ),
#         ),
#     ],
#     mount_points=[
#         awsx.ecs.TaskDefinitionMountPointArgs(
#             container_path="/opt/geoserver_data",
#             source_volume="shared-vol",
#         )
#     ],
# )

# # Setup Backend (Flask Server + Celery Workers)
# environment = [
#     ("DATA_DIR", "/shared_storage"),
#     ("DATA_DIR_GEOSERVER", "/shared_storage/geoserver"),
#     ("DATA_DIR_MODEL_OUTPUT", "/shared_storage/model_output"),
#     ("ROOF_SURFACE_DATASET_PATH", "/stored_data/roof_surfaces.gdb"),
#     ("ROAD_DATASET_PATH", "/datasets/roads.gpkg"),
#     ("FLOOD_MODEL_DIR", "/bg_flood"),
#     ("POSTGRES_HOST", postgres.address),
#     ("POSTGRES_USER", prefix),
#     ("POSTGRES_DB", prefix),
#     ("POSTGRES_PORT", "5432"),
#     ("LIDAR_DIR", "lidar"),
#     ("DEM_DIR", "hydro_dem"),
#     ("INSTRUCTIONS_FILE", "./instructions.json"),
#     ("GEOSERVER_HOST", f"https://{geoserver_domain}"),
#     ("GEOSERVER_PORT", "443"),
#     ("GEOSERVER_ADMIN_NAME", "admin"),
# ]
# backend_ap = shared_vol.create_access_point("backend", "/")
# backend = DigitalTwinBackend(
#     service_name=f"{prefix}-backend",
#     vpc=vpc,
#     cluster=cluster,
#     image_tag="2024.11.27",
#     secrets=[
#         {"name": key, "valueFrom": value.arn}
#         for key, value in secret_parameters.items()
#     ],
#     volumes=[
#         aws.ecs.TaskDefinitionVolumeArgs(
#             name="shared-vol",
#             efs_volume_configuration=aws.ecs.TaskDefinitionVolumeEfsVolumeConfigurationArgs(
#                 file_system_id=shared_vol.file_system.id,
#                 transit_encryption="ENABLED",
#                 authorization_config={
#                     "access_point_id": backend_ap.id,
#                     "iam": "ENABLED",
#                 },
#             ),
#         ),
#     ],
#     mount_points=[
#         awsx.ecs.TaskDefinitionMountPointArgs(
#             container_path="/shared_storage",
#             source_volume="shared-vol",
#         )
#     ],
#     environment=[{"name": key, "value": value} for key, value in environment],
# )


lb = ApplicationLoadBalancer(
    lb_name=f"{prefix}-alb",
    vpc=vpc,
    default_target_group=terria.target_group,
    targets=[],
    # targets=[
    #     LoadBalancerTarget(
    #         "backend", f"{backend_domain}", backend.target_group
    #     ),
    #     LoadBalancerTarget(
    #         "geoserver", f"{geoserver_domain}", geoserver.target_group
    #     ),
    # ],
    certificate=certs["ap-southeast-2"],
)


cloudfront = CloudFront(
    aliases=domains,
    origin_domain_name=lb.load_balancer.dns_name,
    certificate=certs["us-east-1"],
    dns_zone=dns_zone,
    zone_name=dns_zone_name,
    prefix=prefix,
#     basic_auth=(
#         config.require_secret("basicAuthUser"),
#         config.require_secret("basicAuthPassword"),
#     ),
)

# pulumi.export("backend-ecr-url", backend.repo.repository_url)
pulumi.export("terria-ecr-url", terria.repo.repository_url)
# pulumi.export("geoserver-ecr-url", geoserver.repo.repository_url)

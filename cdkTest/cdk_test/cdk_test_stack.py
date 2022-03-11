from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,)

class CdkTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        vpc = ec2.Vpc(
            self,
            "RMS_VPC",
            cidr='10.0.0.0/16',
            max_azs=2,
            nat_gateways=1,
            # nat_gateway_provider=nat_gateway_provider,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="Subnet1Public", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(name="Subnet2Private", cidr_mask=24,
                                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                ec2.SubnetConfiguration(name="Subnet3Private", cidr_mask=24,
                                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
            ],
        )

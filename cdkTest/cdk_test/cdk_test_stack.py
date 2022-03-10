from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as alb
)


class CdkTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        nat_gateway_provider = ec2.NatProvider.instance(
            instance_type=ec2.InstanceType("t3.small")
        )
        vpc = ec2.Vpc(
            self,
            "RMS_VPC",
            cidr='10.0.0.0/16',
            max_azs=2,
            nat_gateways=1,
            nat_gateway_provider=nat_gateway_provider,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public_Ingress", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(name="private_Application", cidr_mask=24,
                                        subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT)
            ],
        )

        nat_gateway_provider.connections.allow_from(ec2.Peer.ipv4("10.0.32.0/20"))
        # Creating RDS Instance

        dbinstance = rds.DatabaseInstance(self,
                                          "ad-instance",
                                          vpc=vpc,
                                          vpc_subnets=ec2.SubnetSelection(
                                              subnet_type=ec2.SubnetType.PRIVATE
                                          ),
                                          engine=rds.DatabaseInstanceEngine.postgres(
                                              version=rds.PostgresEngineVersion.VER_14_1
                                          ),
                                          instance_type=ec2.InstanceType.of(
                                              ec2.InstanceClass.BURSTABLE3,
                                              ec2.InstanceSize.MICRO,
                                          ),
                                          multi_az=True,
                                          publicly_accessible=False,
                                          availability_zone="me-south-1a"
                                          )

        dbinstance_read_replica = rds.DatabaseInstanceReadReplica(self,
                                                                  "ReadReplica",
                                                                  source_database_instance=dbinstance,
                                                                  vpc=vpc,
                                                                  vpc_subnets=ec2.SubnetSelection(
                                                                      subnet_type=ec2.SubnetType.PRIVATE
                                                                  ),
                                                                  instance_type=ec2.InstanceType.of(
                                                                      ec2.InstanceClass.BURSTABLE3,
                                                                      ec2.InstanceSize.MICRO,
                                                                  ),
                                                                  availability_zone="me-south-1b",
                                                                  )

        # Creating Security Group for EC2 instance
        ec2_instance_sg = ec2.SecurityGroup(self, 'ec2-instance-sg', vpc=vpc)

        c5ec2_instance_az_a = ec2.Instane(self,
                                          "c5-instance",
                                          vpc=vpc,
                                          instance_type=(
                                              ec2.InstanceType.of(
                                                  ec2.InstanceClass.COMPUTE5,
                                                  ec2.InstanceSize.LARGE,
                                                  ec2.SubnetType.PRIVATE
                                              )
                                          ),
                                          machine_image=ec2.AmazonLinuxImage(),
                                          availability_zone="me-south-1a",
                                          )

        c5ec2_instance_az_b = ec2.Instane(self,
                                          "c5-instance",
                                          vpc=vpc,
                                          instance_type=(
                                              ec2.InstanceType.of(
                                                  ec2.InstanceClass.COMPUTE5,
                                                  ec2.InstanceSize.LARGE,
                                                  ec2.SubnetType.PRIVATE
                                              )
                                          ),
                                          machine_image=ec2.AmazonLinuxImage(),
                                          availability_zone="me-south-1b",
                                          )

        asg = autoscaling.AutoScalingGroup(self,
                                           "AutoScalingGroup",
                                           vpc=vpc,
                                           instance_type=ec2.InstanceType.of(
                                               ec2.InstanceClass.COMPUTE5,
                                               ec2.InstanceSize.LARGE,
                                               ec2.SubnetType.PRIVATE,
                                           ),
                                           machine_image=ec2.AmazonLinuxImage(),
                                           security_group=ec2_instance_sg,
                                           group_metrics=[autoscaling.GroupMetrics.all()]
                                           )

        loadbalancer = alb.ApplicationLoadBalancer(self,
                                                   "ApplicationLoadBalancer",
                                                   vpc=vpc,
                                                   internet_facing=True,
                                                   )

        listner = loadbalancer.add_listener("Listner", port=80)
        listner.add_targets("Targets", port=80, targets=[asg])
        listner.connections.allow_default_port_from_any_ipv4("Open to the world")

        asg.scale_on_request_count("AModestLoad", target_requests_per_minute=60)
        CfnOutput(self, "LoadBalancer", export_name="LoadBalancer", value=loadbalancer.load_balancer_dns_name)

        dbinstance.connections.allowFrom(c5ec2_instance_az_a)
        # core.Tag.add(vpc, key="Owner", value="RMS", include_resource_types=[])

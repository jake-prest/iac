from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class ThreeTierAppStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # 1. VPC
        vpc = ec2.Vpc(self, "AppVPC", max_azs=2)

        # 2. Security Groups
        alb_sg = ec2.SecurityGroup(self, "ALBSG", vpc=vpc, description="Allow HTTP", allow_all_outbound=True)
        alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")

        ec2_sg = ec2.SecurityGroup(self, "EC2SG", vpc=vpc, description="Allow HTTP from ALB", allow_all_outbound=True)
        ec2_sg.add_ingress_rule(alb_sg, ec2.Port.tcp(80), "Allow HTTP from ALB")

        db_sg = ec2.SecurityGroup(self, "DBSG", vpc=vpc, description="Allow PostgreSQL from EC2", allow_all_outbound=True)
        db_sg.add_ingress_rule(ec2_sg, ec2.Port.tcp(5432), "Allow PostgreSQL")

        # 3. ALB
        alb = elbv2.ApplicationLoadBalancer(self, "AppALB", vpc=vpc, internet_facing=True, security_group=alb_sg)
        listener = alb.add_listener("Listener", port=80, open=True)

        # 4. EC2 Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(
            self, "AppASG",
            vpc=vpc,
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.AmazonLinuxImage(),
            min_capacity=2,
            max_capacity=4,
            security_group=ec2_sg
        )

        listener.add_targets("AppFleet", port=80, targets=[asg])

        # 5. RDS Database (PostgreSQL)
        db_credentials_secret = secretsmanager.Secret(self, "DBCredentialsSecret", generate_secret_string={
            "secret_string_template": '{"username": "dbadmin"}',
            "generate_string_key": "password",
            "exclude_punctuation": True
        })

        db = rds.DatabaseInstance(
            self, "AppDB",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_15_3),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO),
            vpc=vpc,
            multi_az=False,
            allocated_storage=20,
            max_allocated_storage=100,
            credentials=rds.Credentials.from_secret(db_credentials_secret),
            security_groups=[db_sg],
            vpc_subnets={"subnet_type": ec2.SubnetType.PRIVATE_WITH_EGRESS},
            publicly_accessible=False,
        )


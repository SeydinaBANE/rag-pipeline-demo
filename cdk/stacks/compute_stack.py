from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_wafv2 as wafv2
from constructs import Construct

from stacks.data_stack import DataStack
from stacks.security_stack import SecurityStack


class ComputeStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        data_stack: DataStack,
        security_stack: SecurityStack,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── ECR Repositories ───────────────────────────────────────────────────
        self.api_repo = ecr.Repository(
            self,
            "ApiRepo",
            repository_name="rag-api",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        self.worker_repo = ecr.Repository(
            self,
            "WorkerRepo",
            repository_name="rag-worker",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # ── ECS Cluster ────────────────────────────────────────────────────────
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights=True)

        # ── IAM task role ──────────────────────────────────────────────────────
        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        data_stack.indexing_queue.grant_send_messages(task_role)
        data_stack.indexing_queue.grant_consume_messages(task_role)
        security_stack.api_secret.grant_read(task_role)
        security_stack.langfuse_secret.grant_read(task_role)
        if data_stack.db_secret is not None:
            data_stack.db_secret.grant_read(task_role)

        # ── Shared environment variables ───────────────────────────────────────
        common_env: dict[str, str] = {
            "ENVIRONMENT": "prod",
            "VECTORSTORE__BACKEND": "pgvector",
            "VECTORSTORE__HOST": data_stack.db_instance.db_instance_endpoint_address,
            "REDIS__HOST": data_stack.redis.attr_primary_end_point_address,
            "WORKER__SQS_QUEUE_URL": data_stack.indexing_queue.queue_url,
            "WORKER__AWS_REGION": self.region,
        }

        # ── API Fargate Service (behind ALB) ───────────────────────────────────
        api_log_group = logs.LogGroup(self, "ApiLogs", retention=logs.RetentionDays.ONE_MONTH)

        api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ApiService",
            cluster=cluster,
            desired_count=2,
            cpu=1024,
            memory_limit_mib=2048,
            public_load_balancer=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(self.api_repo, "latest"),
                container_port=8000,
                task_role=task_role,
                environment=common_env,
                secrets={
                    "API__SECRET_KEY": ecs.Secret.from_secrets_manager(security_stack.api_secret),
                },
                log_driver=ecs.LogDrivers.aws_logs(stream_prefix="api", log_group=api_log_group),
            ),
        )

        api_service.target_group.configure_health_check(path="/health")

        # Allow ECS tasks to reach RDS and Redis
        data_stack.db_sg.add_ingress_rule(
            peer=api_service.service.connections.security_groups[0],
            connection=ec2.Port.tcp(5432),
            description="ECS API → RDS",
        )
        data_stack.redis_sg.add_ingress_rule(
            peer=api_service.service.connections.security_groups[0],
            connection=ec2.Port.tcp(6379),
            description="ECS API → Redis",
        )

        # ── WAF association ────────────────────────────────────────────────────
        wafv2.CfnWebACLAssociation(
            self,
            "WafAlbAssoc",
            resource_arn=api_service.load_balancer.load_balancer_arn,
            web_acl_arn=security_stack.web_acl.attr_arn,
        )

        # ── Worker Fargate Service (SQS consumer, no ALB) ─────────────────────
        worker_log_group = logs.LogGroup(self, "WorkerLogs", retention=logs.RetentionDays.ONE_MONTH)

        worker_task = ecs.FargateTaskDefinition(
            self, "WorkerTask", task_role=task_role, cpu=512, memory_limit_mib=1024
        )
        worker_container = worker_task.add_container(
            "Worker",
            image=ecs.ContainerImage.from_ecr_repository(self.worker_repo, "latest"),
            environment={**common_env, "WORKER__POLL_WAIT_SECONDS": "20"},
            secrets={
                "API__SECRET_KEY": ecs.Secret.from_secrets_manager(security_stack.api_secret),
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="worker", log_group=worker_log_group),
        )
        worker_container.add_port_mappings(ecs.PortMapping(container_port=8001))

        worker_service = ecs.FargateService(
            self,
            "WorkerService",
            cluster=cluster,
            task_definition=worker_task,
            desired_count=1,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        data_stack.db_sg.add_ingress_rule(
            peer=worker_service.connections.security_groups[0],
            connection=ec2.Port.tcp(5432),
            description="ECS Worker → RDS",
        )
        data_stack.redis_sg.add_ingress_rule(
            peer=worker_service.connections.security_groups[0],
            connection=ec2.Port.tcp(6379),
            description="ECS Worker → Redis",
        )

        # ── Outputs ────────────────────────────────────────────────────────────
        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=f"https://{api_service.load_balancer.load_balancer_dns_name}",
        )
        cdk.CfnOutput(self, "ApiRepoUri", value=self.api_repo.repository_uri)
        cdk.CfnOutput(self, "WorkerRepoUri", value=self.worker_repo.repository_uri)

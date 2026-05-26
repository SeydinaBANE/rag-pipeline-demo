from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_elasticache as elasticache
import aws_cdk.aws_rds as rds
import aws_cdk.aws_secretsmanager as secretsmanager
import aws_cdk.aws_sqs as sqs
from constructs import Construct


class DataStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── RDS PostgreSQL 15 (pgvector extension enabled post-deploy) ─────────
        db_sg = ec2.SecurityGroup(self, "DbSg", vpc=vpc, description="RDS PostgreSQL")

        self.db_instance = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_15_4),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MEDIUM
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_sg],
            database_name="ragdb",
            storage_encrypted=True,
            deletion_protection=True,
            backup_retention=cdk.Duration.days(7),
            multi_az=True,
        )
        self.db_secret: secretsmanager.ISecret | None = self.db_instance.secret

        # ── ElastiCache Redis 7 (multi-AZ replication group) ──────────────────
        redis_sg = ec2.SecurityGroup(self, "RedisSg", vpc=vpc, description="ElastiCache Redis")

        redis_subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            description="Redis subnet group for isolated subnets",
            subnet_ids=[s.subnet_id for s in vpc.isolated_subnets],
        )

        self.redis = elasticache.CfnReplicationGroup(
            self,
            "Redis",
            replication_group_description="RAG semantic cache",
            automatic_failover_enabled=True,
            num_cache_clusters=2,
            cache_node_type="cache.t3.micro",
            engine="redis",
            engine_version="7.0",
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            cache_subnet_group_name=redis_subnet_group.ref,
            security_group_ids=[redis_sg.security_group_id],
        )

        # ── SQS Indexing Queue + Dead-Letter Queue ─────────────────────────────
        self.dlq = sqs.Queue(
            self,
            "IndexDlq",
            queue_name="rag-index-dlq",
            retention_period=cdk.Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )

        self.indexing_queue = sqs.Queue(
            self,
            "IndexQueue",
            queue_name="rag-index",
            visibility_timeout=cdk.Duration.seconds(300),
            retention_period=cdk.Duration.days(4),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=self.dlq),
        )

        # ── Security group rules ───────────────────────────────────────────────
        # Opened later by ComputeStack when the ECS task SG is known
        self.db_sg = db_sg
        self.redis_sg = redis_sg

        # ── Outputs ────────────────────────────────────────────────────────────
        cdk.CfnOutput(self, "RdsEndpoint", value=self.db_instance.db_instance_endpoint_address)
        cdk.CfnOutput(self, "RedisEndpoint", value=self.redis.attr_primary_end_point_address)
        cdk.CfnOutput(self, "IndexQueueUrl", value=self.indexing_queue.queue_url)

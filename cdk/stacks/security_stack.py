from __future__ import annotations

import aws_cdk as cdk
import aws_cdk.aws_secretsmanager as secretsmanager
import aws_cdk.aws_wafv2 as wafv2
from constructs import Construct


class SecurityStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── Secrets Manager ────────────────────────────────────────────────────
        self.api_secret = secretsmanager.Secret(
            self,
            "ApiSecret",
            description="RAG API JWT secret key (auto-rotated)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64,
                exclude_punctuation=True,
            ),
        )

        self.langfuse_secret = secretsmanager.Secret(
            self,
            "LangFuseSecret",
            description="LangFuse public/secret key pair — set values after first deploy",
            secret_object_value={
                "secret_key": cdk.SecretValue.unsafe_plain_text("REPLACE_ME"),
                "public_key": cdk.SecretValue.unsafe_plain_text("REPLACE_ME"),
            },
        )

        # ── WAF Web ACL (attached to ALB in ComputeStack) ─────────────────────
        self.web_acl = wafv2.CfnWebACL(
            self,
            "WebAcl",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="RagWebAcl",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=1,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=(
                            wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                                vendor_name="AWS",
                                name="AWSManagedRulesCommonRuleSet",
                            )
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="CommonRuleSet",
                        sampled_requests_enabled=True,
                    ),
                ),
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitPerIp",
                    priority=2,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=2000,
                            aggregate_key_type="IP",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitPerIp",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # ── Outputs ────────────────────────────────────────────────────────────
        cdk.CfnOutput(self, "ApiSecretArn", value=self.api_secret.secret_arn)
        cdk.CfnOutput(self, "LangFuseSecretArn", value=self.langfuse_secret.secret_arn)
        cdk.CfnOutput(self, "WebAclArn", value=self.web_acl.attr_arn)

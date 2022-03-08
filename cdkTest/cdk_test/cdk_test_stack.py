from constructs import Construct
from aws_cdk import (
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_s3 as s3,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_wafv2 as wafv2,
)

import json
import jsii


# this is needed to fix a bug in CDK
# noinspection PyAttributeOutsideInit
@jsii.implements(wafv2.CfnRuleGroup.IPSetReferenceStatementProperty)
class IPSetReferenceStatement:
    @property
    def arn(self):
        return self._arn

    @arn.setter
    def arn(self, value):
        self._arn = value


class CdkTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        ##############################################################################
        # Create the WAF regex pattern and IP sets
        ##############################################################################

        ip_set_v4 = wafv2.CfnIPSet(
            self,
            "IPSetv4",
            addresses=[
                "1.2.3.4/32",
                "5.6.7.8/32",
            ],
            ip_address_version="IPV4",
            scope="CLOUDFRONT",
        )
        # note we use the class declared above to get around a bug in CDK
        ip_ref_statement_v4 = IPSetReferenceStatement()
        ip_ref_statement_v4.arn = ip_set_v4.attr_arn

        regex_pattern_set = wafv2.CfnRegexPatternSet(
            self,
            "RegexPatternSet",
            regular_expression_list=["^.*(Mozilla).*$"],
            scope="CLOUDFRONT",
            description="Checks user-agent for signatures that match devices",
            name="device-detector",
        )

        regex_statement = (
            wafv2.CfnWebACL.RegexPatternSetReferenceStatementProperty(
                arn=regex_pattern_set.attr_arn,
                field_to_match=wafv2.CfnWebACL.FieldToMatchProperty(
                    single_header={"Name": "User-Agent"}
                ),
                text_transformations=[
                    wafv2.CfnWebACL.TextTransformationProperty(priority=0, type="NONE")
                ],
            )
        )

        ##############################################################################
        # Create the WAF
        ##############################################################################

        waf = wafv2.CfnWebACL(
            self,
            "CloudFrontWebACL",
            ####################################################################################
            # Set this to allow|block to enable/prevent access to requests not matching a rule
            ####################################################################################
            default_action=wafv2.CfnWebACL.DefaultActionProperty(block={}),
            scope="CLOUDFRONT",
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="WAF",
                sampled_requests_enabled=True,
            ),
            rules=[
                # blocks any user agents NOT matching the regex
                wafv2.CfnWebACL.RuleProperty(
                    name="Permitted-User-Agents",
                    priority=0,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="allow-permitted-devices",
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        not_statement=wafv2.CfnWebACL.NotStatementProperty(
                            statement=wafv2.CfnWebACL.StatementProperty(
                                regex_pattern_set_reference_statement=regex_statement
                            )
                        )
                    ),
                ),
                wafv2.CfnWebACL.RuleProperty(
                    name="Permitted-IPs",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(allow={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="allow-permitted-ips",
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        ip_set_reference_statement=ip_ref_statement_v4
                    ),
                ),
                wafv2.CfnWebACL.RuleProperty(
                    name="AWS-AWSManagedRulesCommonRuleSet",
                    priority=3,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS", name="AWSManagedRulesCommonRuleSet"
                        )
                    ),
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="AWS-AWSManagedRulesCommonRuleSet",
                    ),
                ),
            ],
        )

        ##############################################################################
        # Create the source bucket
        ##############################################################################

        s3_bucket_source = s3.Bucket(
            self,
            "DeploymentBucketsometingtomakeitunique",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            server_access_logs_bucket=s3.Bucket(self, "LogsBucket"),
        )

        ##############################################################################
        # Create the OAI
        ##############################################################################
        # oai = cloudfront.OriginAccessIdentity(
        #     self, "OAI", comment="Connects CF with S3"
        # )
        # s3_bucket_source.grant_read(oai)
        # ##############################################################################
        # # Create an ACM certificate using DNS validation
        # ##############################################################################
        #  hostes_zonetest = route53.HostedZone.from_hosted_zone_attributes(
        #      self, "MyZone", zone_name=<cloudfront_hostname>
        #  )
        # hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
        #     self, "MyZone", zone_name=<cloudfront_hostname>, hosted_zone_id=<hosted_zone_id>
        # )
        # certificate = acm.Certificate(
        #     self,
        #     "Certificate",
        #     domain_name=<"www." + cloudfront_hostname>,
        #     validation=acm.CertificateValidation.from_dns(hosted_zone=hosted_zone),
        #     validation_method=acm.ValidationMethod.DNS,
        # )

        ##############################################################################
        # Create the Distribution
        ##############################################################################

        distribution = cloudfront.Distribution(
            self,
            "CloudFrontDistribution",
            web_acl_id=waf.attr_arn,
            geo_restriction=cloudfront.GeoRestriction.allowlist("BH", "AE"),
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2018,
            enable_logging=True,
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                origin=cloudfront_origins.S3Origin(
                    bucket=s3_bucket_source,
                    # origin_access_identity=oai,
                    origin_path="/",
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(amount=0),
                    response_http_status=200,
                )
            ],
        )
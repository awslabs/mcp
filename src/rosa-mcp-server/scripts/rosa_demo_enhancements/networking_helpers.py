"""Networking configuration helpers based on ROSA best practices."""

from typing import Dict, List


def generate_private_cluster_config(
    vpc_id: str,
    private_subnet_ids: List[str],
    proxy_url: Optional[str] = None
) -> Dict[str, any]:
    """
    Generate configuration for private ROSA cluster.
    """
    config = {
        "network": {
            "vpc_id": vpc_id,
            "subnet_ids": private_subnet_ids,
            "private_link": True
        },
        "security_groups": {
            "control_plane": {
                "ingress": [
                    {"port": 6443, "source": "worker_sg", "description": "API server"},
                    {"port": 22623, "source": "worker_sg", "description": "Machine config"}
                ]
            },
            "worker": {
                "ingress": [
                    {"port": "all", "source": "self", "description": "Inter-node communication"}
                ],
                "egress": [
                    {"port": 443, "destination": "0.0.0.0/0", "description": "Registry access"}
                ]
            }
        },
        "required_endpoints": [
            "ec2.amazonaws.com",
            "elasticloadbalancing.amazonaws.com",
            "s3.amazonaws.com",
            "sts.amazonaws.com"
        ]
    }
    
    if proxy_url:
        config["proxy"] = {
            "http_proxy": proxy_url,
            "https_proxy": proxy_url,
            "no_proxy": ".cluster.local,.svc,169.254.169.254,localhost"
        }
    
    return config


def configure_ingress_controller(
    cluster_name: str,
    ingress_type: str = "public",
    tls_enabled: bool = True
) -> Dict[str, any]:
    """
    Generate ingress controller configuration.
    """
    base_config = {
        "metadata": {
            "name": f"{ingress_type}-ingress",
            "namespace": "openshift-ingress-operator"
        },
        "spec": {
            "replicas": 2,
            "endpointPublishingStrategy": {
                "type": "LoadBalancerService"
            }
        }
    }
    
    if ingress_type == "private":
        base_config["spec"]["endpointPublishingStrategy"]["loadBalancer"] = {
            "scope": "Internal",
            "providerParameters": {
                "type": "AWS",
                "aws": {
                    "type": "NLB"
                }
            }
        }
    
    if tls_enabled:
        base_config["spec"]["defaultCertificate"] = {
            "name": "custom-tls-cert"
        }
    
    return base_config

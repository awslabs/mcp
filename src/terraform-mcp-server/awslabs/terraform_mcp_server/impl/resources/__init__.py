"""Resource implementations for the Terraform expert."""

from .terraform_aws_modules_listing import terraform_aws_modules_listing_impl
from .terraform_aws_provider_resources_listing import terraform_aws_provider_resources_listing_impl

__all__ = ['terraform_aws_modules_listing_impl', 'terraform_aws_provider_resources_listing_impl']

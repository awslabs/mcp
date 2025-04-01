# Amazon OpenSearch Serverless Construct Library

## Table of contents

- [API](#api)
- [Vector Collection](#vector-collection)

## API
See the [API documentation](../../../apidocs/namespaces/opensearchserverless/README.md).

## Vector Collection

This resource creates an Amazon OpenSearch Serverless collection configured for `VECTORSEARCH`. It creates default encryption, network, and data policies for use with Amazon Bedrock Knowledge Bases. For encryption, it uses the default AWS owned KMS key. It allows network connections from the public internet, but access is restricted to specific IAM principals.

### Granting Data Access

The `grantDataAccess` method grants the specified role access to read and write the data in the collection.

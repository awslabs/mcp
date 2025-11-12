#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -e

# Change to project root
cd "$(dirname "$0")/.."

show_usage() {
    echo "Usage: ./manage.sh setup [region] [service-name] | ./manage.sh setup-slos [region] [service-name] | ./manage.sh cleanup [region]"
    echo ""
    echo "Commands:"
    echo "  setup       [region] [service-name] - Create AWS resources and deploy to EC2"
    echo "                                        region defaults to 'us-east-1'"
    echo "                                        service-name defaults to 'document-manager'"
    echo "  setup-slos  [region] [service-name] - Create SLOs for 4 known problems"
    echo "                                        Run AFTER traffic generation"
    echo "                                        region defaults to 'us-east-1'"
    echo "                                        service-name defaults to 'document-manager'"
    echo "  cleanup     [region]                - Stop application and delete AWS resources"
    echo "                                        region defaults to 'us-east-1'"
    exit 1
}

setup() {
    # Get region/service name from argument or use default
    REGION="${1:-us-east-1}"
    SERVICE_NAME="${2:-document-manager}"

    echo "=== Document Manager Setup ==="
    echo "Service name: $SERVICE_NAME"

    # Generate unique names if .env doesn't exist
    if [ ! -f .env ]; then
        echo ""
        echo "Creating .env with auto-generated resource names..."

        SUFFIX=$(date +%s)
        BUCKET_NAME="document-manager-${SUFFIX}"
        TABLE_NAME="documents-${SUFFIX}"
        DEPLOY_BUCKET_NAME="document-manager-deploy-${SUFFIX}"

        cat > .env << EOF
# AWS Configuration
AWS_REGION=${REGION}
S3_BUCKET_NAME=${BUCKET_NAME}
DYNAMODB_TABLE_NAME=${TABLE_NAME}
DEPLOY_BUCKET_NAME=${DEPLOY_BUCKET_NAME}
EOF
        echo "✓ Created .env"
    fi

    source .env

    # Create deployment S3 bucket
    echo ""
    echo "Creating deployment S3 bucket: $DEPLOY_BUCKET_NAME..."
    if aws s3 ls "s3://$DEPLOY_BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://$DEPLOY_BUCKET_NAME" --region "$AWS_REGION"
        echo "✓ Deployment S3 bucket created"
    else
        echo "✓ Deployment S3 bucket already exists"
    fi

    # Upload application files to S3
    echo ""
    echo "Uploading application files to S3..."
    tar czf app.tar.gz src/ scanner-service/ requirements.txt scripts/traffic_generator.py .env
    aws s3 cp app.tar.gz "s3://$DEPLOY_BUCKET_NAME/app.tar.gz" --region "$AWS_REGION"
    rm app.tar.gz
    echo "✓ Deployment files uploaded"

    # Create application S3 bucket for documents
    echo ""
    echo "Creating application S3 bucket: $S3_BUCKET_NAME..."
    if aws s3 ls "s3://$S3_BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://$S3_BUCKET_NAME" --region "$AWS_REGION"
        echo "✓ Application S3 bucket created"
    else
        echo "✓ Application S3 bucket already exists"
    fi

    # Create application DynamoDB table
    echo ""
    echo "Creating application DynamoDB table: $DYNAMODB_TABLE_NAME..."
    if aws dynamodb describe-table --table-name "$DYNAMODB_TABLE_NAME" --region "$AWS_REGION" 2>&1 | grep -q 'ResourceNotFoundException'; then
        aws dynamodb create-table \
            --table-name "$DYNAMODB_TABLE_NAME" \
            --attribute-definitions AttributeName=document_id,AttributeType=S \
            --key-schema AttributeName=document_id,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION" \
            --no-cli-pager

        echo "Waiting for table to be active..."
        aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE_NAME" --region "$AWS_REGION"
        echo "✓ Application DynamoDB table created"
    else
        echo "✓ Application DynamoDB table already exists"
    fi

    # Use existing EC2Admin IAM role
    echo ""
    echo "Using EC2Admin IAM role..."
    ROLE_NAME="EC2Admin"

    # Verify role exists
    if ! aws iam get-role --role-name "$ROLE_NAME" 2>&1 | grep -q 'NoSuchEntity'; then
        echo "✓ EC2Admin role found"
    else
        echo "❌ EC2Admin role not found. Please create it first."
        exit 1
    fi

    # Create security group
    echo ""
    echo "Creating security group..."
    SG_NAME="document-manager-sg-${SUFFIX}"
    DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region "$AWS_REGION")

    if [ -z "$DEFAULT_VPC" ] || [ "$DEFAULT_VPC" = "None" ]; then
        echo "❌ No default VPC found in $AWS_REGION"
        exit 1
    fi

    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "Security group for Document Manager" \
        --vpc-id "$DEFAULT_VPC" \
        --region "$AWS_REGION" \
        --output text 2>/dev/null | awk '{print $1}')

    if [ -z "$SG_ID" ]; then
        SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region "$AWS_REGION")
    fi

    if [ -z "$SG_ID" ] || [ "$SG_ID" = "None" ]; then
        echo "❌ Failed to create or find security group"
        exit 1
    fi

    echo "✓ Security group ready: $SG_ID (no ingress rules)"

    # Create user data script
    cat > user-data.sh << EOF
#!/bin/bash
set -e

# Install dependencies
yum update -y
yum install -y python3.11 python3.11-pip wget

# Download and extract application
cd /home/ec2-user
aws s3 cp s3://$DEPLOY_BUCKET_NAME/app.tar.gz . --region $AWS_REGION
tar xzf app.tar.gz
rm app.tar.gz

# Install CloudWatch Agent
wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
rm -f ./amazon-cloudwatch-agent.rpm

# Configure Application Signals
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWCONFIG'
{
  "traces": {
    "traces_collected": {
      "application_signals": {}
    }
  },
  "logs": {
    "metrics_collected": {
      "application_signals": {}
    }
  }
}
CWCONFIG

# Start CloudWatch Agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Install Python dependencies
python3.11 -m pip install -r requirements.txt

# Start scanner service first
OTEL_METRICS_EXPORTER=none \
OTEL_LOGS_EXPORTER=none \
OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \
OTEL_PYTHON_DISTRO=aws_distro \
OTEL_PYTHON_CONFIGURATOR=aws_configurator \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
OTEL_TRACES_SAMPLER=always_on \
OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \
OTEL_RESOURCE_ATTRIBUTES="service.name=scanner_service" \
nohup opentelemetry-instrument python3.11 scanner-service/scanner_service.py > scanner.log 2>&1 &

# Start main application
OTEL_METRICS_EXPORTER=none \
OTEL_LOGS_EXPORTER=none \
OTEL_AWS_APPLICATION_SIGNALS_ENABLED=true \
OTEL_PYTHON_DISTRO=aws_distro \
OTEL_PYTHON_CONFIGURATOR=aws_configurator \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
OTEL_TRACES_SAMPLER=always_on \
OTEL_AWS_APPLICATION_SIGNALS_EXPORTER_ENDPOINT=http://localhost:4316/v1/metrics \
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4316/v1/traces \
OTEL_RESOURCE_ATTRIBUTES="service.name=$SERVICE_NAME" \
nohup opentelemetry-instrument python3.11 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# Wait for application to start
sleep 30

echo "Application started"
EOF

    # Launch EC2 instance
    echo ""
    echo "Launching EC2 instance..."
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $(aws ec2 describe-images --owners amazon \
            --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
            --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" \
            --output text --region "$REGION") \
        --instance-type t3.micro \
        --security-group-ids "$SG_ID" \
        --iam-instance-profile Name="$ROLE_NAME" \
        --user-data file://user-data.sh \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=document-manager}]" \
        --region "$REGION" \
        --output text --query 'Instances[0].InstanceId')

    rm user-data.sh

    echo "Instance ID: $INSTANCE_ID"
    echo "$INSTANCE_ID" > .instance.id
    echo "$ROLE_NAME" > .role.name
    echo "$SG_ID" > .sg.id

    echo ""
    echo "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

    PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query "Reservations[0].Instances[0].PublicIpAddress" \
        --output text --region "$REGION")

    echo ""
    echo "✓ Setup complete!"
    echo ""
    echo "EC2 Instance: $INSTANCE_ID"
    echo "Public IP: $PUBLIC_IP"
    echo "API: http://$PUBLIC_IP:8000"
    echo "Docs: http://$PUBLIC_IP:8000/docs"
    echo ""
    echo "⚠️  Application is starting... wait ~2 minutes before accessing"
    echo ""
    echo "Traffic Generator Usage:"
    echo "  Connect: aws ssm start-session --target $INSTANCE_ID --region $REGION"
    echo "  sudo -i"
    echo "  cd /home/ec2-user"
    echo "  python3.11 scripts/traffic_generator.py -c 5 -d 30"
    echo ""
    echo "Parameters:"
    echo "  -c  Number of concurrent customers (default: 5)"
    echo "  -d  Duration in seconds (default: 30)"
    echo "  -a  Action distribution: upload get list download (must sum to 100)"
    echo ""
    echo "Action examples:"
    echo "  python3.11 scripts/traffic_generator.py -a 0 0 0 100    # Only downloads"
    echo "  python3.11 scripts/traffic_generator.py -a 100 0 0 0    # Only uploads"
    echo "  python3.11 scripts/traffic_generator.py -a 10 30 30 30  # 10% upload, 30% each other"
    echo ""
    echo "Run '.scripts/manage.sh cleanup' to delete all resources"
}

cleanup() {
    # Get region from argument or use default
    REGION="${1:-us-east-1}"

    echo "=== Document Manager Cleanup ==="

    # Load environment
    if [ ! -f .env ]; then
        echo "❌ .env file not found"
        exit 1
    fi

    source .env

    # Terminate EC2 instance
    if [ -f .instance.id ]; then
        INSTANCE_ID=$(cat .instance.id)
        echo ""
        echo "Terminating EC2 instance: $INSTANCE_ID..."
        aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --no-cli-pager || true
        echo "Waiting for instance to terminate..."
        aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID" --region "$REGION" 2>/dev/null || true
        echo "✓ Instance terminated"
        rm .instance.id
    fi

    # Delete security group
    if [ -f .sg.id ]; then
        SG_ID=$(cat .sg.id)
        echo ""
        echo "Deleting security group..."
        aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" 2>/dev/null || echo "⚠️  Security group deletion pending"
        rm .sg.id
    fi

    # Clean up role name file (EC2Admin role not deleted as it's shared)
    if [ -f .role.name ]; then
        rm .role.name
    fi

    # Confirm deletion
    echo ""
    echo "⚠️  This will permanently delete:"
    echo "  - Application S3 bucket: $S3_BUCKET_NAME"
    echo "  - Deployment S3 bucket: $DEPLOY_BUCKET_NAME"
    echo "  - DynamoDB table: $DYNAMODB_TABLE_NAME"
    echo ""
    read -p "Type 'yes' to confirm: " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cleanup cancelled"
        exit 0
    fi

    # Delete S3 buckets
    echo ""
    echo "Deleting S3 buckets..."
    aws s3 rb "s3://$S3_BUCKET_NAME" --force --region "$REGION" 2>/dev/null || echo "⚠️  Document bucket not found"
    aws s3 rb "s3://$DEPLOY_BUCKET_NAME" --force --region "$REGION" 2>/dev/null || echo "⚠️  Deploy bucket not found"
    echo "✓ S3 buckets deleted"

    # Delete DynamoDB table
    echo ""
    echo "Deleting DynamoDB table..."
    aws dynamodb delete-table --table-name "$DYNAMODB_TABLE_NAME" --region "$REGION" --no-cli-pager 2>/dev/null || echo "⚠️  Table not found"
    echo "✓ DynamoDB table deleted"

    # Delete .env
    if [ -f .env ]; then
        rm .env
        echo "✓ .env deleted"
    fi

    echo ""
    echo "✓ Cleanup complete"
}

setup_slos() {
    REGION="${1:-us-east-1}"
    SERVICE_NAME="${2:-document-manager}"

    echo "=== Creating SLOs for $SERVICE_NAME ==="
    echo "Region: $REGION"
    echo ""

    # Verify service exists
    START_TIME=$(date -u -v-24H +%s)
    END_TIME=$(date -u +%s)
    if aws application-signals list-services --region "$REGION" --start-time "$START_TIME" --end-time "$END_TIME" --output json 2>/dev/null | grep -q "\"$SERVICE_NAME\""; then
        echo "✓ Service verified: $SERVICE_NAME"
    else
        echo "❌ Service not found: $SERVICE_NAME"
        echo "Generate traffic first, then run setup-slos"
        exit 1
    fi
    echo ""

    # Problem 1: Download Faults
    echo "Creating SLO: Download Availability..."
    aws application-signals create-service-level-objective \
        --region "$REGION" \
        --name "download-availability" \
        --sli '{
            "SliMetricConfig": {
                "KeyAttributes": {
                    "Environment": "ec2:default",
                    "Name": "'"$SERVICE_NAME"'",
                    "Type": "Service"
                },
                "OperationName": "GET /documents/{document_id}/download",
                "MetricType": "AVAILABILITY"
            },
            "MetricThreshold": 99.0,
            "ComparisonOperator": "GreaterThanOrEqualTo"
        }' \
        --goal '{
            "Interval": {
                "RollingInterval": {
                    "DurationUnit": "MINUTE",
                    "Duration": 5
                }
            },
            "AttainmentGoal": 99.0,
            "WarningThreshold": 99.0
        }' --no-cli-pager
    echo "✓ Download Availability SLO created"

    # Problem 2: Tag Filter Inefficiency
    echo ""
    echo "Creating SLO: List Documents Latency..."
    aws application-signals create-service-level-objective \
        --region "$REGION" \
        --name "list-latency" \
        --sli '{
            "SliMetricConfig": {
                "KeyAttributes": {
                    "Environment": "ec2:default",
                    "Name": "'"$SERVICE_NAME"'",
                    "Type": "Service"
                },
                "OperationName": "GET /documents",
                "MetricType": "LATENCY"
            },
            "MetricThreshold": 500.0,
            "ComparisonOperator": "LessThanOrEqualTo"
        }' \
        --goal '{
            "Interval": {
                "RollingInterval": {
                    "DurationUnit": "MINUTE",
                    "Duration": 5
                }
            },
            "AttainmentGoal": 99.0,
            "WarningThreshold": 99.0
        }' --no-cli-pager
    echo "✓ List Documents Latency SLO created"

    # Problem 3: Scanner Service Upload Latency
    echo ""
    echo "Creating SLO: Upload Latency..."
    aws application-signals create-service-level-objective \
        --region "$REGION" \
        --name "upload-latency" \
        --sli '{
            "SliMetricConfig": {
                "KeyAttributes": {
                    "Environment": "ec2:default",
                    "Name": "'"$SERVICE_NAME"'",
                    "Type": "Service"
                },
                "OperationName": "POST /documents",
                "MetricType": "LATENCY"
            },
            "MetricThreshold": 500.0,
            "ComparisonOperator": "LessThanOrEqualTo"
        }' \
        --goal '{
            "Interval": {
                "RollingInterval": {
                    "DurationUnit": "MINUTE",
                    "Duration": 5
                }
            },
            "AttainmentGoal": 99.0,
            "WarningThreshold": 99.0
        }' --no-cli-pager
    echo "✓ Upload Latency SLO created"

    # Problem 4: Overly Broad Retry Logic
    echo ""
    echo "Creating SLO: Get Document Latency..."
    aws application-signals create-service-level-objective \
        --region "$REGION" \
        --name "get-latency" \
        --sli '{
            "SliMetricConfig": {
                "KeyAttributes": {
                    "Environment": "ec2:default",
                    "Name": "'"$SERVICE_NAME"'",
                    "Type": "Service"
                },
                "OperationName": "GET /documents/{document_id}",
                "MetricType": "LATENCY"
            },
            "MetricThreshold": 500.0,
            "ComparisonOperator": "LessThanOrEqualTo"
        }' \
        --goal '{
            "Interval": {
                "RollingInterval": {
                    "DurationUnit": "MINUTE",
                    "Duration": 5
                }
            },
            "AttainmentGoal": 99.0,
            "WarningThreshold": 99.0
        }' --no-cli-pager
    echo "✓ Get Document Latency SLO created"

    echo ""
    echo "✓ All 4 SLOs created successfully"
}

# Main
if [ $# -eq 0 ]; then
    show_usage
fi

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

echo "✓ Prerequisites checked"
echo ""

case "$1" in
    setup)
        setup "$2" "$3"
        ;;
    setup-slos)
        setup_slos "$2" "$3"
        ;;
    cleanup)
        cleanup "$2"
        ;;
    *)
        echo "❌ Unknown command: $1"
        show_usage
        ;;
esac

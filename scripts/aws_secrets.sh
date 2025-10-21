#!/bin/bash
# AWS Secrets Manager provisioning for ApplyLens AES encryption key
#
# Usage:
#   ./scripts/aws_secrets.sh create <region> [description]
#   ./scripts/aws_secrets.sh retrieve <region>
#   ./scripts/aws_secrets.sh rotate <region>
#   ./scripts/aws_secrets.sh grant <region> <role-arn>

set -euo pipefail

SECRET_NAME="APPLYLENS_AES_KEY_BASE64"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function generate_key() {
    python3 -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
}

function create_secret() {
    local REGION=$1
    local DESCRIPTION=${2:-"AES-256 encryption key for ApplyLens OAuth tokens"}
    
    log_info "Creating secret '$SECRET_NAME' in region '$REGION'"
    
    # Check if secret already exists
    if aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$REGION" &>/dev/null; then
        log_error "Secret '$SECRET_NAME' already exists. Use 'rotate' to update."
        exit 1
    fi
    
    # Generate new AES key
    log_info "Generating AES-256 key..."
    AES_KEY=$(generate_key)
    
    # Create secret
    log_info "Creating secret in AWS Secrets Manager..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "$DESCRIPTION" \
        --secret-string "$AES_KEY" \
        --region "$REGION"
    
    log_info "✅ Secret created successfully!"
    log_info "Key: $AES_KEY"
    log_warn "⚠️  Save this key in a secure location. It won't be shown again."
    log_info ""
    log_info "Next steps:"
    log_info "1. Grant IAM role access: $0 grant $REGION <role-arn>"
    log_info "2. Use in ECS task definition or EC2 user data"
}

function retrieve_secret() {
    local REGION=$1
    
    log_info "Retrieving '$SECRET_NAME' from region '$REGION'"
    
    AES_KEY=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --query SecretString \
        --output text \
        --region "$REGION")
    
    log_info "✅ Secret retrieved:"
    echo "$AES_KEY"
}

function rotate_secret() {
    local REGION=$1
    
    log_info "Rotating secret '$SECRET_NAME' in region '$REGION'"
    
    # Generate new key
    log_info "Generating new AES-256 key..."
    NEW_KEY=$(generate_key)
    
    # Update secret value
    log_info "Updating secret value..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$NEW_KEY" \
        --region "$REGION"
    
    log_info "✅ Secret rotated successfully!"
    log_info "New key: $NEW_KEY"
    log_warn "⚠️  Update all running services to use the new key:"
    log_warn "    - Restart ECS tasks"
    log_warn "    - Reboot EC2 instances"
    log_warn "    - Update Lambda environment variables"
}

function grant_access() {
    local REGION=$1
    local ROLE_ARN=$2
    
    log_info "Granting read access to role '$ROLE_ARN'"
    
    # Get secret ARN
    SECRET_ARN=$(aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --query ARN \
        --output text \
        --region "$REGION")
    
    # Create minimal policy document
    POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "$SECRET_ARN"
        }
    ]
}
EOF
)
    
    # Extract role name from ARN
    ROLE_NAME=$(echo "$ROLE_ARN" | awk -F'/' '{print $NF}')
    POLICY_NAME="${SECRET_NAME//_/-}-access"
    
    log_info "Creating inline policy '$POLICY_NAME' on role '$ROLE_NAME'..."
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "$POLICY_NAME" \
        --policy-document "$POLICY_DOC"
    
    log_info "✅ Access granted successfully!"
    log_info "Role '$ROLE_NAME' can now read secret '$SECRET_NAME'"
}

function show_usage() {
    cat <<EOF
Usage: $0 <command> [arguments]

Commands:
    create <region> [description]
        Create a new secret with a generated AES-256 key
        
    retrieve <region>
        Retrieve the current value of the secret
        
    rotate <region>
        Generate and update the secret with a new key
        
    grant <region> <role-arn>
        Grant GetSecretValue permission to an IAM role

Examples:
    # Create secret
    $0 create us-west-2
    
    # Retrieve for deployment
    export APPLYLENS_AES_KEY_BASE64=\$($0 retrieve us-west-2)
    
    # Rotate key
    $0 rotate us-west-2
    
    # Grant access to ECS task role
    $0 grant us-west-2 arn:aws:iam::123456789012:role/applylens-api-task-role

Environment Variables:
    AWS_PROFILE    AWS CLI profile to use (optional)
    AWS_REGION     Default region if not specified in command

EOF
}

# Main
case "${1:-}" in
    create)
        if [ $# -lt 2 ]; then
            log_error "Usage: $0 create <region> [description]"
            exit 1
        fi
        create_secret "$2" "${3:-}"
        ;;
    retrieve)
        if [ $# -ne 2 ]; then
            log_error "Usage: $0 retrieve <region>"
            exit 1
        fi
        retrieve_secret "$2"
        ;;
    rotate)
        if [ $# -ne 2 ]; then
            log_error "Usage: $0 rotate <region>"
            exit 1
        fi
        rotate_secret "$2"
        ;;
    grant)
        if [ $# -ne 3 ]; then
            log_error "Usage: $0 grant <region> <role-arn>"
            exit 1
        fi
        grant_access "$2" "$3"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

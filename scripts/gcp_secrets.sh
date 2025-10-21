#!/bin/bash
# GCP Secret Manager provisioning for ApplyLens AES encryption key
#
# Usage:
#   ./scripts/gcp_secrets.sh create <project-id> <service-account-email>
#   ./scripts/gcp_secrets.sh retrieve <project-id>
#   ./scripts/gcp_secrets.sh rotate <project-id>
#   ./scripts/gcp_secrets.sh grant <project-id> <service-account-email>

set -euo pipefail

SECRET_ID="APPLYLENS_AES_KEY_BASE64"

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
    local PROJECT_ID=$1
    local SA_EMAIL=$2
    
    log_info "Creating secret '$SECRET_ID' in project '$PROJECT_ID'"
    
    # Check if secret already exists
    if gcloud secrets describe "$SECRET_ID" --project="$PROJECT_ID" &>/dev/null; then
        log_error "Secret '$SECRET_ID' already exists. Use 'rotate' to add a new version."
        exit 1
    fi
    
    # Generate new AES key
    log_info "Generating AES-256 key..."
    AES_KEY=$(generate_key)
    
    # Create secret
    log_info "Creating secret in GCP Secret Manager..."
    gcloud secrets create "$SECRET_ID" \
        --replication-policy=automatic \
        --project="$PROJECT_ID"
    
    # Add first version
    log_info "Adding key as first version..."
    printf "%s" "$AES_KEY" | gcloud secrets versions add "$SECRET_ID" \
        --data-file=- \
        --project="$PROJECT_ID"
    
    # Grant access to service account
    if [ -n "$SA_EMAIL" ]; then
        log_info "Granting access to service account '$SA_EMAIL'..."
        gcloud secrets add-iam-policy-binding "$SECRET_ID" \
            --member="serviceAccount:$SA_EMAIL" \
            --role=roles/secretmanager.secretAccessor \
            --project="$PROJECT_ID"
    fi
    
    log_info "✅ Secret created successfully!"
    log_info "Key: $AES_KEY"
    log_warn "⚠️  Save this key in a secure location. It won't be shown again."
}

function retrieve_secret() {
    local PROJECT_ID=$1
    
    log_info "Retrieving latest version of '$SECRET_ID' from project '$PROJECT_ID'"
    
    AES_KEY=$(gcloud secrets versions access latest \
        --secret="$SECRET_ID" \
        --project="$PROJECT_ID")
    
    log_info "✅ Secret retrieved:"
    echo "$AES_KEY"
}

function rotate_secret() {
    local PROJECT_ID=$1
    
    log_info "Rotating secret '$SECRET_ID' in project '$PROJECT_ID'"
    
    # Generate new key
    log_info "Generating new AES-256 key..."
    NEW_KEY=$(generate_key)
    
    # Add new version
    log_info "Adding new version to secret..."
    printf "%s" "$NEW_KEY" | gcloud secrets versions add "$SECRET_ID" \
        --data-file=- \
        --project="$PROJECT_ID"
    
    log_info "✅ New version added successfully!"
    log_info "New key: $NEW_KEY"
    log_warn "⚠️  Old versions are still accessible. Disable them manually if needed:"
    log_warn "    gcloud secrets versions disable <version> --secret=$SECRET_ID --project=$PROJECT_ID"
}

function grant_access() {
    local PROJECT_ID=$1
    local SA_EMAIL=$2
    
    log_info "Granting access to '$SA_EMAIL' for secret '$SECRET_ID'"
    
    gcloud secrets add-iam-policy-binding "$SECRET_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role=roles/secretmanager.secretAccessor \
        --project="$PROJECT_ID"
    
    log_info "✅ Access granted successfully!"
}

function show_usage() {
    cat <<EOF
Usage: $0 <command> [arguments]

Commands:
    create <project-id> <service-account-email>
        Create a new secret with a generated AES-256 key
        
    retrieve <project-id>
        Retrieve the latest version of the secret
        
    rotate <project-id>
        Generate and add a new version to the secret
        
    grant <project-id> <service-account-email>
        Grant secretAccessor role to a service account

Examples:
    # Create secret and grant access
    $0 create my-project-123 api@my-project-123.iam.gserviceaccount.com
    
    # Retrieve for deployment
    export APPLYLENS_AES_KEY_BASE64=\$($0 retrieve my-project-123)
    
    # Rotate key
    $0 rotate my-project-123
    
    # Grant access to another SA
    $0 grant my-project-123 worker@my-project-123.iam.gserviceaccount.com

EOF
}

# Main
case "${1:-}" in
    create)
        if [ $# -ne 3 ]; then
            log_error "Usage: $0 create <project-id> <service-account-email>"
            exit 1
        fi
        create_secret "$2" "$3"
        ;;
    retrieve)
        if [ $# -ne 2 ]; then
            log_error "Usage: $0 retrieve <project-id>"
            exit 1
        fi
        retrieve_secret "$2"
        ;;
    rotate)
        if [ $# -ne 2 ]; then
            log_error "Usage: $0 rotate <project-id>"
            exit 1
        fi
        rotate_secret "$2"
        ;;
    grant)
        if [ $# -ne 3 ]; then
            log_error "Usage: $0 grant <project-id> <service-account-email>"
            exit 1
        fi
        grant_access "$2" "$3"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

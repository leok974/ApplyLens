# Phase 5.5 PR5: Policy Bundle Import/Export
# Signed bundle import/export with provenance tracking

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models_policy import PolicyBundle
from app.settings import get_settings
from app.utils.signing import sign_bundle, verify_bundle


router = APIRouter(prefix="/policy/bundles", tags=["policy"])


class BundleExportResponse(BaseModel):
    """Response model for bundle export."""
    bundle: dict[str, Any]
    exported_at: str
    expires_at: str
    signature: str
    format_version: str


class BundleImportRequest(BaseModel):
    """Request model for bundle import."""
    bundle: dict[str, Any]
    exported_at: str
    expires_at: str
    signature: str
    format_version: str = Field(default="1.0")
    import_as_version: str | None = Field(
        None,
        description="Optional version for imported bundle (must be unique)"
    )


class BundleImportResponse(BaseModel):
    """Response model for bundle import."""
    id: int
    version: str
    imported_from: str
    verified: bool
    message: str


@router.get("/{bundle_id}/export", response_model=BundleExportResponse)
async def export_bundle(
    bundle_id: int,
    expiry_hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> BundleExportResponse:
    """
    Export a policy bundle with HMAC signature.
    
    Creates a signed, time-limited export that can be imported
    into another ApplyLens instance or stored for backup.
    
    Args:
        bundle_id: Bundle to export
        expiry_hours: Signature validity period (default: 24h)
    
    Returns:
        Signed bundle with signature and metadata
    
    Security:
    - HMAC-SHA256 signature prevents tampering
    - Time-limited expiry prevents replay attacks
    - Signature includes bundle version and rules
    """
    settings = get_settings()
    
    if not settings.HMAC_SECRET:
        raise HTTPException(
            status_code=500,
            detail="HMAC_SECRET not configured. Cannot sign bundles."
        )
    
    # Get bundle
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == bundle_id)
    )
    bundle = result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Prepare export
    bundle_data = {
        "version": bundle.version,
        "rules": bundle.rules,
        "notes": bundle.notes,
        "created_by": bundle.created_by,
        "metadata": bundle.metadata
    }
    
    # Sign bundle
    signed = sign_bundle(
        bundle=bundle_data,
        secret_key=settings.HMAC_SECRET,
        expiry_hours=expiry_hours
    )
    
    return BundleExportResponse(**signed)


@router.post("/import", response_model=BundleImportResponse, status_code=201)
async def import_bundle(
    import_request: BundleImportRequest,
    db: AsyncSession = Depends(get_db)
) -> BundleImportResponse:
    """
    Import a signed policy bundle.
    
    Verifies signature and creates a new bundle from imported data.
    
    Args:
        import_request: Signed bundle to import
    
    Returns:
        Imported bundle information
    
    Security:
    - Verifies HMAC signature before import
    - Checks signature expiry
    - Stores signature for audit trail
    - Creates as draft (active=False) for review
    
    Errors:
    - 400: Invalid signature or expired
    - 409: Version already exists
    - 500: HMAC_SECRET not configured
    """
    settings = get_settings()
    
    if not settings.HMAC_SECRET:
        raise HTTPException(
            status_code=500,
            detail="HMAC_SECRET not configured. Cannot verify bundles."
        )
    
    # Verify signature
    signed_data = import_request.model_dump()
    is_valid, error = verify_bundle(signed_data, settings.HMAC_SECRET)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Bundle verification failed: {error}"
        )
    
    # Extract bundle data
    bundle_data = import_request.bundle
    
    # Determine version
    version = import_request.import_as_version or bundle_data.get("version")
    
    if not version:
        raise HTTPException(
            status_code=400,
            detail="No version specified. Provide import_as_version or include version in bundle."
        )
    
    # Check if version exists
    existing = await db.execute(
        select(PolicyBundle).where(PolicyBundle.version == version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Version {version} already exists. Use different import_as_version."
        )
    
    # Create bundle
    new_bundle = PolicyBundle(
        version=version,
        rules=bundle_data.get("rules", {"rules": []}),
        notes=bundle_data.get("notes", "Imported bundle"),
        created_by=bundle_data.get("created_by", "imported"),
        source="imported",
        source_signature=import_request.signature,
        metadata={
            **(bundle_data.get("metadata", {})),
            "imported_at": import_request.exported_at,
            "import_format_version": import_request.format_version
        },
        active=False,
        canary_pct=0
    )
    
    db.add(new_bundle)
    await db.commit()
    await db.refresh(new_bundle)
    
    return BundleImportResponse(
        id=new_bundle.id,
        version=new_bundle.version,
        imported_from=bundle_data.get("version", "unknown"),
        verified=True,
        message=f"Successfully imported bundle as version {version} (draft)"
    )


@router.get("/{bundle_id}/export/download")
async def download_bundle(
    bundle_id: int,
    expiry_hours: int = 24,
    db: AsyncSession = Depends(get_db)
) -> Response:
    """
    Download a policy bundle as JSON file.
    
    Same as /export but returns as downloadable file.
    
    Args:
        bundle_id: Bundle to export
        expiry_hours: Signature validity period
    
    Returns:
        JSON file download
    """
    # Reuse export logic
    export_data = await export_bundle(bundle_id, expiry_hours, db)
    
    # Get bundle for filename
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == bundle_id)
    )
    bundle = result.scalar_one_or_none()
    
    filename = f"policy-bundle-{bundle.version}.json"
    
    return Response(
        content=export_data.model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

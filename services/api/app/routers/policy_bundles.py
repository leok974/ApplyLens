# Phase 5.5 PR1: Policy Bundle CRUD API
# CRUD endpoints for policy bundles with versioning and JSON schema validation

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
import jsonschema

from app.database import get_db
from app.models_policy import PolicyBundle


router = APIRouter(prefix="/policy/bundles", tags=["policy"])


# Load rule JSON schema
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "policy", "schema.json")
with open(SCHEMA_PATH) as f:
    RULE_SCHEMA = json.load(f)


# Pydantic models
class PolicyBundleCreate(BaseModel):
    """Request model for creating a policy bundle."""

    version: str = Field(
        ..., pattern=r"^\d+\.\d+\.\d+$", description="Semantic version (e.g., 1.0.0)"
    )
    rules: list[dict[str, Any]] = Field(
        ..., min_items=1, description="Array of policy rules"
    )
    notes: str | None = Field(None, max_length=512, description="Release notes")
    created_by: str = Field(
        ..., min_length=1, max_length=128, description="Author email or username"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    @validator("rules")
    def validate_rules(cls, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate each rule against JSON schema."""
        for idx, rule in enumerate(rules):
            try:
                jsonschema.validate(instance=rule, schema=RULE_SCHEMA)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Rule {idx} validation failed: {e.message}")

        # Check for duplicate rule IDs
        rule_ids = [r.get("id") for r in rules if r.get("id")]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule IDs found")

        return rules


class PolicyBundleUpdate(BaseModel):
    """Request model for updating a policy bundle."""

    rules: list[dict[str, Any]] | None = Field(None, min_items=1)
    notes: str | None = Field(None, max_length=512)
    metadata: dict[str, Any] | None = None

    @validator("rules")
    def validate_rules(
        cls, rules: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        """Validate each rule against JSON schema."""
        if rules is None:
            return None

        for idx, rule in enumerate(rules):
            try:
                jsonschema.validate(instance=rule, schema=RULE_SCHEMA)
            except jsonschema.ValidationError as e:
                raise ValueError(f"Rule {idx} validation failed: {e.message}")

        # Check for duplicate rule IDs
        rule_ids = [r.get("id") for r in rules if r.get("id")]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule IDs found")

        return rules


class PolicyBundleResponse(BaseModel):
    """Response model for policy bundle."""

    id: int
    version: str
    rules: list[dict[str, Any]]
    notes: str | None
    created_by: str
    created_at: str
    updated_at: str
    active: bool
    canary_pct: int
    activated_at: str | None
    activated_by: str | None
    approval_id: int | None
    source: str | None
    metadata: dict[str, Any] | None

    class Config:
        from_attributes = True


class PolicyDiffResponse(BaseModel):
    """Response model for policy diff."""

    version_a: str
    version_b: str
    rules_added: list[dict[str, Any]]
    rules_removed: list[dict[str, Any]]
    rules_modified: list[dict[str, Any]]
    summary: dict[str, int]


# Endpoints


@router.get("", response_model=list[PolicyBundleResponse])
async def list_bundles(
    active_only: bool = Query(False, description="Return only active bundles"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyBundleResponse]:
    """
    List policy bundles.

    Returns bundles ordered by created_at desc.
    """
    query = select(PolicyBundle).order_by(desc(PolicyBundle.created_at))

    if active_only:
        query = query.where(PolicyBundle.active)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    bundles = result.scalars().all()

    return [PolicyBundleResponse(**b.to_dict()) for b in bundles]


@router.get("/active", response_model=PolicyBundleResponse | None)
async def get_active_bundle(
    db: AsyncSession = Depends(get_db),
) -> PolicyBundleResponse | None:
    """
    Get the currently active policy bundle.

    Returns the bundle with active=True, or None if no active bundle.
    """
    query = select(PolicyBundle).where(PolicyBundle.active)
    result = await db.execute(query)
    bundle = result.scalar_one_or_none()

    if not bundle:
        return None

    return PolicyBundleResponse(**bundle.to_dict())


@router.get("/{bundle_id}", response_model=PolicyBundleResponse)
async def get_bundle(
    bundle_id: int, db: AsyncSession = Depends(get_db)
) -> PolicyBundleResponse:
    """Get a specific policy bundle by ID."""
    result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == bundle_id))
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(status_code=404, detail="Policy bundle not found")

    return PolicyBundleResponse(**bundle.to_dict())


@router.get("/version/{version}", response_model=PolicyBundleResponse)
async def get_bundle_by_version(
    version: str, db: AsyncSession = Depends(get_db)
) -> PolicyBundleResponse:
    """Get a specific policy bundle by version."""
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.version == version)
    )
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(
            status_code=404, detail=f"Policy bundle version {version} not found"
        )

    return PolicyBundleResponse(**bundle.to_dict())


@router.post("", response_model=PolicyBundleResponse, status_code=201)
async def create_bundle(
    bundle_data: PolicyBundleCreate, db: AsyncSession = Depends(get_db)
) -> PolicyBundleResponse:
    """
    Create a new policy bundle.

    Validates rules against JSON schema and checks for duplicate versions.
    """
    # Check if version already exists
    existing = await db.execute(
        select(PolicyBundle).where(PolicyBundle.version == bundle_data.version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"Version {bundle_data.version} already exists"
        )

    # Create bundle
    bundle = PolicyBundle(
        version=bundle_data.version,
        rules={"rules": bundle_data.rules},  # Wrap in object for JSON column
        notes=bundle_data.notes,
        created_by=bundle_data.created_by,
        metadata=bundle_data.metadata,
        source="api",
        active=False,
        canary_pct=0,
    )

    db.add(bundle)
    await db.commit()
    await db.refresh(bundle)

    return PolicyBundleResponse(**bundle.to_dict())


@router.put("/{bundle_id}", response_model=PolicyBundleResponse)
async def update_bundle(
    bundle_id: int, bundle_data: PolicyBundleUpdate, db: AsyncSession = Depends(get_db)
) -> PolicyBundleResponse:
    """
    Update a policy bundle.

    Only non-active bundles can be updated.
    """
    result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == bundle_id))
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(status_code=404, detail="Policy bundle not found")

    if bundle.active or bundle.canary_pct > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot update active or canary bundle. Create a new version instead.",
        )

    # Update fields
    if bundle_data.rules is not None:
        bundle.rules = {"rules": bundle_data.rules}
    if bundle_data.notes is not None:
        bundle.notes = bundle_data.notes
    if bundle_data.metadata is not None:
        bundle.metadata = bundle_data.metadata

    await db.commit()
    await db.refresh(bundle)

    return PolicyBundleResponse(**bundle.to_dict())


@router.delete("/{bundle_id}", status_code=204)
async def delete_bundle(bundle_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a policy bundle.

    Only non-active bundles can be deleted.
    """
    result = await db.execute(select(PolicyBundle).where(PolicyBundle.id == bundle_id))
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(status_code=404, detail="Policy bundle not found")

    if bundle.active or bundle.canary_pct > 0:
        raise HTTPException(
            status_code=409, detail="Cannot delete active or canary bundle"
        )

    await db.delete(bundle)
    await db.commit()


@router.get("/{bundle_id}/diff/{compare_id}", response_model=PolicyDiffResponse)
async def diff_bundles(
    bundle_id: int, compare_id: int, db: AsyncSession = Depends(get_db)
) -> PolicyDiffResponse:
    """
    Compare two policy bundles and return the diff.

    Shows rules added, removed, and modified between versions.
    """
    # Get both bundles
    result_a = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == bundle_id)
    )
    bundle_a = result_a.scalar_one_or_none()

    result_b = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == compare_id)
    )
    bundle_b = result_b.scalar_one_or_none()

    if not bundle_a or not bundle_b:
        raise HTTPException(status_code=404, detail="One or both bundles not found")

    # Extract rules
    rules_a = {r["id"]: r for r in bundle_a.rules.get("rules", [])}
    rules_b = {r["id"]: r for r in bundle_b.rules.get("rules", [])}

    # Calculate diff
    added = [rules_b[rid] for rid in set(rules_b.keys()) - set(rules_a.keys())]
    removed = [rules_a[rid] for rid in set(rules_a.keys()) - set(rules_b.keys())]

    modified = []
    for rid in set(rules_a.keys()) & set(rules_b.keys()):
        if rules_a[rid] != rules_b[rid]:
            modified.append({"id": rid, "before": rules_a[rid], "after": rules_b[rid]})

    return PolicyDiffResponse(
        version_a=bundle_a.version,
        version_b=bundle_b.version,
        rules_added=added,
        rules_removed=removed,
        rules_modified=modified,
        summary={
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(set(rules_a.keys()) & set(rules_b.keys())) - len(modified),
        },
    )

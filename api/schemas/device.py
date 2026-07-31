"""Pydantic schemas for Device API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    """Schema for creating a new device (POST /devices)."""

    mac: str = Field(..., min_length=12, max_length=17, description="Device MAC address")
    hostname: str = Field(default="", max_length=255)
    ip: str = Field(default="", max_length=15)
    vendor: str = Field(default="", max_length=255)
    friendly_name: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=1000)
    device_type: str = Field(default="unknown")
    os_type: str = Field(default="unknown")
    ttl: int = Field(default=300, ge=30, le=86400)


class DeviceUpdate(BaseModel):
    """Schema for updating an existing device (PUT /devices/{mac})."""

    hostname: str | None = Field(default=None, max_length=255)
    ip: str | None = Field(default=None, max_length=15)
    vendor: str | None = Field(default=None, max_length=255)
    friendly_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    device_type: str | None = None
    os_type: str | None = None
    ttl: int | None = Field(default=None, ge=30, le=86400)


class DeviceResponse(BaseModel):
    """Schema for device API responses."""

    mac: str
    hostname: str
    ip: str
    vendor: str
    first_seen: str
    last_seen: str
    last_source: str
    confidence: int
    status: str
    friendly_name: str
    description: str
    device_type: str
    os_type: str
    ttl: int
    online: bool

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    """Schema for paginated device list response."""

    total: int
    online_count: int
    offline_count: int
    devices: list[DeviceResponse]

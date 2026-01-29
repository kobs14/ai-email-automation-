"""
CRM data models.

Vendor-agnostic dataclasses representing CRM entities.
These models decouple the application from any specific CRM provider,
allowing different backends (HubSpot, Salesforce, Zoho, etc.) to
map to and from the same structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CRMCustomer:
    """
    Represents a customer record in the CRM.

    Attributes:
        crm_id: Identifier in the external CRM system (None if not yet synced).
        email: Customer's email address (primary lookup key).
        name: Full name of the customer.
        phone: Phone number.
        address: Physical / service address.
        segment: Business segment, e.g. "residential", "commercial", "vip".
        lifecycle_stage: e.g. "lead", "customer", "churned".
        tags: Arbitrary labels attached to the customer.
        custom_fields: Provider-specific or user-defined extra fields.
        created_at: When the record was created in the CRM.
        updated_at: When the record was last modified in the CRM.
    """

    email: str
    crm_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    segment: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class CRMInteraction:
    """
    Represents a logged interaction with a customer.

    Attributes:
        interaction_type: Kind of interaction, e.g. "email_received",
            "email_sent", "quote_sent", "booking_created".
        channel: Communication channel, e.g. "email", "phone", "web".
        occurred_at: Timestamp of the interaction.
        subject: Short subject / title (optional).
        summary: Longer description or notes (optional).
        metadata: Flexible payload for extra data such as email_id,
            response_id, quote details, etc.
    """

    interaction_type: str
    channel: str
    occurred_at: datetime
    subject: Optional[str] = None
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CRMDeal:
    """
    Represents a deal / opportunity in the CRM.

    Attributes:
        customer_id: Reference to the associated CRMCustomer (crm_id or email).
        title: Short description of the deal.
        stage: Pipeline stage, e.g. "new", "quoted", "booked",
            "completed", "lost".
        crm_id: Identifier in the external CRM system (None if not yet synced).
        value: Monetary value of the deal.
        currency: ISO 4217 currency code, defaults to "USD".
        service_type: Type of cleaning service requested.
        metadata: Flexible payload for extra data.
        created_at: When the deal was created.
        updated_at: When the deal was last modified.
    """

    customer_id: str
    title: str
    stage: str
    crm_id: Optional[str] = None
    value: Optional[float] = None
    currency: str = "USD"
    service_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

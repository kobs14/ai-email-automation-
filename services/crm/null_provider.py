"""
Null (no-op) CRM provider.

Used as the default when no CRM integration is configured.
Every method returns a safe default value (None, empty list, False)
with debug-level logging, ensuring the rest of the system behaves
identically to a pre-CRM state.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.crm.base import BaseCRMProvider
from services.crm.models import CRMCustomer, CRMDeal, CRMInteraction

logger = logging.getLogger(__name__)


class NullCRMProvider(BaseCRMProvider):
    """No-op CRM provider. Used when no CRM is configured."""

    # ------------------------------------------------------------------
    # Customer operations
    # ------------------------------------------------------------------

    def find_customer_by_email(self, email: str) -> Optional[CRMCustomer]:
        """Return None — no CRM backend to query."""
        logger.debug("NullCRMProvider: find_customer_by_email('%s') → None", email)
        return None

    def find_customer_by_phone(self, phone: str) -> Optional[CRMCustomer]:
        """Return None — no CRM backend to query."""
        logger.debug("NullCRMProvider: find_customer_by_phone('%s') → None", phone)
        return None

    def create_customer(self, customer: CRMCustomer) -> CRMCustomer:
        """Return the input customer unchanged — nothing is persisted."""
        logger.debug("NullCRMProvider: create_customer('%s') → no-op", customer.email)
        return customer

    def update_customer(
        self, crm_id: str, updates: Dict[str, Any]
    ) -> CRMCustomer:
        """Return a stub customer — nothing is persisted."""
        logger.debug("NullCRMProvider: update_customer('%s') → no-op", crm_id)
        return CRMCustomer(email="", crm_id=crm_id)

    def get_or_create_customer(
        self, email: str, defaults: Optional[Dict[str, Any]] = None
    ) -> Tuple[CRMCustomer, bool]:
        """Return a stub customer with created=False — nothing is persisted."""
        logger.debug(
            "NullCRMProvider: get_or_create_customer('%s') → stub, False", email
        )
        return CRMCustomer(email=email), False

    # ------------------------------------------------------------------
    # Interaction logging
    # ------------------------------------------------------------------

    def log_interaction(
        self, customer_id: str, interaction: CRMInteraction
    ) -> bool:
        """Return False — interaction not recorded."""
        logger.debug(
            "NullCRMProvider: log_interaction('%s', type='%s') → False",
            customer_id,
            interaction.interaction_type,
        )
        return False

    def get_customer_interactions(
        self, customer_id: str, limit: int = 20
    ) -> List[CRMInteraction]:
        """Return empty list — no interactions stored."""
        logger.debug(
            "NullCRMProvider: get_customer_interactions('%s') → []", customer_id
        )
        return []

    # ------------------------------------------------------------------
    # Deal / opportunity management
    # ------------------------------------------------------------------

    def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """Return the input deal unchanged — nothing is persisted."""
        logger.debug(
            "NullCRMProvider: create_deal('%s') → no-op", deal.title
        )
        return deal

    def update_deal_stage(self, deal_id: str, stage: str) -> CRMDeal:
        """Return a stub deal — nothing is persisted."""
        logger.debug(
            "NullCRMProvider: update_deal_stage('%s', '%s') → no-op",
            deal_id,
            stage,
        )
        return CRMDeal(customer_id="", title="", stage=stage, crm_id=deal_id)

    def get_deals_for_customer(self, customer_id: str) -> List[CRMDeal]:
        """Return empty list — no deals stored."""
        logger.debug(
            "NullCRMProvider: get_deals_for_customer('%s') → []", customer_id
        )
        return []

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return False — null provider is never 'available'."""
        return False

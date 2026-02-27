"""
Abstract base class for CRM providers.

Defines the contract that every CRM integration must implement.
Concrete providers (HubSpot, Salesforce, Zoho, etc.) subclass
``BaseCRMProvider`` and implement each method.

Integration points (to be wired when a concrete provider is added):
    - After email fetched      -> get_or_create_customer()
    - After entity extraction  -> update_customer()
    - After response sent      -> log_interaction()
    - After quote calculated   -> create_deal()
    - After calendar event     -> update_deal_stage()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from services.crm.models import CRMCustomer, CRMDeal, CRMInteraction


class BaseCRMProvider(ABC):
    """Abstract interface for CRM integration."""

    # ------------------------------------------------------------------
    # Customer operations
    # ------------------------------------------------------------------

    @abstractmethod
    def find_customer_by_email(self, email: str) -> Optional[CRMCustomer]:
        """
        Look up a customer by email address.

        Args:
            email: The email address to search for.

        Returns:
            The matching CRMCustomer, or None if not found.
        """
        ...

    @abstractmethod
    def find_customer_by_phone(self, phone: str) -> Optional[CRMCustomer]:
        """
        Look up a customer by phone number.

        Args:
            phone: The phone number to search for.

        Returns:
            The matching CRMCustomer, or None if not found.
        """
        ...

    @abstractmethod
    def create_customer(self, customer: CRMCustomer) -> CRMCustomer:
        """
        Create a new customer record in the CRM.

        Args:
            customer: The customer data to create.

        Returns:
            The created CRMCustomer (with crm_id populated).

        Raises:
            CRMValidationError: If the customer data is invalid.
            CRMConnectionError: If the CRM is unreachable.
        """
        ...

    @abstractmethod
    def update_customer(self, crm_id: str, updates: Dict[str, Any]) -> CRMCustomer:
        """
        Update an existing customer record.

        Args:
            crm_id: The CRM identifier of the customer to update.
            updates: Dictionary of field names to new values.

        Returns:
            The updated CRMCustomer.

        Raises:
            CRMCustomerNotFoundError: If no customer matches crm_id.
            CRMConnectionError: If the CRM is unreachable.
        """
        ...

    @abstractmethod
    def get_or_create_customer(self, email: str, defaults: Optional[Dict[str, Any]] = None) -> Tuple[CRMCustomer, bool]:
        """
        Find an existing customer by email, or create one with *defaults*.

        Args:
            email: The email address to look up.
            defaults: Field values used when creating a new customer.

        Returns:
            A tuple of (customer, created) where *created* is True when a
            new record was inserted.
        """
        ...

    # ------------------------------------------------------------------
    # Interaction logging
    # ------------------------------------------------------------------

    @abstractmethod
    def log_interaction(self, customer_id: str, interaction: CRMInteraction) -> bool:
        """
        Record an interaction against a customer.

        Args:
            customer_id: The CRM identifier of the customer.
            interaction: The interaction data to log.

        Returns:
            True if the interaction was recorded successfully.
        """
        ...

    @abstractmethod
    def get_customer_interactions(self, customer_id: str, limit: int = 20) -> List[CRMInteraction]:
        """
        Retrieve recent interactions for a customer.

        Args:
            customer_id: The CRM identifier of the customer.
            limit: Maximum number of interactions to return.

        Returns:
            A list of CRMInteraction objects, newest first.
        """
        ...

    # ------------------------------------------------------------------
    # Deal / opportunity management
    # ------------------------------------------------------------------

    @abstractmethod
    def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """
        Create a new deal / opportunity in the CRM.

        Args:
            deal: The deal data to create.

        Returns:
            The created CRMDeal (with crm_id populated).
        """
        ...

    @abstractmethod
    def update_deal_stage(self, deal_id: str, stage: str) -> CRMDeal:
        """
        Move a deal to a new pipeline stage.

        Args:
            deal_id: The CRM identifier of the deal.
            stage: The new stage name.

        Returns:
            The updated CRMDeal.
        """
        ...

    @abstractmethod
    def get_deals_for_customer(self, customer_id: str) -> List[CRMDeal]:
        """
        Retrieve all deals associated with a customer.

        Args:
            customer_id: The CRM identifier of the customer.

        Returns:
            A list of CRMDeal objects.
        """
        ...

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check whether the CRM provider is reachable and operational.

        Returns:
            True if the provider can accept requests, False otherwise.
        """
        ...

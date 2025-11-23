from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import stripe

from correlation import get_request_id
from database import Database

logger = logging.getLogger("rag.billing")


class BillingServiceError(Exception):
    """Raised when billing operations fail."""


class BillingService:
    """
    Thin wrapper around Stripe subscription APIs.

    Responsibilities:
    - Ensure organizations have Stripe customers
    - Create checkout + billing portal sessions
    - Handle webhook events and persist billing status in PostgreSQL
    """

    def __init__(
        self,
        db: Database,
        api_key: str,
        *,
        webhook_secret: Optional[str] = None,
        default_price_id: Optional[str] = None,
        default_success_url: Optional[str] = None,
        default_cancel_url: Optional[str] = None,
        default_portal_return_url: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise BillingServiceError("Stripe API key is required to enable billing.")
        stripe.api_key = api_key
        self.db = db
        self.webhook_secret = webhook_secret
        self.default_price_id = default_price_id
        self.default_success_url = default_success_url
        self.default_cancel_url = default_cancel_url
        self.default_portal_return_url = default_portal_return_url

    async def create_checkout_session(
        self,
        organization_id: str,
        *,
        price_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        org = await self._fetch_org(organization_id)
        customer_id = await self._ensure_customer(org)
        price = price_id or self.default_price_id
        if not price:
            raise BillingServiceError("No Stripe price configured for checkout.")

        request_id = get_request_id()
        metadata = {"organization_id": organization_id}
        if request_id:
            metadata["request_id"] = request_id

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price, "quantity": 1}],
                success_url=success_url or self.default_success_url,
                cancel_url=cancel_url or self.default_cancel_url,
                metadata=metadata,
                subscription_data={"metadata": dict(metadata)},
                client_reference_id=request_id or organization_id,
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            logger.exception("Stripe checkout session creation failed: %s", exc)
            raise BillingServiceError(str(exc)) from exc
        return dict(session)

    async def create_billing_portal_session(
        self,
        organization_id: str,
        *,
        return_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        org = await self._fetch_org(organization_id)
        customer_id = await self._ensure_customer(org)
        try:
            session = stripe.billing_portal.Session.create(  # type: ignore[attr-defined]
                customer=customer_id,
                return_url=return_url or self.default_portal_return_url or self.default_success_url,
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            logger.exception("Stripe billing portal session creation failed: %s", exc)
            raise BillingServiceError(str(exc)) from exc
        return dict(session)

    def construct_event(self, payload: bytes, signature: Optional[str]) -> Dict[str, Any]:
        if not self.webhook_secret:
            raise BillingServiceError("Stripe webhook secret is not configured.")
        try:
            return stripe.Webhook.construct_event(  # type: ignore[attr-defined]
                payload,
                signature,
                self.webhook_secret,
            )
        except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
            logger.warning("Invalid Stripe signature: %s", exc)
            raise BillingServiceError("Invalid Stripe signature.") from exc

    async def handle_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type", "")
        data_object = (event.get("data") or {}).get("object") or {}
        organization_id = await self._resolve_organization_id(event, data_object)

        if organization_id:
            await self._record_event(organization_id, event)

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(organization_id, data_object)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            await self._handle_subscription_update(organization_id, data_object)
        elif event_type == "customer.subscription.deleted":
            await self._update_billing_state(
                organization_id,
                status="canceled",
                stripe_customer_id=data_object.get("customer"),
                subscription_id=data_object.get("id"),
                current_period_end=None,
                trial_end=None,
            )
        elif event_type == "invoice.payment_failed":
            await self._update_billing_state(
                organization_id,
                status="past_due",
                stripe_customer_id=data_object.get("customer"),
                subscription_id=data_object.get("subscription"),
                current_period_end=None,
                trial_end=None,
            )
        else:
            logger.debug("Unhandled Stripe event type=%s", event_type)

    async def _handle_checkout_completed(self, organization_id: Optional[str], session: Dict[str, Any]) -> None:
        if not organization_id:
            logger.warning("Checkout completed without organization metadata.")
            return
        await self._update_billing_state(
            organization_id,
            status="active",
            stripe_customer_id=session.get("customer"),
            subscription_id=session.get("subscription"),
            current_period_end=None,
            trial_end=None,
        )

    async def _handle_subscription_update(self, organization_id: Optional[str], subscription: Dict[str, Any]) -> None:
        if not organization_id:
            organization_id = await self._lookup_org_by_customer(subscription.get("customer"))
        await self._update_billing_state(
            organization_id,
            status=self._normalize_stripe_status(subscription.get("status")),
            stripe_customer_id=subscription.get("customer"),
            subscription_id=subscription.get("id"),
            current_period_end=subscription.get("current_period_end"),
            trial_end=subscription.get("trial_end"),
        )

    async def _fetch_org(self, organization_id: str) -> Dict[str, Any]:
        row = await self.db.fetch_one(
            """
            SELECT id, name, stripe_customer_id
            FROM organizations
            WHERE id = $1
            """,
            (organization_id,),
        )
        if not row:
            raise BillingServiceError(f"Organization {organization_id} not found.")
        return dict(row)

    async def _ensure_customer(self, organization: Dict[str, Any]) -> str:
        customer_id = organization.get("stripe_customer_id")
        if customer_id:
            return customer_id
        request_id = get_request_id()
        try:
            customer = stripe.Customer.create(  # type: ignore[attr-defined]
                name=organization.get("name"),
                metadata=self._customer_metadata(organization.get("id"), request_id),
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            logger.exception("Failed to create Stripe customer: %s", exc)
            raise BillingServiceError(str(exc)) from exc
        customer_id = customer.get("id")
        await self.db.execute(
            """
            UPDATE organizations
            SET stripe_customer_id = $2, billing_updated_at = NOW()
            WHERE id = $1
            """,
            (organization["id"], customer_id),
        )
        return customer_id

    async def _resolve_organization_id(self, event: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
        metadata = payload.get("metadata") or {}
        if metadata.get("organization_id"):
            return metadata["organization_id"]
        customer_id = payload.get("customer")
        if customer_id:
            return await self._lookup_org_by_customer(customer_id)
        return None

    async def _lookup_org_by_customer(self, customer_id: Optional[str]) -> Optional[str]:
        if not customer_id:
            return None
        row = await self.db.fetch_one(
            "SELECT id FROM organizations WHERE stripe_customer_id = $1",
            (customer_id,),
        )
        return row["id"] if row else None

    async def _record_event(self, organization_id: str, event: Dict[str, Any]) -> None:
        try:
            await self.db.execute(
                """
                INSERT INTO organization_billing_events (organization_id, event_id, event_type, payload)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    organization_id,
                    event.get("id"),
                    event.get("type"),
                    json.dumps(event, default=str),
                ),
            )
        except Exception as exc:
            logger.warning("Failed to persist billing event %s: %s", event.get("id"), exc)

    async def _update_billing_state(
        self,
        organization_id: Optional[str],
        *,
        status: str,
        stripe_customer_id: Optional[str],
        subscription_id: Optional[str],
        current_period_end: Optional[int],
        trial_end: Optional[int],
    ) -> None:
        if not organization_id:
            logger.warning("Cannot update billing state without organization_id.")
            return
        subscription_expires_at = self._epoch_to_datetime(current_period_end)
        trial_ends_at = self._epoch_to_datetime(trial_end)

        await self.db.execute(
            """
            UPDATE organizations
            SET
                billing_status = $2,
                stripe_customer_id = COALESCE($3, stripe_customer_id),
                stripe_subscription_id = COALESCE($4, stripe_subscription_id),
                subscription_expires_at = COALESCE($5, subscription_expires_at),
                trial_ends_at = COALESCE($6, trial_ends_at),
                billing_updated_at = NOW()
            WHERE id = $1
            """,
            (
                organization_id,
                status,
                stripe_customer_id,
                subscription_id,
                subscription_expires_at,
                trial_ends_at,
            ),
        )

    @staticmethod
    def _epoch_to_datetime(value: Optional[int]) -> Optional[datetime]:
        if not value:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc)

    @staticmethod
    def _normalize_stripe_status(status: Optional[str]) -> str:
        if not status:
            return "incomplete"
        if status in ("active", "trialing"):
            return status
        if status in ("past_due", "unpaid", "incomplete_expired"):
            return "past_due"
        if status in ("canceled"):
            return "canceled"
        return status

    @staticmethod
    def _customer_metadata(organization_id: Optional[str], request_id: Optional[str]) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        if organization_id:
            metadata["organization_id"] = organization_id
        if request_id:
            metadata["request_id"] = request_id
        return metadata


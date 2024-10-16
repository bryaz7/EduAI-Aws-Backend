import logging
import traceback
from datetime import datetime
from typing import Optional, Dict

import stripe
import os
from flask import jsonify, request

from db.models import Parent, User, PackageGroup, Package, Subscription
from main import app, db

from dotenv import load_dotenv, find_dotenv

from services.notification_service import generate_notification
from utils.auth import validate_token
from utils.exceptions import ItemNotFoundError, NotificationGenerationError, ValidationError

# Configure API key
load_dotenv(find_dotenv())
stripe.api_key = os.getenv('STRIPE_API_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

SUCCESS_URL = os.getenv('SUCCESS_URL')
CANCEL_URL = os.getenv('CANCEL_URL')
RETURN_URL = os.getenv('RETURN_URL')


@app.route('/api/stripe-payment/child/create-checkout-session', methods=['POST'])
@validate_token
def child_create_checkout_session():
    try:
        data = request.get_json()
        package_id = data.get('package_id')
        user_id = data.get('user_id')
        payment_type = data.get('payment_type')

        package = db.session.get(Package, package_id)
        if not package_id:
            return jsonify({'message': 'Package not found'}), 404

        user = db.session.get(User, user_id)
        if not user_id:
            return jsonify({'message': 'User not found'}), 404

        parent = user.parent
        if parent is not None:
            users = parent.users
            if len(users) > 1:
                raise ValidationError(f"Associated parent has more than 1 learner, which is not applied at the moment. "
                                      f"Ask parent to upgrade the package instead.")

        customer_id = user.stripe_client_id
        if not customer_id:
            # Create a new customer on Stripe
            customer_object = stripe.Customer.create(
                address=user.address,
                email=user.email,
                name=user.display_name
            )
            user.stripe_client_id = customer_id = customer_object["id"]
            db.session.commit()

        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                "price": package.stripe_yearly_pay_price_id if payment_type == 'yearly'
                else package.stripe_monthly_pay_price_id,
                "quantity": 1
            }],
            mode='subscription',
            success_url=SUCCESS_URL.format(package_id),
            cancel_url=CANCEL_URL.format(package_id, payment_type),
            customer=customer_id,
            subscription_data={
                "metadata": {
                    "buyer_type": "user",
                    "buyer_id": user_id,
                    "package_id": package_id
                }
            },
            allow_promotion_codes=True,
            consent_collection={
                "terms_of_service": "required"
            }
        )
        return jsonify({'url': checkout_session.url, 'id': checkout_session.id})
    except Exception as e:
        return jsonify({'message': f'An exception occurred during payment: {e}'}), 503


@app.route('/api/stripe-payment/parent/create-checkout-session', methods=['POST'])
@validate_token
def parent_create_checkout_session():
    try:
        data = request.get_json()
        package_id = data.get('package_id')
        parent_id = data.get('parent_id')
        payment_type = data.get('payment_type')

        package = db.session.get(Package, package_id)
        if not package_id:
            return jsonify({'message': 'Package not found'}), 404

        parent = db.session.get(Parent, parent_id)
        if not parent:
            return jsonify({'message': 'Parent not found'}), 404

        users = parent.users
        if len(users) > package.num_learners:
            raise ValidationError(f"The package applies to only {package.num_learners} learner(s), "
                                  f"but parent linked to {len(users)} learner(s).")
        user_ids = [user.id for user in users]

        customer_id = parent.stripe_client_id
        if not customer_id:
            # Create a new customer on Stripe
            customer_object = stripe.Customer.create(
                address=parent.address,
                email=parent.email,
                name=parent.display_name
            )
            parent.stripe_client_id = customer_id = customer_object["id"]
            db.session.commit()

        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                "price": package.stripe_yearly_pay_price_id if payment_type == 'yearly'
                else package.stripe_monthly_pay_price_id,
                "quantity": 1
            }],
            mode='subscription',
            success_url=SUCCESS_URL.format(package_id),
            cancel_url=CANCEL_URL.format(package_id, payment_type),
            customer=customer_id,
            subscription_data={
                "metadata": {
                    "user_ids": ",".join(map(str, user_ids)) if user_ids else "",
                    "package_id": package_id,
                    "buyer_type": "parent",
                    "buyer_id": parent_id
                }
            },
            allow_promotion_codes=True,
            consent_collection={
                "terms_of_service": "required"
            }
        )
        return jsonify({'url': checkout_session.url, 'id': checkout_session.id})
    except Exception as e:
        return jsonify({'message': f'An exception occurred during payment: {e}'}), 503


@app.route('/api/stripe-payment/child/create-portal-session', methods=['POST'])
@validate_token
def child_create_portal_session():
    data = request.get_json()
    user_id = data.get('user_id')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    customer_id = user.stripe_client_id
    if not customer_id:
        # Create a new customer on Stripe
        customer_object = stripe.Customer.create(
            address=user.address,
            email=user.email
        )
        user.stripe_client_id = customer_id = customer_object["id"]
        db.session.commit()

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=RETURN_URL
    )
    return jsonify({'url': portal_session.url})


@app.route('/api/stripe-payment/parent/create-portal-session', methods=['POST'])
@validate_token
def parent_create_portal_session():
    data = request.get_json()
    parent_id = data.get('parent_id')

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    customer_id = parent.stripe_client_id
    if not customer_id:
        # Create a new customer on Stripe
        customer_object = stripe.Customer.create(
            address=parent.address,
            email=parent.email
        )
        parent.stripe_client_id = customer_id = customer_object["id"]
        db.session.commit()

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=RETURN_URL
    )
    return jsonify({'url': portal_session.url})


@app.route('/api/stripe-payment/child/cancel-subscription', methods=['PUT'])
@validate_token
def child_cancel_subscription():
    buyer_type = "user"
    data = request.get_json()
    buyer_id = data.get("user_id")
    package_group_id = data.get("package_group_id")
    if not buyer_id:
        return jsonify({"message": "Missing user_id field"}), 400
    if not package_group_id:
        return jsonify({"message": "Missing package_group_id field"}), 400
    return cancel_subscription(buyer_type, buyer_id, package_group_id)


@app.route('/api/stripe-payment/parent/cancel-subscription', methods=['PUT'])
@validate_token
def parent_cancel_subscription():
    buyer_type = "parent"
    data = request.get_json()
    buyer_id = data.get("parent_id")
    package_group_id = data.get("package_group_id")
    if not buyer_id:
        return jsonify({"message": "Missing parent_id field"}), 400
    if not package_group_id:
        return jsonify({"message": "Missing package_group_id field"}), 400
    return cancel_subscription(buyer_type, buyer_id, package_group_id)


def cancel_subscription(buyer_type, buyer_id, package_group_id):
    package_group = db.session.get(PackageGroup, package_group_id)
    if not package_group:
        return jsonify({"message": "PackageGroup not found"}), 404
    if package_group.cancel_at_period_end:
        return jsonify({"message": "Subscription has already been cancelled to renew."}), 403
    elif package_group.buyer_type == buyer_type and package_group.buyer_id == buyer_id:
        stripe.Subscription.modify(
            sid=package_group.stripe_subscription_id,
            cancel_at_period_end=True
        )
        return jsonify({"message": "Success"})
    else:
        return jsonify({"message": "Specified user is not the owner of the package, cannot cancel."}), 401


@app.route('/api/webhook', methods=['POST'])
def webhook_received():
    request_data = request.get_json()

    if STRIPE_WEBHOOK_SECRET:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=STRIPE_WEBHOOK_SECRET)
            data = event['data']
        except ValueError as e:
            # Invalid payload
            return jsonify({'message': f'Value Error with details: {e}'}), 510
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return jsonify({'message': f'Signature Error with details: {e}'}), 511
        except Exception as e:
            return jsonify({'message': f'Error with details: {e}'}), 512
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        data = request_data['data']
        event_type = request_data['type']
    data_object = data['object']

    try:
        if event_type == 'customer.subscription.created':
            create_package_group(data_object)
        elif event_type == 'customer.subscription.updated':
            update_package_group(data_object)
        elif event_type == 'customer.subscription.deleted':
            update_package_group(data_object)
    except KeyError as e:
        return jsonify({'message': f'Getting a null or error data format from Stripe: {e}'}), 513
    except ItemNotFoundError:
        return jsonify({'message': f'Item not found from the PostgreSQL database'}), 514
    except Exception as e:
        return jsonify({'message': f'Error with details: {e}'}), 515

    return jsonify({'status': 'success'})


def apply_package(buyer_id: int, buyer_type: str, status: str, data: Dict, metadata: Dict, package_group: PackageGroup):
    # Get invoice and payment method
    current_period_start = datetime.fromtimestamp(data.get("current_period_start"))
    current_period_end = datetime.fromtimestamp(data.get("current_period_end"))
    cancel_at_period_end = data.get("cancel_at_period_end")
    invoice = stripe.Invoice.retrieve(data.get('latest_invoice'))
    invoice_id = invoice.get("id")
    payment_method = stripe.PaymentMethod.retrieve(data.get('default_payment_method'))
    reference_number = invoice.get("number")
    total_payment = invoice.get("amount_paid") / 100
    payment_method_val = payment_method.get("type")
    currency = invoice.get("currency")

    # Update information
    package_group.update_fields(
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        reference_number=reference_number,
        total_payment=total_payment,
        payment_method=payment_method_val,
        currency=currency,
        status=status,
        latest_invoice=invoice_id,
        cancel_at_period_end=cancel_at_period_end
    )

    if buyer_type == "parent":
        # Apply package for the parent and their user_ids
        parent_id = buyer_id
        user_ids = metadata.get("user_ids")
        if user_ids is not None:
            user_ids = map(int, user_ids.split(","))
        else:
            user_ids = []

        parent = db.session.get(Parent, parent_id)
        if not parent:
            raise ItemNotFoundError(f"Parent with id {parent_id} not found")
        parent.package_group_id = package_group.id

        for user_id in user_ids:
            user = db.session.get(User, user_id)
            if not user:
                raise ItemNotFoundError(f"User with id {user_id} not found")
            user.package_group_id = package_group.id

        try:
            generate_notification(
                event_code="PARENT_UPGRADE_SUBSCRIPTION_SUCCESS",
                receive_parent_id=parent_id
            )
        except NotificationGenerationError:
            logging.info("Warning: Fail to generate and push notification")

    elif buyer_type == "user":
        # Apply package for the user only
        user_id = buyer_id
        user = db.session.get(User, user_id)
        if not user:
            raise ItemNotFoundError(f"User with id {user_id} not found")
        user.package_group_id = package_group.id
        parent = user.parent
        if parent is not None:
            parent.package_group_id = package_group.id

        try:
            generate_notification(
                event_code="CHILD_UPGRADE_SUBSCRIPTION_SUCCESS",
                receive_user_id=user_id
            )
        except NotificationGenerationError:
            logging.info("Warning: Fail to generate and push notification")

    else:
        raise Exception(f"Buyer type {buyer_type} is not available. It should be either `user` or `parent`")

    db.session.commit()


def create_package_group(data: Dict):
    metadata = data.get('metadata')
    if not metadata:
        return jsonify({'message': 'Metadata does not exist in the payload'})

    buyer_type = metadata.get('buyer_type')
    buyer_id = metadata.get('buyer_id')
    package_id = metadata.get('package_id')

    # Initialize the package information (metadata)
    stripe_subscription_id = data.get('id')
    status = data.get('status')

    # Create new PackageGroup
    package_group = PackageGroup(
        buyer_type=buyer_type,
        buyer_id=buyer_id,
        stripe_subscription_id=stripe_subscription_id
    )
    db.session.add(package_group)
    db.session.flush()

    # Create new Subscription
    subscription = Subscription(
        package_id=package_id,
        package_group_id=package_group.id
    )
    db.session.add(subscription)
    db.session.flush()

    if status == "active":
        apply_package(
            buyer_id=buyer_id,
            buyer_type=buyer_type,
            status=status,
            data=data,
            metadata=metadata,
            package_group=package_group
        )

    db.session.commit()


def handle_cancellation(package_group):
    package_group.update_fields(cancel_at_period_end=True)
    db.session.commit()
    buyer_type = package_group.buyer_type
    buyer_id = package_group.buyer_id
    if buyer_type == "parent":
        try:
            generate_notification(
                event_code="PARENT_CANCEL_SUBSCRIPTION_SUCCESS",
                receive_parent_id=buyer_id
            )
        except NotificationGenerationError:
            logging.warning("Unable to send cancellation notification")
    elif buyer_type == "user":
        try:
            generate_notification(
                event_code="CHILD_CANCEL_SUBSCRIPTION_SUCCESS",
                receive_user_id=buyer_id
            )
        except NotificationGenerationError:
            logging.warning("Unable to send cancellation notification")


def update_package_group(data: Dict):
    stripe_subscription_id = data.get('id')
    # Get PackageGroup by subscription ID
    package_group: Optional[PackageGroup] = db.session.query(PackageGroup) \
        .filter(PackageGroup.stripe_subscription_id == stripe_subscription_id) \
        .first()

    buyer_type = package_group.buyer_type
    buyer_id = package_group.buyer_id
    metadata = data.get('metadata')
    new_cancel_at_period_end = data.get('cancel_at_period_end')
    prev_cancel_at_period_end = package_group.cancel_at_period_end
    new_status = data.get('status')
    prev_status = package_group.status

    if not prev_cancel_at_period_end and new_cancel_at_period_end:
        handle_cancellation(package_group)
    elif new_status == "active":
        apply_package(
            buyer_id=buyer_id,
            buyer_type=buyer_type,
            status=new_status,
            data=data,
            metadata=metadata,
            package_group=package_group
        )
    elif new_status != "active" and prev_status == "active":
        remove_package(
            data=data,
            package_group=package_group
        )
    db.session.commit()


def remove_package(data: Dict, package_group: PackageGroup):
    status = data.get('status')
    package_group.status = status

    # Find all users in this package
    users = package_group.users
    parents = package_group.parents

    for user in users:
        user.package_group_id = None
    for parent in parents:
        parent.package_group_id = None

    db.session.commit()

# services/client_service.py
from app.models.client import Client
from app import db


def find_or_create_client(name, phone_number):
    """
    Looks up a Client by phone_number. If not found, creates a new record
    with the provided name and phone_number. Returns the Client instance.
    """
    existing_client = Client.query.filter_by(phone_number=phone_number).first()
    if existing_client:
        return existing_client

    # If client doesn't exist, create a new one
    new_client = Client(name=name, phone_number=phone_number)
    new_client.save()
    return new_client

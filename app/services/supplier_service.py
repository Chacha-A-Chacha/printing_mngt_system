# services/supplier_service.py
from typing import List, Dict, Optional
from sqlalchemy.exc import IntegrityError
from ..models import Supplier, db

from app import logger


class SupplierService:
    @staticmethod
    def create_supplier(data: dict) -> Supplier:
        """Create a new supplier with validation"""
        logger.info(f"Creating new supplier with data: {data}")

        # Check if supplier exists by phone number
        existing_supplier = Supplier.query.filter_by(
            phone_number=data['phone_number']
        ).first()

        if existing_supplier:
            logger.info(f"Supplier with phone {data['phone_number']} already exists")
            return existing_supplier

        supplier = Supplier(
            name=data['name'],
            phone_number=data['phone_number'],
            contact_info=data.get('contact_info', {}),
            tax_id=data.get('tax_id')
        )

        try:
            supplier.save()
            logger.info(f"Supplier created successfully: {supplier.phone_number}")
            return supplier
        except Exception as e:
            logger.error(f"Error creating supplier: {str(e)}")
            raise

    @staticmethod
    def get_suppliers() -> List[Supplier]:
        """Get all suppliers"""
        return Supplier.query.all()

    @staticmethod
    def get_supplier_by_phone(phone_number: str) -> Optional[Supplier]:
        """Get supplier by phone number"""
        return Supplier.query.filter_by(phone_number=phone_number).first()
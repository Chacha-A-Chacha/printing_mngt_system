from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.materials import Material, MaterialUsage


class MaterialService:
    @staticmethod
    def create_material(data: Dict) -> Material:
        """Create a new material with validation"""
        # Validate required fields
        required_fields = ['material_code', 'name', 'category', 'type',
                           'unit_of_measure', 'min_threshold', 'reorder_quantity',
                           'cost_per_unit', 'supplier_id']

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate numerical values
        if data.get('cost_per_unit', 0) <= 0:
            raise ValueError("Cost per unit must be positive")

        if data.get('min_threshold', 0) < 0:
            raise ValueError("Minimum threshold cannot be negative")

        # Create material instance
        material = Material(
            material_code=data['material_code'],
            name=data['name'],
            category=data['category'],
            type=data['type'],
            unit_of_measure=data['unit_of_measure'],
            min_threshold=data['min_threshold'],
            reorder_quantity=data['reorder_quantity'],
            cost_per_unit=data['cost_per_unit'],
            supplier_id=data['supplier_id'],
            specifications=data.get('specifications', {}),
            stock_level=data.get('stock_level', 0.0)
        )

        try:
            material.save()
            return material
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Material code must be unique")

    @staticmethod
    def get_materials(filters: Optional[Dict] = None) -> List[Material]:
        """Get materials with optional filtering"""
        query = Material.query

        if filters:
            if 'category' in filters:
                query = query.filter_by(category=filters['category'])
            if 'type' in filters:
                query = query.filter_by(type=filters['type'])
            if 'supplier_id' in filters:
                query = query.filter_by(supplier_id=filters['supplier_id'])

        return query.all()

    @staticmethod
    def get_low_stock_materials() -> List[Material]:
        """Get materials below minimum threshold"""
        return Material.query.filter(
            Material.stock_level <= Material.min_threshold
        ).all()

    @staticmethod
    def record_material_usage(data: dict) -> MaterialUsage:
        """
        Records material usage with proper validation and stock management.

        Args:
            data: {
                'material_id': int,
                'job_id': int,
                'quantity_used': float,
                'user_id': int,
                'wastage': float,
                'notes': str
            }
        """
        try:
            # Start database transaction
            with db.session.begin():
                # Fetch material
                material = Material.query.get(data['material_id'])
                if not material:
                    raise ValueError("Material not found")

                quantity = float(data['quantity_used'])
                wastage = float(data.get('wastage', 0.0))
                total_deduction = quantity + wastage

                # Validate quantities
                if quantity <= 0:
                    raise ValueError("Usage quantity must be positive")
                if wastage < 0:
                    raise ValueError("Wastage cannot be negative")

                # Check stock availability
                if material.stock_level < total_deduction:
                    raise ValueError(
                        f"Insufficient stock. Available: {material.stock_level}, Required: {total_deduction}")

                # Create usage record
                usage = MaterialUsage(
                    material_id=material.id,
                    job_id=data['job_id'],
                    quantity_used=quantity,
                    unit_of_measure=material.unit_of_measure,
                    user_id=data['user_id'],
                    wastage=wastage,
                    notes=data.get('notes', '')
                )

                # Update stock level
                material.stock_level -= total_deduction

                # Check if stock level is below threshold after deduction
                if material.stock_level <= material.min_threshold:
                    # You might want to trigger notifications here
                    pass

                # Save both records
                db.session.add(usage)
                db.session.commit()

                return usage

        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def get_material_usage_history(
            material_id: int,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[MaterialUsage]:
        """Get usage history for a specific material"""
        query = MaterialUsage.query.filter_by(material_id=material_id)

        if start_date:
            query = query.filter(MaterialUsage.usage_date >= start_date)
        if end_date:
            query = query.filter(MaterialUsage.usage_date <= end_date)

        return query.order_by(MaterialUsage.usage_date.desc()).all()


    @staticmethod
    def restock_material(data: dict) -> StockTransaction:
        """
        Handle material restocking from supplier deliveries

        Args:
            data: {
                'material_id': int,
                'quantity': float,
                'user_id': int,
                'reference_number': str,  # PO number
                'notes': str
            }
        """
        try:
            with db.session.begin():
                material = Material.query.get(data['material_id'])
                if not material:
                    raise ValueError("Material not found")

                quantity = float(data['quantity'])
                if quantity <= 0:
                    raise ValueError("Restock quantity must be positive")

                previous_stock = material.stock_level
                material.stock_level += quantity

                transaction = StockTransaction(
                    material_id=material.id,
                    transaction_type='RESTOCK',
                    quantity=quantity,
                    previous_stock=previous_stock,
                    new_stock=material.stock_level,
                    user_id=data['user_id'],
                    reference_number=data.get('reference_number'),
                    notes=data.get('notes', '')
                )

                db.session.add(transaction)
                db.session.commit()

                return transaction


    @staticmethod
    def adjust_stock(data: dict) -> StockTransaction:
    """
    Handle stock adjustments (e.g., after inventory count)

    Args:
        data: {
            'material_id': int,
            'new_stock_level': float,
            'user_id': int,
            'reference_number': str,
            'notes': str  # Reason for adjustment
        }
    """
    try:
        with db.session.begin():
            material = Material.query.get(data['material_id'])
            if not material:
                raise ValueError("Material not found")

            new_stock = float(data['new_stock_level'])
            if new_stock < 0:
                raise ValueError("Stock level cannot be negative")

            previous_stock = material.stock_level
            quantity_difference = new_stock - previous_stock

            transaction = StockTransaction(
                material_id=material.id,
                transaction_type='ADJUSTMENT',
                quantity=quantity_difference,
                previous_stock=previous_stock,
                new_stock=new_stock,
                user_id=data['user_id'],
                reference_number=data.get('reference_number'),
                notes=data.get('notes', '')
            )

            material.stock_level = new_stock

            db.session.add(transaction)
            db.session.commit()

            return transaction


        @staticmethod
        def get_stock_transactions(
                material_id: int,
                transaction_type: Optional[str] = None,
                start_date: Optional[datetime] = None,
                end_date: Optional[datetime] = None
        ) -> List[StockTransaction]:
            """Get stock transaction history with filters"""
            query = StockTransaction.query.filter_by(material_id=material_id)

            if transaction_type:
                query = query.filter_by(transaction_type=transaction_type)
            if start_date:
                query = query.filter(StockTransaction.created_at >= start_date)
            if end_date:
                query = query.filter(StockTransaction.created_at <= end_date)

            return query.order_by(StockTransaction.created_at.desc()).all()
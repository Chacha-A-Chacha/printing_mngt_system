from typing import Dict, Any
from datetime import datetime
from io import BytesIO
import csv
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from typing import List, Dict, Optional
from sqlalchemy.exc import IntegrityError

from app import db, logger
from app.models.materials import Material, MaterialUsage, StockTransaction
from app.services.supplier_service import SupplierService


class MaterialService:
    @staticmethod
    def create_material(data: Dict) -> Material:
        """
        Create a new material with validation.
        Automatically creates supplier if it doesn't exist.

        Args:
            data: {
                'material_code': str,
                'name': str,
                'category': str,
                'type': str,
                'unit_of_measure': str,
                'min_threshold': float,
                'reorder_quantity': float,
                'cost_per_unit': float,
                'supplier': {  # Changed from supplier_id to supplier object
                    'name': str,
                    'phone_number': str,
                    'contact_info': dict (optional),
                    'tax_id': str (optional)
                },
                'specifications': dict (optional),
                'stock_level': float (optional)
            }
        Returns:
            Material: Created material instance
        Raises:
            ValueError: If validation fails or required fields are missing
        """
        logger.info(f"Creating new material with data: {data}")

        try:
            # Validate required fields except supplier_id
            required_fields = ['material_code', 'name', 'category', 'type',
                               'unit_of_measure', 'min_threshold', 'reorder_quantity',
                               'cost_per_unit', 'supplier']

            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    raise ValueError(f"Missing required field: {field}")

            # Validate numerical values
            if data.get('cost_per_unit', 0) <= 0:
                raise ValueError("Cost per unit must be positive")

            if data.get('min_threshold', 0) < 0:
                raise ValueError("Minimum threshold cannot be negative")

            # Handle supplier creation/retrieval
            supplier_data = data.pop('supplier')  # Remove supplier from material data
            supplier = SupplierService.create_supplier(supplier_data)

            logger.info(f"Using supplier: {supplier.phone_number}")

            # Create material instance with supplier_id
            material = Material(
                material_code=data['material_code'],
                name=data['name'],
                category=data['category'],
                type=data['type'],
                unit_of_measure=data['unit_of_measure'],
                min_threshold=data['min_threshold'],
                reorder_quantity=data['reorder_quantity'],
                cost_per_unit=data['cost_per_unit'],
                supplier_id=supplier.id,  # Use the supplier id
                specifications=data.get('specifications', {}),
                stock_level=data.get('stock_level', 0.0)
            )
            logger.info(f"Material instance created: {material.material_code}")

            try:
                material.save()
                logger.info(f"Material saved successfully: {material.material_code}")
                return material
            except IntegrityError as e:
                logger.error(f"Integrity error: {str(e)}")
                if "unique constraint" in str(e).lower():
                    raise ValueError("Material code must be unique")
                raise ValueError("Database integrity error")

        except Exception as e:
            logger.error(f"Error in create_material: {str(e)}")
            raise

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
    def get_material_by_code(material_code: str) -> Optional[Material]:
        """Get material by unique code"""
        return Material.query.filter_by(material_code=material_code).first()

    @staticmethod
    def search_materials(
            search_term: str,
            category: Optional[str] = None,
            supplier_id: Optional[int] = None
    ) -> List[Material]:
        """Search materials by name or code"""
        query = Material.query

        if search_term:
            search = f"%{search_term}%"
            query = query.filter(
                db.or_(
                    Material.name.ilike(search),
                    Material.material_code.ilike(search)
                )
            )

        if category:
            query = query.filter_by(category=category)
        if supplier_id:
            query = query.filter_by(supplier_id=supplier_id)

        return query.all()

    @staticmethod
    def record_material_usage(data: dict) -> MaterialUsage:
        """Records material usage"""
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
            raise ValueError(f"Insufficient stock. Available: {material.stock_level}, Required: {total_deduction}")

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

        # Save both changes using the model's save method
        material.save()  # This handles its own transaction
        usage.save()  # This handles its own transaction

        return usage

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

        # Use model's save methods
        material.save()
        transaction.save()

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

        # Use model's save methods
        material.save()
        transaction.save()

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


class ReportingService:
    @staticmethod
    def _generate_pdf(data: dict) -> BytesIO:
        """Generate PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Add title
        title = "Material Report"
        elements.append(Paragraph(title, styles['Heading1']))
        elements.append(Spacer(1, 12))

        # Add metadata
        if 'total_usage' in data:  # Usage report
            metadata = [
                f"Total Usage: {data['total_usage']}",
                f"Total Wastage: {data['total_wastage']}",
                f"Efficiency Rate: {data['efficiency_rate']:.2f}%"
            ]
        else:  # Stock report
            metadata = [
                f"Total Value: ${data['total_value']:.2f}",
                f"Last Updated: {data['last_updated']}"
            ]

        for meta in metadata:
            elements.append(Paragraph(meta, styles['Normal']))
        elements.append(Spacer(1, 12))

        # Create table data
        if data['items']:
            # Get headers from first item
            headers = list(data['items'][0].keys())
            table_data = [headers]

            # Add rows
            for item in data['items']:
                row = [str(item[header]) for header in headers]
                table_data.append(row)

            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _generate_csv(data: dict) -> BytesIO:
        """Generate CSV report"""
        buffer = BytesIO()

        if data['items']:
            # Get headers from first item
            headers = list(data['items'][0].keys())

            # Write to CSV
            writer = csv.DictWriter(buffer, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data['items'])

        buffer.seek(0)
        return buffer

    @staticmethod
    def _generate_excel(data: dict) -> BytesIO:
        """Generate Excel report"""
        buffer = BytesIO()

        # Create Excel writer
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Convert items to DataFrame
            df = pd.DataFrame(data['items'])
            df.to_excel(writer, sheet_name='Data', index=False)

            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Data']

            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4F81BD',
                'font_color': 'white'
            })

            # Format headers
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 15)  # Set column width

            # Add summary sheet if available
            if 'summary' in data:
                summary_df = pd.DataFrame([data['summary']])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Add metadata sheet
            metadata = {}
            if 'total_usage' in data:  # Usage report
                metadata = {
                    'Total Usage': data['total_usage'],
                    'Total Wastage': data['total_wastage'],
                    'Efficiency Rate': f"{data['efficiency_rate']:.2f}%"
                }
            else:  # Stock report
                metadata = {
                    'Total Value': f"${data['total_value']:.2f}",
                    'Last Updated': data['last_updated']
                }

            pd.DataFrame([metadata]).to_excel(
                writer,
                sheet_name='Metadata',
                index=False
            )

        buffer.seek(0)
        return buffer

    @staticmethod
    def get_stock_report_data(params: dict) -> Dict[str, Any]:
        """Get stock report data for both display and file generation"""
        data = {}

        # Get base data based on report type
        if params['report_type'] == "CURRENT_STOCK":
            items = StockReportingService._get_current_stock_data(
                category=params.get('category'),
                supplier_id=params.get('supplier_id')
            )
        elif params['report_type'] == "BELOW_THRESHOLD":
            items = StockReportingService._get_below_threshold_data()
        elif params['report_type'] == "STOCK_HISTORY":
            items = StockReportingService._get_stock_history_data(
                params['start_date'],
                params['end_date']
            )

        # Apply sorting
        items = StockReportingService._sort_data(
            items,
            params['sort_by'],
            params['sort_order']
        )

        # Generate chart data
        chart_data = StockReportingService._generate_chart_data(items)

        return {
            'items': items,
            'total_value': sum(item['value'] for item in items),
            'last_updated': datetime.now(),
            'chart_data': chart_data
        }

    @staticmethod
    def get_usage_report_data(params: dict) -> Dict[str, Any]:
        """Get usage report data for both display and file generation"""
        data = {}

        # Get base data
        items = UsageReportingService._get_usage_data(
            start_date=params['start_date'],
            end_date=params['end_date'],
            material_id=params.get('material_id'),
            job_id=params.get('job_id'),
            group_by=params['group_by']
        )

        # Calculate summary statistics
        total_usage = sum(item['quantity_used'] for item in items)
        total_wastage = sum(item['wastage'] for item in items)

        # Generate chart data
        chart_data = UsageReportingService._generate_chart_data(
            items,
            params['group_by']
        )

        # Generate summary insights
        summary = UsageReportingService._generate_summary(items)

        return {
            'items': items,
            'total_usage': total_usage,
            'total_wastage': total_wastage,
            'efficiency_rate': ((total_usage - total_wastage) / total_usage * 100)
            if total_usage > 0 else 100,
            'chart_data': chart_data,
            'summary': summary
        }

    @staticmethod
    def generate_report_file(data: dict, format_type: str) -> BytesIO:
        """Generate report file in specified format"""
        if format_type == 'PDF':
            return ReportingService._generate_pdf(data)
        elif format_type == 'CSV':
            return ReportingService._generate_csv(data)
        else:  # EXCEL
            return ReportingService._generate_excel(data)


class StockReportingService:
    @staticmethod
    def _get_current_stock_data(category=None, supplier_id=None):
        """Get current stock levels with filtering"""
        query = Material.query

        if category:
            query = query.filter_by(category=category)
        if supplier_id:
            query = query.filter_by(supplier_id=supplier_id)

        materials = query.all()

        return [{
            'material_code': m.material_code,
            'name': m.name,
            'category': m.category,
            'current_stock': m.stock_level,
            'min_threshold': m.min_threshold,
            'unit': m.unit_of_measure,
            'value': m.stock_level * m.cost_per_unit,
            'status': 'LOW' if m.stock_level <= m.min_threshold else 'HEALTHY'
        } for m in materials]

    @staticmethod
    def _generate_chart_data(items: list) -> dict:
        """Generate chart data for stock reports"""
        return {
            'stock_levels': {
                'labels': [item['name'] for item in items],
                'datasets': [{
                    'label': 'Current Stock',
                    'data': [item['current_stock'] for item in items]
                }]
            },
            'categories': {
                'labels': list(set(item['category'] for item in items)),
                'data': [
                    sum(1 for item in items if item['category'] == cat)
                    for cat in set(item['category'] for item in items)
                ]
            },
            'values': {
                'labels': [item['name'] for item in items],
                'data': [item['value'] for item in items]
            }
        }

    @staticmethod
    def _get_below_threshold_data():
        """Get materials below minimum threshold"""
        materials = Material.query.filter(
            Material.stock_level <= Material.min_threshold
        ).all()

        return [{
            'material_code': m.material_code,
            'name': m.name,
            'category': m.category,
            'current_stock': m.stock_level,
            'min_threshold': m.min_threshold,
            'unit': m.unit_of_measure,
            'value': m.stock_level * m.cost_per_unit,
            'status': 'LOW',
            'reorder_quantity': m.reorder_quantity
        } for m in materials]

    @staticmethod
    def _get_stock_history_data(start_date, end_date):
        """Get stock level history within date range"""
        transactions = StockTransaction.query.filter(
            StockTransaction.created_at.between(start_date, end_date)
        ).order_by(StockTransaction.created_at).all()

        return [{
            'date': tx.created_at.strftime('%Y-%m-%d'),
            'material_code': tx.material.material_code,
            'name': tx.material.name,
            'transaction_type': tx.transaction_type,
            'quantity': tx.quantity,
            'previous_stock': tx.previous_stock,
            'new_stock': tx.new_stock,
            'reference_number': tx.reference_number,
            'unit': tx.material.unit_of_measure
        } for tx in transactions]

    @staticmethod
    def _sort_data(items, sort_by, sort_order):
        """Sort data based on specified field and order"""
        reverse = sort_order == 'desc'
        return sorted(items, key=lambda x: x[sort_by], reverse=reverse)


class UsageReportingService:
    @staticmethod
    def _get_usage_data(start_date, end_date, material_id=None,
                        job_id=None, group_by='day'):
        """Get usage data with filtering and grouping"""
        query = MaterialUsage.query.filter(
            MaterialUsage.usage_date.between(start_date, end_date)
        )

        if material_id:
            query = query.filter_by(material_id=material_id)
        if job_id:
            query = query.filter_by(job_id=job_id)

        usages = query.all()

        # Group data if required
        if group_by in ['week', 'month']:
            # Implementation of grouping logic
            pass

        return [{
            'date': usage.usage_date.strftime('%Y-%m-%d'),
            'material_id': usage.material_id,
            'material_name': usage.material.name,
            'job_id': usage.job_id,
            'quantity_used': usage.quantity_used,
            'wastage': usage.wastage,
            'efficiency_rate': (
                (usage.quantity_used - usage.wastage) / usage.quantity_used * 100
                if usage.quantity_used > 0 else 100
            )
        } for usage in usages]

    @staticmethod
    def _generate_chart_data(items: list, group_by: str) -> dict:
        """Generate chart data for usage reports"""
        # Group data by date
        dates = sorted(set(item['date'] for item in items))
        materials = sorted(set(item['material_name'] for item in items))

        return {
            'timeline': {
                'labels': dates,
                'datasets': [
                    {
                        'label': 'Usage',
                        'data': [sum(item['quantity_used']
                                     for item in items if item['date'] == date)
                                 for date in dates]
                    },
                    {
                        'label': 'Wastage',
                        'data': [sum(item['wastage']
                                     for item in items if item['date'] == date)
                                 for date in dates]
                    }
                ]
            },
            'materials': {
                'labels': materials,
                'data': [sum(item['quantity_used']
                             for item in items if item['material_name'] == material)
                         for material in materials]
            },
            'wastage': {
                'labels': materials,
                'data': [sum(item['wastage']
                             for item in items if item['material_name'] == material)
                         for material in materials]
            }
        }

    @staticmethod
    def _generate_summary(items: list) -> dict:
        """Generate summary statistics for usage report"""
        # Group by material
        material_usage = {}
        for item in items:
            if item['material_name'] not in material_usage:
                material_usage[item['material_name']] = {
                    'quantity': 0,
                    'wastage': 0
                }
            material_usage[item['material_name']]['quantity'] += item['quantity_used']
            material_usage[item['material_name']]['wastage'] += item['wastage']

        # Find most used material
        most_used = max(material_usage.items(),
                        key=lambda x: x[1]['quantity'])

        # Find highest wastage
        highest_wastage = max(material_usage.items(),
                              key=lambda x: x[1]['wastage'])

        # Find peak usage day
        daily_usage = {}
        for item in items:
            if item['date'] not in daily_usage:
                daily_usage[item['date']] = 0
            daily_usage[item['date']] += item['quantity_used']

        peak_usage = max(daily_usage.items(), key=lambda x: x[1])

        return {
            'most_used': {
                'name': most_used[0],
                'quantity': most_used[1]['quantity'],
                'percentage': (most_used[1]['quantity'] /
                               sum(m['quantity'] for m in material_usage.values()) * 100)
            },
            'highest_wastage': {
                'material': highest_wastage[0],
                'quantity': highest_wastage[1]['wastage'],
                'percentage': (highest_wastage[1]['wastage'] /
                               sum(m['wastage'] for m in material_usage.values()) * 100)
            },
            'peak_usage': {
                'date': peak_usage[0],
                'quantity': peak_usage[1]
            }
        }

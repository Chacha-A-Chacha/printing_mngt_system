# models/user.py
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from . import BaseModel
from .. import db


class Role(BaseModel):
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.JSON, nullable=True)  # Store role permissions as JSON

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions
        }


class User(BaseModel):
    __tablename__ = 'users'

    # Basic Info
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Personal Info
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))

    # Status and Security
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)

    # Role-based Access Control
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role = db.relationship('Role', backref=db.backref('users', lazy=True))

    # Additional Info
    department = db.Column(db.String(50))
    position = db.Column(db.String(50))
    employee_id = db.Column(db.String(50), unique=True)

    # Settings and Preferences
    preferences = db.Column(db.JSON, nullable=True)
    notification_settings = db.Column(db.JSON, nullable=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        self.last_login = datetime.now()
        self.save()

    def has_permission(self, permission):
        if not self.role or not self.role.permissions:
            return False
        return permission in self.role.permissions

    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'department': self.department,
            'position': self.position,
            'employee_id': self.employee_id,
            'role': self.role.serialize() if self.role else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<User {self.username}>'


# Pre-defined roles
DEFAULT_ROLES = [
    {
        'name': 'admin',
        'description': 'Full system access',
        'permissions': ['all']
    },
    {
        'name': 'manager',
        'description': 'Management access',
        'permissions': [
            'view_reports',
            'manage_materials',
            'manage_users',
            'approve_orders'
        ]
    },
    {
        'name': 'operator',
        'description': 'Basic operations access',
        'permissions': [
            'view_materials',
            'record_usage',
            'view_own_reports'
        ]
    },
    {
        'name': 'store_keeper',
        'description': 'Inventory management access',
        'permissions': [
            'manage_materials',
            'view_reports',
            'restock_materials',
            'adjust_stock'
        ]
    }
]


def init_roles(app):
    """Initialize default roles in the database"""
    try:
        # Check if roles already exist
        if Role.query.first() is not None:
            app.logger.info("Roles already initialized")
            return

        for role_data in DEFAULT_ROLES:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            try:
                role.save()  # Using BaseModel's save method
                app.logger.info(f"Role '{role.name}' created successfully")
            except Exception as e:
                app.logger.error(f"Error creating role '{role_data['name']}': {str(e)}")
                raise

        app.logger.info("Successfully initialized default roles")

    except Exception as e:
        app.logger.error(f"Error initializing roles: {str(e)}")
        raise

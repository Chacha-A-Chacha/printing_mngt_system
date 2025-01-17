from datetime import datetime
from typing import Optional, List
from app.models import Job
from app.models.machine import Machine, MachineReading
from app import logger


class MachineService:
    """Service for handling machine-related operations"""

    @staticmethod
    def create_machine(data: dict) -> Machine:
        """
        Create a new machine

        Args:
            data: Dictionary containing machine data

        Returns:
            Created Machine instance

        Raises:
            ValueError: If validation fails
        """
        try:
            machine = Machine(**data)
            machine.save()
            logger.info(f"Created new machine: {machine}")
            return machine
        except Exception as e:
            logger.error(f"Error creating machine: {str(e)}")
            raise ValueError(f"Failed to create machine: {str(e)}")

    @staticmethod
    def get_machine(machine_id: int) -> Optional[Machine]:
        """Get a machine by ID"""
        return Machine.get_by_id(machine_id)

    @staticmethod
    def update_machine(machine_id: int, data: dict) -> Machine:
        """Update a machine's details"""
        machine = Machine.get_by_id(machine_id)
        if not machine:
            raise ValueError(f"Machine with ID {machine_id} not found")

        for key, value in data.items():
            setattr(machine, key, value)

        machine.save()
        return machine


class MachineReadingService:
    """Service for handling machine reading operations"""

    @staticmethod
    def create_reading(data: dict) -> MachineReading:
        """
        Create a new machine reading

        Args:
            data: Dictionary containing reading data including:
                - job_id: ID of the job
                - machine_id: ID of the machine
                - start_meter: Initial meter reading
                - end_meter: Final meter reading
                - operator_id: Optional operator ID

        Returns:
            Created MachineReading instance

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate meter readings
            if data['end_meter'] < data['start_meter']:
                raise ValueError("End meter reading cannot be less than start meter reading")

            # Ensure job exists
            job = Job.get_by_id(data['job_id'])
            if not job:
                raise ValueError(f"Job with ID {data['job_id']} not found")

            # Ensure machine exists
            machine = Machine.get_by_id(data['machine_id'])
            if not machine:
                raise ValueError(f"Machine with ID {data['machine_id']} not found")

            reading = MachineReading(**data)
            reading.save()

            logger.info(f"Created new machine reading: {reading}")
            return reading

        except Exception as e:
            logger.error(f"Error creating machine reading: {str(e)}")
            raise ValueError(f"Failed to create machine reading: {str(e)}")

    @staticmethod
    def get_job_readings(job_id: int) -> List[MachineReading]:
        """Get all machine readings for a specific job"""
        return MachineReading.query.filter_by(job_id=job_id).all()

    @staticmethod
    def get_machine_readings(
            machine_id: int,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[MachineReading]:
        """Get machine readings for a specific machine within a date range"""
        query = MachineReading.query.filter_by(machine_id=machine_id)

        if start_date:
            query = query.filter(MachineReading.created_at >= start_date)
        if end_date:
            query = query.filter(MachineReading.created_at <= end_date)

        return query.order_by(MachineReading.created_at.desc()).all()

    @staticmethod
    def get_machine_total_usage(
            machine_id: int,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> float:
        """Calculate total machine usage within a date range"""
        readings = MachineReadingService.get_machine_readings(
            machine_id, start_date, end_date
        )
        return sum(reading.calculate_meter_difference() for reading in readings)

    @staticmethod
    def delete_reading(reading_id: int) -> None:
        """Delete a machine reading"""
        reading = MachineReading.get_by_id(reading_id)
        if not reading:
            raise ValueError(f"Reading with ID {reading_id} not found")

        reading.delete()

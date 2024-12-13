# services/job_service.py

from app.models.in_house_printing import Material, MachineReading


class MaterialService:
    @staticmethod
    def check_stock_levels():
        low_stock_materials = Material.query.filter(Material.stock_level < Material.min_threshold).all()
        return low_stock_materials

    @staticmethod
    def deduct_material_usage(material_id, usage_amount):
        material = Material.query.get(material_id)
        if material:
            material.stock_level -= usage_amount
            material.save()


class MachineUsageService:
    @staticmethod
    def calculate_material_usage(start_meter, end_meter, material_margin=0.05):
        total_meters = end_meter - start_meter
        material_usage = total_meters * (1 + material_margin)
        return material_usage

    @staticmethod
    def log_machine_usage(job_id, start_meter, end_meter, material_id):
        material_usage = MachineUsageService.calculate_material_usage(start_meter, end_meter)
        MachineReading(
            job_id=job_id,
            start_meter=start_meter,
            end_meter=end_meter,
            material_usage=material_usage
        ).save()

        MaterialService.deduct_material_usage(material_id, material_usage)
        return material_usage

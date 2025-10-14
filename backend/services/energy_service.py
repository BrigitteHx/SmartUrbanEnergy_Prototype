from datetime import datetime, timedelta
from database import db
from models import Area, LightingUnit, EnergyConsumptionData, Recommendation
from sqlalchemy import func, extract
import random

def get_aggregated_energy_data(area_id, period_str):
    area = Area.query.get(area_id)
    if not area:
        return None, "Area not found"
    
    end_time = datetime.now()
    
    # Bepaal start_time en aggregation_interval/time_format_str
    if period_str == 'day':
        start_time = end_time - timedelta(hours=24)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'HH24:00:00')
    elif period_str == 'month':
        start_time = end_time - timedelta(days=30)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
    else: # Default is 'week'
        start_time = end_time - timedelta(days=7)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')

    # Query voor geaggregeerd verbruik
    aggregated_consumption = db.session.query(
        aggregation_interval.label('interval_start'),
        func.sum(EnergyConsumptionData.consumption_kwh).label('total_consumption')
    ).join(LightingUnit).filter(
        LightingUnit.area_id == area_id,
        EnergyConsumptionData.timestamp >= start_time,
        EnergyConsumptionData.timestamp <= end_time
    ).group_by(
        'interval_start'
    ).order_by(
        'interval_start'
    ).all()
    
    formatted_data = []
    for row in aggregated_consumption:
        formatted_data.append({
            "timestamp": row.interval_start, 
            "consumption_kwh": row.total_consumption,
        })
    
    # Simulatie voor inefficiëntie markering 
    inefficiency_data_query = db.session.query(
        aggregation_interval.label('interval_start'),
        func.sum(EnergyConsumptionData.consumption_kwh).label('inefficient_consumption')
    ).join(LightingUnit).filter(
        LightingUnit.area_id == area_id,
        EnergyConsumptionData.timestamp >= start_time,
        EnergyConsumptionData.timestamp <= end_time,
        EnergyConsumptionData.status_recording == 'Daylight_Inefficiency'
    ).group_by(
        'interval_start'
    ).order_by(
        'interval_start'
    ).all()

    inefficiency_markers = []
    for row in inefficiency_data_query:
        inefficiency_markers.append({
            "timestamp": row.interval_start, 
            "consumption_kwh": row.inefficient_consumption
        })
    
    total_consumption_kwh = sum([d['consumption_kwh'] for d in formatted_data]) if formatted_data else 0.0

    return {
        "area_id": area_id,
        "area_name": area.name,
        "total_consumption_kwh": total_consumption_kwh,
        "chart_data": formatted_data,
        "inefficiency_markers": inefficiency_markers
    }, None

def get_area_recommendation(area_id):
    area = Area.query.get(area_id)
    if not area:
        return None, "Area not found"

    existing_rec = Recommendation.query.filter_by(
        area_id=area_id, 
        title='Optimaliseer Schakeltijden Openbare Verlichting'
    ).first()
    
    if existing_rec:
        rec_data = {
            "title": existing_rec.title,
            "description": existing_rec.description,
            "potential_savings_kwh": existing_rec.potential_savings_kwh,
            "potential_savings_euro": existing_rec.potential_savings_euro,
            "percentage_savings": existing_rec.potential_savings_kwh / 50 * 100 if existing_rec.potential_savings_kwh else 0 
        }
    else:
        potential_kwh_per_month = random.uniform(25.0, 75.0) 
        potential_euro_per_month = round(potential_kwh_per_month * 0.40, 2)

        new_rec = Recommendation(
            area_id=area_id,
            date_generated=datetime.now().date(),
            title='Optimaliseer Schakeltijden Openbare Verlichting',
            description='Onnodig energieverbruik gedetecteerd door straatverlichting die onnodig lang aanstaat of niet meeschaalt met de daglichturen. Door schakeltijden aan te passen of te dimmen tussen 07:00 en 18:00 uur kan significant bespaard worden.',
            potential_savings_kwh=potential_kwh_per_month,
            potential_savings_euro=potential_euro_per_month,
            action_status='Nieuw'
        )
        db.session.add(new_rec)
        db.session.commit()
        rec_data = {
            "title": new_rec.title,
            "description": new_rec.description,
            "potential_savings_kwh": new_rec.potential_savings_kwh,
            "potential_savings_euro": new_rec.potential_savings_euro,
            "percentage_savings": new_rec.potential_savings_kwh / 50 * 100 
        }

    return rec_data, None

def get_simulated_savings_scenario(area_id, period_str):
    area = Area.query.get(area_id)
    if not area:
        return None, "Area not found"
    
    end_time = datetime.now()
    if period_str == 'day':
        start_time = end_time - timedelta(hours=24)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'HH24:00:00')
    elif period_str == 'month':
        start_time = end_time - timedelta(days=30)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
    else: # Default is 'week'
        start_time = end_time - timedelta(days=7)
        aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
            
    # Haal het verbruiksprofiel op
    actual_consumption_query = db.session.query(
        aggregation_interval.label('interval_start'),
        func.sum(EnergyConsumptionData.consumption_kwh).label('total_consumption')
    ).join(LightingUnit).filter(
        LightingUnit.area_id == area_id,
        EnergyConsumptionData.timestamp >= start_time,
        EnergyConsumptionData.timestamp <= end_time
    ).group_by(
        'interval_start'
    ).order_by(
        'interval_start'
    ).all()
    
    actual_consumption_map = {row.interval_start: row.total_consumption for row in actual_consumption_query}

    inefficient_consumption_query = db.session.query(
        aggregation_interval.label('interval_start'),
        func.sum(EnergyConsumptionData.consumption_kwh).label('inefficient_kwh')
    ).join(LightingUnit).filter(
        LightingUnit.area_id == area_id,
        EnergyConsumptionData.timestamp >= start_time,
        EnergyConsumptionData.timestamp <= end_time,
        EnergyConsumptionData.status_recording == 'Daylight_Inefficiency'
    ).group_by(
        'interval_start'
    ).order_by(
        'interval_start'
    ).all()
    
    inefficient_consumption_map = {row.interval_start: row.inefficient_kwh for row in inefficient_consumption_query}

    # Simuleer de besparing per interval: trek het inefficiënte deel af
    savings_scenario_data = []
    all_intervals = sorted(actual_consumption_map.keys())

    for interval_start_str in all_intervals:
        actual_kwh = actual_consumption_map.get(interval_start_str, 0.0)
        inefficient_kwh_for_interval = inefficient_consumption_map.get(interval_start_str, 0.0)
        
        new_kwh = actual_kwh - inefficient_kwh_for_interval
        if new_kwh < 0: new_kwh = 0

        savings_scenario_data.append({
            "timestamp": interval_start_str,
            "consumption_kwh": new_kwh,
        })

    return savings_scenario_data, None
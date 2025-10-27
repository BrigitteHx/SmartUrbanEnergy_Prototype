# backend/seed_data.py

from datetime import datetime, timedelta
import random
from database import db # Importeer db uit database.py
from models import City, Area, LightingUnit, EnergyConsumptionData, Recommendation
from sqlalchemy import func

# De seed functie hoeft de app niet meer als argument te krijgen, 
# omdat we deze nu aanroepen binnen app.app_context() in app.py
def seed_initial_data(): 
    # --- Controleer en voeg Cities and Areas toe ---
    if not City.query.first():
        print("Adding demo City and Area data...")
        dutch_capitals = [
            "Amsterdam", "2Rotterdam", "Den Haag", "Utrecht", "Groningen", 
            "Leeuwarden", "Arnhem", "Zwolle", "Middelburg", "Maastricht", 
            "Haarlem", "'s-Hertogenbosch", "Lelystad", "Assen"
        ]
        for capital_name in dutch_capitals:
            city = City(name=capital_name)
            db.session.add(city)
            db.session.commit() 
            area = Area(city_id=city.id, name=f'Centrum {capital_name}', description=f'Hoofdgebied van {capital_name}')
            db.session.add(area)
        db.session.commit()
        print(f"Demo Cities and Areas added ({len(dutch_capitals)} total).")
    else:
        print("City and Area data already exists, skipping demo data insertion.")

    # --- Controleer en voeg LightingUnits toe (indien nog niet aanwezig) ---
    if not LightingUnit.query.first():
        print("Adding demo LightingUnits for all areas...")
        all_areas = Area.query.all()
        for area in all_areas:
            lu1 = LightingUnit(area=area, unit_type='LED', location=f'Hoofdstraat {area.name}', power_watt=50)
            lu2 = LightingUnit(area=area, unit_type='LED', location=f'Kerklaan {area.name}', power_watt=50)
            lu3 = LightingUnit(area=area, unit_type='Hogedruk Natrium', location=f'Marktplein {area.name}', power_watt=100)
            db.session.add_all([lu1, lu2, lu3])
        db.session.commit()
        print("Demo LightingUnits added.")
    else:
        print("LightingUnits already exist.")
        

    # --- Energieverbruiksdata genereren of aanvullen ---
    # We willen data genereren tot het huidige uur (afgerond op uur)
    generate_until_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Bepaal het meest recente tijdstip van bestaande data
    max_existing_timestamp = db.session.query(func.max(EnergyConsumptionData.timestamp)).scalar()
    
    all_lighting_units_db = LightingUnit.query.all()
    if not all_lighting_units_db:
        print("No lighting units found, cannot generate consumption data.")
        return

    # Scenario 1: Geen data, of data is veel te oud (meer dan 2 dagen oud)
    # Volledige hergeneratie van ~40 dagen data tot nu
    if not max_existing_timestamp or max_existing_timestamp < (generate_until_time - timedelta(days=2)):
        print("No recent consumption data found or data is too old. Deleting existing consumption data and generating new data for ~40 days up to now...")
        EnergyConsumptionData.query.delete() # Verwijder alle oude verbruiksdata
        db.session.commit()
        
        start_simulation_time = generate_until_time - timedelta(days=40)
        
        for lu in all_lighting_units_db:
            current_time = start_simulation_time
            while current_time <= generate_until_time:
                consumption = 0.0
                status = 'Normal'

                if (current_time.hour >= 18 or current_time.hour < 7) or lu.unit_type == 'Hogedruk Natrium':
                    base_consumption = (lu.power_watt / 1000) * random.uniform(0.2, 0.5)
                    consumption = base_consumption
                    if lu.unit_type == 'Hogedruk Natrium' and (current_time.hour >= 7 and current_time.hour < 18):
                        status = 'Daylight_Inefficiency'
                    elif current_time.hour >= 7 and current_time.hour < 18:
                        status = 'Daylight_Off'
                
                consumption += random.uniform(-consumption * 0.1, consumption * 0.1)
                if consumption < 0: consumption = 0
                
                data_entry = EnergyConsumptionData(
                    lighting_unit=lu,
                    timestamp=current_time,
                    consumption_kwh=consumption,
                    status_recording=status
                )
                db.session.add(data_entry)
                current_time += timedelta(hours=1)
        db.session.commit()
        print("Demo EnergyConsumptionData generated up to current hour for all lighting units.")
    
    # Scenario 2: Data is aanwezig, maar niet up-to-date tot het huidige uur
    elif max_existing_timestamp < generate_until_time:
        print(f"Existing data ends at {max_existing_timestamp}. Generating supplementary data up to current hour...")
        start_new_data_generation = max_existing_timestamp + timedelta(hours=1)
        
        for lu in all_lighting_units_db:
            current_time = start_new_data_generation
            while current_time <= generate_until_time:
                consumption = 0.0
                status = 'Normal'

                if (current_time.hour >= 18 or current_time.hour < 7) or lu.unit_type == 'Hogedruk Natrium':
                    base_consumption = (lu.power_watt / 1000) * random.uniform(0.2, 0.5)
                    consumption = base_consumption
                    if lu.unit_type == 'Hogedruk Natrium' and (current_time.hour >= 7 and current_time.hour < 18):
                        status = 'Daylight_Inefficiency'
                    elif current_time.hour >= 7 and current_time.hour < 18:
                        status = 'Daylight_Off'
                
                consumption += random.uniform(-consumption * 0.1, consumption * 0.1)
                if consumption < 0: consumption = 0
                
                data_entry = EnergyConsumptionData(
                    lighting_unit=lu,
                    timestamp=current_time,
                    consumption_kwh=consumption,
                    status_recording=status
                )
                db.session.add(data_entry)
                current_time += timedelta(hours=1)
        db.session.commit()
        print("Supplementary EnergyConsumptionData generated.")
    else:
        print("EnergyConsumptionData is already up-to-date.")
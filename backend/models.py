from datetime import datetime, timedelta
from database import db 
from sqlalchemy import func 

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    areas = db.relationship('Area', backref='city', lazy=True, cascade='all, delete-orphan') 

    def __repr__(self):
        return f"<City {self.name}>"

class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False) 
    description = db.Column(db.Text)
    
    lighting_units = db.relationship('LightingUnit', backref='area', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Area {self.name} in City {self.city.name}>"

class LightingUnit(db.Model):
    __tablename__ = 'lighting_units'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    unit_type = db.Column(db.String(50))
    location = db.Column(db.String(255))
    power_watt = db.Column(db.Integer)
    
    consumption_data = db.relationship('EnergyConsumptionData', backref='lighting_unit', lazy=True, cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', backref='lighting_unit', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<LightingUnit {self.location} in Area {self.area.name}>"

class EnergyConsumptionData(db.Model):
    __tablename__ = 'energy_consumption_data'
    id = db.Column(db.Integer, primary_key=True)
    lighting_unit_id = db.Column(db.Integer, db.ForeignKey('lighting_units.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    consumption_kwh = db.Column(db.Float, nullable=False)
    status_recording = db.Column(db.String(50))

    def __repr__(self):
        return f"<Consumption {self.consumption_kwh}kWh at {self.timestamp} for LU_ID:{self.lighting_unit_id}>"

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=True) 
    lighting_unit_id = db.Column(db.Integer, db.ForeignKey('lighting_units.id'), nullable=True) 
    date_generated = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    potential_savings_kwh = db.Column(db.Float)
    potential_savings_euro = db.Column(db.Float)
    action_status = db.Column(db.String(50))

    def __repr__(self):
        return f"<Recommendation {self.title} for AreaID:{self.area_id} LU_ID:{self.lighting_unit_id}>"
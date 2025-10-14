from flask import Blueprint, jsonify
from database import db
from models import City, Area

city_bp = Blueprint('city_bp', __name__, url_prefix='/cities')

@city_bp.route('/')
def get_cities():
    cities = City.query.all()
    return jsonify([{"id": city.id, "name": city.name} for city in cities])

@city_bp.route('/<int:city_id>/area') # Specifieker dan /city_area
def get_area_for_city(city_id):
    area = Area.query.filter_by(city_id=city_id).first()
    if not area:
        return jsonify({"error": "Area not found for this city"}), 404
    return jsonify({"id": area.id, "name": area.name, "description": area.description})
from database.db import db
from models import Hospital
from utils.location import calculate_distance as get_distance
import math

class HospitalService:
    def __init__(self):
        pass

    def find_nearby_hospitals(self, latitude, longitude, radius=10):
        """Find hospitals within a specified radius (in km) of given coordinates."""
        if latitude is None or longitude is None:
            return []

        # Get all hospitals from database
        all_hospitals = Hospital.query.all()
        nearby_hospitals = []

        for hospital in all_hospitals:
            # Skip hospitals with missing coordinates
            if hospital.latitude is None or hospital.longitude is None:
                continue

            # Calculate distance
            distance = self._calculate_distance(
                latitude, longitude,
                float(hospital.latitude), float(hospital.longitude)
            )

            # If within radius, add to results with distance
            if distance <= radius:
                hospital.distance = round(distance, 2)
                nearby_hospitals.append(hospital)

        # Sort by distance (closest first)
        nearby_hospitals.sort(key=lambda h: h.distance)

        return nearby_hospitals

    def search_hospitals(self, query="", city="", state="", emergency_services=None):
        """Search hospitals by various criteria."""
        # Build query
        hospitals_query = Hospital.query

        if query:
            search_term = f"%{query}%"
            hospitals_query = hospitals_query.filter(
                Hospital.name.ilike(search_term) |
                Hospital.address.ilike(search_term) |
                Hospital.city.ilike(search_term)
            )

        if city:
            hospitals_query = hospitals_query.filter(Hospital.city.ilike(f"%{city}%"))

        if state:
            hospitals_query = hospitals_query.filter(Hospital.state.ilike(f"%{state}%"))

        if emergency_services is not None:
            hospitals_query = hospitals_query.filter(Hospital.emergency_services == emergency_services)

        # Order by name
        hospitals_query = hospitals_query.order_by(Hospital.name)

        return hospitals_query.all()

    def get_hospital_by_id(self, hospital_id):
        """Get hospital by ID."""
        return Hospital.query.get(hospital_id)

    def get_hospitals_by_city(self, city):
        """Get all hospitals in a specific city."""
        return Hospital.query.filter(Hospital.city.ilike(f"%{city}%")).order_by(Hospital.name).all()

    def get_hospitals_by_state(self, state):
        """Get all hospitals in a specific state."""
        return Hospital.query.filter(Hospital.state.ilike(f"%{state}%")).order_by(Hospital.name).all()

    def get_top_rated_hospitals(self, limit=10):
        """Get top-rated hospitals."""
        return Hospital.query.filter(Hospital.rating.isnot(None))\
            .order_by(Hospital.rating.desc())\
            .limit(limit)\
            .all()

    def get_hospitals_with_emergency_services(self):
        """Get hospitals that have emergency services."""
        return Hospital.query.filter_by(emergency_services=True)\
            .order_by(Hospital.name)\
            .all()

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points on Earth using Haversine formula."""
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r

    def get_hospital_stats(self):
        """Get statistics about hospitals in the database."""
        total_hospitals = Hospital.query.count()
        emergency_hospitals = Hospital.query.filter_by(emergency_services=True).count()

        # Average rating (only for hospitals that have ratings)
        avg_rating = db.session.query(db.func.avg(Hospital.rating)).filter(Hospital.rating.isnot(None)).scalar()

        # Hospitals by state
        states = db.session.query(Hospital.state, db.func.count(Hospital.id))\
            .group_by(Hospital.state)\
            .order_by(db.func.count(Hospital.id).desc())\
            .all()

        return {
            'total_hospitals': total_hospitals,
            'emergency_hospitals': emergency_hospitals,
            'average_rating': round(float(avg_rating), 2) if avg_rating else None,
            'hospitals_by_state': [{'state': state, 'count': count} for state, count in states]
        }
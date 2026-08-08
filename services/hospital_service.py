"""
services/hospital_service.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hospital lookup service with a two-tier provider strategy:

  PRIMARY  : Geoapify Places API — rich data (address, phone, website)
  FALLBACK : OpenStreetMap Overpass  — no API key required

Provider selection:
  - If GEOAPIFY_API_KEY is set and HOSPITALS_PROVIDER=geoapify → use Geoapify
  - If Geoapify fails for any reason → fall back to Overpass
  - If HOSPITALS_PROVIDER=overpass (or key is missing) → use Overpass directly

Geoapify API key is ALWAYS kept server-side. It is never included in HTTP
responses, never written to templates, never logged.

All DB-backed methods for admin Hospital model are preserved unchanged.
"""

import math
import os
import logging
import requests
from database.db import db
from models import Hospital

logger = logging.getLogger(__name__)

# ── Geoapify Places API ────────────────────────────────────────────────────
GEOAPIFY_URL = 'https://api.geoapify.com/v2/places'

# Healthcare categories that cover hospitals, clinics and medical centres.
# Geoapify uses comma-separated category strings.
GEOAPIFY_CATEGORIES = 'healthcare.hospital,healthcare.clinic_or_praxis'

# ── Overpass API ───────────────────────────────────────────────────────────
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

# ── Defaults ──────────────────────────────────────────────────────────────
DEFAULT_RADIUS_KM = int(os.environ.get('HOSPITALS_RADIUS_KM', '10'))
MAX_RESULTS       = 15
TIMEOUT_GEOAPIFY  = 10   # seconds
TIMEOUT_OVERPASS  = 15   # seconds


def _get_geoapify_key() -> str:
    """Return the Geoapify API key from environment. Never log the value."""
    return os.environ.get('GEOAPIFY_API_KEY', '').strip()


def _geoapify_configured() -> bool:
    """True only when a non-empty API key is present and provider is 'geoapify'."""
    provider = os.environ.get('HOSPITALS_PROVIDER', 'geoapify').strip().lower()
    return bool(_get_geoapify_key()) and provider == 'geoapify'


class HospitalService:
    """
    Public interface:
      find_nearby_hospitals_api(lat, lng, radius_km) -> dict

    Internal flow:
      1. _search_geoapify()   -> list of normalised dicts (or raises)
      2. if fails -> _search_overpass() -> list of normalised dicts (or raises)
      3. Sort by distance_km ascending
      4. Return structured JSON-serialisable response
    """

    # ------------------------------------------------------------------ #
    # Main public method (used by /hospital/api/nearby)
    # ------------------------------------------------------------------ #

    def find_nearby_hospitals_api(self, latitude: float, longitude: float,
                                  radius_km: float = DEFAULT_RADIUS_KM,
                                  limit: int = MAX_RESULTS) -> dict:
        """
        Find nearby hospitals. Geoapify is tried first; Overpass is the fallback.

        Returns:
        {
          'success': bool,
          'hospitals': [...],
          'count': int,
          'source': 'geoapify' | 'overpass' | 'error',
          'error': str | None,
          'attribution': str
        }
        """
        if not self._valid_coords(latitude, longitude):
            return self._error_response('Invalid coordinates provided.')

        radius_km = max(1.0, min(float(radius_km), 50.0))   # clamp 1–50 km

        # ── Try Geoapify ───────────────────────────────────────────────
        if _geoapify_configured():
            try:
                hospitals = self._search_geoapify(latitude, longitude,
                                                  radius_km, limit)
                if hospitals is not None:
                    hospitals = sorted(hospitals,
                                       key=lambda h: h['distance_km'])
                    return {
                        'success': True,
                        'hospitals': hospitals,
                        'count': len(hospitals),
                        'source': 'geoapify',
                        'error': None,
                        'attribution': 'Powered by Geoapify | Data (c) OpenStreetMap contributors',
                    }
            except _GeoapifyError as exc:
                logger.warning(
                    'Geoapify failed, falling back to Overpass. Reason: %s', exc)
            except Exception as exc:
                logger.error('Unexpected Geoapify error: %s', type(exc).__name__)

        elif _get_geoapify_key():
            logger.debug('Geoapify key present but HOSPITALS_PROVIDER != geoapify; using Overpass.')
        else:
            logger.info('No GEOAPIFY_API_KEY configured; using Overpass.')

        # ── Fallback: Overpass ─────────────────────────────────────────
        try:
            hospitals = self._search_overpass(latitude, longitude,
                                              radius_km, limit)
            hospitals = sorted(hospitals, key=lambda h: h['distance_km'])
            return {
                'success': True,
                'hospitals': hospitals,
                'count': len(hospitals),
                'source': 'overpass',
                'error': None,
                'attribution': '(c) OpenStreetMap contributors',
            }
        except _OverpassError as exc:
            logger.error('Overpass also failed: %s', exc)
            return self._error_response(
                'Unable to retrieve nearby hospitals at this time.')
        except Exception as exc:
            logger.error('Unexpected Overpass error: %s', type(exc).__name__)
            return self._error_response(
                'Unable to retrieve nearby hospitals at this time.')

    # ------------------------------------------------------------------ #
    # Geoapify Places API
    # ------------------------------------------------------------------ #

    def _search_geoapify(self, lat: float, lng: float,
                         radius_km: float, limit: int) -> list:
        """
        Call Geoapify Places API with a circular filter.

        Geoapify filter format: circle:LON,LAT,RADIUS_M  (longitude FIRST)

        Returns a list of normalised hospital dicts.
        Raises _GeoapifyError on any failure.
        """
        api_key   = _get_geoapify_key()
        radius_m  = int(radius_km * 1000)

        params = {
            'categories': GEOAPIFY_CATEGORIES,
            # IMPORTANT: Geoapify filter uses lon,lat order (not lat,lon)
            'filter'    : f'circle:{lng},{lat},{radius_m}',
            'bias'      : f'proximity:{lng},{lat}',
            'limit'     : min(limit, 50),        # Geoapify free tier max = 500
            'apiKey'    : api_key,               # server-side only
        }

        try:
            resp = requests.get(
                GEOAPIFY_URL,
                params=params,
                timeout=TIMEOUT_GEOAPIFY,
                headers={'User-Agent': 'NexVitaHealthApp/1.0'},
            )
        except requests.exceptions.Timeout:
            raise _GeoapifyError('Request timed out')
        except requests.exceptions.ConnectionError:
            raise _GeoapifyError('Network connection error')
        except requests.exceptions.RequestException as exc:
            raise _GeoapifyError(f'Request failed: {type(exc).__name__}')

        if resp.status_code == 400:
            try:
                msg = resp.json().get('message', 'Bad request')
            except Exception:
                msg = 'Bad request (400)'
            logger.error('Geoapify 400: %s', msg)
            raise _GeoapifyError(f'Bad request: {msg}')

        if resp.status_code in (401, 403):
            logger.error(
                'Geoapify auth error %s — check GEOAPIFY_API_KEY.',
                resp.status_code)
            raise _GeoapifyError(f'Auth error {resp.status_code}')

        if resp.status_code == 429:
            logger.warning('Geoapify rate limit / quota exceeded.')
            raise _GeoapifyError('Quota exceeded')

        if not resp.ok:
            logger.error('Geoapify HTTP %s', resp.status_code)
            raise _GeoapifyError(f'HTTP {resp.status_code}')

        try:
            data = resp.json()
        except ValueError:
            raise _GeoapifyError('Invalid JSON response')

        features = data.get('features', [])
        if not features:
            return []   # valid response, no hospitals in radius

        results = []
        for feature in features:
            normalised = self._normalise_geoapify_feature(feature, lat, lng)
            if normalised:
                results.append(normalised)

        return results

    def _normalise_geoapify_feature(self, feature: dict,
                                    user_lat: float, user_lng: float) -> dict | None:
        """
        Convert a raw Geoapify GeoJSON Feature into the canonical hospital dict.
        Returns None if the feature cannot be meaningfully normalised.
        Never fabricates data — every field comes from the API or is null.
        """
        props = feature.get('properties', {})
        geom  = feature.get('geometry',   {})

        # Coordinates: GeoJSON stores [longitude, latitude]
        coords = geom.get('coordinates', [])
        if len(coords) < 2:
            return None
        h_lng = coords[0]
        h_lat = coords[1]
        if h_lat is None or h_lng is None:
            return None

        # Name — skip unnamed results (they are noise)
        name = props.get('name') or props.get('address_line1')
        if not name or not name.strip():
            return None
        name = name.strip()

        # Full formatted address from Geoapify (includes city, state, etc.)
        address = props.get('formatted') or None
        if address:
            address = address.strip()

        # Phone — Geoapify returns contact info in 'contact' sub-object
        contact = props.get('contact', {}) or {}
        phone = (contact.get('phone')
                 or contact.get('mobile')
                 or props.get('phone')     # some versions put it at top level
                 or None)
        if phone:
            phone = phone.strip()

        # Website
        website = (contact.get('website')
                   or props.get('website')
                   or None)

        # Geoapify does NOT provide ratings or open-now status
        rating       = None
        rating_count = None
        open_now     = None
        business_status = None

        # Distance using Haversine
        dist_km = round(self._haversine(user_lat, user_lng, h_lat, h_lng), 2)

        # Map URL — prefer Geoapify/OSM link; fall back to generic Google Maps search
        place_id = props.get('place_id') or props.get('osm_id') or None

        if place_id:
            maps_url = (
                f'https://www.geoapify.com/places/'
                f'?id={place_id}'
            )
        else:
            maps_url = (
                f'https://www.openstreetmap.org/'
                f'?mlat={h_lat}&mlon={h_lng}&zoom=17'
            )

        # Emergency services — check categories list
        categories = props.get('categories', []) or []
        emergency_services = (
            'healthcare.hospital' in categories
            or 'healthcare.emergency' in categories
        )

        return {
            'id'              : str(place_id) if place_id else None,
            'name'            : name,
            'address'         : address,
            'latitude'        : h_lat,
            'longitude'       : h_lng,
            'distance_km'     : dist_km,
            'phone'           : phone,
            'website'         : website,
            'rating'          : rating,           # None — Geoapify has no ratings
            'rating_count'    : rating_count,     # None
            'open_now'        : open_now,         # None — not provided
            'business_status' : business_status, # None
            'maps_url'        : maps_url,
            'place_id'        : str(place_id) if place_id else None,
            'source'          : 'geoapify',
            'emergency_services': emergency_services,
        }

    # ------------------------------------------------------------------ #
    # Overpass API — fallback
    # ------------------------------------------------------------------ #

    def _search_overpass(self, lat: float, lng: float,
                         radius_km: float, limit: int) -> list:
        """
        Query OpenStreetMap Overpass API for nearby hospitals.
        Returns a list of normalised hospital dicts.
        Raises _OverpassError on failure.
        """
        radius_m = int(radius_km * 1000)
        overpass_limit = limit * 2   # request extra to allow for dedup

        query = (
            f'[out:json][timeout:{TIMEOUT_OVERPASS}];'
            f'('
            f'  node["amenity"="hospital"](around:{radius_m},{lat},{lng});'
            f'  way["amenity"="hospital"](around:{radius_m},{lat},{lng});'
            f'  node["amenity"="clinic"](around:{radius_m},{lat},{lng});'
            f'  node["healthcare"="hospital"](around:{radius_m},{lat},{lng});'
            f');'
            f'out center {overpass_limit};'
        )

        try:
            resp = requests.post(
                OVERPASS_URL,
                data={'data': query},
                timeout=TIMEOUT_OVERPASS,
                headers={'User-Agent': 'NexVitaHealthApp/1.0'},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            raise _OverpassError('Overpass timed out')
        except requests.exceptions.RequestException as exc:
            raise _OverpassError(f'Overpass request failed: {type(exc).__name__}')
        except ValueError:
            raise _OverpassError('Invalid JSON from Overpass')

        elements = data.get('elements', [])
        hospitals = []
        seen = set()

        for el in elements:
            tags = el.get('tags', {})

            if el['type'] == 'node':
                h_lat, h_lng = el.get('lat'), el.get('lon')
            else:
                center = el.get('center', {})
                h_lat, h_lng = center.get('lat'), center.get('lon')

            if h_lat is None or h_lng is None:
                continue

            name = tags.get('name') or tags.get('name:en')
            if not name:
                continue   # skip unnamed — they are noise

            key = (name.lower(), round(h_lat, 3), round(h_lng, 3))
            if key in seen:
                continue
            seen.add(key)

            dist_km = round(self._haversine(lat, lng, h_lat, h_lng), 2)

            phone = (tags.get('phone')
                     or tags.get('contact:phone')
                     or tags.get('contact:mobile')
                     or None)

            parts = [
                tags.get('addr:housenumber', ''),
                tags.get('addr:street', ''),
                tags.get('addr:suburb', ''),
                tags.get('addr:city') or tags.get('addr:town', ''),
            ]
            address = ', '.join(p for p in parts if p) or None

            opening = tags.get('opening_hours', '')
            open_now = True if '24/7' in opening.upper() else None

            maps_url = (
                f'https://www.openstreetmap.org/'
                f'?mlat={h_lat}&mlon={h_lng}&zoom=17'
            )

            hospitals.append({
                'id'              : str(el.get('id', '')),
                'name'            : name,
                'address'         : address,
                'latitude'        : h_lat,
                'longitude'       : h_lng,
                'distance_km'     : dist_km,
                'phone'           : phone,
                'website'         : None,
                'rating'          : None,
                'rating_count'    : None,
                'open_now'        : open_now,
                'business_status' : None,
                'maps_url'        : maps_url,
                'place_id'        : str(el.get('id', '')),
                'source'          : 'overpass',
                'emergency_services': tags.get('emergency') == 'yes',
            })

            if len(hospitals) >= limit:
                break

        return hospitals

    # ------------------------------------------------------------------ #
    # Existing DB-backed methods — unchanged for admin pages
    # ------------------------------------------------------------------ #

    def find_nearby_hospitals(self, latitude, longitude, radius=10):
        """Find admin-seeded DB hospitals within radius km."""
        if latitude is None or longitude is None:
            return []
        all_hospitals = Hospital.query.all()
        nearby = []
        for h in all_hospitals:
            if h.latitude is None or h.longitude is None:
                continue
            dist = self._haversine(float(latitude), float(longitude),
                                   float(h.latitude), float(h.longitude))
            if dist <= radius:
                h.distance = round(dist, 2)
                nearby.append(h)
        nearby.sort(key=lambda h: h.distance)
        return nearby

    def search_hospitals(self, query='', city='', state='',
                         emergency_services=None):
        q = Hospital.query
        if query:
            term = f'%{query}%'
            q = q.filter(
                Hospital.name.ilike(term)
                | Hospital.address.ilike(term)
                | Hospital.city.ilike(term)
            )
        if city:
            q = q.filter(Hospital.city.ilike(f'%{city}%'))
        if state:
            q = q.filter(Hospital.state.ilike(f'%{state}%'))
        if emergency_services is not None:
            q = q.filter(Hospital.emergency_services == emergency_services)
        return q.order_by(Hospital.name).all()

    def get_hospital_by_id(self, hospital_id):
        return db.session.get(Hospital, hospital_id)

    def get_hospitals_by_city(self, city):
        return Hospital.query.filter(
            Hospital.city.ilike(f'%{city}%')
        ).order_by(Hospital.name).all()

    def get_hospitals_by_state(self, state):
        return Hospital.query.filter(
            Hospital.state.ilike(f'%{state}%')
        ).order_by(Hospital.name).all()

    def get_top_rated_hospitals(self, limit=10):
        return (Hospital.query
                .filter(Hospital.rating.isnot(None))
                .order_by(Hospital.rating.desc())
                .limit(limit).all())

    def get_hospitals_with_emergency_services(self):
        return (Hospital.query
                .filter_by(emergency_services=True)
                .order_by(Hospital.name).all())

    def get_hospital_stats(self):
        total     = Hospital.query.count()
        emergency = Hospital.query.filter_by(emergency_services=True).count()
        avg_rating = (db.session.query(db.func.avg(Hospital.rating))
                      .filter(Hospital.rating.isnot(None)).scalar())
        states    = (db.session.query(Hospital.state,
                                      db.func.count(Hospital.id))
                     .group_by(Hospital.state)
                     .order_by(db.func.count(Hospital.id).desc()).all())
        return {
            'total_hospitals'  : total,
            'emergency_hospitals': emergency,
            'average_rating'   : round(float(avg_rating), 2) if avg_rating else None,
            'hospitals_by_state': [{'state': s, 'count': c} for s, c in states],
        }

    # ------------------------------------------------------------------ #
    # Static helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _valid_coords(lat, lng) -> bool:
        try:
            return -90 <= float(lat) <= 90 and -180 <= float(lng) <= 180
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        """Return great-circle distance in km (Haversine formula)."""
        lat1, lon1, lat2, lon2 = map(math.radians,
                                     [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        return 2 * math.asin(math.sqrt(a)) * 6371.0

    @staticmethod
    def _error_response(msg: str) -> dict:
        return {
            'success'    : False,
            'hospitals'  : [],
            'count'      : 0,
            'source'     : 'error',
            'error'      : msg,
            'attribution': '',
        }


# ── Private exception types ────────────────────────────────────────────────

class _GeoapifyError(Exception):
    """Raised internally when Geoapify search fails."""


class _OverpassError(Exception):
    """Raised internally when Overpass search fails."""
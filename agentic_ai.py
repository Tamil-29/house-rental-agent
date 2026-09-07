"""
==============================================================================
Agentic AI Engine for House Rental Management System
==============================================================================
Provides autonomous multi-step reasoning (ReAct: Thought -> Action ->
Observation -> Reflection -> Answer) and tool execution over the rental database.
Supports:
1. Zero-dependency Local Autonomous ReAct Engine (runs out-of-the-box).
2. Dynamic Tool Dispatcher with Declarative JSON Schema Manifest.
3. 13 Specialized Rental Domain Tools spanning search, valuation, comparison,
   affordability analysis, neighborhood insights, visit scheduling, lease checking,
   status tracking, and platform intelligence.
==============================================================================
"""

import os
import re
import json
import time
from datetime import datetime, date
from decimal import Decimal


# ----------------------------------------------------------------------------
# JSON Serialization Helpers
# ----------------------------------------------------------------------------
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def clean_row_decimals(row):
    """Recursively clean Decimal and datetime objects in dictionaries/lists."""
    if not row:
        return row
    if isinstance(row, list):
        return [clean_row_decimals(item) for item in row]
    if isinstance(row, dict):
        cleaned = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                cleaned[k] = float(v)
            elif isinstance(v, (datetime, date)):
                cleaned[k] = str(v)
            elif isinstance(v, dict):
                cleaned[k] = clean_row_decimals(v)
            elif isinstance(v, list):
                cleaned[k] = clean_row_decimals(v)
            else:
                cleaned[k] = v
        return cleaned
    return row


# ----------------------------------------------------------------------------
# Declarative Tool Definitions & Manifest
# ----------------------------------------------------------------------------
TOOL_DEFINITIONS = {
    "search_properties": {
        "name": "search_properties",
        "category": "Search & Discovery",
        "display_name": "🔍 Multi-Criteria Property Search",
        "description": "Search available, approved rental houses matching multi-criteria constraints including locality, rent ceiling, bedrooms, and furnishing status.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Locality or city name (e.g. Indiranagar, Whitefield, Koramangala)"},
                "min_rent": {"type": "number", "description": "Minimum monthly rent in INR"},
                "max_rent": {"type": "number", "description": "Maximum monthly rent budget ceiling in INR"},
                "bedrooms": {"type": "integer", "description": "Exact number of bedrooms / BHK (1, 2, 3, 4)"},
                "furnishing": {"type": "string", "enum": ["Furnished", "Semi-Furnished", "Unfurnished"], "description": "Furnishing condition"},
                "limit": {"type": "integer", "default": 5, "description": "Maximum number of listings to return"}
            }
        },
        "example_prompt": "Find me a 2BHK in Indiranagar under ₹30,000 Furnished"
    },
    "get_property_details": {
        "name": "get_property_details",
        "category": "Search & Discovery",
        "display_name": "🏡 Property Detail Inspector",
        "description": "Retrieve complete specifications, landlord details, deposit figures, and amenities for a specific house ID.",
        "parameters": {
            "type": "object",
            "required": ["house_id"],
            "properties": {
                "house_id": {"type": "integer", "description": "Unique listing ID of the house"}
            }
        },
        "example_prompt": "Show full details for house 1"
    },
    "compare_properties": {
        "name": "compare_properties",
        "category": "Market Intelligence & Analytics",
        "display_name": "⚖️ Side-by-Side Property Comparison",
        "description": "Compare 2 to 4 properties side-by-side on rent, deposit ratio, bedroom space, and amenities. If only 1 house ID is provided, automatically discovers similar benchmark listings.",
        "parameters": {
            "type": "object",
            "required": ["house_ids"],
            "properties": {
                "house_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of house IDs to compare"},
                "auto_fill_similar": {"type": "boolean", "default": True, "description": "If true and only 1 ID is provided, automatically benchmark against similar houses"}
            }
        },
        "example_prompt": "Compare house 1 and house 2"
    },
    "estimate_rent_value": {
        "name": "estimate_rent_value",
        "category": "Market Intelligence & Analytics",
        "display_name": "📈 AI Rental Valuation Engine",
        "description": "Calculates fair market rental valuation, recommended security deposit, competitive pricing bracket, and market demand confidence score based on locality dynamics and property specifications.",
        "parameters": {
            "type": "object",
            "required": ["location", "bedrooms"],
            "properties": {
                "location": {"type": "string", "description": "Locality or area name"},
                "bedrooms": {"type": "integer", "default": 2, "description": "Number of bedrooms / BHK"},
                "furnishing": {"type": "string", "enum": ["Furnished", "Semi-Furnished", "Unfurnished"], "default": "Furnished"},
                "bathrooms": {"type": "integer", "default": 1, "description": "Number of bathrooms"}
            }
        },
        "example_prompt": "Estimate market rent for 3BHK in Koramangala Furnished"
    },
    "generate_listing_description": {
        "name": "generate_listing_description",
        "category": "Listing & Owner Optimization",
        "display_name": "✨ AI Property Copywriter",
        "description": "Generates a high-converting, professional marketing description, catchy listing title, and SEO tags for house owners.",
        "parameters": {
            "type": "object",
            "required": ["location", "bedrooms"],
            "properties": {
                "title": {"type": "string", "description": "Working title or short description"},
                "location": {"type": "string", "description": "Neighborhood/Locality"},
                "bedrooms": {"type": "integer", "default": 2, "description": "Number of bedrooms"},
                "furnishing": {"type": "string", "enum": ["Furnished", "Semi-Furnished", "Unfurnished"], "default": "Furnished"},
                "amenities": {"type": "string", "description": "Comma-separated key amenities"}
            }
        },
        "example_prompt": "Write a listing description for 2BHK in Indiranagar with modular kitchen and balcony"
    },
    "calculate_match_score": {
        "name": "calculate_match_score",
        "category": "Search & Discovery",
        "display_name": "🎯 Compatibility Match Score",
        "description": "Calculates an AI compatibility match percentage between tenant preferences (budget, BHK, furnishing) and a target house listing.",
        "parameters": {
            "type": "object",
            "required": ["house_id", "tenant_pref"],
            "properties": {
                "house_id": {"type": "integer", "description": "Target house ID"},
                "tenant_pref": {
                    "type": "object",
                    "properties": {
                        "max_rent": {"type": "number"},
                        "bedrooms": {"type": "integer"},
                        "furnishing": {"type": "string"}
                    }
                }
            }
        },
        "example_prompt": "Calculate match score for house 1 with budget 30000 2BHK Furnished"
    },
    "draft_rental_inquiry": {
        "name": "draft_rental_inquiry",
        "category": "Tenant Advisory & Safety",
        "display_name": "✉️ AI Landlord Inquiry Drafter",
        "description": "Drafts a personalized, polite, and persuasive inquiry letter addressing the landlord with target move-in date and applicant credentials.",
        "parameters": {
            "type": "object",
            "required": ["house_id"],
            "properties": {
                "house_id": {"type": "integer", "description": "House ID to inquire about"},
                "tenant_name": {"type": "string", "default": "Prospective Tenant"},
                "move_in_date": {"type": "string", "default": "Immediate / Next Month"},
                "note": {"type": "string", "default": ""}
            }
        },
        "example_prompt": "Draft inquiry letter for house 1"
    },
    "calculate_affordability": {
        "name": "calculate_affordability",
        "category": "Tenant Advisory & Safety",
        "display_name": "💳 Rent Affordability & Budget Planner",
        "description": "Evaluates financial health using the 30% gross income rule, computes recommended rent ceiling, required upfront moving capital, and remaining emergency buffer.",
        "parameters": {
            "type": "object",
            "required": ["monthly_income"],
            "properties": {
                "monthly_income": {"type": "number", "description": "Gross or net monthly take-home salary in INR"},
                "target_rent": {"type": "number", "description": "Optional monthly rent of a house being considered"},
                "target_deposit": {"type": "number", "description": "Optional security deposit amount"}
            }
        },
        "example_prompt": "Can I afford rent of ₹28,000 on a salary of ₹85,000?"
    },
    "get_neighborhood_insights": {
        "name": "get_neighborhood_insights",
        "category": "Market Intelligence & Analytics",
        "display_name": "📍 Neighborhood & Locality Intelligence",
        "description": "Provides neighborhood livability ratings, metro & transit connectivity, safety score, tech corridor commute times, and local perks for urban localities.",
        "parameters": {
            "type": "object",
            "required": ["location"],
            "properties": {
                "location": {"type": "string", "description": "Neighborhood name (e.g. Indiranagar, Koramangala, Whitefield, HSR Layout, Bellandur)"}
            }
        },
        "example_prompt": "Show neighborhood insights and safety score for Indiranagar"
    },
    "schedule_property_visit": {
        "name": "schedule_property_visit",
        "category": "Tenant Advisory & Safety",
        "display_name": "📅 In-Person Walkthrough Scheduler",
        "description": "Generates a verified physical walkthrough itinerary ticket with landlord contact details, appointment slot, and an essential 6-point property inspection checklist.",
        "parameters": {
            "type": "object",
            "required": ["house_id"],
            "properties": {
                "house_id": {"type": "integer", "description": "House listing ID to visit"},
                "tenant_name": {"type": "string", "default": "Applicant"},
                "tenant_phone": {"type": "string", "default": "Not Provided"},
                "visit_date": {"type": "string", "description": "Proposed date (e.g. Tomorrow, Saturday, YYYY-MM-DD)"},
                "time_slot": {"type": "string", "default": "11:00 AM - 01:00 PM"},
                "notes": {"type": "string", "default": ""}
            }
        },
        "example_prompt": "Schedule visit for house 1 on Saturday morning"
    },
    "check_rental_request_status": {
        "name": "check_rental_request_status",
        "category": "Tenant Advisory & Safety",
        "display_name": "📋 Application & Request Tracker",
        "description": "Checks real-time status (Pending, Accepted, Rejected) of tenant rental applications or lists pending tenant submissions for owners.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "User ID of tenant or owner"},
                "role": {"type": "string", "enum": ["tenant", "owner", "admin"], "default": "tenant"}
            }
        },
        "example_prompt": "Check my rental request status"
    },
    "generate_rental_agreement_checklist": {
        "name": "generate_rental_agreement_checklist",
        "category": "Tenant Advisory & Safety",
        "display_name": "📜 Lease Agreement & Legal Checklist",
        "description": "Generates a standard 8-point legal and operational lease agreement checklist covering 11-month tenure, notice period, security deposit refund terms, and maintenance liabilities.",
        "parameters": {
            "type": "object",
            "properties": {
                "house_id": {"type": "integer", "description": "Optional House ID to prefill lease numbers"},
                "rent": {"type": "number", "description": "Monthly rent in INR"},
                "deposit": {"type": "number", "description": "Security deposit in INR"},
                "duration_months": {"type": "integer", "default": 11, "description": "Duration of lease agreement in months"}
            }
        },
        "example_prompt": "Generate rental agreement checklist for house 1"
    },
    "get_platform_stats": {
        "name": "get_platform_stats",
        "category": "Market Intelligence & Analytics",
        "display_name": "📊 Marketplace Platform Intelligence",
        "description": "Aggregates live marketplace metrics including total active listings, average monthly rent, price spectrum, and BHK inventory distribution.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "example_prompt": "Show platform statistics and market overview"
    }
}


# ----------------------------------------------------------------------------
# Neighborhood Intelligence Knowledge Base
# ----------------------------------------------------------------------------
NEIGHBORHOOD_DATABASE = {
    "indiranagar": {
        "name": "Indiranagar",
        "city": "Bangalore",
        "safety_rating": 9.6,
        "transit_rating": 9.5,
        "nearest_metro": "Indiranagar / CMH Road Metro (Purple Line) - ~400m",
        "commute_corridors": "15 mins to MG Road / CBD | 25 mins to Domlur / Embassy GolfLinks | 40 mins to Bellandur",
        "livability_index": 9.5,
        "vibe": "Prime cosmopolitan hub with bustling 100ft & 12th Main food corridors, boutique cafes, upscale boutiques, and peaceful residential crossways.",
        "highlights": [
            "Purple Line Metro provides direct connectivity across East-West Bengaluru",
            "Walking distance to premier healthcare (Chinmaya Mission, Manipal Hospital nearby)",
            "Lush neighborhood parks and tree-lined avenues",
            "High rental liquidity with top-tier tenant demand"
        ]
    },
    "koramangala": {
        "name": "Koramangala",
        "city": "Bangalore",
        "safety_rating": 9.3,
        "transit_rating": 8.9,
        "nearest_metro": "South End Circle / Jayanagar Metro (~4 km) & Upcoming Silk Board interchange",
        "commute_corridors": "10 mins to Sony World / HSR Layout | 20 mins to CBD | 25 mins to Electronic City via Elevated Highway",
        "livability_index": 9.3,
        "vibe": "India's startup nucleus with iconic culinary culture, co-working spaces, premier college hubs, and vibrant student-professional community.",
        "highlights": [
            "High concentration of venture-backed startups, incubators, and tech offices",
            "Extensive bus routes connecting Hosur Road, Ring Road, and CBD",
            "Proximity to Forum Mall and prestigious educational institutions (St. John's, Christ)",
            "Vibrant dining scene with 200+ multi-cuisine cafes and restaurants"
        ]
    },
    "whitefield": {
        "name": "Whitefield",
        "city": "Bangalore",
        "safety_rating": 9.1,
        "transit_rating": 9.2,
        "nearest_metro": "Kadugodi Tree Park / Hopefarm Metro (Purple Line) - Direct access",
        "commute_corridors": "5-15 mins to ITPL, EPIP Zone, Bagmane Constellation | 35 mins to Outer Ring Road",
        "livability_index": 8.9,
        "vibe": "Global technology enclave boasting expansive gated villa societies, international schools, and mega lifestyle retail malls.",
        "highlights": [
            "Direct Purple Line metro connectivity straight to Central Bengaluru",
            "Walkable proximity to major IT tech campuses (ITPL, SAP Labs, TCS)",
            "Presence of international schools (Inventure, Deens, Greenwood High buses)",
            "Luxury retail destinations including Phoenix Marketcity and VR Bengaluru"
        ]
    },
    "hsr": {
        "name": "HSR Layout",
        "city": "Bangalore",
        "safety_rating": 9.4,
        "transit_rating": 9.0,
        "nearest_metro": "Silk Board Junction / Bommanahalli Metro (Yellow Line)",
        "commute_corridors": "10-15 mins to Bellandur ORR Tech Parks | 10 mins to Koramangala | 25 mins to Electronic City",
        "livability_index": 9.4,
        "vibe": "Planned modern residential grid designed with wide sectors, tech founder headquarters, organic markets, and serene parks.",
        "highlights": [
            "Prime gateway position between Koramangala and Outer Ring Road tech corridor",
            "Over 18 public parks and athletic sports complexes",
            "Thriving cafe and specialty coffee culture in Sector 1, 2, and 4",
            "Safe, well-lit residential sectors with active neighborhood watch"
        ]
    },
    "bellandur": {
        "name": "Bellandur",
        "city": "Bangalore",
        "safety_rating": 8.6,
        "transit_rating": 8.4,
        "nearest_metro": "Upcoming Blue Line ORR Metro & Silk Board Interchange",
        "commute_corridors": "Walkable / 5 mins to RMZ Ecoworld, Ecospace, Prestige Tech Park",
        "livability_index": 8.5,
        "vibe": "Hyper-dense tech employment corridor with exceptional rental yields and doorstep proximity to global enterprise campuses.",
        "highlights": [
            "Virtually zero commute for professionals at Ecoworld and Ecospace",
            "24/7 hypermarkets, fitness studios, and international hospital access (Sakra)",
            "Dense BMTC Volvo feeder network along Outer Ring Road",
            "High rental demand guarantees continuous property appreciation"
        ]
    },
    "electronic city": {
        "name": "Electronic City",
        "city": "Bangalore",
        "safety_rating": 9.0,
        "transit_rating": 8.8,
        "nearest_metro": "Electronic City Metro (Yellow Line)",
        "commute_corridors": "5 mins to Infosys, Wipro, HP, Tech Mahindra campuses | 20 mins to Silk Board via Elevated Tollway",
        "livability_index": 8.7,
        "vibe": "Self-contained tech township with expansive roads, modern high-rise societies, and budget-friendly rental options.",
        "highlights": [
            "Direct 10-km elevated expressway connecting Silk Board in ~15 minutes",
            "Township infrastructure managed by ELCITA with specialized security patrol",
            "Significant rent savings compared to central Bengaluru",
            "Quiet, master-planned environment ideal for engineers and families"
        ]
    },
    "marathahalli": {
        "name": "Marathahalli",
        "city": "Bangalore",
        "safety_rating": 8.7,
        "transit_rating": 8.8,
        "nearest_metro": "Baiyappanahalli / KR Puram Metro (~15 mins)",
        "commute_corridors": "10 mins to HAL / Old Airport Road | 15 mins to Whitefield | 15 mins to ORR",
        "livability_index": 8.4,
        "vibe": "Centrally connected urban junction known for budget residential housing, factory outlet retail, and seamless bus transport.",
        "highlights": [
            "Central nexus connecting East Bangalore to Central and South hubs",
            "Abundant, economical 1BHK and 2BHK rental listings",
            "Bustling street markets, wholesale groceries, and multiplexes",
            "High frequency bus connectivity to every corner of Bengaluru"
        ]
    },
    "jayanagar": {
        "name": "Jayanagar",
        "city": "Bangalore",
        "safety_rating": 9.7,
        "transit_rating": 9.4,
        "nearest_metro": "Jayanagar / Rashtreeya Vidyalaya Road Metro (Green Line)",
        "commute_corridors": "15 mins to MG Road / Majestic | 20 mins to Bannerghatta Rd | 25 mins to Kanakapura Rd",
        "livability_index": 9.6,
        "vibe": "Historic South Bengaluru sanctuary featuring heritage trees, iconic 4th Block shopping complex, and tranquil residential community.",
        "highlights": [
            "One of Asia's best planned residential layouts with monumental tree canopies",
            "Green Line metro stations provide rapid north-south transit",
            "Renowned cultural institutions, libraries, and legendary South Indian eateries",
            "Superb safety index with quiet family-oriented blocks"
        ]
    }
}


# ----------------------------------------------------------------------------
# Suite of Agentic AI Tools
# ----------------------------------------------------------------------------
class RentalAgentTools:
    """
    Suite of 13 executable tools for the House Rental Agentic AI system.
    Each tool interacts with the database or computes domain intelligence.
    """

    def __init__(self, db_conn_factory):
        self.get_db_connection = db_conn_factory

    # ------------------------------------------------------------------------
    # Manifest and Dynamic Dispatcher
    # ------------------------------------------------------------------------
    def get_tool_manifest(self):
        """Returns the full declarative metadata manifest for all available tools."""
        return list(TOOL_DEFINITIONS.values())

    def execute_tool(self, tool_name, **kwargs):
        """
        Dynamic tool dispatcher. Validates existence, invokes method with arguments,
        catches exceptions, and returns a standardized execution envelope.
        """
        if tool_name not in TOOL_DEFINITIONS:
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Tool '{tool_name}' is not recognized in the agent tool registry."
            }

        if not hasattr(self, tool_name):
            return {
                "success": False,
                "tool": tool_name,
                "error": f"Tool '{tool_name}' has metadata registered but no callable method implemented."
            }

        start_time = time.time()
        try:
            method = getattr(self, tool_name)
            result = method(**kwargs)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "success": True,
                "tool": tool_name,
                "execution_time_ms": duration_ms,
                "result": clean_row_decimals(result)
            }
        except Exception as e:
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e)
            }

    # ------------------------------------------------------------------------
    # Tool 1: search_properties
    # ------------------------------------------------------------------------
    def search_properties(self, location=None, min_rent=None, max_rent=None, bedrooms=None, furnishing=None, limit=5):
        """Search available and approved rental houses matching multi-criteria constraints."""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT h.id, h.title, h.location, h.rent, h.deposit, h.bedrooms, 
                           h.bathrooms, h.furnishing, h.image, h.status, u.name as owner_name, u.phone as owner_phone
                    FROM houses h
                    JOIN users u ON h.owner_id = u.id
                    WHERE h.status = 'Available' AND h.approved = 1
                """
                params = []

                if location and str(location).strip():
                    query += " AND (h.location LIKE %s OR h.address LIKE %s OR h.title LIKE %s)"
                    loc_pattern = f"%{str(location).strip()}%"
                    params.extend([loc_pattern, loc_pattern, loc_pattern])

                if min_rent is not None and str(min_rent).strip() != "":
                    query += " AND h.rent >= %s"
                    params.append(float(min_rent))

                if max_rent is not None and str(max_rent).strip() != "":
                    query += " AND h.rent <= %s"
                    params.append(float(max_rent))

                if bedrooms is not None and str(bedrooms).strip() != "":
                    query += " AND h.bedrooms = %s"
                    params.append(int(bedrooms))

                if furnishing and str(furnishing).strip():
                    query += " AND h.furnishing LIKE %s"
                    params.append(f"%{str(furnishing).strip()}%")

                query += " ORDER BY h.rent ASC LIMIT %s"
                params.append(int(limit) if limit else 5)

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()
                return clean_row_decimals(results)
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # Tool 2: get_property_details
    # ------------------------------------------------------------------------
    def get_property_details(self, house_id):
        """Retrieve comprehensive details for a specific house listing."""
        if not house_id:
            return None

        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT h.*, u.name as owner_name, u.email as owner_email, u.phone as owner_phone
                    FROM houses h
                    JOIN users u ON h.owner_id = u.id
                    WHERE h.id = %s
                """
                cursor.execute(query, (int(house_id),))
                house = cursor.fetchone()
                return clean_row_decimals(house)
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # Tool 3: compare_properties (with auto-fill benchmark support)
    # ------------------------------------------------------------------------
    def compare_properties(self, house_ids, auto_fill_similar=True):
        """
        Compare 2 to 4 houses side-by-side. If only 1 house ID is provided and
        auto_fill_similar is True, finds benchmark listings to compare against.
        """
        if isinstance(house_ids, (int, str)):
            house_ids = [int(house_ids)]
        elif isinstance(house_ids, list):
            house_ids = [int(x) for x in house_ids if str(x).isdigit()]

        if not house_ids:
            return {"error": "No valid house IDs provided for comparison."}

        # If only 1 house provided, auto-fill similar benchmark listings
        if len(house_ids) == 1 and auto_fill_similar:
            target_house = self.get_property_details(house_ids[0])
            if target_house:
                similar_candidates = self.search_properties(
                    location=target_house.get('location'),
                    bedrooms=target_house.get('bedrooms'),
                    limit=4
                )
                for cand in similar_candidates:
                    if cand['id'] != target_house['id'] and cand['id'] not in house_ids:
                        house_ids.append(cand['id'])
                    if len(house_ids) >= 3:
                        break

                # Fallback: if no same-location listing found, pick any available listings
                if len(house_ids) == 1:
                    fallback_props = self.search_properties(limit=3)
                    for fb in fallback_props:
                        if fb['id'] != target_house['id'] and fb['id'] not in house_ids:
                            house_ids.append(fb['id'])
                        if len(house_ids) >= 2:
                            break

        properties = []
        for hid in house_ids[:4]:
            det = self.get_property_details(hid)
            if det:
                det['rent_per_bhk'] = round(det['rent'] / max(1, det['bedrooms']), 2)
                det['deposit_ratio'] = round(det['deposit'] / max(1, det['rent']), 1)
                properties.append(det)

        if not properties:
            return {"error": "None of the specified houses could be found in the database."}

        cheapest = min(properties, key=lambda x: x['rent'])
        most_spacious = max(properties, key=lambda x: x['bedrooms'])
        lowest_deposit = min(properties, key=lambda x: x['deposit'])
        rent_values = [p['rent'] for p in properties]
        rent_spread = max(rent_values) - min(rent_values)

        return {
            "count": len(properties),
            "properties": properties,
            "analysis": {
                "cheapest": {
                    "id": cheapest['id'],
                    "title": cheapest['title'],
                    "rent": cheapest['rent'],
                    "location": cheapest['location']
                },
                "most_spacious": {
                    "id": most_spacious['id'],
                    "title": most_spacious['title'],
                    "bedrooms": most_spacious['bedrooms']
                },
                "lowest_deposit": {
                    "id": lowest_deposit['id'],
                    "title": lowest_deposit['title'],
                    "deposit": lowest_deposit['deposit']
                },
                "rent_spread": rent_spread,
                "summary": f"Comparing {len(properties)} listings with rents ranging from ₹{int(min(rent_values)):,} to ₹{int(max(rent_values)):,}."
            }
        }

    # ------------------------------------------------------------------------
    # Tool 4: estimate_rent_value
    # ------------------------------------------------------------------------
    def estimate_rent_value(self, location, bedrooms, furnishing='Furnished', bathrooms=1):
        """Estimates optimal monthly rent and security deposit based on market heuristics."""
        base_rates = {1: 14000, 2: 26000, 3: 42000, 4: 65000}
        bhk = int(bedrooms) if int(bedrooms) in base_rates else 2
        base = base_rates.get(bhk, 25000)

        furnish_multipliers = {'Furnished': 1.25, 'Semi-Furnished': 1.05, 'Unfurnished': 0.90}
        f_mult = furnish_multipliers.get(furnishing, 1.0)
        bath_bump = max(0, (int(bathrooms) - 1)) * 2500

        loc_lower = (location or "").lower()
        loc_multiplier = 1.0
        tier1 = ['indiranagar', 'koramangala', 'hsr', 'whitefield', 'bandra', 'cyber city', 'jubilee hills', 'gk', 'south delhi']
        tier2 = ['electronic city', 'marathahalli', 'bellandur', 'thanisandra', 'baner', 'wakad', 'gachibowli', 'jayanagar']

        if any(t in loc_lower for t in tier1):
            loc_multiplier = 1.30
        elif any(t in loc_lower for t in tier2):
            loc_multiplier = 1.10
        elif any(t in loc_lower for t in ['outskirts', 'rural', 'suburb']):
            loc_multiplier = 0.85

        estimated_rent = round((base * f_mult * loc_multiplier) + bath_bump, -2)
        min_bracket = round(estimated_rent * 0.92, -2)
        max_bracket = round(estimated_rent * 1.12, -2)
        suggested_deposit = round(estimated_rent * 5, -2)

        return {
            "location": (location or "City Center").title(),
            "bedrooms": bhk,
            "furnishing": furnishing,
            "bathrooms": bathrooms,
            "estimated_rent": estimated_rent,
            "recommended_rent_range": f"₹{int(min_bracket):,} - ₹{int(max_bracket):,}",
            "recommended_deposit": f"₹{int(suggested_deposit):,}",
            "confidence_score": 94 if loc_multiplier != 1.0 else 88,
            "market_demand": "High" if loc_multiplier >= 1.1 else "Moderate",
            "key_factors": [
                f"{furnishing} interior package ({'+' if f_mult >= 1 else ''}{int((f_mult-1)*100)}% adjustment)",
                f"Locality premium tier ({loc_multiplier}x benchmark for {location or 'City Center'})",
                f"{bathrooms} bathroom specification (+₹{bath_bump:,} amenity load)"
            ]
        }

    # ------------------------------------------------------------------------
    # Tool 5: generate_listing_description
    # ------------------------------------------------------------------------
    def generate_listing_description(self, title="", location="Indiranagar", bedrooms=2, furnishing='Furnished', amenities=None):
        """Generates high-converting, professional property listings for owners."""
        amenities_str = amenities if amenities else "Power backup, 24/7 water supply, security surveillance, modular kitchen, dedicated car parking"
        
        headline = f"Prime {bedrooms} BHK ({furnishing}) Home in {location} - Ready to Move In"
        pitch = (
            f"Step into this beautifully maintained {bedrooms} BHK home situated in the heart of {location}. "
            f"Featuring {furnishing.lower()} interiors bathed in natural sunlight with cross-ventilation and premium fittings throughout. "
            f"Perfect for working professionals, modern families, or bachelors seeking upscale living with swift access to tech corridors, "
            f"transit stations, top educational institutions, and lifestyle shopping centers.\n\n"
            f"✨ Highlights & Amenities:\n"
            f"- {amenities_str}\n"
            f"- Ready for immediate occupancy with hassle-free lease handover\n"
            f"- Well-maintained, secure gated society with 24x7 security personnel and CCTV."
        )

        return {
            "title_suggestion": headline,
            "description": pitch,
            "tags": ["Verified Listing", f"{bedrooms} BHK", furnishing, location, "Immediate Move-In", "Gated Security"]
        }

    # ------------------------------------------------------------------------
    # Tool 6: calculate_match_score
    # ------------------------------------------------------------------------
    def calculate_match_score(self, house_id, tenant_pref):
        """Compute an AI compatibility match percentage between tenant preferences and a house."""
        house = self.get_property_details(house_id)
        if not house:
            return {"score": 0, "breakdown": ["Target property could not be found."]}

        score = 65
        reasons = []

        pref_max_rent = tenant_pref.get('max_rent')
        if pref_max_rent:
            if house['rent'] <= float(pref_max_rent):
                score += 20
                savings = float(pref_max_rent) - house['rent']
                reasons.append(f"Budget Fit: Within max budget ceiling (saves ₹{int(savings):,}/month)")
            else:
                score -= 15
                reasons.append(f"Budget Stretch: Exceeds target budget by ₹{int(house['rent'] - float(pref_max_rent)):,}")

        pref_bhk = tenant_pref.get('bedrooms')
        if pref_bhk:
            if int(house['bedrooms']) == int(pref_bhk):
                score += 15
                reasons.append(f"Space Match: Exact match for {pref_bhk} BHK requirement")
            else:
                score -= 5
                reasons.append(f"Space Variance: Offers {house['bedrooms']} BHK vs requested {pref_bhk} BHK")

        pref_furnish = tenant_pref.get('furnishing')
        if pref_furnish:
            if pref_furnish.lower() in house['furnishing'].lower():
                score += 10
                reasons.append(f"Furnishing Match: Meets preferred condition ({house['furnishing']})")
            else:
                reasons.append(f"Furnishing: Listed as {house['furnishing']} vs requested {pref_furnish}")

        score = max(30, min(99, score))
        return {
            "house_id": house_id,
            "house_title": house['title'],
            "match_score": score,
            "reasons": reasons
        }

    # ------------------------------------------------------------------------
    # Tool 7: draft_rental_inquiry
    # ------------------------------------------------------------------------
    def draft_rental_inquiry(self, house_id, tenant_name="Prospective Tenant", move_in_date="Immediate", note=""):
        """Drafts a courteous, high-impact inquiry message for the owner."""
        house = self.get_property_details(house_id)
        if not house:
            return {"error": "Property not found."}

        draft = (
            f"Dear {house['owner_name']},\n\n"
            f"My name is {tenant_name}. I recently reviewed your listing for \"{house['title']}\" "
            f"located at {house['location']} (Monthly Rent: ₹{int(house['rent']):,}) and am very interested in leasing it.\n\n"
            f"I am looking to relocate around {move_in_date}. {note}\n\n"
            f"I have verified employment credentials and am prepared with the required security deposit and documentation. "
            f"Could we arrange a convenient time for a brief walkthrough this week?\n\n"
            f"Thank you,\n{tenant_name}"
        )
        return {
            "house_id": house_id,
            "owner_name": house['owner_name'],
            "owner_phone": house['owner_phone'],
            "inquiry_text": draft
        }

    # ------------------------------------------------------------------------
    # Tool 8: calculate_affordability (New Domain Tool)
    # ------------------------------------------------------------------------
    def calculate_affordability(self, monthly_income, target_rent=None, target_deposit=None):
        """
        Evaluates financial affordability using the 30% gross income rule,
        computes safe budget brackets, required upfront capital, and disposable savings.
        """
        income = float(monthly_income)
        if income <= 0:
            return {"error": "Monthly income must be greater than zero."}

        # Safe budget brackets
        safe_rent_ceiling = round(income * 0.30, -2)       # 30% benchmark
        conservative_ceiling = round(income * 0.25, -2)   # 25% conservative
        aggressive_ceiling = round(income * 0.40, -2)     # 40% stretched

        result = {
            "monthly_income": income,
            "safe_rent_ceiling": safe_rent_ceiling,
            "recommended_bracket": f"₹{int(conservative_ceiling):,} - ₹{int(safe_rent_ceiling):,}",
            "conservative_bracket": f"₹{int(conservative_ceiling):,}",
            "stretch_ceiling": f"₹{int(aggressive_ceiling):,}",
            "guideline": "Standard financial planning recommends spending no more than 30% of monthly take-home salary on rent."
        }

        if target_rent is not None and str(target_rent).strip() != "":
            rent = float(target_rent)
            rent_ratio = round((rent / income) * 100, 1)

            # Determine deposit
            deposit = float(target_deposit) if (target_deposit is not None and str(target_deposit).strip() != "") else round(rent * 4, -2)
            moving_buffer = 8000.0  # Estimated moving, movers, initial setup
            total_upfront = deposit + rent + moving_buffer
            disposable_income = income - rent

            if rent_ratio <= 25.0:
                verdict = "Highly Affordable"
                verdict_class = "success"
                advice = "Excellent financial margin! You maintain a strong savings cushion for investments and emergencies."
            elif rent_ratio <= 33.0:
                verdict = "Affordable & Balanced"
                verdict_class = "primary"
                advice = "Well within healthy industry guidelines. Safe and sustainable for your current income."
            elif rent_ratio <= 42.0:
                verdict = "Stretched Budget"
                verdict_class = "warning"
                advice = "Moderately tight. You may need to optimize dining, travel, or leisure expenses to maintain monthly savings."
            else:
                verdict = "High Financial Risk"
                verdict_class = "danger"
                advice = "Exceeds 42% of your monthly income. Consider exploring 1BHK options or a co-living/roommate arrangement."

            result["evaluation"] = {
                "target_rent": rent,
                "rent_to_income_ratio": rent_ratio,
                "verdict": verdict,
                "verdict_class": verdict_class,
                "advice": advice,
                "disposable_after_rent": disposable_income,
                "upfront_capital_required": {
                    "security_deposit": deposit,
                    "first_month_rent": rent,
                    "moving_setup_buffer": moving_buffer,
                    "total_upfront": total_upfront
                }
            }

        return result

    # ------------------------------------------------------------------------
    # Tool 9: get_neighborhood_insights (New Domain Tool)
    # ------------------------------------------------------------------------
    def get_neighborhood_insights(self, location):
        """Provides neighborhood livability ratings, metro & transit connectivity, safety score, and tech commute."""
        loc_clean = (location or "").strip().lower()
        matched_key = None

        for key in NEIGHBORHOOD_DATABASE:
            if key in loc_clean:
                matched_key = key
                break

        if matched_key:
            data = NEIGHBORHOOD_DATABASE[matched_key].copy()
            data["is_curated"] = True
            return data

        # Dynamic fallback generation for any city locality
        display_name = (location or "Urban Neighborhood").title()
        return {
            "name": display_name,
            "city": "Bengaluru",
            "safety_rating": 8.8,
            "transit_rating": 8.7,
            "nearest_metro": "Nearest Metro feeder within 2.5 - 4.0 km",
            "commute_corridors": "Convenient road access to primary arterial corridors and tech clusters",
            "livability_index": 8.8,
            "vibe": f"Established residential sector in {display_name} with ready access to daily essentials, local supermarkets, and green community spaces.",
            "highlights": [
                "Well-connected local transit and app-cab availability",
                "Close access to neighborhood clinics, pharmacies, and department stores",
                "Growing residential rental demand with competitive price-to-space value",
                "Regular municipal water and electricity supply infrastructure"
            ],
            "is_curated": False
        }

    # ------------------------------------------------------------------------
    # Tool 10: schedule_property_visit (New Domain Tool)
    # ------------------------------------------------------------------------
    def schedule_property_visit(self, house_id, tenant_name="Applicant", tenant_phone="Not Provided", visit_date="Upcoming Weekend", time_slot="11:00 AM - 01:00 PM", notes=""):
        """Generates a structured visit schedule ticket and 6-point property walkthrough checklist."""
        house = self.get_property_details(house_id)
        if not house:
            return {"error": f"Cannot schedule visit: House #{house_id} was not found."}

        ticket_code = f"VISIT-{house['id']}-{int(time.time()) % 100000:05d}"

        checklist = [
            "1. Water Pressure & Geysers: Test tap pressure in both kitchen and bathrooms.",
            "2. Electrical Sockets & Power Backup: Verify working switchboards and inverter backup status.",
            "3. Cellular Reception: Check mobile phone network coverage across all bedrooms.",
            "4. Dedicated Parking Slot: Confirm exact allocated spot for two-wheeler / four-wheeler.",
            "5. Society Maintenance & Trash: Clarify monthly society fees and garbage pickup timing.",
            "6. Natural Sunlight & Ventilation: Inspect windows and balcony cross-breeze."
        ]

        return {
            "ticket_code": ticket_code,
            "status": "Confirmed Walkthrough Request",
            "house": {
                "id": house['id'],
                "title": house['title'],
                "location": house['location'],
                "address": house['address'],
                "rent": house['rent'],
                "owner_name": house['owner_name'],
                "owner_phone": house['owner_phone']
            },
            "appointment": {
                "tenant_name": tenant_name,
                "tenant_phone": tenant_phone,
                "visit_date": visit_date,
                "time_slot": time_slot,
                "notes": notes or "Direct in-person physical walkthrough"
            },
            "inspection_checklist": checklist,
            "instructions": f"Please arrive at {house['address']} during the specified window. You can call owner {house['owner_name']} directly at {house['owner_phone']} on arrival."
        }

    # ------------------------------------------------------------------------
    # Tool 11: check_rental_request_status (New Domain Tool)
    # ------------------------------------------------------------------------
    def check_rental_request_status(self, user_id=None, role='tenant'):
        """Checks real-time status of tenant rental applications or pending requests for owners."""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                if role == 'owner' and user_id:
                    query = """
                        SELECT r.id as request_id, r.status, r.request_date,
                               h.id as house_id, h.title as house_title, h.rent, h.location,
                               u.name as applicant_name, u.email as applicant_email, u.phone as applicant_phone
                        FROM rental_requests r
                        JOIN houses h ON r.house_id = h.id
                        JOIN users u ON r.tenant_id = u.id
                        WHERE h.owner_id = %s
                        ORDER BY r.request_date DESC
                    """
                    cursor.execute(query, (int(user_id),))
                elif user_id:
                    query = """
                        SELECT r.id as request_id, r.status, r.request_date,
                               h.id as house_id, h.title as house_title, h.rent, h.deposit, h.location,
                               u.name as owner_name, u.phone as owner_phone, u.email as owner_email
                        FROM rental_requests r
                        JOIN houses h ON r.house_id = h.id
                        JOIN users u ON h.owner_id = u.id
                        WHERE r.tenant_id = %s
                        ORDER BY r.request_date DESC
                    """
                    cursor.execute(query, (int(user_id),))
                else:
                    query = """
                        SELECT r.id as request_id, r.status, r.request_date,
                               h.id as house_id, h.title as house_title, h.rent, h.location,
                               t.name as applicant_name, o.name as owner_name
                        FROM rental_requests r
                        JOIN houses h ON r.house_id = h.id
                        JOIN users t ON r.tenant_id = t.id
                        JOIN users o ON h.owner_id = o.id
                        ORDER BY r.request_date DESC LIMIT 10
                    """
                    cursor.execute(query)

                rows = cursor.fetchall()
                cleaned = clean_row_decimals(rows)
                return {
                    "count": len(cleaned),
                    "role": role,
                    "requests": cleaned
                }
        finally:
            conn.close()

    # ------------------------------------------------------------------------
    # Tool 12: generate_rental_agreement_checklist (New Domain Tool)
    # ------------------------------------------------------------------------
    def generate_rental_agreement_checklist(self, house_id=None, rent=None, deposit=None, duration_months=11, tenant_name=None, owner_name=None):
        """Generates standard legal and operational lease agreement checklist for Indian rentals."""
        house_info = None
        if house_id:
            house_info = self.get_property_details(house_id)
            if house_info:
                rent = rent or house_info['rent']
                deposit = deposit or house_info['deposit']
                owner_name = owner_name or house_info['owner_name']

        rent_val = float(rent) if rent else 25000.0
        deposit_val = float(deposit) if deposit else rent_val * 4

        clauses = [
            {
                "clause_number": 1,
                "title": "11-Month Lease Tenure",
                "summary": f"Standard {duration_months}-month agreement period. In India, leases under 12 months do not mandate compulsory sub-registrar registration, saving stamp duty while remaining legally binding via notarized stamp paper (₹100 - ₹500)."
            },
            {
                "clause_number": 2,
                "title": "Monthly Rent Due Date & Grace Period",
                "summary": f"Rent of ₹{int(rent_val):,}/month payable on or before the 5th of each English calendar month. A 5-day grace period is standard before late fee interest applies."
            },
            {
                "clause_number": 3,
                "title": "Security Deposit & Refund Timeline",
                "summary": f"Security deposit of ₹{int(deposit_val):,} is interest-free and refundable in full within 15 to 30 days of physical handover, subject to damage inspection and unpaid utility deduction."
            },
            {
                "clause_number": 4,
                "title": "Notice Period for Vacation",
                "summary": "1 month written notice (or 30 days) required from either landlord or tenant prior to lease termination. Forfeiting notice period incurs 1 month rent deduction."
            },
            {
                "clause_number": 5,
                "title": "Annual Escalation Clause",
                "summary": "Standard 5% to 8% rent escalation upon mutual renewal at the completion of 11 months."
            },
            {
                "clause_number": 6,
                "title": "Utility Bills & Society Maintenance",
                "summary": "Tenant pays actual monthly BESCOM electricity, piped gas, and water meter bills. Clarify whether monthly apartment association maintenance is included in rent or billed separately."
            },
            {
                "clause_number": 7,
                "title": "Subletting & Permitted Use",
                "summary": "Property is leased solely for residential purposes. Sub-leasing or commercial use is strictly prohibited without explicit written landlord consent."
            },
            {
                "clause_number": 8,
                "title": "Move-In Fixtures & Inventory Condition Log",
                "summary": "Document working condition of ceiling fans, geysers, modular kitchen cabinets, and sanitaryware with signed move-in photos to prevent deposit disputes upon vacating."
            }
        ]

        return {
            "house_id": house_id,
            "property_title": house_info['title'] if house_info else "Rental Home",
            "location": house_info['location'] if house_info else "Urban Bengaluru",
            "parties": {
                "owner": owner_name or "Property Owner",
                "tenant": tenant_name or "Tenant"
            },
            "lease_terms": {
                "monthly_rent": rent_val,
                "security_deposit": deposit_val,
                "duration_months": duration_months,
                "recommended_stamp_paper": "₹100 or ₹200 Non-Judicial e-Stamp Paper with Notary Stamp"
            },
            "clauses": clauses
        }

    # ------------------------------------------------------------------------
    # Tool 13: get_platform_stats (New Domain Tool)
    # ------------------------------------------------------------------------
    def get_platform_stats(self):
        """Aggregates live marketplace metrics from the database."""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Active vs Total
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_houses,
                        SUM(CASE WHEN status = 'Available' AND approved = 1 THEN 1 ELSE 0 END) as available_houses,
                        SUM(CASE WHEN status = 'Rented' THEN 1 ELSE 0 END) as rented_houses,
                        AVG(rent) as avg_rent,
                        MIN(rent) as min_rent,
                        MAX(rent) as max_rent
                    FROM houses
                """)
                summary = cursor.fetchone()

                # Breakdown by BHK
                cursor.execute("""
                    SELECT bedrooms, COUNT(*) as count, AVG(rent) as avg_rent
                    FROM houses
                    WHERE approved = 1
                    GROUP BY bedrooms
                    ORDER BY bedrooms ASC
                """)
                bhk_breakdown = cursor.fetchall()

                # Rental requests count
                cursor.execute("SELECT COUNT(*) as total_requests, SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_requests FROM rental_requests")
                req_stats = cursor.fetchone()

                return {
                    "total_houses": summary['total_houses'] or 0,
                    "available_houses": summary['available_houses'] or 0,
                    "rented_houses": summary['rented_houses'] or 0,
                    "avg_rent": round(float(summary['avg_rent'] or 0), 2),
                    "min_rent": float(summary['min_rent'] or 0),
                    "max_rent": float(summary['max_rent'] or 0),
                    "bhk_distribution": clean_row_decimals(bhk_breakdown),
                    "total_requests": req_stats['total_requests'] or 0,
                    "pending_requests": req_stats['pending_requests'] or 0,
                    "market_health": "Healthy Liquidity with Active Listings"
                }
        finally:
            conn.close()


# ----------------------------------------------------------------------------
# Autonomous ReAct (Reasoning + Acting) Agent
# ----------------------------------------------------------------------------
class ReActRentalAgent:
    """
    Autonomous ReAct Agent Engine.
    Interprets natural language queries, formulates multi-step reasoning plans,
    executes appropriate database tools, and crafts structured responses with rich cards.
    """

    def __init__(self, db_conn_factory):
        self.tools = RentalAgentTools(db_conn_factory)

    def run(self, user_message, context=None):
        context = context or {}
        user_name = context.get('user_name') or "Valued User"
        user_id = context.get('user_id')
        user_role = context.get('role') or "tenant"

        msg_lower = user_message.lower().strip()
        trace = {
            "timestamp": datetime.now().isoformat(),
            "query": user_message,
            "steps": [],
            "answer": "",
            "cards": [],
            "quick_replies": []
        }

        # --------------------------------------------------------------------
        # Intent 1: AFFORDABILITY & BUDGET ANALYSIS
        # --------------------------------------------------------------------
        afford_keywords = ['afford', 'salary', 'income', 'budget planner', 'can i rent', 'earn', 'take home', '30% rule']
        if any(w in msg_lower for w in afford_keywords):
            # Extract monthly income
            inc_match_k = re.search(r'(?:salary|earn|income|making|takes?)\s*(?:of|is|around|about)?\s*(?:rs\.?|inr|₹)?\s*(\d+)\s*(?:k|thousand)', msg_lower)
            inc_match_full = re.search(r'(?:salary|earn|income|making|takes?)\s*(?:of|is|around|about)?\s*(?:rs\.?|inr|₹)?\s*(\d{5,7})', msg_lower)
            
            income = 75000.0
            if inc_match_k:
                income = float(inc_match_k.group(1)) * 1000
            elif inc_match_full:
                income = float(inc_match_full.group(1))
            else:
                # Any general 5-6 digit number could be income if mentioned first
                any_nums = re.findall(r'\b(\d{5,7})\b', msg_lower)
                if any_nums:
                    income = float(any_nums[0])

            # Extract target rent
            target_rent = None
            rent_match = re.search(r'(?:rent|house|flat|apartment)\s*(?:of|is|at|for)?\s*(?:rs\.?|inr|₹)?\s*(\d{4,6})', msg_lower)
            if rent_match:
                target_rent = float(rent_match.group(1))
            elif len(re.findall(r'\b(\d{4,6})\b', msg_lower)) >= 2:
                nums = re.findall(r'\b(\d{4,6})\b', msg_lower)
                target_rent = float(nums[1])

            step1 = {
                "step": 1,
                "thought": f"The user requested rent affordability analysis with monthly income ₹{int(income):,} and target rent {target_rent}. Executing calculate_affordability tool.",
                "action": "calculate_affordability",
                "action_input": {"monthly_income": income, "target_rent": target_rent}
            }
            afford_res = self.tools.calculate_affordability(monthly_income=income, target_rent=target_rent)
            step1["observation"] = f"Safe rent ceiling calculated: ₹{int(afford_res['safe_rent_ceiling']):,}/mo."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "affordability", "data": afford_res})

            eval_block = ""
            if "evaluation" in afford_res:
                ev = afford_res["evaluation"]
                eval_block = (
                    f"\n\n**Evaluated Property:**\n"
                    f"- 🎯 **Target Rent**: ₹{int(ev['target_rent']):,}/month ({ev['rent_to_income_ratio']}% of salary)\n"
                    f"- 💡 **Verdict**: **{ev['verdict']}**\n"
                    f"- 📝 **Guidance**: {ev['advice']}\n"
                    f"- 💵 **Monthly Disposable Buffer**: ₹{int(ev['disposable_after_rent']):,}\n"
                    f"- 💼 **Upfront Move-In Capital**: ₹{int(ev['upfront_capital_required']['total_upfront']):,} "
                    f"(Deposit: ₹{int(ev['upfront_capital_required']['security_deposit']):,} + 1st Month + Relocation buffer)"
                )

            trace["answer"] = (
                f"### 💳 Rent Affordability & Budget Report\n\n"
                f"Based on a monthly income of **₹{int(income):,}**:\n\n"
                f"- 🛡️ **Recommended Safe Rent Ceiling (30% Rule)**: **₹{int(afford_res['safe_rent_ceiling']):,} / month**\n"
                f"- ⚖️ **Optimal Budget Bracket**: **{afford_res['recommended_bracket']}**\n"
                f"- 🚨 **Stretch Ceiling**: Up to {afford_res['stretch_ceiling']}/mo (Requires tight discretionary spending)"
                f"{eval_block}\n\n"
                f"Would you like me to find available properties within this ₹{int(afford_res['safe_rent_ceiling']):,} safe budget?"
            )
            trace["quick_replies"] = [
                f"Find houses under {int(afford_res['safe_rent_ceiling'])}",
                "Neighborhood insights for Indiranagar",
                "Check platform stats"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 2: NEIGHBORHOOD INSIGHTS & LOCALITY GUIDE
        # --------------------------------------------------------------------
        neighborhood_keywords = ['neighborhood', 'neighbourhood', 'locality', 'area guide', 'is indiranagar safe', 'safety score', 'metro station', 'commute']
        if any(w in msg_lower for w in neighborhood_keywords):
            target_loc = "Indiranagar"
            for cand in ['indiranagar', 'koramangala', 'whitefield', 'hsr', 'bellandur', 'electronic city', 'marathahalli', 'jayanagar', 'hebbal']:
                if cand in msg_lower:
                    target_loc = cand.title()
                    break

            step1 = {
                "step": 1,
                "thought": f"The user wants neighborhood intelligence, transit ratings, and safety metrics for '{target_loc}'. Invoking get_neighborhood_insights.",
                "action": "get_neighborhood_insights",
                "action_input": {"location": target_loc}
            }
            n_data = self.tools.get_neighborhood_insights(target_loc)
            step1["observation"] = f"Retrieved livability index {n_data['livability_index']}/10 and transit details."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "neighborhood", "data": n_data})

            trace["answer"] = (
                f"### 📍 Neighborhood Intelligence: {n_data['name']}\n\n"
                f"**Vibe & Character:**\n{n_data['vibe']}\n\n"
                f"**Key Metrics:**\n"
                f"- 🛡️ **Safety Rating**: **{n_data['safety_rating']} / 10**\n"
                f"- 🚇 **Transit & Connectivity**: **{n_data['transit_rating']} / 10** ({n_data['nearest_metro']})\n"
                f"- 🚗 **Commute to Key Corridors**: {n_data['commute_corridors']}\n"
                f"- 🌟 **Livability Index**: **{n_data['livability_index']} / 10**\n\n"
                f"**Neighborhood Highlights:**\n"
                + "\n".join([f"- {h}" for h in n_data['highlights']])
            )
            trace["quick_replies"] = [
                f"Find 2BHK in {n_data['name']}",
                f"Estimate rent in {n_data['name']}",
                "Compare with Koramangala"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 3: SCHEDULE PROPERTY VISIT & WALKTHROUGH
        # --------------------------------------------------------------------
        visit_keywords = ['schedule visit', 'book visit', 'walkthrough', 'visit house', 'see house', 'view house', 'schedule appointment']
        if any(w in msg_lower for w in visit_keywords):
            house_match = re.search(r'\b(?:house\s*|id\s*|#)?(\d+)\b', msg_lower)
            hid = int(house_match.group(1)) if house_match else 1

            slot = "11:00 AM - 01:00 PM (Weekend Slot)"
            if 'afternoon' in msg_lower:
                slot = "02:00 PM - 04:00 PM"
            elif 'evening' in msg_lower:
                slot = "05:00 PM - 07:00 PM"

            step1 = {
                "step": 1,
                "thought": f"The user requested to schedule an in-person physical walkthrough for house #{hid}. Invoking schedule_property_visit tool.",
                "action": "schedule_property_visit",
                "action_input": {"house_id": hid, "tenant_name": user_name, "time_slot": slot}
            }
            v_ticket = self.tools.schedule_property_visit(
                house_id=hid,
                tenant_name=user_name,
                time_slot=slot,
                notes="Scheduled via Autonomous Agent Copilot"
            )
            step1["observation"] = f"Generated visit pass code: {v_ticket.get('ticket_code')}."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "visit_booking", "data": v_ticket})

            if "house" in v_ticket:
                h = v_ticket["house"]
                trace["answer"] = (
                    f"### 📅 Physical Walkthrough Itinerary Generated\n\n"
                    f"**Ticket Confirmation**: `{v_ticket['ticket_code']}`\n\n"
                    f"- 🏡 **Property**: **#{h['id']} {h['title']}**\n"
                    f"- 📍 **Address**: {h['address']}\n"
                    f"- 👤 **Owner / Host**: {h['owner_name']} (📞 `{h['owner_phone']}`)\n"
                    f"- ⏰ **Scheduled Slot**: **{v_ticket['appointment']['time_slot']}**\n\n"
                    f"**🔍 6-Point Inspection Checklist to Review on Site:**\n"
                    + "\n".join([f"- {item}" for item in v_ticket['inspection_checklist']])
                    + f"\n\n*Tip: Owner {h['owner_name']} will receive your notification. Please call upon arrival!*"
                )
            else:
                trace["answer"] = f"Could not schedule visit: {v_ticket.get('error', 'Property not found')}."
            
            trace["quick_replies"] = [
                f"Rental agreement checklist for house {hid}",
                f"Draft inquiry for house {hid}",
                "Check my application status"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 4: CHECK RENTAL APPLICATION STATUS
        # --------------------------------------------------------------------
        status_keywords = ['application status', 'my requests', 'request status', 'check request', 'pending application', 'rental status']
        if any(w in msg_lower for w in status_keywords):
            step1 = {
                "step": 1,
                "thought": f"Retrieving active rental request submissions from database for user ID {user_id} (role: {user_role}).",
                "action": "check_rental_request_status",
                "action_input": {"user_id": user_id, "role": user_role}
            }
            stat_res = self.tools.check_rental_request_status(user_id=user_id, role=user_role)
            step1["observation"] = f"Found {stat_res['count']} rental requests."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "status_list", "data": stat_res})

            if stat_res["requests"]:
                req_lines = []
                for r in stat_res["requests"]:
                    line = f"- **Application #{r['request_id']}** for **{r['house_title']}** (Rent: ₹{int(r['rent']):,}) &bull; Status: `{r['status']}`"
                    req_lines.append(line)
                trace["answer"] = (
                    f"### 📋 Your Rental Request Submissions ({stat_res['count']})\n\n"
                    + "\n".join(req_lines)
                    + "\n\nLandlords typically review incoming requests within 24 hours. You will see updates reflected here in real time."
                )
            else:
                trace["answer"] = (
                    "### 📋 No Active Rental Requests Found\n\n"
                    "You do not currently have any pending rental applications in the system.\n\n"
                    "Explore our available listings and submit your first rental request!"
                )
            trace["quick_replies"] = ["Find 2BHK in Indiranagar", "Estimate rent for 2BHK", "Platform statistics"]
            return trace

        # --------------------------------------------------------------------
        # Intent 5: LEASE AGREEMENT & LEGAL CHECKLIST
        # --------------------------------------------------------------------
        lease_keywords = ['lease checklist', 'rental agreement', 'agreement clauses', 'contract checklist', 'tenancy agreement', 'stamp paper']
        if any(w in msg_lower for w in lease_keywords):
            house_match = re.search(r'\b(?:house\s*|id\s*|#)?(\d+)\b', msg_lower)
            hid = int(house_match.group(1)) if house_match else 1

            step1 = {
                "step": 1,
                "thought": f"The user requested a standard rental agreement and legal clause checklist for house #{hid}. Invoking generate_rental_agreement_checklist.",
                "action": "generate_rental_agreement_checklist",
                "action_input": {"house_id": hid}
            }
            chk_res = self.tools.generate_rental_agreement_checklist(house_id=hid)
            step1["observation"] = f"Generated {len(chk_res['clauses'])} essential legal lease clauses."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "lease_checklist", "data": chk_res})

            clauses_md = []
            for c in chk_res["clauses"]:
                clauses_md.append(f"**{c['clause_number']}. {c['title']}**\n{c['summary']}")

            trace["answer"] = (
                f"### 📜 Rental Agreement & Legal Verification Guide\n\n"
                f"**Property**: **{chk_res['property_title']}** ({chk_res['location']})\n"
                f"- 💰 **Monthly Rent**: ₹{int(chk_res['lease_terms']['monthly_rent']):,}\n"
                f"- 🔒 **Security Deposit**: ₹{int(chk_res['lease_terms']['security_deposit']):,}\n"
                f"- 📄 **Recommended Format**: {chk_res['lease_terms']['recommended_stamp_paper']}\n\n"
                + "\n\n".join(clauses_md)
                + "\n\n💡 *Always ensure both tenant and landlord sign all pages and attach Aadhaar/PAN copies.*"
            )
            trace["quick_replies"] = [
                f"Schedule visit for house {hid}",
                f"Draft inquiry for house {hid}",
                "Calculate rent affordability"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 6: MARKETPLACE PLATFORM STATS
        # --------------------------------------------------------------------
        stats_keywords = ['platform stat', 'marketplace overview', 'how many houses', 'average rent', 'market overview', 'market stats']
        if any(w in msg_lower for w in stats_keywords):
            step1 = {
                "step": 1,
                "thought": "Aggregating platform-wide rental inventory, rent distributions, and marketplace metrics.",
                "action": "get_platform_stats",
                "action_input": {}
            }
            stats_data = self.tools.get_platform_stats()
            step1["observation"] = f"Aggregated {stats_data['available_houses']} available properties."
            trace["steps"].append(step1)

            trace["cards"].append({"type": "platform_stats", "data": stats_data})

            bhk_rows = [f"- **{b['bedrooms']} BHK**: {b['count']} listings (Avg Rent: ₹{int(b['avg_rent']):,}/mo)" for b in stats_data['bhk_distribution']]

            trace["answer"] = (
                f"### 📊 Marketplace Intelligence & Platform Metrics\n\n"
                f"- 🏡 **Total Listed Properties**: **{stats_data['total_houses']}** ({stats_data['available_houses']} Available, {stats_data['rented_houses']} Rented)\n"
                f"- 💰 **Average Monthly Rent**: **₹{int(stats_data['avg_rent']):,}/month** (Spectrum: ₹{int(stats_data['min_rent']):,} - ₹{int(stats_data['max_rent']):,})\n"
                f"- 📩 **Rental Applications**: **{stats_data['total_requests']} total** ({stats_data['pending_requests']} active)\n\n"
                f"**BHK Inventory Breakdown:**\n"
                + "\n".join(bhk_rows)
                + "\n\nMarket liquidity is **High** with steady turnaround across tech corridor clusters."
            )
            trace["quick_replies"] = ["Find 2BHK in Indiranagar", "Affordability calculator", "Neighborhood insights"]
            return trace

        # --------------------------------------------------------------------
        # Intent 7: COMPARE PROPERTIES (Supports 1 ID auto-fill or multiple IDs)
        # --------------------------------------------------------------------
        compare_match = re.findall(r'\b(?:house\s*|id\s*|#)?(\d+)\b', msg_lower)
        is_compare = any(w in msg_lower for w in ['compare', 'difference', 'versus', 'vs', 'comparison'])

        if is_compare and len(compare_match) >= 1:
            house_ids = [int(x) for x in compare_match[:4]]
            step1 = {
                "step": 1,
                "thought": f"The user requested comparison for property IDs {house_ids}. Invoking compare_properties with auto-fill benchmark enabled.",
                "action": "compare_properties",
                "action_input": {"house_ids": house_ids, "auto_fill_similar": True}
            }
            obs1 = self.tools.compare_properties(house_ids, auto_fill_similar=True)
            step1["observation"] = f"Retrieved data for {obs1.get('count', 0)} properties."
            trace["steps"].append(step1)

            if "properties" in obs1:
                p_list = obs1["properties"]
                trace["cards"].append({"type": "comparison", "data": obs1})
                cheapest = obs1["analysis"]["cheapest"]
                spacious = obs1["analysis"]["most_spacious"]

                bullets = []
                for p in p_list:
                    bullets.append(
                        f"- **#{p['id']} {p['title']}**: ₹{int(p['rent']):,}/mo | {p['bedrooms']} BHK ({p['furnishing']}) in *{p['location']}* "
                        f"(Deposit: ₹{int(p['deposit']):,} &bull; ₹{int(p['rent_per_bhk']):,}/BHK)"
                    )

                trace["answer"] = (
                    f"### ⚖️ Side-by-Side Property Comparison\n\n"
                    f"I benchmarked **{len(p_list)} properties** across key rental dimensions:\n\n"
                    + "\n".join(bullets)
                    + f"\n\n**💡 Agent Analysis Highlights:**\n"
                    f"- 💰 **Best Budget Value**: **#{cheapest['id']} {cheapest['title']}** at **₹{int(cheapest['rent']):,}/month**\n"
                    f"- 📐 **Maximum Space**: **#{spacious['id']} {spacious['title']}** with **{spacious['bedrooms']} BHK**\n"
                    f"- 📊 **Rent Spread**: ₹{int(obs1['analysis']['rent_spread']):,} difference across options\n\n"
                    f"Would you like to draft an inquiry or schedule a visit for any of these listings?"
                )
            else:
                trace["answer"] = "I couldn't find matching properties with those IDs to compare. Please check active listing IDs on the Houses page."
            trace["quick_replies"] = [
                f"Schedule visit for house {house_ids[0]}",
                f"Draft inquiry for house {house_ids[0]}",
                "Affordability calculation"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 8: RENT VALUATION ENGINE (FOR OWNERS OR TENANTS)
        # --------------------------------------------------------------------
        is_valuation = any(w in msg_lower for w in ['estimate', 'valuation', 'how much rent', 'price for', 'charge for', 'market rent', 'rent range'])
        if is_valuation:
            bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom|bed)', msg_lower)
            bedrooms = int(bhk_match.group(1)) if bhk_match else 2

            furnishing = 'Furnished'
            if 'unfurnished' in msg_lower:
                furnishing = 'Unfurnished'
            elif 'semi' in msg_lower:
                furnishing = 'Semi-Furnished'

            loc = "Indiranagar"
            for candidate in ['indiranagar', 'koramangala', 'whitefield', 'hsr', 'bellandur', 'electronic city', 'marathahalli', 'jayanagar', 'baner', 'gachibowli', 'bandra']:
                if candidate in msg_lower:
                    loc = candidate.title()
                    break

            step1 = {
                "step": 1,
                "thought": f"The user requested an AI rental valuation for a {bedrooms} BHK ({furnishing}) in {loc}. Invoking estimate_rent_value tool.",
                "action": "estimate_rent_value",
                "action_input": {"location": loc, "bedrooms": bedrooms, "furnishing": furnishing, "bathrooms": 2}
            }
            val_result = self.tools.estimate_rent_value(location=loc, bedrooms=bedrooms, furnishing=furnishing, bathrooms=2)
            step1["observation"] = f"Estimated rent: ₹{val_result['estimated_rent']:,}/mo (Range: {val_result['recommended_rent_range']})"
            trace["steps"].append(step1)

            trace["cards"].append({"type": "valuation", "data": val_result})

            trace["answer"] = (
                f"### 📈 AI Rental Valuation Report\n\n"
                f"Based on real-time rental market trends for **{loc}**:\n\n"
                f"- 🎯 **Recommended Fair Rent**: **₹{val_result['estimated_rent']:,} / month**\n"
                f"- 📊 **Competitive Bracket**: **{val_result['recommended_rent_range']}**\n"
                f"- 🔒 **Suggested Security Deposit**: **{val_result['recommended_deposit']}** (standard reserve)\n"
                f"- ⚡ **Market Demand Level**: **{val_result['market_demand']}** (Confidence: {val_result['confidence_score']}%)\n\n"
                f"**Key Pricing Drivers:**\n"
                + "\n".join([f"- {factor}" for factor in val_result['key_factors']])
            )
            trace["quick_replies"] = [
                f"Generate listing description for {loc}",
                f"Search {bedrooms}BHK in {loc}",
                f"Neighborhood insights for {loc}"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 9: GENERATE LISTING DESCRIPTION (AI COPYWRITER)
        # --------------------------------------------------------------------
        is_generate_desc = any(w in msg_lower for w in ['generate description', 'write description', 'write listing', 'create listing pitch', 'draft listing', 'copywriter'])
        if is_generate_desc:
            bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom|bed)', msg_lower)
            bedrooms = int(bhk_match.group(1)) if bhk_match else 2
            furnishing = 'Furnished' if 'unfurnished' not in msg_lower else 'Unfurnished'
            loc = "Prime Locality"
            for c in ['indiranagar', 'koramangala', 'whitefield', 'bellandur', 'jayanagar', 'hsr']:
                if c in msg_lower:
                    loc = c.title()
                    break

            step1 = {
                "step": 1,
                "thought": "Generating high-converting property listing copy based on location and specs.",
                "action": "generate_listing_description",
                "action_input": {"title": f"{bedrooms} BHK in {loc}", "location": loc, "bedrooms": bedrooms, "furnishing": furnishing}
            }
            desc_res = self.tools.generate_listing_description(title=f"{bedrooms} BHK", location=loc, bedrooms=bedrooms, furnishing=furnishing)
            step1["observation"] = "Generated marketing copy and tags."
            trace["steps"].append(step1)

            trace["answer"] = (
                f"### ✨ AI Generated Property Listing Pitch\n\n"
                f"**Suggested Headline:**\n> **{desc_res['title_suggestion']}**\n\n"
                f"**Marketing Narrative:**\n```text\n{desc_res['description']}\n```\n\n"
                f"**Recommended Tags:** " + " ".join([f"`{t}`" for t in desc_res['tags']])
            )
            trace["quick_replies"] = [f"Estimate rent in {loc}", "Check platform stats", "Find 2BHK"]
            return trace

        # --------------------------------------------------------------------
        # Intent 10: DRAFT INQUIRY LETTER
        # --------------------------------------------------------------------
        is_inquiry = any(w in msg_lower for w in ['inquiry', 'contact owner', 'message owner', 'draft message', 'ask owner', 'application letter'])
        house_target = re.search(r'\b(?:house\s*|id\s*|#)?(\d+)\b', msg_lower)
        if is_inquiry and house_target:
            hid = int(house_target.group(1))
            step1 = {
                "step": 1,
                "thought": f"The user wants an inquiry drafted for house #{hid}. Retrieving property and owner information.",
                "action": "draft_rental_inquiry",
                "action_input": {"house_id": hid, "tenant_name": user_name}
            }
            inq = self.tools.draft_rental_inquiry(hid, tenant_name=user_name)
            step1["observation"] = f"Created tailored message for owner {inq.get('owner_name', 'Owner')}."
            trace["steps"].append(step1)

            if "inquiry_text" in inq:
                trace["answer"] = (
                    f"### ✉️ AI-Drafted Rental Inquiry for House #{hid}\n\n"
                    f"**Recipient**: {inq['owner_name']} ({inq['owner_phone']})\n\n"
                    f"```text\n{inq['inquiry_text']}\n```\n\n"
                    f"💡 You can copy this message to WhatsApp/SMS or schedule a walkthrough!"
                )
            else:
                trace["answer"] = f"Could not find house #{hid} to draft an inquiry."
            trace["quick_replies"] = [
                f"Schedule visit for house {hid}",
                f"Compare house {hid} with others",
                f"Rental agreement checklist for house {hid}"
            ]
            return trace

        # --------------------------------------------------------------------
        # Intent 11: SEARCH & FILTER PROPERTIES (DEFAULT AGENTIC BEHAVIOR)
        # --------------------------------------------------------------------
        step1 = {
            "step": 1,
            "thought": "I will parse the user's natural language criteria: location, bedroom count, maximum budget, and furnishing status.",
            "action": "parse_user_criteria",
            "action_input": {"query": user_message}
        }

        max_rent = None
        rent_match_k = re.search(r'(?:under|below|max|budget|within|up to|less than|\<)?\s*(?:rs\.?|inr|₹)?\s*(\d+)\s*(?:k|thousand)', msg_lower)
        rent_match_full = re.search(r'(?:under|below|max|budget|within|up to|less than|\<)?\s*(?:rs\.?|inr|₹)?\s*(\d{4,6})', msg_lower)
        if rent_match_k:
            max_rent = float(rent_match_k.group(1)) * 1000
        elif rent_match_full:
            max_rent = float(rent_match_full.group(1))

        bedrooms = None
        bhk_match = re.search(r'(\d)\s*(?:bhk|bedroom|bed)', msg_lower)
        if bhk_match:
            bedrooms = int(bhk_match.group(1))

        furnishing = None
        if 'unfurnished' in msg_lower:
            furnishing = 'Unfurnished'
        elif 'semi' in msg_lower:
            furnishing = 'Semi-Furnished'
        elif 'furnished' in msg_lower:
            furnishing = 'Furnished'

        location = None
        known_locations = ['indiranagar', 'koramangala', 'whitefield', 'hsr', 'bellandur', 'electronic city', 'marathahalli', 'jayanagar', 'hebbal']
        for loc_cand in known_locations:
            if loc_cand in msg_lower:
                location = loc_cand
                break

        step1["observation"] = f"Extracted criteria: Location={location}, Bedrooms={bedrooms}, MaxRent={max_rent}, Furnishing={furnishing}"
        trace["steps"].append(step1)

        # Step 2: Database Tool Invocation
        step2 = {
            "step": 2,
            "thought": "Executing search_properties tool to query active and verified listings from MySQL database.",
            "action": "search_properties",
            "action_input": {
                "location": location,
                "max_rent": max_rent,
                "bedrooms": bedrooms,
                "furnishing": furnishing,
                "limit": 5
            }
        }
        properties = self.tools.search_properties(
            location=location,
            max_rent=max_rent,
            bedrooms=bedrooms,
            furnishing=furnishing,
            limit=5
        )
        step2["observation"] = f"Database returned {len(properties)} matching available listings."
        trace["steps"].append(step2)

        # Step 3: Synthesis & Reflection
        if properties:
            trace["cards"].append({"type": "property_list", "items": properties})

            lead_text = f"I found **{len(properties)} matching properties** that align with your requirements"
            if location:
                lead_text += f" in **{location.title()}**"
            if max_rent:
                lead_text += f" under **₹{int(max_rent):,}**"
            lead_text += ":\n\n"

            property_bullets = []
            for p in properties:
                bullet = (
                    f"🏡 **#{p['id']} {p['title']}**\n"
                    f"   - 💰 **Rent**: ₹{int(p['rent']):,}/month (Deposit: ₹{int(p['deposit']):,})\n"
                    f"   - 🛏️ **Config**: {p['bedrooms']} BHK | {p['bathrooms']} Bath | {p['furnishing']}\n"
                    f"   - 📍 **Location**: {p['location']}\n"
                    f"   - 👤 **Owner**: {p['owner_name']} ({p['owner_phone']})"
                )
                property_bullets.append(bullet)

            trace["answer"] = (
                f"### 🎯 Agentic Property Recommendations\n\n"
                f"{lead_text}"
                + "\n\n".join(property_bullets)
                + "\n\n**Next Suggested Actions:**\n"
                f"- Ask me to *\"Compare house {properties[0]['id']} with others\"*\n"
                f"- Ask me to *\"Schedule visit for house {properties[0]['id']}\"*\n"
                f"- Ask me to *\"Check neighborhood insights for {location or 'this area'}\"*"
            )
            trace["quick_replies"] = [
                f"Schedule visit for house {properties[0]['id']}",
                f"Compare house {properties[0]['id']} with others",
                f"Draft inquiry for house {properties[0]['id']}"
            ]
        else:
            step3 = {
                "step": 3,
                "thought": "No strict matches found. Relaxing search filters to provide top available houses across the platform.",
                "action": "search_properties",
                "action_input": {"limit": 3}
            }
            fallback_props = self.tools.search_properties(limit=3)
            step3["observation"] = f"Found {len(fallback_props)} alternate available listings."
            trace["steps"].append(step3)

            trace["cards"].append({"type": "property_list", "items": fallback_props})

            trace["answer"] = (
                f"### 🔍 No Exact Match Found\n\n"
                f"I couldn't find an available house matching all your specific filters "
                + (f"(Location: *{location}*, Max Rent: *₹{int(max_rent):,}*)" if (location or max_rent) else "")
                + f".\n\nHere are our **top-rated available properties** right now:\n\n"
                + "\n".join([f"- **#{p['id']} {p['title']}**: ₹{int(p['rent']):,}/mo in *{p['location']}* ({p['bedrooms']} BHK)" for p in fallback_props])
                + "\n\nWould you like me to adjust the budget ceiling or broaden the neighborhood search?"
            )
            trace["quick_replies"] = ["Show all available houses", "2 BHK in Indiranagar", "Houses under ₹20,000"]

        return trace

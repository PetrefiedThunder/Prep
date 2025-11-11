"""
City Regulatory Service - Database Setup and Initialization

This module handles database creation, initialization, and sample data loading
for the city-level compliance regulatory system.
"""

import os
from datetime import datetime, UTC

from models import (
    Base,
    CityInsuranceRequirement,
    CityJurisdiction,
    CityPermitApplication,
    CityRegulation,
    FacilityComplianceStatus,
    FacilityType,
    RegulationType,
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Database configuration
DATABASE_DIR = "/home/user/Prep/data/cities"
DATABASE_PATH = os.path.join(DATABASE_DIR, "prep_city_regulations.sqlite")


def get_engine(database_path: str = DATABASE_PATH, echo: bool = False):
    """
    Create and return a SQLAlchemy engine for the city regulations database.

    Args:
        database_path: Path to the SQLite database file
        echo: Whether to echo SQL statements (for debugging)

    Returns:
        SQLAlchemy engine instance
    """
    os.makedirs(os.path.dirname(database_path), exist_ok=True)

    # Create engine with SQLite-specific optimizations
    engine = create_engine(
        f"sqlite:///{database_path}",
        echo=echo,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def get_session(engine=None) -> Session:
    """Get a database session"""
    if engine is None:
        engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database(engine=None) -> None:
    """
    Initialize the database schema.

    Args:
        engine: SQLAlchemy engine (creates new one if not provided)
    """
    if engine is None:
        engine = get_engine()

    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")


def load_sample_data(session: Session) -> None:
    """
    Load sample data for the 8 target cities.

    This creates placeholder structures that will be populated with real
    regulatory data gathered from city sources.

    Cities: NYC, San Francisco, Chicago, Atlanta, Los Angeles, Seattle, Portland, Boston
    """
    print("Loading sample city jurisdictions...")

    # Define the 8 target cities with their basic information
    cities_data = [
        {
            "city_name": "New York",
            "state": "NY",
            "county": "New York County",
            "fips_code": "36061",
            "population": 8336817,
            "health_department_name": "NYC Department of Health and Mental Hygiene",
            "health_department_url": "https://www.nyc.gov/site/doh/index.page",
            "business_licensing_dept": "NYC Department of Consumer and Worker Protection",
            "business_licensing_url": "https://www.nyc.gov/site/dca/index.page",
            "fire_department_name": "FDNY Fire Prevention",
            "fire_department_url": "https://www.nyc.gov/site/fdny/index.page",
            "phone": "311",
            "timezone": "America/New_York",
        },
        {
            "city_name": "San Francisco",
            "state": "CA",
            "county": "San Francisco County",
            "fips_code": "06075",
            "population": 873965,
            "health_department_name": "SF Department of Public Health",
            "health_department_url": "https://www.sfdph.org/",
            "business_licensing_dept": "SF Office of the Treasurer & Tax Collector",
            "business_licensing_url": "https://sftreasurer.org/",
            "fire_department_name": "SF Fire Department",
            "fire_department_url": "https://sf-fire.org/",
            "phone": "311",
            "timezone": "America/Los_Angeles",
        },
        {
            "city_name": "Chicago",
            "state": "IL",
            "county": "Cook County",
            "fips_code": "17031",
            "population": 2746388,
            "health_department_name": "Chicago Department of Public Health",
            "health_department_url": "https://www.chicago.gov/city/en/depts/cdph.html",
            "business_licensing_dept": "Chicago Department of Business Affairs and Consumer Protection",
            "business_licensing_url": "https://www.chicago.gov/city/en/depts/bacp.html",
            "fire_department_name": "Chicago Fire Department",
            "fire_department_url": "https://www.chicago.gov/city/en/depts/cfd.html",
            "phone": "311",
            "timezone": "America/Chicago",
        },
        {
            "city_name": "Atlanta",
            "state": "GA",
            "county": "Fulton County",
            "fips_code": "13121",
            "population": 498715,
            "health_department_name": "Fulton County Board of Health",
            "health_department_url": "https://www.fultoncountyga.gov/services/health-services",
            "business_licensing_dept": "City of Atlanta Office of Revenue",
            "business_licensing_url": "https://www.atlantaga.gov/government/departments/finance/office-of-revenue",
            "fire_department_name": "Atlanta Fire Rescue Department",
            "fire_department_url": "https://www.atlantaga.gov/government/departments/fire-rescue",
            "phone": "404-330-6000",
            "timezone": "America/New_York",
        },
        {
            "city_name": "Los Angeles",
            "state": "CA",
            "county": "Los Angeles County",
            "fips_code": "06037",
            "population": 3898747,
            "health_department_name": "LA County Department of Public Health",
            "health_department_url": "http://publichealth.lacounty.gov/",
            "business_licensing_dept": "LA Office of Finance",
            "business_licensing_url": "https://finance.lacity.org/",
            "fire_department_name": "LA Fire Department",
            "fire_department_url": "https://www.lafd.org/",
            "phone": "311",
            "timezone": "America/Los_Angeles",
        },
        {
            "city_name": "Seattle",
            "state": "WA",
            "county": "King County",
            "fips_code": "53033",
            "population": 749256,
            "health_department_name": "Seattle-King County Public Health",
            "health_department_url": "https://kingcounty.gov/depts/health.aspx",
            "business_licensing_dept": "Seattle Department of Finance and Administrative Services",
            "business_licensing_url": "https://www.seattle.gov/business-licenses-and-taxes",
            "fire_department_name": "Seattle Fire Department",
            "fire_department_url": "https://www.seattle.gov/fire",
            "phone": "206-684-5000",
            "timezone": "America/Los_Angeles",
        },
        {
            "city_name": "Portland",
            "state": "OR",
            "county": "Multnomah County",
            "fips_code": "41051",
            "population": 652503,
            "health_department_name": "Multnomah County Health Department",
            "health_department_url": "https://www.multco.us/health",
            "business_licensing_dept": "Portland Revenue Division",
            "business_licensing_url": "https://www.portland.gov/revenue",
            "fire_department_name": "Portland Fire & Rescue",
            "fire_department_url": "https://www.portland.gov/fire",
            "phone": "503-823-4000",
            "timezone": "America/Los_Angeles",
        },
        {
            "city_name": "Boston",
            "state": "MA",
            "county": "Suffolk County",
            "fips_code": "25025",
            "population": 675647,
            "health_department_name": "Boston Public Health Commission",
            "health_department_url": "https://www.boston.gov/departments/public-health-commission",
            "business_licensing_dept": "City of Boston Licensing Board",
            "business_licensing_url": "https://www.boston.gov/departments/licensing-board",
            "fire_department_name": "Boston Fire Department",
            "fire_department_url": "https://www.boston.gov/departments/fire-department",
            "phone": "311",
            "timezone": "America/New_York",
        },
    ]

    # Create city jurisdictions
    city_objects = []
    for city_data in cities_data:
        city = CityJurisdiction(
            **city_data,
            data_source="Initial city setup",
            last_verified=datetime.now(UTC),
        )
        city_objects.append(city)
        session.add(city)

    session.commit()
    print(f"Created {len(city_objects)} city jurisdictions")

    # Create sample regulations for each city
    # These are placeholders that will be replaced with real data
    print("Creating placeholder regulation structures...")

    regulation_templates = [
        {
            "regulation_type": RegulationType.HEALTH_PERMIT.value,
            "title": "Food Service Establishment Permit",
            "description": "Required permit for all food preparation and service facilities",
            "enforcement_agency": "Health Department",
            "priority": "critical",
            "applicable_facility_types": [
                FacilityType.COMMERCIAL_KITCHEN.value,
                FacilityType.GHOST_KITCHEN.value,
                FacilityType.RESTAURANT.value,
                FacilityType.CATERING.value,
            ],
        },
        {
            "regulation_type": RegulationType.BUSINESS_LICENSE.value,
            "title": "General Business License",
            "description": "Required business operating license for commercial operations",
            "enforcement_agency": "Business Licensing Department",
            "priority": "critical",
            "applicable_facility_types": [ft.value for ft in FacilityType],
        },
        {
            "regulation_type": RegulationType.FOOD_HANDLER_CERT.value,
            "title": "Food Handler Certification",
            "description": "Certification required for all food handling staff",
            "enforcement_agency": "Health Department",
            "priority": "high",
            "applicable_facility_types": [
                FacilityType.COMMERCIAL_KITCHEN.value,
                FacilityType.GHOST_KITCHEN.value,
                FacilityType.RESTAURANT.value,
            ],
        },
        {
            "regulation_type": RegulationType.FIRE_SAFETY.value,
            "title": "Fire Safety Inspection and Permit",
            "description": "Annual fire safety inspection and compliance certification",
            "enforcement_agency": "Fire Department",
            "priority": "critical",
            "applicable_facility_types": [ft.value for ft in FacilityType],
        },
        {
            "regulation_type": RegulationType.INSURANCE.value,
            "title": "General Liability Insurance",
            "description": "Required liability insurance coverage for food service operations",
            "enforcement_agency": "Business Licensing Department",
            "priority": "critical",
            "applicable_facility_types": [ft.value for ft in FacilityType],
        },
    ]

    regulation_count = 0
    for city in city_objects:
        for template in regulation_templates:
            regulation = CityRegulation(
                city_id=city.id,
                **template,
                local_code_reference=f"{city.city_name} Code - Pending data collection",
                effective_date=datetime(2024, 1, 1),
                renewal_period_days=365,
                agency_url=city.health_department_url if "health" in template["enforcement_agency"].lower() else city.business_licensing_url,
                requirements={
                    "note": "Detailed requirements to be populated from city sources"
                },
                application_process={
                    "note": "Application process to be documented from city sources"
                },
                required_documents=["To be populated with actual document list"],
                fees={"application_fee": 0.00, "note": "Actual fees to be collected"},
                is_active=True,
                data_source="Placeholder - awaiting city data",
                last_verified=None,
                notes=f"Placeholder structure for {city.city_name} - to be populated with actual regulatory data",
            )
            session.add(regulation)
            regulation_count += 1

    session.commit()
    print(f"Created {regulation_count} placeholder regulation entries")

    # Create sample insurance requirements
    print("Creating placeholder insurance requirement structures...")

    insurance_templates = [
        {
            "insurance_type": "general_liability",
            "coverage_name": "Commercial General Liability",
            "description": "Coverage for bodily injury and property damage",
            "minimum_coverage_amount": 1000000.00,
            "per_occurrence_limit": 1000000.00,
            "aggregate_limit": 2000000.00,
            "is_mandatory": True,
        },
        {
            "insurance_type": "workers_compensation",
            "coverage_name": "Workers Compensation",
            "description": "Required coverage for employee injuries",
            "minimum_coverage_amount": 500000.00,
            "is_mandatory": True,
            "employee_count_threshold": 1,
        },
        {
            "insurance_type": "product_liability",
            "coverage_name": "Product Liability",
            "description": "Coverage for food-borne illness and product defects",
            "minimum_coverage_amount": 1000000.00,
            "per_occurrence_limit": 1000000.00,
            "aggregate_limit": 2000000.00,
            "is_mandatory": True,
        },
    ]

    insurance_count = 0
    for city in city_objects:
        for template in insurance_templates:
            insurance_req = CityInsuranceRequirement(
                city_id=city.id,
                **template,
                applicable_facility_types=[ft.value for ft in FacilityType],
                local_ordinance=f"{city.city_name} ordinance - to be documented",
                effective_date=datetime(2024, 1, 1),
                notes=f"Placeholder for {city.city_name} - actual requirements to be collected",
            )
            session.add(insurance_req)
            insurance_count += 1

    session.commit()
    print(f"Created {insurance_count} placeholder insurance requirement entries")

    print("\nSample data loading complete!")
    print(f"Total cities: {len(city_objects)}")
    print(f"Total regulation placeholders: {regulation_count}")
    print(f"Total insurance requirement placeholders: {insurance_count}")
    print("\nNOTE: All entries are placeholders awaiting real regulatory data collection.")


def clear_database(session: Session) -> None:
    """Clear all data from the database (for testing/reloading)"""
    print("Clearing all database tables...")
    session.query(FacilityComplianceStatus).delete()
    session.query(CityPermitApplication).delete()
    session.query(CityInsuranceRequirement).delete()
    session.query(CityRegulation).delete()
    session.query(CityJurisdiction).delete()
    session.commit()
    print("Database cleared!")


def main():
    """Main function to initialize database and load sample data"""
    print("=" * 80)
    print("City Regulatory Service - Database Initialization")
    print("=" * 80)
    print()

    # Create engine and initialize schema
    engine = get_engine(echo=False)
    init_database(engine)

    # Get session and load sample data
    session = get_session(engine)

    # Check if data already exists
    existing_cities = session.query(CityJurisdiction).count()
    if existing_cities > 0:
        print(f"\nDatabase already contains {existing_cities} cities.")
        response = input("Do you want to clear and reload? (yes/no): ")
        if response.lower() == "yes":
            clear_database(session)
        else:
            print("Keeping existing data.")
            session.close()
            return

    # Load sample data
    load_sample_data(session)

    # Display summary
    print("\n" + "=" * 80)
    print("Database initialization complete!")
    print("=" * 80)
    print(f"\nDatabase location: {DATABASE_PATH}")
    print("\nNext steps:")
    print("1. Collect actual regulatory data from city sources")
    print("2. Use the ETL pipeline to ingest real data")
    print("3. Start the FastAPI service to access the data")
    print()

    session.close()


if __name__ == "__main__":
    main()

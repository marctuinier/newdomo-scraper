import os
import time
import json
from datetime import datetime, timezone

# Load a .env file from the working directory, if present (optional dependency)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import create_client, Client

# Attempt to import specific error types for better handling
try:
    from gotrue.errors import APIError as AuthAPIError
except ImportError:
    AuthAPIError = Exception

try:
    from postgrest.exceptions import APIError as PostgrestAPIError
except ImportError:
    try:
        from postgrest_py.exceptions import APIError as PostgrestAPIError
    except ImportError:
        PostgrestAPIError = Exception

# --- Hunter Imports ---
try:
    from .hunters.hunter import browser, Prey
    from .hunters.pararius import Pararius
    from .hunters.kamernet import Kamernet
    from .hunters.gruno import Gruno
    from .hunters.wonen123 import Wonen123
    from .hunters.huurwoningen import Huurwoningen
    from .hunters.funda import Funda
except ImportError:
    from hunters.hunter import browser, Prey
    from hunters.pararius import Pararius
    from hunters.kamernet import Kamernet
    from hunters.gruno import Gruno
    from hunters.wonen123 import Wonen123
    from hunters.huurwoningen import Huurwoningen
    from hunters.funda import Funda

# --- Configuration (see .env.example) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Comma-separated list of cities to scrape. Each hunter only runs for the
# cities it supports (see supported_cities() in each hunter).
CITIES_TO_SCRAPE = [
    c.strip() for c in os.environ.get(
        "CITIES", "Amsterdam,Rotterdam,The Hague,Utrecht,Groningen"
    ).split(",") if c.strip()
]

# Without Supabase credentials (or with DRY_RUN=1) listings are printed to
# stdout instead of stored, so you can try the scraper without a database.
DRY_RUN = os.environ.get("DRY_RUN") == "1" or not (SUPABASE_URL and SUPABASE_SERVICE_KEY)

ALL_HUNTER_CLASSES = [Pararius, Kamernet, Gruno, Wonen123, Huurwoningen, Funda]

supabase_client: Client = None


def initialize_supabase_client():
    global supabase_client
    if DRY_RUN:
        print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Running in DRY RUN mode: listings are printed, not stored. "
              "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to persist them.")
        return
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Supabase client initialized.")
    except Exception as e:
        print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Failed to initialize Supabase client: {e}")
        exit(1)


def store_listing_to_supabase(prey_item: Prey, max_retries=3):
    try:
        price_value = int(prey_item.price)
    except (ValueError, TypeError):
        print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Invalid price for {prey_item.link}: '{prey_item.price}'. Skipping.")
        return False

    if DRY_RUN:
        print(f"LISTING: {prey_item}")
        return True

    if not supabase_client:
        print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Supabase client not initialized in store_listing_to_supabase.")
        return False

    # city_scraped_for: use hunter-derived actual city from listing URL slug when set; otherwise search city
    listing_data = {
        "link": prey_item.link,
        "name": prey_item.name,
        "price": price_value,
        "m2": prey_item.m2,
        "agency": prey_item.agency,
        "website": prey_item.website,
        "city_scraped_for": prey_item.city_scraped_for,
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "data_json": json.dumps(vars(prey_item), default=str)
    }

    # Retry logic for transient network errors (broken pipe, connection reset, etc.)
    for attempt in range(max_retries):
        try:
            response = supabase_client.table("apartments").insert(listing_data).execute()

            # response.error will be None on success, or a PostgrestError object on failure.
            if hasattr(response, 'error') and response.error:
                # Duplicate key violation (PostgreSQL error code 23505) means the listing was already seen
                if hasattr(response.error, 'code') and response.error.code == '23505':
                    return False  # Not newly added
                else:
                    print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Supabase insert error for {prey_item.link}: Code {getattr(response.error, 'code', 'N/A')} - {getattr(response.error, 'message', 'No message')}")
                    return False
            elif hasattr(response, 'data') and response.data:
                return True  # New listing inserted
            else:
                # No error and no data - might mean duplicate if table has ON CONFLICT DO NOTHING,
                # or RLS prevented the insert without erroring to the client.
                return False

        except (PostgrestAPIError, AuthAPIError) as api_exc:
            error_details = {}
            if hasattr(api_exc, 'json') and callable(api_exc.json):  # For postgrest-py style errors
                try:
                    error_details = api_exc.json()
                except Exception:
                    pass
            elif hasattr(api_exc, 'args') and len(api_exc.args) > 0 and isinstance(api_exc.args[0], dict):  # For some gotrue errors
                error_details = api_exc.args[0]

            if error_details.get('code') == '23505':
                return False  # Duplicate link
            else:
                # Don't retry on API errors (they're not transient)
                print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Supabase APIError during operation for {prey_item.link}: {api_exc} | Details: {error_details}")
                return False
        except (ConnectionError, OSError) as network_exc:
            # Retry on network errors (broken pipe, connection reset, etc.)
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Network error (attempt {attempt + 1}/{max_retries}) for {prey_item.link}: {network_exc}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Network error (failed after {max_retries} attempts) for {prey_item.link}: {network_exc}")
                return False
        except Exception as e:
            # Check if it's a network-related error (broken pipe, connection reset, etc.)
            error_str = str(e).lower()
            if any(term in error_str for term in ['broken pipe', 'connection', 'errno 32', 'errno 104', 'errno 110']):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)
                    print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Network error (attempt {attempt + 1}/{max_retries}) for {prey_item.link}: {e.__class__.__name__} - {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Network error (failed after {max_retries} attempts) for {prey_item.link}: {e.__class__.__name__} - {e}")
                    return False
            else:
                # Non-network errors: don't retry
                print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Unexpected Python exception during Supabase op for {prey_item.link}: {e.__class__.__name__} - {e}")
                return False

    return False


def run_scheduled_scrape():
    print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Scrape run starting for cities: {', '.join(CITIES_TO_SCRAPE)}")
    initialize_supabase_client()

    if browser is None:
        print(f"CRITICAL_ERROR: [{datetime.now(timezone.utc).isoformat()}] Selenium browser not initialized. Check hunter.py and your Chrome installation.")
        exit(1)

    total_newly_saved_count = 0

    for city in CITIES_TO_SCRAPE:
        print(f"--- INFO: [{datetime.now(timezone.utc).isoformat()}] Processing city: {city} ---")
        for HunterClass in ALL_HUNTER_CLASSES:
            hunter_instance = HunterClass()
            try:
                supported_for_hunter = {c.lower(): c for c in hunter_instance.supported_cities().keys()}
                if city.lower() not in supported_for_hunter:
                    continue
                hunter_instance.set_city(supported_for_hunter[city.lower()])
            except ValueError as e:
                print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Cannot set city {city} for {hunter_instance.name}: {e}.")
                continue

            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Running: {hunter_instance.name} for {city} (URL: {getattr(hunter_instance, 'url', 'N/A')})")
            try:
                listings_found = hunter_instance.hunt()
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] {hunter_instance.name} found {len(listings_found)} potential listings for {city}.")
                for prey in listings_found:
                    # Saved to DB: hunter-set actual city from listing URL slug when present; else search city
                    if not getattr(prey, 'city_scraped_for', None):
                        prey.city_scraped_for = city
                    if not hasattr(prey, 'website') or not prey.website:
                        prey.website = hunter_instance.name
                    if store_listing_to_supabase(prey):
                        total_newly_saved_count += 1
            except Exception as e:
                print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] during hunt with {hunter_instance.name} for {city}: {e}")

        print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Finished city {city}. Brief pause.")
        time.sleep(1)

    verb = "printed" if DRY_RUN else "saved to Supabase"
    print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Scrape cycle complete. {total_newly_saved_count} new listings {verb}.")


if __name__ == "__main__":
    start_time = time.time()
    try:
        run_scheduled_scrape()
    except Exception as e_main:
        print(f"FATAL: [{datetime.now(timezone.utc).isoformat()}] Unhandled exception in main script: {e_main}")
    finally:
        if browser is not None:
            try:
                browser.quit()
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Selenium browser quit successfully.")
            except Exception as e_quit:
                print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Exception during browser.quit(): {e_quit}")
    end_time = time.time()
    print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Scraper finished. Total execution time: {end_time - start_time:.2f} seconds.")

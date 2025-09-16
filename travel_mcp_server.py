from mcp.server.fastmcp import FastMCP
import pandas as pd


mcp = FastMCP("Travel")





# Load CSV once
df = pd.read_csv(r"destinations.csv")

@mcp.tool()
def search_destinations(query: str) -> str:
    """
    Search destinations based on the user query by matching city, country, category, or season.
    Returns a summary of matching destinations from the CSV data.
    """
    query_words = query.lower().split()
    
    def row_matches(row):
        row_values = f"{row['city']} {row['country']} {row['category']} {row['season']} {row['description']}".lower()
        return any(word in row_values for word in query_words)
    
    filtered = df[df.apply(row_matches, axis=1)]
    
    if filtered.empty:
        return "No destinations found matching your query."

    results = []
    for _, row in filtered.head(5).iterrows():
        results.append(f"{row['city']}, {row['country']} - {row['category']} (Best season: {row['season']})")

    return "Top destinations:\n" + "\n".join(results)




#---------------- SEARCH FLIGHT TOOLS ----------------#

from amadeus import Client, ResponseError
AMADEUS_API_KEY="jr7OYADsGJ2ZK3340rMfAK3NSFtRYCN6"
AMADEUS_API_SECRET="WAhks4Ue0gAGTej7"
airport_df = pd.read_csv(r"airports.csv")  
airport_df = airport_df[airport_df["iata_code"].notnull()]
# Initialize Amadeus client
amadeus = Client(
    client_id=AMADEUS_API_KEY,
    client_secret=AMADEUS_API_SECRET
)


def get_iata(city):
    print(f"Getting IATA code for city: {city}")
    matches = airport_df[
        airport_df["municipality"].str.contains(city, case=False, na=False)
    ]
    large = matches[matches["type"] == "large_airport"]
    
    if not large.empty:
        print('large')
        print(large.iloc[0])
        return large.iloc[0]["iata_code"]
    if not matches.empty:
        print('matches')
        print(matches.iloc[0])
        return matches.iloc[0]["iata_code"]
    return None


def search_flights(departure_iata: str, arrival_iata: str, date: str, travel_class="ECONOMY"):
    """
    Search for available flights using Amadeus API.
    """
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=departure_iata,
            destinationLocationCode=arrival_iata,
            departureDate=date,
            adults=1,
            travelClass=travel_class.upper(),
        )
        return response.data
    except ResponseError as e:
        raise RuntimeError(f"Error fetching flights: {e}")
def get_airline_name(iata_code):
    try:
        response = amadeus.reference_data.airlines.get(airlineCodes=iata_code)
        return response.data[0]["commonName"]
    except:
        return iata_code  # fallback to code if name not found
    
from datetime import datetime

@mcp.tool()
def search_flights_to_destination_detailed(departure_city: str, destination_city: str, date: str, travel_class: str = "ECONOMY") -> str:
    """
    Search flights from departure_city to destination_city on the given date.
    Returns detailed flight info including airline, segments, fare, and baggage info.
    """
    print('calling')
    # Step 1: Get IATA codes
    departure_iata = get_iata(departure_city)
    arrival_iata = get_iata(destination_city)

    if not departure_iata or not arrival_iata:
        return f"Could not find IATA codes for {departure_city} or {destination_city}."

    # Step 2: Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Date format should be YYYY-MM-DD."

    # Step 3: Search flights
    try:
        flights = search_flights(departure_iata, arrival_iata, date, travel_class.upper())
        if not flights:
            return "No flights found."

        results = []
        for idx, flight in enumerate(flights[:5], 1):  # top 5 flights
            offer = flight['itineraries'][0]
            price = flight['price']['total']
            airline_code = flight['validatingAirlineCodes'][0]
            airline_name = get_airline_name(airline_code)

            flight_info = [f"Flight {idx}: Airline: {airline_name} | Price: ${price}"]

            # Segments
            for seg in offer['segments']:
                dep = seg['departure']
                arr = seg['arrival']
                flight_info.append(f"  {dep['iataCode']} ({dep['at']}) → {arr['iataCode']} ({arr['at']})")

            # Fare details
            traveler_pricing = flight.get("travelerPricings", [])
            for traveler in traveler_pricing:
                fare_details = traveler.get("fareDetailsBySegment", [])
                for fare in fare_details:
                    flight_info.append(f"  🛋 Cabin: {fare.get('cabin', 'N/A')}")
                    flight_info.append(f"  🎟 Fare Basis: {fare.get('fareBasis', 'N/A')}")
                    flight_info.append(f"  📋 Class: {fare.get('class', 'N/A')}")

                    bags = fare.get("includedCheckedBags", {})
                    if bags:
                        flight_info.append(f"  🧳 Checked Bags: {bags.get('weight', 'N/A')} {bags.get('weightUnit', '')}")

                    cabin_bags = fare.get("includedCabinBags", {})
                    if cabin_bags:
                        flight_info.append(f"  🎒 Cabin Bags: {cabin_bags.get('weight', 'N/A')} {cabin_bags.get('weightUnit', '')}")

            results.append("\n".join(flight_info))

        return "\n\n".join(results)

    except Exception as e:
        return f"Error fetching flights: {e}"





#---------------- SEARCH IMAGES TOOLS ----------------#
import requests

ACCESS_KEY = "nyLJk-ztqyi5W7qtDowqocrLDTtl1B5mUQ5uMqTh3Ag"

def search_unsplash(query):
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {ACCESS_KEY}"}
    params = {"query": query, "per_page": 1}  # <- Only 1 image
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    # Check if results exist
    if data.get("results"):
        image_url = data["results"][0]["urls"]["regular"]
        return f"{image_url}&w=600&q=60"
    return None
@mcp.tool()
def get_destination_images(destination: str) -> list:
    """Fetch travel images for a destination using Unsplash API."""
    return search_unsplash(destination)

# if __name__ == "__main__":
#     #mcp.run(transport="stdio")

#     mcp.run(transport="streamable-http")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Render provides PORT env
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)

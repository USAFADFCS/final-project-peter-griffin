import requests
import json
from fairlib.core.interfaces.tools import AbstractTool

class FlightTool(AbstractTool):
    name = "flight_search_tool"
    description = (
        "A tool for finding flights."
        "Inputs must follow the exact format of the examples"
        "Example inputs:\n"
        '{"Origin": "DEN", "Destination": "MCO",  "Departure": "2025-11-20", "Max_Price": "600"}\n'
        '{"Origin": "BOS", "Destination": "LAX",  "Departure": "2026-01-17", "Max_Price": "750"}'
    )

    def use(self, expression: str) -> str:
        expression = expression.upper()
        user_specs_obj = json.loads(expression)
        flights = self.search_flights(user_specs_obj)
        return flights

    def get_auth_token(self):
        base_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_key = {
            "grant_type":"client_credentials",
            "client_id":"GYVKgQEJ46QKGocNYvnEAIxUykjbCutE",
            "client_secret":"JGCTX6Ba41h745Ji"
        }

        response = requests.post(base_url, headers=headers, data=api_key).json()
        token = response["access_token"]
        return token

    def search_flights(self, flightInfo):
        base_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        
        # Gather user input
        origin = flightInfo["ORIGIN"].strip().upper()
        destination = flightInfo["DESTINATION"].strip().upper()
        departure_date = flightInfo["DEPARTURE"].strip()
        max_price = flightInfo["MAX_PRICE"].strip()

        # Optional: you could also let users specify returnDate, adults, etc.
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": 1,
            "maxPrice": max_price
        }

        # Replace this with your real token
        token = self.get_auth_token()
        headers = {
            "Authorization": "Bearer " + token
        }

        try:

            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # print("\n--- Flight Results ---")
            # for offer in data.get("data", []):
            #     price = offer["price"]["total"]
            #     itineraries = offer["itineraries"]
            #     print(f"Total Price: {price}")
            #     for i, itinerary in enumerate(itineraries, start=1):
            #         print(f"  Itinerary {i}:")
            #         for segment in itinerary["segments"]:
            #             dep = segment["departure"]["iataCode"]
            #             arr = segment["arrival"]["iataCode"]
            #             dep_time = segment["departure"]["at"]
            #             arr_time = segment["arrival"]["at"]
            #             print(f"    {dep} -> {arr} ({dep_time} -> {arr_time})")
            #     print("-" * 30)
            return json.dumps(data)
        except requests.exceptions.RequestException as e:
            return(f"API request failed: {e}")



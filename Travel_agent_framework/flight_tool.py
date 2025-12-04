import requests
import json
import os
from dotenv import load_dotenv
from fairlib.core.interfaces.tools import AbstractTool
load_dotenv()

class FlightTool(AbstractTool):
    def __init__(self):
        super().__init__()
        self.api_endpoint = "api.amadeus.com" # production environment
        # self.api_endpoint = "api.amadeus.com" # test environment

        self.token = self.get_auth_token()
    
    name = "flight_search_tool"
    description = (
        "A tool for finding flights."
        "Inputs must follow the exact format of the examples, with no additional entries."
        "Leave out the return date field if you are looking for a one way flight. Must specify Max_Price."
        "Example inputs:\n"
        '{"Origin": "DEN", "Destination": "MCO",  "Departure": "2025-11-20", "Return":"2025-11-22", "Max_Price": "600"}\n'
        '{"Origin": "BOS", "Destination": "LAX",  "Departure": "2026-01-17", "Max_Price": "750"}'
    )

    def use(self, expression: str) -> str:
        expression = expression.upper()
        user_specs_obj = json.loads(expression)
        flights = self.search_flights(user_specs_obj)
        return flights

    def get_auth_token(self):
        base_url = f"https://{self.api_endpoint}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_key = {
            "grant_type":"client_credentials",
            "client_id":os.getenv("AMADEUS_KEY"),
            "client_secret":os.getenv("AMADEUS_SECRET")
        }
        try:
            response = requests.post(base_url, headers=headers, data=api_key).json()
            token = response["access_token"]
            return token
        except:
            print(response)

    def search_flights(self, flightInfo):
        base_url = f"https://{self.api_endpoint}/v2/shopping/flight-offers"
        
        # Gather user input
        origin = flightInfo["ORIGIN"].strip().upper()
        destination = flightInfo["DESTINATION"].strip().upper()
        departure_date = flightInfo["DEPARTURE"].strip()
        max_price = flightInfo["MAX_PRICE"].strip()
        try:
            return_date = flightInfo["RETURN"].strip()
        except:
            return_date = ""

        # Optional: you could also let users specify returnDate, adults, etc.
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": 1,
            "maxPrice": max_price,
            "max": 20,
        }
        if return_date:
            params["returnDate"] = return_date

        # Replace this with your real token
        token = self.token
        headers = {
            "Authorization": "Bearer " + token
        }

        try:

            response = requests.get(base_url, headers=headers, params=params)
            data = response.json()
            response.raise_for_status()
            output_str = ""

            output_str += ("--- Flight Options: ---\n")
            for offer_num, offer in enumerate(data.get("data", []), start =1):
                price = offer["price"]["total"]
                itineraries = offer["itineraries"]
                output_str += f"\n Option {offer_num}"
                output_str += (f"\n   Total Price: {price}")
                for i, itinerary in enumerate(itineraries, start=1):
                    if i == 1: output_str += (f"\n   Departure:")
                    else: output_str += (f"\n   Return:")

                    for segment in itinerary["segments"]:
                        flightNumber = segment["carrierCode"] + segment["number"]
                        dep = segment["departure"]["iataCode"]
                        arr = segment["arrival"]["iataCode"]
                        dep_time = segment["departure"]["at"]
                        arr_time = segment["arrival"]["at"]
                        output_str += (f"    flight number [{flightNumber}]: {dep} -> {arr} ({dep_time} -> {arr_time})")
            if(len(data.get("data", [])) == 0):
                output_str += "No available flights given the input parameters."
            return output_str
        except requests.exceptions.RequestException as e:
            return(f"API request failed: {e}\nDetails: {data["errors"][0]["detail"]}")


if __name__ == "__main__":
    tool = FlightTool()
    flights = tool.use('{"Origin": "DEN", "Destination": "ANC", "Departure": "2025-06-03", "Return": "2025-06-17", "Max_Price": "750"}')
    print(flights)
import requests
import json
from fairlib.core.interfaces.tools import AbstractTool
import os
from tqdm import tqdm
# load API keys from .env
from dotenv import load_dotenv
load_dotenv()

class HotelTool(AbstractTool):
    def __init__(self):
        super().__init__()
        self.token = self.get_auth_token()

    name = "hotel_search_tool"
    description = (
        "A tool for finding hotels.\n"
        "The only valid input parameters are: cityCode, ratings, adults, checkInDate, checkOutDate, and priceRange"
        "Inputs must follow the exact format of the examples"
        "Example inputs:\n"
        '{"cityCode": "PAR", "ratings": "3,4,5", "adults": "2", "checkInDate": "2025-11-05", "checkOutDate": "2025-11-10", "priceRange": "200-300"}\n'
    )

    def use(self, expression: str) -> str:
        expression = expression.upper()
        user_specs_obj = json.loads(expression)
        hotel_list = self.list_hotels(user_specs_obj)
        hotelIDs = [hotel["hotelId"] for hotel in hotel_list["data"]]
        hotels = self.search_hotels(user_specs_obj, hotelIDs)
        return hotels

    def format_hotels(self, data):
        output_str = ""

        for hotel_num, hotel_entry in enumerate(data.get("data", []), start=1):
            hotel_info = hotel_entry.get("hotel", {})
            name = hotel_info.get("name", "Unknown Hotel")
            city = hotel_info.get("cityCode", "N/A")

            output_str += f"\n Option"
            output_str += f"\n   Hotel: {name} ({city})"

            offers = hotel_entry.get("offers", [])
            for offer in offers:
                check_in = offer.get("checkInDate", "N/A")
                check_out = offer.get("checkOutDate", "N/A")
                price_total = offer.get("price", {}).get("total", "N/A")
                currency = offer.get("price", {}).get("currency", "N/A")

                room = offer.get("room", {})
                desc = room.get("description", {}).get("text", "").replace("\n", " ")
                room_type = room.get("typeEstimated", {}).get("category", "N/A")
                bed_info = room.get("typeEstimated", {})

                beds = bed_info.get("beds", "N/A")
                bed_type = bed_info.get("bedType", "N/A")

                output_str += f"\n   Stay:"
                output_str += f"\n     Check-in: {check_in}"
                output_str += f"\n     Check-out: {check_out}"
                output_str += f"\n     Total Price: {price_total} {currency}"
                output_str += f"\n     Room Type: {room_type.replace('_',' ').title()}"
                output_str += f"\n     Beds: {beds} ({bed_type.title()})"
                output_str += f"\n     Description: {desc}"

        return output_str

    def get_auth_token(self):
        base_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        api_key = {
            "grant_type":"client_credentials",
            "client_id":os.getenv("AMADEUS_KEY"),
            "client_secret":os.getenv("AMADEUS_SECRET")
        }

        response = requests.post(base_url, headers=headers, data=api_key).json()
        token = response["access_token"]
        return token
    
    def list_hotels(self, hotelInfo):
        base_url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
        
        # Gather user input
        cityCode = hotelInfo["CITYCODE"].strip().upper()
        ratings = hotelInfo["RATINGS"].strip().upper()

        # Optional: you could also let users specify returnDate, adults, etc.
        params = {
            "cityCode": cityCode,
            "ratings": ratings
        }

        # Replace this with your real token
        
        headers = {
            "Authorization": "Bearer " + self.token
        }

        try:
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        
        except requests.exceptions.RequestException as e:
            return(f"API request failed: {e}")

    def search_hotels(self, hotelInfo, hotelIDs):
        base_url = "https://test.api.amadeus.com/v3/shopping/hotel-offers"
        
        # Gather user input
        adults = hotelInfo["ADULTS"].strip()
        checkInDate = hotelInfo["CHECKINDATE"].strip()
        checkOutDate = hotelInfo["CHECKOUTDATE"].strip()
        priceRange = hotelInfo["PRICERANGE"].strip()

        # Optional: you could also let users specify returnDate, adults, etc.
        params = {
            "hotelIds": hotelIDs[0],
            "adults": adults,
            "checkInDate": checkInDate,
            "checkOutDate": checkOutDate,
            "priceRange": priceRange,
            "currency": "USD",
            "includeClosed":"True"
        }

        headers = {
            "Authorization": "Bearer " + self.token
        }

        output_str = ""
        output_str += "--- Hotel Options: ---\n"
        for id in tqdm(hotelIDs, desc=f"Finding hotel options"):
            params["hotelIds"] = id
            r = requests.get(base_url, headers=headers, params=params)

            # print("REQUEST URL:", r.url)
            # print("STATUS:", r.status_code)
            # print("RESPONSE BODY:", r.text)

            try:
                r.raise_for_status()
                data = r.json()
                output_str += self.format_hotels(data)
                
            except requests.exceptions.HTTPError as e:
                # show the server error body to reason about the 400
                ##print(f"API error: {e}")
                pass
        return output_str

if __name__ == "__main__":
    tool = HotelTool()
    out = tool.use('{"city": "Berlin", "cityCode": "BER", "ratings": "3,4", "adults": "2", "checkInDate": "2025-12-22", "checkOutDate": "2025-12-29", "priceRange": "60-200"}')
    print(out)
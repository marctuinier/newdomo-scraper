import requests

class Paddle:
    def __init__(self, apiKey):
        self.apiKey = apiKey
        self.headers = {'Authorization': f'Bearer {apiKey}'}
        self.website = 'https://sandbox-api.paddle.com/'

    def list_products(self):
        response = requests.get(self.website + 'products', headers=self.headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            # Iterate over the products in the data
            for product in data.get('data', []):
                product_id = product.get('id', 'N/A')
                product_name = product.get('name', 'N/A')

                # Print the product details
                print(f"Product ID: {product_id}")
                print(f"Product Name: {product_name}")
                print("---------------------------")
        else:
            print(f"Failed to connect to Paddle API. Status code: {response.status_code}")

# config.py

BUSINESS_CONTEXT = {
    "Company Name": "EID Parry",
    "Industry": "Sugar Manufacturing and Distribution",
    "Products": [
        "Sugar",
        "Refined Sugar",
        "Industrial Sugar",
        "Brown Sugar",
        "Liquid Sugar",
    ],
    "Customers": [
        "Retailers",
        "Wholesalers",
        "Dealers",
        "Distributors",
        "Food manufacturers",
        "Beverage companies",
        "Industrial buyers",
        "Export customers",
        "Procurement teams",
        "Corporate buyers",
        "Government buyers",
    ]
}

# The minimum confidence required to automatically route an email to a support/lead queue.
# If confidence is below this threshold, it is routed to 'others' for human review.
MIN_CONFIDENCE_THRESHOLD = 0.8

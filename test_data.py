# test_data.py

TEST_EMAILS = [
    # --- LEADS (0-20) ---
    {
        "from": "Enquiry <enquiry@example.com>",
        "subject": "Product Enquiry",
        "body": "I need 500 bags of sugar.",
        "message_id": "msg-000",
    },
    {
        "from": "Buyer <buyer@example.com>",
        "subject": "Need quotation for 100 MT",
        "body": "Please provide a quotation for 100 metric tons of refined product.",
        "message_id": "msg-001",
    },
    {
        "from": "Wholesale <ws@example.com>",
        "subject": "Looking for wholesale supply",
        "body": "We are a food manufacturer looking for a reliable wholesale supplier. Can we discuss rates?",
        "message_id": "msg-002",
    },
    {
        "from": "Export <ex@example.com>",
        "subject": "Can you export to Dubai?",
        "body": "We are based in the UAE and looking to import your products. Do you export to Dubai?",
        "message_id": "msg-003",
    },
    {
        "from": "Dealer <dlr@example.com>",
        "subject": "Interested in dealership",
        "body": "I have a large distribution network in my state and want to become a dealer for your products.",
        "message_id": "msg-004",
    },
    {
        "from": "Tender <gov@example.com>",
        "subject": "Government Tender Enquiry",
        "body": "Please find attached the tender documents for the supply of 5000 MT of refined sugar. Submit your bid by Friday.",
        "message_id": "msg-005",
    },
    {
        "from": "Procurement <procure@bakery.com>",
        "subject": "Monthly Supply Contract",
        "body": "We run a bakery chain and need a monthly supply of 10 tons of brown sugar. Send pricing.",
        "message_id": "msg-006",
    },
    {
        "from": "Factory <ops@bev.com>",
        "subject": "Liquid Sugar bulk pricing",
        "body": "Do you manufacture liquid sugar? We need 50,000 liters monthly for our beverage plant.",
        "message_id": "msg-007",
    },
    {
        "from": "Retailer <owner@supermarket.com>",
        "subject": "Product Catalogue request",
        "body": "Can you share your latest product catalogue and distributor prices for retail packets?",
        "message_id": "msg-008",
    },
    {
        "from": "Import <import@europe.com>",
        "subject": "Export capabilities to EU",
        "body": "We are interested in sourcing raw sugar. Do you meet EU export standards? Send quotation.",
        "message_id": "msg-009",
    },
    {
        "from": "Bakery <sales@sweettooth.com>",
        "subject": "Sample request",
        "body": "Before we place a bulk order, can you send us a 1kg sample of your finest refined sugar?",
        "message_id": "msg-010",
    },
    {
        "from": "Distributor <dist@region.com>",
        "subject": "Exclusive distributorship",
        "body": "We want exclusive distribution rights for your brand in our region. How do we proceed?",
        "message_id": "msg-011",
    },
    {
        "from": "Sweets <purchase@sweets.com>",
        "subject": "RFQ: 50 MT Brown Sugar",
        "body": "Please quote your best price for 50 metric tons of brown sugar delivered to Mumbai.",
        "message_id": "msg-012",
    },
    {
        "from": "Corporate <gifts@corp.com>",
        "subject": "Corporate gifting bulk order",
        "body": "We want to order 2000 boxes of premium sugar cubes for Diwali corporate gifting.",
        "message_id": "msg-013",
    },
    {
        "from": "Trading <trade@global.com>",
        "subject": "Tender for Sugar Supply",
        "body": "We are participating in a global tender and need your backing as a manufacturer. Quote enclosed quantities.",
        "message_id": "msg-014",
    },
    {
        "from": "Vendor <vendor@platform.com>",
        "subject": "Become a vendor",
        "body": "We want to list your sugar products on our B2B wholesale platform. Let's discuss pricing.",
        "message_id": "msg-015",
    },
    {
        "from": "Restaurant <chef@diner.com>",
        "subject": "Sugar packets for restaurant",
        "body": "We need 50,000 single-serve sugar sachets per month with custom branding. Price?",
        "message_id": "msg-016",
    },
    {
        "from": "Beverages <supply@drink.com>",
        "subject": "Availability of industrial sugar",
        "body": "Is industrial grade sugar available in 50kg bags? We need 2 truckloads.",
        "message_id": "msg-017",
    },
    {
        "from": "Caterer <cater@events.com>",
        "subject": "Event supply",
        "body": "We have a massive catering contract for next month. Can you supply 5 tons at short notice?",
        "message_id": "msg-018",
    },
    {
        "from": "Hospitality <purchase@hotel.com>",
        "subject": "Annual contract renewal",
        "body": "We want to sign an annual contract for our 5 hotels. Send the proposed rate card.",
        "message_id": "msg-019",
    },
    {
        "from": "Reseller <resell@market.com>",
        "subject": "Reseller terms",
        "body": "What is the minimum order quantity for resellers?",
        "message_id": "msg-020",
    },
    # --- SUPPORT (21-35) ---
    {
        "from": "Customer A <custA@example.com>",
        "subject": "Shipment delayed",
        "body": "My order #12345 was supposed to arrive yesterday but I haven't received it yet.",
        "message_id": "msg-021",
    },
    {
        "from": "Customer B <custB@example.com>",
        "subject": "Invoice missing",
        "body": "The delivery was received, but the invoice was not attached. Can you email it?",
        "message_id": "msg-022",
    },
    {
        "from": "Customer C <custC@example.com>",
        "subject": "Password reset",
        "body": "I am locked out of my wholesale ordering portal account. Can you help reset my password?",
        "message_id": "msg-023",
    },
    {
        "from": "Complaint <comp@angry.com>",
        "subject": "Quality issue - Urgent",
        "body": "The last batch of sugar bags we received were damp and clumpy. This is unacceptable. Order #999.",
        "message_id": "msg-024",
    },
    {
        "from": "Returns <return@shop.com>",
        "subject": "Damaged goods in transit",
        "body": "3 bags of refined sugar were torn during unloading. I want a refund for the damaged goods.",
        "message_id": "msg-025",
    },
    {
        "from": "Accounts <acct@buyer.com>",
        "subject": "Incorrect billing",
        "body": "Your invoice INV-004 charges us for 50 tons, but we only ordered and received 40 tons.",
        "message_id": "msg-026",
    },
    {
        "from": "Logistics <log@trans.com>",
        "subject": "Missing items",
        "body": "Our driver noted that the pallet was short by 5 bags. Please check your loading dock.",
        "message_id": "msg-027",
    },
    {
        "from": "User <user@portal.com>",
        "subject": "Website down?",
        "body": "I'm trying to track my order but the dealer portal keeps giving a 500 error.",
        "message_id": "msg-028",
    },
    {
        "from": "Client <client@corp.com>",
        "subject": "Modify my order",
        "body": "Can I add 2 more tons of brown sugar to my pending order #777 before it ships?",
        "message_id": "msg-029",
    },
    {
        "from": "Store <store@retail.com>",
        "subject": "Replacement request",
        "body": "The sugar sachets we got yesterday had the wrong branding. We need them replaced ASAP.",
        "message_id": "msg-030",
    },
    {
        "from": "Manager <mgr@branch.com>",
        "subject": "Where is my truck?",
        "body": "The truck was dispatched 2 days ago but hasn't reached our warehouse.",
        "message_id": "msg-031",
    },
    {
        "from": "Billing <bill@corp.com>",
        "subject": "Need ledger statement",
        "body": "Please send the ledger statement for our account for the last financial year.",
        "message_id": "msg-032",
    },
    {
        "from": "Support <supp@client.com>",
        "subject": "Account suspension",
        "body": "Why is my purchasing account suspended? We cleared all dues last week.",
        "message_id": "msg-033",
    },
    {
        "from": "Admin <admin@buy.com>",
        "subject": "Change delivery address",
        "body": "Please change the delivery address for order #444 to our new warehouse in Pune.",
        "message_id": "msg-034",
    },
    {
        "from": "Quality <qa@food.com>",
        "subject": "Certificate of Analysis missing",
        "body": "You forgot to attach the COA for the liquid sugar batch delivered today. Send it now.",
        "message_id": "msg-035",
    },
    # --- OTHERS (36-50) ---
    {
        "from": "Applicant <app@example.com>",
        "subject": "Job application",
        "body": "Please find my resume attached for the open position.",
        "message_id": "msg-036",
    },
    {
        "from": "Travel <travel@example.com>",
        "subject": "Hotel booking",
        "body": "Your hotel booking confirmation is ready.",
        "message_id": "msg-037",
    },
    {
        "from": "Sales <sales@printers.com>",
        "subject": "Printer sale",
        "body": "Buy our new office printers at 20% off!",
        "message_id": "msg-038",
    },
    {
        "from": "Spam <win@lottery.com>",
        "subject": "YOU WON!",
        "body": "Click here to claim your $1,000,000 prize!!!",
        "message_id": "msg-039",
    },
    {
        "from": "HR <hr@agency.com>",
        "subject": "Candidate profiles",
        "body": "We have shortlisted 5 candidates for your factory manager role.",
        "message_id": "msg-040",
    },
    {
        "from": "IT <it@services.com>",
        "subject": "Laptop repair quote",
        "body": "The motherboard replacement for your employee's laptop will cost $200.",
        "message_id": "msg-041",
    },
    {
        "from": "Furniture <desk@office.com>",
        "subject": "Ergonomic chairs",
        "body": "Upgrade your office with our new ergonomic chairs.",
        "message_id": "msg-042",
    },
    {
        "from": "Bank <alerts@bank.com>",
        "subject": "Account statement",
        "body": "Your monthly bank statement is attached.",
        "message_id": "msg-043",
    },
    {
        "from": "Newsletter <news@industry.com>",
        "subject": "Weekly Sugar Trends",
        "body": "Read about the latest global sugar production trends.",
        "message_id": "msg-044",
    },
    {
        "from": "Insurance <agent@insure.com>",
        "subject": "Policy renewal",
        "body": "Your factory fire insurance policy is due for renewal next month.",
        "message_id": "msg-045",
    },
    {"from": "Empty <no@body.com>", "subject": "", "body": "", "message_id": "msg-046"},
    {
        "from": "Ambiguous <huh@what.com>",
        "subject": "Hello",
        "body": "Call me back about the job posting.",
        "message_id": "msg-047",
    },
    {
        "from": "Attachment Only <att@chment.com>",
        "subject": "See attached",
        "body": "",
        "message_id": "msg-048",
    },
    {
        "from": "Marketing <promo@ad.com>",
        "subject": "Boost your SEO",
        "body": "We can help rank your website on page 1 of Google.",
        "message_id": "msg-049",
    },
    {
        "from": "Event <invite@gala.com>",
        "subject": "Charity Dinner",
        "body": "You are invited to our annual charity fundraising dinner.",
        "message_id": "msg-050",
    },
]

EXPECTED_CLASSIFICATIONS = ["lead"] * 21 + ["support"] * 15 + ["other"] * 15
EXPECTED_CLASSIFICATIONS[41] = "support"  # Laptop repair quote (internal support)
EXPECTED_CLASSIFICATIONS[46] = "failed"   # Empty
EXPECTED_CLASSIFICATIONS[48] = "failed"   # Empty body

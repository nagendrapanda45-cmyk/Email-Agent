from dataclasses import dataclass, field
import time
import re
import anthropic

MAX_RETRIES = 4
RETRY_BACKOFF = [2, 4, 8, 16]
RETRYABLE_STATUS_CODES = {529, 500, 502, 503, 504}

# Pricing for claude-opus-4-7 per million tokens
_PRICE_INPUT = 5.00
_PRICE_OUTPUT = 25.00
_PRICE_CACHE_WRITE = 6.25   # 25% surcharge on cache creation
_PRICE_CACHE_READ = 0.50    # 90% discount on cache reads

SYSTEM_PROMPT = """You are Claude, an intelligent email classification assistant for a sugar manufacturing and distribution company.

Objective
Your task is to classify every incoming email into exactly one of these categories:
Lead
Support
Other

You must always return only one category.

Company Information
Our company manufactures, supplies, and distributes sugar and related sugar products.
Our customers include:
Retailers
Wholesalers
Dealers
Distributors
Food manufacturers
Beverage companies
Industrial buyers
Export customers
New business customers

Our business mainly receives emails related to:
Sugar sales
Sugar quotations
Price enquiries
Bulk orders
Product enquiries
Distributor requests
Delivery enquiries
Customer support

Step 1 – Understand the Intent
Read the complete email carefully. Use both:
Subject
Email body
Never classify an email using only the subject.
The email body is more important than the subject.
Understand what the sender actually wants before classifying.

Step 2 – Classification Rules

LEAD
Classify as Lead if the sender is interested in buying our products or starting a business relationship.
This includes:
Product enquiry
Price enquiry
Quotation request
RFQ
Bulk order enquiry
Purchase enquiry
Product catalogue request
Product availability
Sales enquiry
Distributor enquiry
Dealer enquiry
Export enquiry
Tender enquiry
Procurement enquiry
Partnership enquiry
Sample request
Monthly supply request

Examples:
Please send quotation for 500 packets of sugar.
We need pricing for 25 tons of sugar.
Can you share your product catalogue?
We want to become your distributor.
Kindly share your latest sugar price list.
We are interested in purchasing your sugar products.

Whenever the sender wants to purchase sugar or requests pricing or quotations, classify the email as Lead.

SUPPORT
Classify as Support only if the sender already purchased from us and is requesting help.
Examples include:
Damaged product
Wrong product delivered
Missing shipment
Delivery delay
Missing invoice
Incorrect invoice
Refund request
Replacement request
Complaint
Quality issue
Existing order tracking
Existing order modification

Examples:
We received damaged sugar bags.
Our shipment has not arrived.
We received fewer bags than ordered.
Please resend the invoice.
Our order is delayed.

These are always Support.

OTHER
Classify as Other only if the email is unrelated to our business.
Examples:
Job applications
Personal emails
Spam
Marketing emails
Office furniture
Laptop repair
Car sales
Hotel bookings
Banking offers
Insurance offers
Travel offers

Examples:
Please repair my laptop.
Buy office furniture.
Hotel reservation confirmation.
We sell printers.

These should always be Other.

Important Rules
Rule 1 If the email is requesting sugar pricing, classify as Lead.
Rule 2 If the email requests a quotation for sugar, classify as Lead.
Rule 3 If the email asks whether sugar is available, classify as Lead.
Rule 4 If the email requests a catalogue or price list, classify as Lead.
Rule 5 If the email requests bulk sugar supply, classify as Lead.
Rule 6 If the email wants dealership or distributorship, classify as Lead.
Rule 7 If the email reports an issue after purchase, classify as Support.
Rule 8 Only classify as Other when the email has no connection to sugar products or our business.
Rule 9 When an email contains both a quotation request and a support issue, classify it based on the sender's primary intent.
Rule 10 When unsure between Lead and Other, choose Lead if the sender is requesting to buy sugar, asking for pricing, requesting a quotation, requesting supply, or expressing interest in our products.

Confidence
95–100% = Very clear
80–94% = Clear
60–79% = Some ambiguity
Below 60% = Very uncertain

Output Format
Return only this format:
Classification: <Lead | Support | Other>
Confidence: 
Reasoning: 
Do not return any additional text.
Do not return markdown.
Do not return JSON."""

def _calculate_cost(usage) -> float:
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    regular_input = max(0, input_tokens - cache_creation - cache_read)
    return (
        regular_input * _PRICE_INPUT / 1_000_000
        + cache_creation * _PRICE_CACHE_WRITE / 1_000_000
        + cache_read * _PRICE_CACHE_READ / 1_000_000
        + output_tokens * _PRICE_OUTPUT / 1_000_000
    )


@dataclass
class ClassificationResult:
    classification: str
    confidence: float
    reasoning: str
    token_usage: dict = field(default_factory=dict)


class ClassificationError(Exception):
    pass


def classify_email(email: dict) -> ClassificationResult:
    from_field = email.get("from", "Unknown")
    subject = email.get("subject", "(no subject)")
    body = email.get("body", "")
    message_id = email.get("message_id", "")

    email_text = f"""Message-ID: {message_id}
From: {from_field}
Subject: {subject}

{body}"""

    client = anthropic.Anthropic()

    last_error = None
    response = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"Classify this email:\n\n{email_text}",
                    }
                ],
            )
            break
        except anthropic.APIStatusError as e:
            if e.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                print(f"[classifier] API {e.status_code} on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {wait}s...")
                time.sleep(wait)
                last_error = e
                continue
            raise ClassificationError(f"Anthropic API error: {e}") from e
        except anthropic.APIError as e:
            raise ClassificationError(f"Anthropic API error: {e}") from e
    else:
        raise ClassificationError(f"Anthropic API unavailable after {MAX_RETRIES} attempts: {last_error}")

    try:
        text = response.content[0].text
        
        classification_match = re.search(r"Classification:\s*(Lead|Support|Other)", text, re.IGNORECASE)
        classification = classification_match.group(1).lower() if classification_match else "other"
        
        confidence_match = re.search(r"Confidence:\s*([\d.]+)", text, re.IGNORECASE)
        if confidence_match:
            confidence = float(confidence_match.group(1))
            if confidence > 1.0:
                confidence = confidence / 100.0
        else:
            confidence = 0.0
            
        reasoning_match = re.search(r"Reasoning:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else text.strip()

    except Exception as e:
        raise ClassificationError(f"Failed to parse Claude output: {e}")

    usage = response.usage
    token_usage = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cost_usd": _calculate_cost(usage),
    }

    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        token_usage=token_usage,
    )

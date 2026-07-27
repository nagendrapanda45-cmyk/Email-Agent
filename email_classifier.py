import re
import time
from dataclasses import dataclass, field

import anthropic

from config import BUSINESS_CONTEXT

MAX_RETRIES = 4
RETRY_BACKOFF = [2, 4, 8, 16]
RETRYABLE_STATUS_CODES = {529, 500, 502, 503, 504}

# Pricing for claude-opus-4-7 per million tokens
_PRICE_INPUT = 5.00
_PRICE_OUTPUT = 25.00
_PRICE_CACHE_WRITE = 6.25  # 25% surcharge on cache creation
_PRICE_CACHE_READ = 0.50  # 90% discount on cache reads


def generate_system_prompt() -> str:
    company = BUSINESS_CONTEXT.get("Company Name", "Company")
    industry = BUSINESS_CONTEXT.get("Industry", "Business")
    products = "\n- ".join(BUSINESS_CONTEXT.get("Products", []))
    customers = "\n- ".join(BUSINESS_CONTEXT.get("Customers", []))

    return f"""You are Claude, an intelligent email classification assistant for {company}, operating in the {industry} industry.

Objective
Your task is to classify every incoming email into exactly one of these categories:
Lead
Support
Other

You must always return only one category.

Company Information
Our company manufactures, supplies, and distributes the following products:
- {products}

Our target customers include:
- {customers}

Step 1 – Understand the Intent
Read the complete email carefully. Use both:
Subject
Email body
Never classify an email using only the subject. The email body is more important than the subject.
Understand what the sender actually wants before classifying.

Step 2 – Classification Rules

LEAD
Classify as Lead if the sender is interested in buying our products, starting a business relationship, or making a commercial enquiry about any of our products/services.
This includes:
- Product pricing or catalogue requests
- Quotation requests, RFQs, or Tender enquiries
- Bulk orders or monthly supply requests
- Dealership, distributorship, or export enquiries
Whenever the sender expresses genuine commercial interest in our offerings, classify as Lead.

SUPPORT
Classify as Support only if the sender already purchased from us or is an existing customer requesting help.
This includes:
- Damaged products, wrong deliveries, or missing shipments
- Delivery delays or tracking
- Invoice issues, refund requests, or replacements
- Existing order modifications or quality complaints
If they are asking for help with an existing purchase, classify as Support.

OTHER
Classify as Other only if the email is completely unrelated to our business or products.
This includes:
- Job applications
- Personal emails
- Spam or unrelated marketing emails
- Booking requests or unrelated product sales (e.g., selling us printers or furniture)

Step 3 - Determining Primary Intent
When an email contains both a quotation request and a support issue, classify it based on the sender's primary intent.
When unsure between Lead and Other, choose Lead if there is any genuine commercial interest in purchasing our products.

Confidence
Score your confidence based on clarity of intent:
0.95–1.0 = Very clear commercial enquiry or very clear existing customer issue.
0.80–0.94 = Clear intent, but perhaps lacking some detail.
0.60–0.79 = Some ambiguity in what they want.
Below 0.60 = Very uncertain or highly ambiguous.

Output Format
Return only this format:
Classification: <Lead | Support | Other>
Confidence: <0.0 to 1.0>
Reasoning: <Your reasoning>

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
    system_prompt = generate_system_prompt()
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
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
                print(
                    f"[classifier] API {e.status_code} on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {wait}s..."
                )
                time.sleep(wait)
                last_error = e
                continue
            raise ClassificationError(f"Anthropic API error: {e}") from e
        except anthropic.APIError as e:
            raise ClassificationError(f"Anthropic API error: {e}") from e
    else:
        raise ClassificationError(
            f"Anthropic API unavailable after {MAX_RETRIES} attempts: {last_error}"
        )

    try:
        text = response.content[0].text

        classification_match = re.search(
            r"Classification:\s*(Lead|Support|Other)", text, re.IGNORECASE
        )
        classification = (
            classification_match.group(1).lower() if classification_match else "other"
        )

        confidence_match = re.search(r"Confidence:\s*([\d.]+)", text, re.IGNORECASE)
        if confidence_match:
            confidence = float(confidence_match.group(1))
            if confidence > 1.0:
                confidence = confidence / 100.0
        else:
            confidence = 0.0

        reasoning_match = re.search(
            r"Reasoning:\s*(.*)", text, re.IGNORECASE | re.DOTALL
        )
        reasoning = (
            reasoning_match.group(1).strip() if reasoning_match else text.strip()
        )

    except Exception as e:
        raise ClassificationError(f"Failed to parse Claude output: {e}")

    usage = response.usage
    token_usage = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0)
        or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
        "cost_usd": _calculate_cost(usage),
    }

    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        token_usage=token_usage,
    )

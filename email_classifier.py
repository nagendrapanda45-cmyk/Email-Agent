import re
import time
from dataclasses import dataclass, field

import openai
import os

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
This explicitly includes:
- Any Product enquiry (e.g., asking for quantities, bags, or details of our products)
- Bulk purchase enquiry or wholesale enquiry
- Quotation requests, RFQs, or Tender enquiries
- Dealer enquiry, distributor enquiry, or export enquiry
- Commercial purchase requests
Whenever the sender expresses genuine commercial interest in our offerings or asks for our products, classify as Lead.

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
    if not usage:
        return 0.0
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    return (
        input_tokens * _PRICE_INPUT / 1_000_000
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

    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )

    last_error = None
    response = None
    system_prompt = generate_system_prompt()
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"Classify this email:\n\n{email_text}",
                    }
                ],
            )
            break
        except openai.APIStatusError as e:
            if e.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[attempt]
                print(
                    f"[classifier] API {e.status_code} on attempt {attempt + 1}/{MAX_RETRIES}, retrying in {wait}s..."
                )
                time.sleep(wait)
                last_error = e
                continue
            raise ClassificationError(f"OpenRouter API error: {e}") from e
        except Exception as e:
            raise ClassificationError(f"OpenRouter API error: {e}") from e
    else:
        raise ClassificationError(
            f"OpenRouter API unavailable after {MAX_RETRIES} attempts: {last_error}"
        )

    try:
        text = response.choices[0].message.content

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
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cost_usd": _calculate_cost(usage),
    }

    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        token_usage=token_usage,
    )

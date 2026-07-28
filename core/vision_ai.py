"""
vision_ai.py

Wraps Google Cloud Vision (label detection) and Gemini (final classification)
calls. Credentials are injected at call time from the app's saved config
rather than requiring the user to export environment variables manually
before launching the app.

Vision API label detection is optional (toggled in Settings). When disabled,
classification runs on Gemini alone and the Google Cloud credentials json is
irrelevant - it is fine for it to be absent or invalid in that mode. When
Vision API is enabled, the credentials json becomes required and must point
to a real file, since ImageAnnotatorClient() needs it to authenticate.
"""

import io
import os

from google.cloud import vision
from google import genai
from google.genai import errors


class CredentialsMissingError(Exception):
    """
    Raised when required credentials are not configured for the current mode:
      - Gemini API key is always required.
      - Google Cloud credentials json is only required when use_vision_api is True.
    """
    pass


def classify_trash(
    image_path: str,
    api_key: str,
    credentials_path: str,
    trash_categories: list,
    use_vision_api: bool = True,
) -> str:
    """
    Runs optional Vision API label detection followed by Gemini classification.

    Returns one of:
      - "<category> <confidence>"   on a well-formed two-token response
      - "Can Not Identify"          if Gemini's answer is not exactly one
                                     recognized category word + one confidence token
      - "error_quota rate_limit"    if the Gemini call raises a client error (e.g. quota)

    Raises CredentialsMissingError if the Gemini api key is missing, or if
    use_vision_api is True and the Google credentials path is missing/invalid.
    """
    if not api_key:
        raise CredentialsMissingError("gemini api key not set")

    labels = []

    if use_vision_api:
        if not credentials_path:
            raise CredentialsMissingError(
                "google credentials json path not set (required while vision api is enabled)"
            )
        if not os.path.isfile(credentials_path):
            raise CredentialsMissingError(f"credentials file not found: {credentials_path}")

        # inject credentials into the process environment, matching what the
        # google-cloud-vision client library expects to find
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        client_vision = vision.ImageAnnotatorClient()

        with io.open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client_vision.label_detection(image=image)
        labels = [label.description.lower() for label in response.label_annotations]
        print("vision api labels:", labels)

    os.environ["GEMINI_API_KEY"] = api_key

    client_genai = genai.Client()
    uploaded_image = client_genai.files.upload(file=image_path)

    category_list = ", ".join(trash_categories)

    if labels:
        context_sentence = f"i detected these labels using computer vision: {labels}. "
    else:
        # vision api disabled - gemini classifies from the image alone
        context_sentence = ""

    prompt = (
        f"{context_sentence}"
        "based on the image, what kind of trash is this? "
        f"answer using exactly this format: one word from this list [{category_list}] "
        "followed by a single space, and then a numerical value for your confidence percentage (e.g., plastic 92%). "
        "do not include any other text or punctuation."
    )

    try:
        response = client_genai.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_image, prompt],
        )
        result_text = response.text.strip()
        print("gen ai response:", result_text)
    except errors.ClientError as e:
        print(f"gen ai error encountered: {e}")
        return "error_quota rate_limit"

    # enforce the "one category word + one confidence token" contract;
    # anything else is treated as unparseable rather than guessed at
    parts = result_text.split()
    if len(parts) != 2:
        return "Can Not Identify"

    category, confidence = parts
    if category.lower() not in [c.lower() for c in trash_categories]:
        return "Can Not Identify"

    return f"{category} {confidence}"

#!/usr/bin/env python3
"""Analyze a local image file using OpenAI's vision API."""

import base64
import os
from openai import OpenAI


def encode_image(image_path: str) -> str:
    """
    Encode a local image file to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_image_from_file(image_path: str) -> str:
    """
    Analyze a local image file and return the analysis.

    Args:
        image_path: Path to the image file to analyze

    Returns:
        The model's response describing the image
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    base64_image = encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is in this image?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Example usage - replace with your image path
    image_path = "path_to_your_image.jpg"
    if os.path.exists(image_path):
        result = analyze_image_from_file(image_path)
        print(result)
    else:
        print(f"Image not found: {image_path}")

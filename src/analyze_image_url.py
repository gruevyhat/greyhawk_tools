#!/usr/bin/env python3
"""Analyze an image from a URL using OpenAI's vision API."""

import os
from openai import OpenAI

def analyze_image_from_url(image_url: str) -> str:
    """
    Analyze an image from a URL and return the analysis.

    Args:
        image_url: URL of the image to analyze

    Returns:
        The model's response describing the image
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Example usage with a sample image
    sample_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    result = analyze_image_from_url(sample_url)
    print(result)

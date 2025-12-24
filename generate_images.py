import os
import base64
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPTS = {
    "mr": "A soft, emotional abstract artwork inspired by nostalgic Japanese pop-rock. Warm light particles, gentle gradients, transparent layers, subtle motion.",
    "composition": "An abstract visualization of music composition. Flowing waveforms, harmonic structures, layered colors, creative energy.",
    "video": "A cinematic abstract artwork inspired by video editing. Lens flares, color grading tones, timeline-like patterns, dynamic motion.",
    "boardgame": "A strategic abstract artwork inspired by board games. Geometric shapes, tension, contrast, layered grids, subtle complexity."
}

def generate_image(genre: str, output_path: str):
    prompt = PROMPTS.get(genre)
    if not prompt:
        raise ValueError(f"Unknown genre: {genre}")

    print(f"Generating image for genre: {genre}")

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        response_format="b64_json"
    )

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    os.makedirs("images", exist_ok=True)
    generate_image("mr", "images/mr.png")
    generate_image("composition", "images/composition.png")
    generate_image("video", "images/video.png")
    generate_image("boardgame", "images/boardgame.png")

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
    """ジャンル別に画像を生成し、ローカルに保存する"""

    prompt = PROMPTS.get(genre)
    if not prompt:
        raise ValueError(f"Unknown genre: {genre}")

    print(f"Generating image for genre: {genre}")

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    # base64データを取り出す
    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    # 保存
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"Saved: {output_path}")
    return output_path

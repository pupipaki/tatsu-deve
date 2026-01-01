import os
import replicate

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

PROMPTS = {
    "mr": "abstract soft emotional artwork, warm light particles, japanese pop-rock mood, cinematic, high detail",
    "composition": "abstract visualization of music composition, flowing waveforms, harmonic colors, layered gradients",
    "video": "cinematic abstract artwork inspired by video editing, lens flares, color grading tones, timeline patterns",
    "boardgame": "strategic abstract artwork inspired by board games, geometric shapes, tension, layered grids"
}

def generate_image(genre: str, output_path: str):
    prompt = PROMPTS.get(genre)
    if not prompt:
        raise ValueError(f"Unknown genre: {genre}")

    print(f"Generating image for genre: {genre}")

    # model = replicate.models.get("stability-ai/sdxl")
    # version = model.versions.get("5c7d5c6e0c6e4e3e8b7e8f7e8b7e8f7e")  # SDXLの安定版


    output = version.predict(
        prompt=prompt,
        width=1024,
        height=1024
    )
    # output = replicate.run(
    #   "google/imagen-4",
    #   input={
    #     "prompt": prompt,
    #     "aspect_ratio": "16:9",
    #     "safety_filter_level": "block_medium_and_above"
    #   }
    # )



    # output は画像URLのリスト
    image_url = output[0]

    # 画像をダウンロードして保存
    import requests
    img = requests.get(image_url).content
    with open(output_path, "wb") as f:
        f.write(img)

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    os.makedirs("images", exist_ok=True)
    generate_image("mr", "images/mr.png")
    generate_image("composition", "images/composition.png")
    generate_image("video", "images/video.png")
    generate_image("boardgame", "images/boardgame.png")

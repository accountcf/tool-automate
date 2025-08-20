# pip install openai edge-tts asyncio
import asyncio, edge_tts, openai, os, json, math
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = os.getenv("OPENROUTER_KEY")

topic = "5 lời khuyên cho người mới khởi nghiệp"
segments = 8
duration_each = 60/segments

prompt = f"""
You are a Vietnamese TikTok script writer.
Create exactly {segments} very short POV paragraphs (≈ {math.floor(duration_each)} s each).
Topic: {topic}
Return JSON: {{"segments": ["text1", "text2", ...]}}
"""
resp = openai.ChatCompletion.create(
    model="openai/gpt-4o",
    messages=[{"role": "user", "content": prompt}]
)
script = json.loads(resp.choices[0].message.content)["segments"]

# TTS
async def gen_tts(text, idx):
    communicate = edge_tts.Communicate(text, "vi-VN-HoaiMyNeural")
    await communicate.save(f"output/{idx:02d}.mp3")
asyncio.run(asyncio.gather(*(gen_tts(t, i) for i, t in enumerate(script))))
print("Audio files ready at output/*.mp3")

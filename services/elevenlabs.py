import os

from elevenlabs import set_api_key, generate

from dotenv import load_dotenv, find_dotenv


# Set API key
load_dotenv(find_dotenv())
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
set_api_key(ELEVENLABS_API_KEY)


def voice_stream(text, voice, stream=True, stream_chunk_size=8192):
    # TODO: Voice must be customized by character
    audio_stream = generate(
        text=text,
        voice=voice,
        stream=stream,
        stream_chunk_size=stream_chunk_size,
        model="eleven_multilingual_v2",
    )
    return audio_stream

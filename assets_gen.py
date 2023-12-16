'''
    assets_gen.py

    - This script generates the assets for the video (script, audio, images, videos)
    - The original script is adapted for local use with balacoon tts by Patrick Walchshofer
    - The original scripts author is Juled Zaganjori    
'''

from balacoon_tts import TTS
from huggingface_hub import hf_hub_download, list_repo_files
import librosa
import os
import openai
import json
import random
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


# Global variables defining asset characteristics and constraints
min_stock_video_length = 5  # Minimum length of stock videos in seconds
min_stock_image_length = 3  # Minimum display time for stock images in seconds
max_stock_video_length = 10  # Maximum length of stock videos in seconds
max_stock_image_length = 5  # Maximum display time for stock images in seconds
max_paragraphs = 3  # Maximum number of paragraphs in the script
orientation = "landscape"  # Preferred orientation for stock images and videos
asset_size = "medium"  # Preferred size for stock images and videos

# Generate random string


def get_random_string(length):
    letters = "abcdefghijklmnopqrstuvwxyz1234567890"
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


# Setup video directory
def video_setup():
    """
    Set up the video directory structure and generate a unique video ID.

    Returns:
        str: A unique video ID.
    """
    global max_paragraphs
    # Generate video ID
    video_id = get_random_string(15)
    if not os.path.exists("videos"):
        os.makedirs("videos")
    # Save output
    if not os.path.exists("videos/" + video_id):
        os.makedirs("videos/" + video_id)
    else:
        video_id = get_random_string(20)

    for i in range(0, max_paragraphs):
        os.makedirs("videos/" + video_id + "/p" + str(i) + "/img")

    for i in range(0, max_paragraphs):
        os.makedirs("videos/" + video_id + "/p" + str(i) + "/video")

    return video_id


# Video script from OpenAI
def get_video_script(topic, video_id):
    """
    Generate a video script for a given topic using OpenAI.

    Args:
        topic (str): The topic for which the video script is to be generated.
        video_id (str): A unique identifier for the video.

    Returns:
        bool: True if the video script is successfully generated, otherwise False.
    """
    global max_paragraphs

    # Prompt
    prompt = '''
        You are a video script generation machine. I give you a topic and you create 3 paragraphs of video script with an intro and an outro. You should output only in JSON format and separate each paragraph in with a different key "P1", "P2", "P3".  You should also include strings in [] where you should include tags for an image that you find reasonable to display in that moment in time. There should be 10 tags minimum in each such as ["black coat", "dressing room", "wardrobe", "HD", "man"... ]. Make sure to include a variety of these tags in different points in time so that the article images correspond and are abundant.
        Please stick to the format. Paragraphs are only text and tags are only strings in []. You can't use special characters. DON'T ADD ANYTHING ELSE TO THE RESPONSE. ONLY THE JSON FORMAT BELOW.
        Here's the format of what I'm looking for (NEVER GO OUT OF THIS FORMAT AND CHANGE THE DICTIONARY KEYS):
        {
            "topic": " '''+topic+''' ",
    '''

    # Create a prompt sample as the one above but as many max_paragraphs value
    for i in range(0, max_paragraphs):
        prompt += '''
                "p''' + str(i) + '''": "paragraph text",
                "p''' + str(i) + '''_img_tags": [...],
        '''

    prompt += '''
        }
    '''

    # Completion
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": topic
            }
        ],
    )

    # Validate output
    try:
        # Sanitize output
        transcript = sanitize_JSON(
            response["choices"][0]["message"]["content"])

        json.loads(transcript)
        with open("videos/" + video_id + "/script.json", "w") as f:
            f.write(transcript)

        return True

    except Exception as e:
        print(e)
        return False


def sanitize_JSON(json_string):
    json_string = str(json_string)
    # Remove \n
    json_string = json_string.replace("\n", "")
    # Remove \"
    json_string = json_string.replace("\\\"", "\"")
    # Remove \'
    json_string = json_string.replace("\\\'", "\'")
    # Remove \\n
    json_string = json_string.replace("\\n", "")

    return json_string

# TTS audio from Balacoon TTS



def get_tts_audio(video_id):
    """
    Generate Text-To-Speech (TTS) audio using Balacoon TTS for the paragraphs in the script.

    Args:
        video_id (str): A unique identifier for the video.

    Returns:
        bool: True if the TTS audio is successfully generated, otherwise False.
    """
    global max_paragraphs
    model_repo_dir = "/home/pwalch/projects/Files/YouTubeVideoTool/text2video/tts_models"  # Specify the directory where the model is located
    model_name_str = "en_us_cmuartic_jets_cpu.addon"  # Specify the appropriate model file
    speaker_str = "rxr"  # Specify the appropriate speaker
    
    # Here, we are downloading the Balacoon TTS model using Hugging Face Hub
    # The model is downloaded only if it is not already present in the specified directory.
    for name in list_repo_files(repo_id="balacoon/tts"):
        if not os.path.isfile(os.path.join(model_repo_dir, name)):
            hf_hub_download(
                repo_id="balacoon/tts",
                filename=name,
                local_dir=model_repo_dir,
            )
    
    model_path = os.path.join(model_repo_dir, model_name_str)
    tts = TTS(model_path)  # Initializing the Balacoon TTS with the specified model
    
    # Read script
    with open("videos/" + video_id + "/script.json", "r") as f:
        script = json.loads(f.read())

    for i in tqdm(range(0, max_paragraphs)):
        text_str = script["p" + str(i)]
        if len(text_str) > 1024:  # Truncate the text if it is longer than 1024 characters
            text_str = text_str[:1024]
        
        samples = tts.synthesize(text_str, speaker_str)  # Synthesize the audio using Balacoon TTS
        
        # Assuming `samples` is a numpy array representing the audio waveform
        # Save it to a .wav file
        output_file_path = "videos/" + video_id + "/p" + str(i) + "/audio.wav"
        librosa.output.write_wav(output_file_path, samples, tts.get_sampling_rate())
        
    return True


# Photo and video assets
def get_stock_images(video_id, part_number, part_tags, image_count, orientation, asset_size):
    api_key = os.getenv("PEXELS_API_KEY")
    # Perform search with the tags joined by a + sign
    response = requests.get("https://api.pexels.com/v1/search?query=" + "+".join(part_tags) + "&per_page=" +
                            str(image_count) + "&orientation=" +
                            orientation + "&size=" + str(asset_size),
                            headers={"Authorization": api_key})
    # Get images
    images = response.json()["photos"]
    # Get image URLs
    image_urls = [image["src"]["original"] for image in images]
    # Download images
    for i in range(0, len(image_urls)):
        # Get image
        image = requests.get(image_urls[i])
        # Save image
        with open("videos/" + video_id + "/p" + str(part_number) + "/img/" + str(i) + ".jpg", "wb") as f:
            f.write(image.content)


def get_stock_videos(video_id, part_number, part_tags, video_count, orientation, asset_size):

    api_key = os.getenv("PEXELS_API_KEY")

    response = requests.get("https://api.pexels.com/videos/search?query=" + "+".join(
        part_tags) + "&orientation=" + orientation + "&size=" + str(asset_size) + "&per_page=" + str(video_count),
        headers={"Authorization": api_key})
    # Get videos
    videos = response.json()["videos"]

    # Get video URLs
    video_urls = [video["video_files"][0]["link"] for video in videos]

    # Download videos
    for i in range(0, video_count):
        # Get video
        video = requests.get(video_urls[i])
        # Save video
        with open("videos/" + video_id + "/p" + str(part_number) + "/video/" + str(i) + ".mp4", "wb") as f:
            f.write(video.content)


# Setup stock assets
def get_part_stock_assets(video_id, part_num, part_len):
    global orientation, asset_size

    # Read tags from script.json
    with open("videos/" + video_id + "/script.json", "r") as f:
        script = json.loads(f.read())

    # Get tags
    part_tags = script["p" + str(part_num) + "_img_tags"]

    img_count = int(part_len / min_stock_image_length / 2)
    video_count = int(part_len / min_stock_video_length / 2)

    get_stock_images(video_id, part_num, part_tags,
                     img_count, orientation, asset_size)
    get_stock_videos(video_id, part_num, part_tags,
                     video_count, orientation, asset_size)


def get_stock_assets(video_id):
    global max_paragraphs
    # Read script.json
    with open("videos/" + video_id + "/script.json", "r") as f:
        script = json.loads(f.read())

    # Calculate part lengths from the audios
    part_lengths = []
    for i in range(0, max_paragraphs):
        # Get audio length
        audio_length = librosa.get_duration(path="videos/" + video_id + "/p" + str(i) + "/audio.wav")
        part_lengths.append(audio_length)

    print("Downloading assets...")
    # Get stock assets for each part
    for i in tqdm(range(0, len(part_lengths))):
        get_part_stock_assets(video_id, i, part_lengths[i])

    return True


def assets_gen(topic, custom_orientation="landscape", custom_asset_size="medium"):
    global orientation, asset_size
    orientation = custom_orientation
    asset_size = custom_asset_size

    # Setup video
    video_id = video_setup()
    # Get video script
    print("Generating video script...")
    if get_video_script(topic, video_id):
        print("Video script generated!")
    else:
        print("Video script generation failed!")
    # Get TTS audio
    print("Generating TTS audio...")
    if get_tts_audio(video_id):
        print("TTS audio generated!")
    else:
        print("TTS audio generation failed!")
    # Get stock assets
    print("Generating stock assets...")
    if get_stock_assets(video_id):
        print("Stock assets generated!")
    else:
        print("Stock assets generation failed!")

    return video_id


if __name__ == "__main__":
    # Get topic
    topic = input("Enter a topic: ")
    # Setup video
    video_id = video_setup()
    # Get video script
    print("Generating video script...")
    if get_video_script(topic, video_id):
        print("Video script generated!")
    else:
        print("Video script generation failed!")
    # Get TTS audio
    print("Generating TTS audio...")
    if get_tts_audio(video_id):
        print("TTS audio generated!")
    else:
        print("TTS audio generation failed!")
    # Get stock assets
    print("Generating stock assets...")
    if get_stock_assets(video_id):
        print("Stock assets generated!")
    else:
        print("Stock assets generation failed!")

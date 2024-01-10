import itertools
import json
import numpy as np
import os
import pulp
import random
import re
import requests
import soundfile as sf
import sys
import nltk
import urllib.parse
from dotenv import load_dotenv
from huggingface_hub import hf_hub_download, list_repo_files
from moviepy.editor import VideoFileClip
from nltk import sent_tokenize
from PIL import Image
from tqdm import tqdm

# Bark imports
from bark.api import semantic_to_waveform
from bark.generation import generate_text_semantic, preload_models
from bark import SAMPLE_RATE

# Custom imports from your scripts
from ranking_assistant import RankingAssistant
from script_creator_no_class import gen_video_script



# Load environment variables from .env file
load_dotenv()

# Initialize global variables
downloaded_urls = set()  # This set will keep track of all downloaded URLs
# Global sets for tracking used media URLs
used_image_urls = set()
used_video_urls = set()
unique_descriptions = set()
used_descriptions = set()


def update_settings(settings):
    global min_stock_video_length
    global min_stock_image_length, max_stock_video_length
    global max_stock_image_length, max_paragraphs,max_retries
    global orientation, asset_size, duration_crossfade, image_per_time
    global vid_per_time, min_count_images, min_count_videos
    global video_fps, audio_fps, video_width, video_height, video_size, silence_duration
    global bark_speaker, bark_gen_temp, bark_min_eos_p
    
    # Add new settings for BARK model preloading
    global bark_text_use_gpu, bark_text_use_small
    global bark_coarse_use_gpu, bark_coarse_use_small
    global bark_fine_use_gpu, bark_fine_use_small
    global bark_codec_use_gpu
    
    min_stock_video_length = settings['min_stock_video_length']
    min_stock_image_length = settings['min_stock_image_length']
    max_stock_video_length = settings['max_stock_video_length']
    max_stock_image_length = settings['max_stock_image_length']
    max_paragraphs = settings['max_paragraphs']
    max_retries = settings["max_retries"]
    orientation = settings['orientation']
    asset_size = settings['asset_size']
    duration_crossfade = settings['duration_crossfade']
    image_per_time = settings['image_per_time']
    vid_per_time = settings['vid_per_time']
    min_count_images = settings['min_count_images']
    min_count_videos = settings['min_count_videos']
    video_fps = settings['video_fps']
    audio_fps = settings['audio_fps']
    video_width = settings['video_width']
    video_height = settings['video_height']
    video_size = (video_width, video_height)
    silence_duration = settings['silence_duration']
    
    # BARK related settings
    bark_speaker = settings.get("bark_speaker", "v2/en_speaker_6")
    bark_gen_temp = settings.get("bark_gen_temp", 0.6)
    bark_min_eos_p = settings.get("bark_min_eos_p", 0.05)
    bark_model_type = settings.get("bark_model_type", "text")

    # Initialize or get BARK model preload settings from the settings dictionary
    bark_text_use_gpu = settings.get("bark_text_use_gpu", True)
    bark_text_use_small = settings.get("bark_text_use_small", False)
    bark_coarse_use_gpu = settings.get("bark_coarse_use_gpu", True)
    bark_coarse_use_small = settings.get("bark_coarse_use_small", False)
    bark_fine_use_gpu = settings.get("bark_fine_use_gpu", True)
    bark_fine_use_small = settings.get("bark_fine_use_small", False)
    bark_codec_use_gpu = settings.get("bark_codec_use_gpu", True)

    # Ensure BARK models are preloaded with the appropriate settings
    preload_models(
        text_use_gpu=bark_text_use_gpu,
        text_use_small=bark_text_use_small,
        coarse_use_gpu=bark_coarse_use_gpu,
        coarse_use_small=bark_coarse_use_small,
        fine_use_gpu=bark_fine_use_gpu,
        fine_use_small=bark_fine_use_small,
        codec_use_gpu=bark_codec_use_gpu,
    )

# Helper and core functions
def get_random_string(length):
    letters = "abcdefghijklmnopqrstuvwxyz1234567890"
    return ''.join(random.choice(letters) for i in range(length))

def video_setup(max_paragraphs):
    video_id = get_random_string(15)
    if not os.path.exists("videos"):
        os.makedirs("videos")
    if not os.path.exists(f"videos/{video_id}"):
        os.makedirs(f"videos/{video_id}")
    else:
        video_id = get_random_string(20)

    for i in range(max_paragraphs):  # 0-based indexing, directories with 1-based numbering
        p_num = i + 1
        img_dir = f"videos/{video_id}/p{p_num}/img"
        video_dir = f"videos/{video_id}/p{p_num}/video"
        script_dir = f"videos/{video_id}/p{p_num}/script"

        os.makedirs(img_dir)
        os.makedirs(video_dir)
        os.makedirs(script_dir)

    return video_id

def create_script_files(video_script_dict, video_id):
    try:
        for paragraph_detail in video_script_dict['script_details']['paragraph_details']:
            p_num = paragraph_detail['paragraph_number']
            paragraph = paragraph_detail['text']
            image_descriptions = paragraph_detail['image_descriptions']
            img_tags = paragraph_detail['image_tags']

            paragraph_data = {
                "paragraph": paragraph,
                "image_descriptions": image_descriptions,
                "img_tags": img_tags
            }

            # Constructing file path
            script_dir_path = f"videos/{video_id}/p{p_num}/script"
            script_file_path = f"{script_dir_path}/script_{p_num}.json"

            # Ensure directory exists
            os.makedirs(script_dir_path, exist_ok=True)

            # Write data to script file
            with open(script_file_path, "w") as f:
                json.dump(paragraph_data, f)
            print(f"Script file created at {script_file_path}")  # Logging the creation

        return True
    except Exception as e:
        print(f"Error creating script files: {e}")
        return False

    
# Function to generate TTS audio using BARK
def get_bark_tts_audio(video_id, max_paragraphs):
    for i in range(max_paragraphs):
        p_num = i + 1  # for user-facing file naming (1-based indexing)
        script_file_path = f"videos/{video_id}/p{p_num}/script/script_{p_num}.json"

        with open(script_file_path, "r") as f:
            script_data = json.load(f)
            script = script_data["paragraph"].replace("\n", " ").strip()

        sentences = nltk.sent_tokenize(script)
        silence = np.zeros(int(0.1 * SAMPLE_RATE))  # quarter second of silence

        pieces = []
        for sentence in sentences:
            semantic_tokens = generate_text_semantic(
                sentence,
                history_prompt=bark_speaker,  # Use the global variable
                temp=bark_gen_temp,          # Use the global variable
                min_eos_p=bark_min_eos_p,    # Use the global variable
            )

            audio_array = semantic_to_waveform(semantic_tokens, history_prompt=bark_speaker)
            pieces += [audio_array, silence.copy()]

        audio_output = np.concatenate(pieces)
        output_file_path = f"videos/{video_id}/p{p_num}/video/audio.wav"
        sf.write(output_file_path, audio_output, SAMPLE_RATE)
    
    return True

def clear_video_directory(video_id):
    """Delete the directory associated with the given video_id."""
    video_dir = f"videos/{video_id}"
    if os.path.exists(video_dir):
        import shutil
        shutil.rmtree(video_dir)

def optimize_clip_distribution(T_a_seconds: float) -> tuple:
    # Retrieve necessary global settings
    global duration_crossfade, image_per_time, vid_per_time, max_stock_image_length, max_stock_video_length, min_count_images, min_count_videos, min_stock_image_length, min_stock_video_length, silence_duration

    # Convert seconds to milliseconds for internal calculations
    T_a = T_a_seconds * 1000  # Audio duration in milliseconds
    T_s = T_a + silence_duration * 1000  # Total sequence duration including silence

    # Pre-calculate total duration allocated for images and videos adjusted for crossfades
    seq_image_duration = image_per_time * T_s - (image_per_time * (min_count_images - 1) * duration_crossfade * 1000)
    seq_video_duration = vid_per_time * T_s - (vid_per_time * (min_count_videos - 1) * duration_crossfade * 1000)

    # Calculate optimal clip counts and durations for images and videos
    N_i, img_d = calculate_clip_counts_and_durations(seq_image_duration, min_stock_image_length * 1000, max_stock_image_length * 1000)
    N_v, vid_d = calculate_clip_counts_and_durations(seq_video_duration, min_stock_video_length * 1000, max_stock_video_length * 1000)

    return N_i, img_d / 1000, N_v, vid_d / 1000  # Convert durations back to seconds for output

def calculate_clip_counts_and_durations(seq_duration, min_duration, max_duration):
    # Calculate the maximum possible number of clips
    max_clips = int(seq_duration // min_duration)  # Using floor division to ensure integer result

    # If the maximum number of clips is zero, return minimum counts and minimum durations
    if max_clips == 0:
        return min_count_images if 'img' in locals() else min_count_videos, min_duration

    # Calculate the total duration that would be taken by the maximum number of clips
    total_duration_with_max_clips = max_clips * min_duration

    # If there's leftover duration, calculate how much needs to be added to each clip
    leftover_duration = seq_duration - total_duration_with_max_clips
    additional_duration_per_clip = leftover_duration / max_clips if max_clips > 0 else 0

    # Calculate the final duration of each clip
    clip_duration = min_duration + additional_duration_per_clip

    # Ensure that the duration does not exceed the maximum allowed duration
    clip_duration = min(clip_duration, max_duration)

    return max_clips, clip_duration



def get_part_lengths(video_id, max_paragraphs):
    """
    Calculates the number of images and videos and their respective durations for each paragraph in the video.

    Parameters:
    video_id (str): Unique identifier for the video.
    max_paragraphs (int): Maximum number of paragraphs to process.

    Returns:
    dict: Dictionary containing part lengths and associated details.
    """
    global part_lengths, image_per_time, vid_per_time, silence_duration, min_stock_image_length, max_stock_image_length, min_stock_video_length, max_stock_video_length

    part_lengths = {}

    for i in range(max_paragraphs):
        p_num = i + 1
        audio_path = f"videos/{video_id}/p{p_num}/video/audio.wav"
        if not os.path.exists(audio_path):
            print(f"Audio file does not exist for paragraph {p_num}. Skipping.")
            continue

        with sf.SoundFile(audio_path) as f:
            frames = f.frames
            rate = f.samplerate
            audio_length = frames / float(rate)  # Audio length in seconds
            total_length = audio_length + silence_duration / 1000.0  # Convert ms to s for total length

        # Using the optimize_clip_distribution function
        N_i, d_i, N_v, d_v = optimize_clip_distribution(total_length)

     
        # Prepare durations lists
        img_durations = [d_i] * int(N_i)
        vid_durations = [d_v] * int(N_v)

        # Store in part_lengths dictionary
        part_lengths[i] = {
            "num_images": int(N_i),
            "num_videos": int(N_v),
            "img_durations": img_durations,
            "vid_durations": vid_durations
        }

        # Debug print for img_durations and vid_durations
        print(f"Paragraph {p_num}:")
        print(f"  Total Lenth:{total_length} seconds")
        print(f"  Number of Image Clips: {N_i} with Duration: {d_i} seconds each")
        print(f"  Number of Video Clips: {N_v} with Duration: {d_v} seconds each")
        print(f"  Image durations: {img_durations}")
        print(f"  Video durations: {vid_durations}")

    return part_lengths



def is_desired_video(video_file):
    """
    Checks if the video file matches the criteria for desired resolution.
    Uses the global 'orientation' variable to determine the target size.
    """
    # Calculate the target size based on the global orientation setting
    target_size = get_target_size(orientation)
    print(f"target_size={target_size}")

    # Compare video file resolution to the target size
    return (video_file['width'], video_file['height']) == target_size

def flatten(lst):
    """Flatten a list of lists to a single list."""
    return [item for sublist in lst for item in sublist]

def get_target_size(orientation):
    if orientation == 'vertical':
        return (1080, 1920)
    elif orientation == 'square':
        return (1080, 1080)
    else:  # 'landscape' or any other case will default to landscape orientation
        return (1920, 1080)

def resize_image_aspect_ratio(img, target_size):
    # Calculate the ratio and the new size
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]

    if target_ratio > img_ratio:
        new_height = int(target_size[0] / img_ratio)
        new_size = (target_size[0], new_height)
    else:
        new_width = int(target_size[1] * img_ratio)
        new_size = (new_width, target_size[1])

    return img.resize(new_size, Image.Resampling.LANCZOS)

def crop_center(img, target_width, target_height):
    width, height = img.size   # Get dimensions
    left = (width - target_width)/2
    top = (height - target_height)/2
    right = (width + target_width)/2
    bottom = (height + target_height)/2

    return img.crop((left, top, right, bottom))


def extract_tags_from_url(url):
    tags = re.findall(r'video/([a-z0-]+)-', url)
    return ' '.join(tags).replace('-', ' ')

def is_desired_video(file, desired_quality='hd'):
    return file['quality'] == desired_quality

def get_stock_images(video_id, part_number, model_descriptions, media_details, paragraph_key):
    global part_lengths, used_image_urls, used_descriptions, orientation, asset_size

    api_key = os.getenv("PEXELS_API_KEY")
    target_image_count = part_lengths[part_number]['num_images']
    print("------------------- get stock images ------------------")
    print(f"{paragraph_key} Target Image Count: {target_image_count}")
    target_size = get_target_size(orientation)  # Define target size based on orientation

    
    model_descriptions_cycle = itertools.cycle(model_descriptions)
    image_index = 1  # Start indexing from 1 for user-facing keys

    while image_index <= target_image_count:
        model_desc = next(model_descriptions_cycle)  # Get next description
        encoded_desc = urllib.parse.quote(model_desc)
        api_url = f"https://api.pexels.com/v1/search?query={encoded_desc}&per_page=80&orientation={orientation}&size={asset_size}"
        print(f"Making API Request to: {api_url}")
        response = requests.get(api_url, headers={"Authorization": api_key})

        if response.status_code == 200:
            # Extract and print rate limit information
            rate_limit = response.headers.get('X-Ratelimit-Limit')
            rate_remaining = response.headers.get('X-Ratelimit-Remaining')
            rate_reset = response.headers.get('X-Ratelimit-Reset')
            print(f"------------- RATE LIMIT PEXELS get_stock_images:\n")
            print("Rate Limit Information:")
            print(f"Rate Limit: {rate_limit}")
            print(f"Rate Remaining: {rate_remaining}")
            print(f"Rate Reset: {rate_reset}")
            print()
            data = response.json()

            for image in data.get("photos", []):
                if image['width'] >= target_size[0] and image['height'] >= target_size[1]:
                    url = image["src"]["original"]
                    fetched_description = image.get('alt', '').strip()

                    # Check for uniqueness and add if unique
                    if fetched_description not in used_descriptions and url not in used_image_urls:
                        image_list = [{
                            'url': url,
                            'description': fetched_description
                        }]
                        used_descriptions.add(fetched_description)
                        used_image_urls.add(url)

                        media_key = f"image{image_index}"
                        media_details[video_id][paragraph_key][media_key] = image_list
                        image_index += 1  # Increment for next unique image

                        print(f"Added image {image_index-1}/{target_image_count}, moving to next.")
                        break  # Break after adding unique image

        else:
            print(f"Failed to fetch images for model description '{model_desc}', status code: {response.status_code}")

        # Exit the loop if all required images have been added
        if image_index > target_image_count:
            print("Reached target image count or no more unique images, exiting loop.")
            break

    return media_details  # Return the updated media details with images

def get_stock_videos(video_id, part_number, model_descriptions, media_details, paragraph_key):
    global part_lengths, used_video_urls, orientation, asset_size, used_descriptions

    api_key = os.getenv("PEXELS_API_KEY")
    target_video_count = part_lengths[part_number]['num_videos']
    print("------------------- get stock videos ------------------")
    print(f"{paragraph_key} Target Video Count: {target_video_count}")
    target_size = get_target_size(orientation)  # Define target size based on orientation
    video_details = {}  # Dictionary to hold lists of urls and descriptive tags per description

    model_descriptions_cycle = itertools.cycle(model_descriptions)

    video_index = 1  # Start indexing from 1 for user-facing keys

    while video_index <= target_video_count:
        model_desc = next(model_descriptions_cycle)  # Get next description
        encoded_desc = urllib.parse.quote(model_desc)
        api_url = f"https://api.pexels.com/videos/search?query={encoded_desc}&per_page=80&orientation={orientation}&size={asset_size}"
        print(f"Making API Request to: {api_url}")
        response = requests.get(api_url, headers={"Authorization": api_key})

        if response.status_code == 200:
            # Extract and print rate limit information
            rate_limit = response.headers.get('X-Ratelimit-Limit')
            rate_remaining = response.headers.get('X-Ratelimit-Remaining')
            rate_reset = response.headers.get('X-Ratelimit-Reset')
            print(f"------------- RATE LIMIT PEXELS get_stock_video:\n")
            print("Rate Limit Information:")
            print(f"Rate Limit: {rate_limit}")
            print(f"Rate Remaining: {rate_remaining}")
            print(f"Rate Reset: {rate_reset}")
            print()
            
            data = response.json()
            video_list = []  # Initialize an empty list for unique videos in this iteration

            for video in data.get("videos", []):
                for file in video["video_files"]:
                    if file['quality'] == 'hd' and file["width"] == target_size[0] and file["height"] == target_size[1]:
                        url = file["link"]
                        fetched_description = extract_tags_from_url(video['url'])

                        # Check for uniqueness and add if unique
                        if fetched_description not in used_descriptions and url not in used_video_urls:
                            video_list.append({
                                'url': url,
                                'description': fetched_description
                            })
                            used_descriptions.add(fetched_description)
                            used_video_urls.add(url)

                            # Break after adding a unique video to the list
                            break

            # Check if unique video was added and increment video index
            if video_list:
                media_key = f"video{video_index}"
                video_details[media_key] = video_list
                video_index += 1  # Increment for next unique video

                print(f"Added video {video_index-1}/{target_video_count}. Unique video added.")

        else:
            print(f"Failed to fetch videos for model description '{model_desc}', status code: {response.status_code}")

        # Exit the loop if all required videos have been added
        if video_index > target_video_count:
            print("Reached target video count or no more unique videos, exiting loop.")
            break

    # Add the collected video details to media details for the paragraph
    media_details[video_id][paragraph_key].update(video_details)
    return media_details  # Return the updated media details with videos




def get_part_stock_assets(video_id, part_num, descriptions, media_details):
    paragraph_key = f"P{part_num + 1}"  # Assuming part_num is 0-based index
    if paragraph_key not in media_details[video_id]:
        media_details[video_id][paragraph_key] = {}

    # Round robin if needed and fetch stock assets
    image_media_count = part_lengths[part_num]['num_images']
    video_media_count = part_lengths[part_num]['num_videos']
    image_descriptions = list(itertools.islice(itertools.cycle(descriptions), image_media_count))
    video_descriptions = list(itertools.islice(itertools.cycle(descriptions), video_media_count))

    # Directly update media_details with the assets
    get_stock_images(video_id, part_num, image_descriptions, media_details, paragraph_key)
    get_stock_videos(video_id, part_num, video_descriptions, media_details, paragraph_key)
    

def trim_and_save_video(url, file_path, max_length, index, target_size):
    """
    Downloads and saves a video from a given URL without trimming.
    Saves the resized video as (i)_resized.mp4 to keep the original downloaded video files.
    """
    try:
        # Download video
        video_content = requests.get(url).content
        original_file_path = file_path  # Save the original file path
        with open(original_file_path, 'wb') as file:
            file.write(video_content)

        # Load and resize video
        #with VideoFileClip(original_file_path) as video:
        #    resized_video = video.resize(newsize=(1920, 1080))
        #    # Define the new file path for the resized video
        #    resized_file_path = f"{os.path.splitext(file_path)[0]}_{index}_resized.mp4"
        #    resized_video.write_videofile(resized_file_path, codec="libx264", audio_codec="aac")
        #    print(f"Processed and saved resized video to {resized_file_path}")
    except Exception as e:
        print(f"Error processing video from {url}: {e}")
        
def download_stock_media(video_id, media_details):
    # Ensure that video_id exists in media_details
    if video_id not in media_details:
        print(f"Video ID {video_id} not found in media_details")
        return

    target_size = get_target_size(orientation)  # Get the target size based on orientation
    
    # Iterate through each paragraph in the media details for the given video_id
    for paragraph_key, paragraph_media in media_details[video_id].items():
        p_num = paragraph_key.lower()  # Convert paragraph_key to lowercase for path construction

        # Iterate through each media type (image or video) in the paragraph
        for media_key, media_list in paragraph_media.items():
            if media_key.startswith('image') or media_key.startswith('video'):
                media_type = 'img' if 'image' in media_key else 'video'
                extension = "jpg" if media_type == 'img' else "mp4"
                directory = f"videos/{video_id}/{p_num}/{media_type}"

                os.makedirs(directory, exist_ok=True)

                for index, media_item in enumerate(media_list, start=1):
                    if isinstance(media_item, dict) and 'url' in media_item:
                        media_url = media_item['url']
                        filename = f"{media_key}.{extension}"
                        media_path = os.path.join(directory, filename)

                        # Download and process the media
                        try:
                            response = requests.get(media_url, stream=True)
                            if response.status_code == 200:
                                with open(media_path, 'wb') as file:
                                    if media_type == 'img':
                                        file.write(response.content)
                                        # Open, Resize, Crop and Save the image
                                        with Image.open(media_path) as img:
                                            img = resize_image_aspect_ratio(img, target_size)
                                            img = crop_center(img, target_size[0], target_size[1])
                                            img.save(media_path)
                                    else:  # Assuming media_type is 'video'
                                        for chunk in response.iter_content(chunk_size=1024):
                                            if chunk:
                                                file.write(chunk)
                                print(f"Downloaded {media_type} to {media_path}")
                            else:
                                print(f"Error downloading {media_type} from {media_url}: Status Code {response.status_code}")
                        except Exception as e:
                            print(f"Exception occurred while downloading {media_type} from {media_url}: {e}")

def process_image(image_path):
    # This function will handle image resizing and cropping
    try:
        with Image.open(image_path) as img:
            img = resize_image_aspect_ratio(img, get_target_size(orientation))
            img = crop_center(img, *get_target_size(orientation))
            img.save(image_path)
        print(f"Processed and saved image to {image_path}")
    except Exception as e:
        print(f"Exception occurred while processing image {image_path}: {e}")

def generate_video_assets(topic, goal):
    global part_lengths, orientation, asset_size, max_paragraphs, downloaded_urls, max_retries
    
    # Set up video directory and return video ID
    video_id = video_setup(max_paragraphs)
    
    # Initialize sets to keep track of used media URLs and descriptions
    used_image_urls = set()
    used_video_urls = set()
    used_descriptions = set()

    # Initialize an instance of the ScriptCreator class this is a placeholder for future updades.
    #script_creator = ScriptCreator(topic, goal, max_paragraphs)
    
    # Generate the script using the ScriptCreator instance
    #video_script_dict, message = script_creator.create_script()
    video_script_dict, message = gen_video_script(topic, goal, max_paragraphs)

    if message.startswith("Success"):
        
        # Create script files for each paragraph
        if not create_script_files(video_script_dict, video_id):
            clear_video_directory(video_id)
            return None

        # Generate Text-To-Speech (TTS) audio for each paragraph
        if not get_bark_tts_audio(video_id, max_paragraphs):
            clear_video_directory(video_id)
            return None

        # Calculate part lengths after TTS to ensure durations match with audio
        part_lengths = get_part_lengths(video_id, max_paragraphs)
        
        # Initialize the media details dictionary
        media_details = {video_id: {}}
        #print(f"initialize media_details = {media_details}")
        descriptions_gen = []

        # Iterate through each paragraph in the script
        for paragraph_detail in video_script_dict['script_details']['paragraph_details']:
            paragraph_num = int(paragraph_detail['paragraph_number'])
            paragraph_key = f"P{paragraph_num}"  # Construct the paragraph key like 'P1', 'P2', etc.

            # Fetch image and video details for the part
            get_part_stock_assets(video_id, paragraph_num - 1, paragraph_detail['image_descriptions'], media_details)
            media_details[video_id][paragraph_key]['paragraph'] = paragraph_detail['text']
            media_details[video_id][paragraph_key]['img_tags'] = paragraph_detail['image_tags']
            descriptions_gen.append(paragraph_detail['image_descriptions']) # Collecting all descriptions

        ranking_assistant = RankingAssistant(descriptions_gen, media_details)
        ranked_media = ranking_assistant.rank()

        # Update media_details with the ranked media
        media_details = ranked_media
        #print(f"updated media_details = {media_details}")
        # Loop through each paragraph in ranked_results
        for video_id, paragraphs in ranked_media.items():
            for paragraph_key, media_content in paragraphs.items():
                # Loop through each media type and its list in the paragraph
                for media_key, media_list in media_content.items():
                    # Ensure we're working with a list of media items and the key indicates it's a media type
                    if isinstance(media_list, list) and (media_key.startswith('image') or media_key.startswith('video')):
                        # Loop through each media item in the list
                        for media in media_list:
                            # Add URL to the respective set based on media type and description to the used descriptions
                            if media_key.startswith('image'):
                                used_image_urls.add(media['url'])
                            elif media_key.startswith('video'):
                                used_video_urls.add(media['url'])
                            used_descriptions.add(media['description'])

                # Download all media assets
                download_stock_media(video_id, media_details)

                print("✅ Stock assets (images and videos) generated successfully.")
                return video_id

    else:
        print("Failed to generate script:", message)
        return None

# Example usage
if __name__ == "__main__":
    topic = "Empowerment"
    goal = "empower viewers to take control of their lives, make positive choices, and pursue their dreams"
    max_paragraphs = 4  # Example value
    silence_duration = 2
    video_id = generate_video_assets(topic, goal)
    print(f"Generated Video ID: {video_id}")
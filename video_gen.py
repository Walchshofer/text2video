from moviepy.editor import *
import os
from pydub import AudioSegment

# Assuming necessary functions from video_creator are correctly imported
from video_creator import get_part_lengths  # or other necessary imports from video_creator

def update_settings(new_settings):
    global settings
    global min_stock_video_length, min_stock_image_length, max_stock_video_length, max_stock_image_length
    global max_paragraphs, orientation, asset_size, duration_crossfade
    global video_fps, audio_fps, video_width, video_height, video_size, silence_duration, YT_shorts_setting

    settings = new_settings
    
    min_stock_video_length = settings.get('min_stock_video_length', 5)
    min_stock_image_length = settings.get('min_stock_image_length', 3)
    max_stock_video_length = settings.get('max_stock_video_length', 5)
    max_stock_image_length = settings.get('max_stock_image_length', 3)
    max_paragraphs = settings.get('max_paragraphs', 6)
    orientation = settings.get('orientation', "landscape")
    asset_size = settings.get('asset_size', "medium")
    duration_crossfade = settings.get('duration_crossfade', 1)
    video_fps = settings.get('video_fps', 30)
    audio_fps = settings.get('audio_fps', 44100)
    video_width = settings.get('video_width', 1920)
    video_height = settings.get('video_height', 1080)
    video_size = (video_width, video_height)
    silence_duration = settings.get('silence_duration', 2000)
    YT_shorts_setting = settings.get('YT_shorts_setting', False)

def get_image_clip(image_path, duration):
    return ImageClip(image_path).set_duration(duration)

def get_video_clip(video_path, duration):
    clip = VideoFileClip(video_path)
    return clip.subclip(0, min(duration, clip.duration))

def crossfade_transition(clip1, clip2):
    duration = settings.get("duration_crossfade", 1)
    return CompositeVideoClip([clip1, clip2.set_start(clip1.duration - duration).crossfadein(duration)],
                              size=(settings.get("video_width", 1920), settings.get("video_height", 1080)))

def create_video_segments(video_id):
    all_clips = []
    # Assuming get_part_lengths is a previously defined function that provides lengths and durations
    part_lengths = get_part_lengths(video_id, settings["max_paragraphs"])
    print(f"part_lenths = {part_lengths}")
    for i in range(settings["max_paragraphs"]):
        p_num = i + 1  # Paragraph number
        paragraph_path = os.path.join("videos", video_id, f"p{p_num}")  # Path to the paragraph directory
        
        part_data = part_lengths.get(i)  # Retrieve data for this part
        if not part_data:  # If no data, skip this part
            continue

        img_assets = [os.path.join(paragraph_path, "img", f"image{j+1}.jpg") for j in range(part_data["num_images"])]
        video_assets = [os.path.join(paragraph_path, "video", f"video{j+1}.mp4") for j in range(part_data["num_videos"])]

        paragraph_clips = []  # List to store all clips (images and videos) for this paragraph

        # Process image assets
        for j, image_path in enumerate(img_assets):
            if os.path.exists(image_path):  # Check if the image file exists
                img_duration = part_data['img_durations'][j]  # Duration for this image
                segment = get_image_clip(image_path, img_duration)  # Create an image clip
                paragraph_clips.append(segment)  # Append the image clip to the paragraph's clips list

        # Process video assets
        for j, video_path in enumerate(video_assets):
            if os.path.exists(video_path):  # Check if the video file exists
                vid_duration = part_data['vid_durations'][j]  # Duration for this video
                segment = get_video_clip(video_path, vid_duration)  # Create a video clip
                paragraph_clips.append(segment)  # Append the video clip to the paragraph's clips list

        if paragraph_clips:  # If there are clips for this paragraph
            # Create a composite video clip starting with the first clip
            paragraph_video = CompositeVideoClip([paragraph_clips[0]])
            # Add the rest of the clips with crossfade transition
            for next_clip in paragraph_clips[1:]:
                paragraph_video = crossfade_transition(paragraph_video, next_clip)
            all_clips.append(paragraph_video)  # Append the paragraph video to the all clips list

    return all_clips  # Return the list of all video clips (one per paragraph)

def render_video(video_id, video_segments, audios):
    print(f"Video segments: {video_segments}")  # Debug print
    print(f"Audio segments: {audios}")  # Debug print
    video_fps = settings.get("video_fps", 30)
    try:
        video = concatenate_videoclips(video_segments, method="compose")
        audio = concatenate_audioclips(audios)
        print(f"Video duration: {video.duration}, Audio duration: {audio.duration}")  # Debug print

        if video.duration < audio.duration:
            # Calculate the time to start the audio in the middle of the video
            delta = (video.duration - audio.duration) / 2
            silence_start = AudioSegment.silent(duration=int(delta * 1000))  # Convert to milliseconds
            silence_end = AudioSegment.silent(duration=int(delta * 1000))
            
            # Concatenate the audio with silence at the beginning and end
            audio = silence_start + audio + silence_end

            # Make sure the audio duration matches the video duration
            audio = audio.set_duration(video.duration)

        video = video.set_audio(audio)

        final_video_path = os.path.join("videos", video_id, "final_video.mp4")
        video.write_videofile(final_video_path, fps=video_fps)
        return final_video_path
    except Exception as e:
        print(f"Error occurred while rendering video: {e}")  # Debug print


def audio_gen(audio_paths):
    audios = []
    for audio_path in audio_paths:
        audio_clip = AudioSegment.from_file(audio_path, format="wav")
        silence = AudioSegment.silent(duration=settings.get("silence_duration", 2000))
        combined_audio = audio_clip + silence
        combined_audio.export(audio_path, format="wav")
        audios.append(AudioFileClip(audio_path))
    return audios

def video_gen(video_id):
    # Ensure settings are loaded or set before this function
    print(f"Generating video for Video ID: {video_id}")  # Debug print
    audio_paths = []
    for i in range(settings["max_paragraphs"]):
        p_num = i + 1
        audio_path = os.path.join("videos", video_id, f"p{p_num}", "video", "audio.wav")
        print(f"Audio path for part {p_num}: {audio_path}")  # Debug print
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")  # Debug print
            return None
        audio_paths.append(audio_path)

    audios = audio_gen(audio_paths)
    video_segments = create_video_segments(video_id)
    if not video_segments:  # Check if video segments are empty
        print("No video segments were created. Check the input data and paths.")  # Debug print
    final_video_path = render_video(video_id, video_segments, audios)
    return final_video_path

if __name__ == "__main__":
    video_id = input("Enter the video id: ")
    # Assuming settings are provided from somewhere, typically frontend
    final_video_path = video_gen(video_id)
    print(f"Final video path: {final_video_path}")
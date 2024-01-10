from moviepy.editor import *
import os
import soundfile as sf
from pydub import AudioSegment
from video_creator import (min_stock_video_length, min_stock_image_length,
                            max_stock_video_length, max_stock_image_length,
                            max_paragraphs, orientation, asset_size,
                            get_part_lengths, duration_crossfade,
                            video_fps, audio_fps, video_width,
                            video_height, video_size, silence_duration)

def get_image_clip(image_path, duration):
    return ImageClip(image_path).set_duration(duration)

def get_video_clip(video_path, duration):
    clip = VideoFileClip(video_path)
    return clip.subclip(0, min(duration, clip.duration))

def get_audio_length(audio_path):
    with sf.SoundFile(audio_path) as f:
        frames = f.frames
        rate = f.samplerate
        return frames / float(rate)

def crossfade_transition(clip1, clip2, duration=duration_crossfade):
    return CompositeVideoClip([clip1, clip2.set_start(clip1.duration-duration).crossfadein(duration)], size=clip1.size)

def create_video_segments(video_id, max_paragraphs):
    all_clips = []
    part_lengths = get_part_lengths(video_id, max_paragraphs)  # Fetch part lengths

    for i in range(max_paragraphs):  # Looping over paragraphs (0-based indexing for internal logic)
        p_num = i + 1  # Adjusting to 1-based indexing for user-facing elements
        paragraph_path = os.path.join("videos", video_id, f"p{p_num}")
        part_data = part_lengths.get(i)  # Access the part data using 0-based indexing
        
        if not part_data:  # Skip if no data for this part
            continue

        img_assets = [os.path.join(paragraph_path, "img", f"{idx}.jpg") for idx in range(part_data["num_images"])]
        video_assets = [os.path.join(paragraph_path, "video", f"{idx}.mp4") for idx in range(part_data["num_videos"])]

        paragraph_clips = []

        # Create clips for images using their specific durations
        for j, image_path in enumerate(img_assets):
            if os.path.exists(image_path):  # Check if image file exists
                img_duration = part_data['img_durations'][j]
                segment = get_image_clip(image_path, img_duration)
                paragraph_clips.append(segment)

        # Create clips for videos using their specific durations
        for j, video_path in enumerate(video_assets):
            if os.path.exists(video_path):  # Check if video file exists
                vid_duration = part_data['vid_durations'][j]
                segment = get_video_clip(video_path, vid_duration)
                paragraph_clips.append(segment)

        # Applying crossfade_transition between clips
        if paragraph_clips:
            paragraph_video = CompositeVideoClip([paragraph_clips[0]])  # Initialize with first clip
            for next_clip in paragraph_clips[1:]:
                paragraph_video = crossfade_transition(paragraph_video, next_clip, duration=duration_crossfade)
            all_clips.append(paragraph_video)

    return all_clips

def render_video(video_id, video_segments, audios):
    video = concatenate_videoclips(video_segments, method="compose")
    audio = concatenate_audioclips(audios)

    if video.duration < audio.duration:
        video = video.fx(vfx.loop, duration=audio.duration)
    video = video.set_audio(audio)
    video = video.resize(newsize=video_size)
    video.write_videofile(os.path.join("videos", video_id, "final_video.mp4"), fps=video_fps)
    video.close()

def audio_gen(audio_paths):
    audios = []
    for audio_path in audio_paths:
        audio_clip = AudioSegment.from_file(audio_path, format="wav")
        silence = AudioSegment.silent(duration=silence_duration)
        combined_audio = audio_clip + silence
        combined_audio.export(audio_path, format="wav")
        audios.append(AudioFileClip(audio_path))
    return audios

def video_gen(video_id):
    audio_paths = []
    for i in range(max_paragraphs):  # 0-based indexing for internal logic
        p_num = i + 1  # 1-based indexing for user-facing elements
        audio_path = os.path.join("videos", video_id, f"p{p_num}", "video", "audio.wav")
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return None
        audio_paths.append(audio_path)

    audios = audio_gen(audio_paths)
    video_segments = create_video_segments(video_id, max_paragraphs)
    render_video(video_id, video_segments, audios)
    print("Video generated successfully!")

    return os.path.join("videos", video_id, "final_video.mp4")

if __name__ == "__main__":
    video_id = input("Enter the video id: ")
    video_gen(video_id)

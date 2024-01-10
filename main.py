import video_creator
from video_gen import video_gen
import os

def main():
    topic = "Sustainable Living: Providing tips, tricks, and insights into living a more sustainable life by reducing waste, conserving resources, and changing consumption habits."
    video_id = video_creator.generate_video_assets(topic)
    if video_id:
        print(f"Video assets generated successfully for video ID: {video_id}")
        # Ask user if they want to enable YouTube shorts format
        YT_shorts = input("Do you want to crop and center for YouTube shorts? (yes/no): ").strip().lower() == 'yes'
        # Generate video with or without YouTube shorts setting
        video_path = video_gen(video_id, YT_shorts_setting=YT_shorts)
        if os.path.exists(video_path):
            print(f"Video generated successfully. Path: {video_path}")
            # Add logic to play the video if required
        else:
            print("Failed to generate the video.")
    else:
        print("Failed to generate video assets.")

if __name__ == "__main__":
    main()

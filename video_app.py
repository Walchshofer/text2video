import streamlit as st
import yaml
import os
import pandas as pd
from video_creator import generate_video_assets, update_settings as update_settings_video_creator
from video_gen import video_gen, update_settings as update_settings_video_gen
import streamlit as st
import numpy as np
import nltk
from bark.generation import generate_text_semantic, preload_models
from bark.api import semantic_to_waveform
from bark import SAMPLE_RATE

# Specify the path to settings.yaml and speakers.yaml
SETTINGS_FILE_PATH = '/home/pwalch/projects/Files/YouTubeVideoTool/text2video/settings.yaml'
SPEAKERS_FILE_PATH = '/home/pwalch/projects/Files/YouTubeVideoTool/text2video/SpeakerSettings.csv'


# Function to load settings from YAML
def load_settings():
    with open(SETTINGS_FILE_PATH, 'r') as f:
        return yaml.safe_load(f)

# Function to save settings to YAML
def save_settings(settings):
    return pd.read_csv(SPEAKERS_FILE_PATH)

# Function to load speakers from YAML
def load_speakers():
    return pd.read_csv(SPEAKERS_FILE_PATH)

# Load current settings and speakers
settings = load_settings()
speakers = load_speakers()

# Initialize Bark Models
preload_models()

# Streamlit UI setup
st.sidebar.title('🛠️ Video Creator Settings')

# Handle orientation and video size settings
def set_video_dimensions(orientation):
    if orientation == 'vertical':
        return 1080, 1920
    elif orientation == 'square':
        return 1080, 1080
    else:  # default to landscape
        return 1920, 1080

# Streamlit UI for settings
orientation = st.sidebar.selectbox('Orientation', ['landscape', 'vertical', 'square'], index=0)
settings["video_width"], settings["video_height"] = set_video_dimensions(orientation)
settings["orientation"] = orientation
settings["asset_size"] = st.sidebar.selectbox('Asset Size', ['small', 'medium', 'large'], index=1)
settings["duration_crossfade"] = st.sidebar.slider('Crossfade Duration', 0, 5, settings.get("duration_crossfade", 1))
settings["video_fps"] = st.sidebar.slider('Video FPS', 15, 60, settings.get("video_fps", 30))
settings["audio_fps"] = st.sidebar.slider('Audio FPS', 22050, 48000, settings.get("audio_fps", 44100))
settings["silence_duration"] = st.sidebar.slider('Silence Duration (s)', 1, 5, settings.get("silence_duration", 2))

# BARK Audio Settings UI
st.sidebar.title('🎙️ BARK Audio Settings')
# Speaker selection based on the CSV content
language_filter = st.sidebar.selectbox('Language', speakers['Language'].unique())
gender_filter = st.sidebar.selectbox('Gender', speakers['Gender'].unique())

filtered_speakers = speakers[(speakers['Language'] == language_filter) & (speakers['Gender'] == gender_filter)]
selected_speaker_index = st.sidebar.selectbox('Select Speaker', range(len(filtered_speakers)), format_func=lambda x: filtered_speakers.iloc[x]['Speaker'])
selected_speaker = filtered_speakers.iloc[selected_speaker_index]

# Displaying audio samples for the selected speaker
st.sidebar.audio(selected_speaker['Prompt Audio Link'], format="audio/mp3")
st.sidebar.audio(selected_speaker['Continuation Audio Link'], format="audio/mp3")

# Saving selected speaker to settings
settings["bark_speaker"] = selected_speaker['Prompt Name']
settings["bark_gen_temp"] = st.sidebar.slider('GEN_TEMP', 0.0, 1.0, value=0.6)
settings["bark_min_eos_p"] = st.sidebar.slider('MIN_EOS_P', 0.0, 1.0, value=0.05)

# BARK Model Preloading Settings
st.sidebar.subheader('Model Preloading Settings')
settings["bark_text_use_gpu"] = st.sidebar.checkbox('Use GPU for Text Model', value=True)
settings["bark_text_use_small"] = st.sidebar.checkbox('Use Small Text Model', value=False)
settings["bark_coarse_use_gpu"] = st.sidebar.checkbox('Use GPU for Coarse Model', value=True)
settings["bark_coarse_use_small"] = st.sidebar.checkbox('Use Small Coarse Model', value=False)
settings["bark_fine_use_gpu"] = st.sidebar.checkbox('Use GPU for Fine Model', value=True)
settings["bark_fine_use_small"] = st.sidebar.checkbox('Use Small Fine Model', value=False)
settings["bark_codec_use_gpu"] = st.sidebar.checkbox('Use GPU for Codec Model', value=True)

# Save Settings Button
if st.sidebar.button('Save Settings'):
    save_settings(settings)
    st.sidebar.success('Settings updated!')
# Main video generator interface
st.title('🎬 General Video Generator')
topic = st.text_area('Enter a topic for the video:', 'Enter your video topic here...')
goal = st.text_area('Your goal is to', 'Enter your goal here... ')
max_paragraphs = st.slider('Maximum Paragraphs', 2, 10, settings.get("max_paragraphs", 6))
settings["max_paragraphs"] = max_paragraphs

# Integration with video generation backend (assumed to be implemented)
if st.button('Generate Video'):
    with st.spinner('🔄 Generating video...'):
        # Ensure settings are correctly updated in video_creator script
        update_settings_video_creator(settings)
        # Here you will call your generate_video_assets and video_gen methods
        video_id = generate_video_assets(topic, goal)
        if video_id:
            update_settings_video_gen(settings)
            st.success(f"🎉 Video assets generated successfully for video ID: {video_id}")
            final_video_path = video_gen(video_id)
            if final_video_path and os.path.exists(final_video_path):
                st.success(f"🌟 Video generated successfully. Path: {final_video_path}")
                st.video(final_video_path)
            else:
                st.error("❌ Failed to generate the video.")
        else:
            st.error("❌ Failed to generate video assets.")
        st.json(settings)  # Just to demonstrate what's being passed

# Ensure you have implemented or integrated generate_video_assets and video_gen functions from your backend.

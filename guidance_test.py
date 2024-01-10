import os
import guidance
import json

# Function to create the guidance prompt based on max_paragraphs
def create_video_script_guidance_prompt(topic, max_paragraphs):
    prompt_intro = f'''
    You are a video script generation machine specialized in creating scripts 
    for voice-over actors and suggesting images for video production. Given 
    the topic "{topic}", your task is to create a script with multiple paragraphs. 
    Each paragraph will be the text for a voice-over actor. After each paragraph, 
    generate a list of 10 images that closely relate to the 
    content of the paragraph and enhance the voice-actor's narration. 

    Additionally, if the user prompt mentions specific video techniques like Aerial, HD, Cinematographic, etc., 
    these should be reflected in the images. For instance, if the topic includes "Cinematographic," 
    ensure tags like "cinematic" or "wide-angle shot" are considered. 

    The script must be in JSON format, with paragraphs as text and descriptions of images as strings in an array. 
    Special characters are not allowed. Here's the format of what I'm looking for:

    {{
        "topic": "{topic}",
        ...
    }}
    '''

    prompt_intro_part = '''
        "P1": "{{gen 'intro_text' topic=topic temperature=0.7}}",
        "P1_images": [
            {{#gen_each 'image' from='intro_text' related_to_topic='{topic}' num_iterations=10 join=','}}{{/gen_each}}
        ],
    '''

    prompt_main_paragraphs = ''.join([
        f'''
            "P{i}": "{{{{gen 'paragraph_text{i}' topic=topic temperature=0.7}}}}",
            "P{i}_images": [
                {{{{#gen_each 'image' from='paragraph_text{i}' related_to_topic='{topic}' num_iterations=10 join=','}}}}
            ],
        ''' for i in range(2, max_paragraphs)
    ])

    prompt_outro = f'''
        "P{max_paragraphs}": "{{{{gen 'outro_text' topic=topic temperature=0.7}}}}",
        "P{max_paragraphs}_imgages": [
            {{{{#gen_each 'image' from='outro_text' related_to_topic='{topic}' num_iterations=10 join=','}}}}
        ]
    }}
    '''
    return prompt_intro + prompt_intro_part + prompt_main_paragraphs + prompt_outro


# Initialize the LiteLLMCompletion model
mistral_gd_model = guidance.models.LiteLLMCompletion(
    model="ollama/mistral", 
    api_base="http://127.0.0.1:8000",
    api_key="NULL"
)

# Function to generate a video script
def generate_video_script(topic, max_paragraphs):
    VIDEO_SCRIPT_GUIDANCE_PROMPT = create_video_script_guidance_prompt(topic, max_paragraphs)
    full_prompt = VIDEO_SCRIPT_GUIDANCE_PROMPT

    response_generator = mistral_gd_model._generator(full_prompt.encode('utf-8'), temperature=1.19, top_k=0.18)
    response = ""
    try:
        for part in response_generator:
            response += part.decode('utf-8')
    except Exception as e:
        print("Error during response generation:", e)

    return response

# Example usage
topic = "The best Video Aerial Nature Footage filemed by drones"
max_paragraphs = 6
video_script = generate_video_script(topic, max_paragraphs)
print(video_script)

import re
from guidance import gen, models, select, system, user, assistant, newline
import guidance

# Initialize the LiteLLMChat model
lm = models.LiteLLMChat(
    model="ollama/dolphin-mistral:v2.6",
    api_base="http://127.0.0.1:8000",
    api_key="NULL",
    temperature=1.0
)
lm.echo = False
lm.caching = False

topic = "Green Energy"
goal = "to educate viewers to take control of their lives, switch to green power and make positive choice for the planet8, and pursue their dreams"
max_paragraphs = 3  # Example value
paragraph_type = 'intro'
text_history = ""



@guidance
def video_script(lm, topic: str, goal: str, paragraph_type: str, text_history: str):
    # Some general instruction to the model
    with system():
        lm += "You are a video script creator. You do not indroduce yourself. Your sole purpose is to create voice narrations"

    with user():
        lm += f"""I need a voice narration for the following topic:
        {topic}
        The video has the goal to {goal}
        
        Generate a clear, engaging narration paragraph for a video with a word count between 80 and 120 words, that fits the context of the video and the specific section being addressed: {paragraph_type}. For the intro paragraph, there is no prior text history. For body and outro paragraphs, consider the context and previous content: {text_history}. Ensure the paragraph welcomes the viewer and introduces or concludes the topic clearly, or delves deeper into the subject for body sections, setting the appropriate tone for the content that will follow in the video.

        Few-shot examples: 

        1. paragraph_type: intro
        text_history: ""
        Result: "Welcome to our journey through the artistic revolution of the Impressionist era. As we unveil each masterpiece, you'll discover the unique brush strokes, vivid colors, and emotional depth that define this beloved period. Prepare to immerse yourself in the world of Monet, Degas, and their contemporaries, as we celebrate the enduring legacy of Impressionist art."

        2. paragraph_type: body
        text_history: "Previously, we introduced the concept of renewable energy."
        Result: "Now, let's delve deeper into the heart of the Impressionist movement. We'll examine the pivotal moments and key figures that propelled these artists to fame. Discover how their innovative techniques and bold subject matter broke with tradition and opened up new avenues for artistic expression. Join us as we continue our exploration of this captivating period in art history."

        3. paragraph_type: outro
        text_history: "Throughout this video, we've witnessed the evolution and impact of Impressionist art."
        Result: "As we conclude our journey, let's reflect on the profound influence of the Impressionist era. The movement not only revolutionized art but also left an indelible mark on the cultural landscape. Thank you for joining us in appreciating these masterpieces. Continue to explore and be inspired by the beauty and innovation that Impressionism has brought to the world of art."

        Now I generate a text with 80 to 120 words for a paragraph_type = '{paragraph_type}'
        """

    with assistant():

        lm += gen(name='text', temperature=1.0, stop=newline)
        print(lm['text'])
    with user():
        lm += f"""Now please create a list with very short captivating tiles for images that align with the voice narration:\n
        Please provide one brief description (approximatly 5 words) at a time.\n
        Here is an example Voice Nararation and its correspondending Image_descriptions list:\n
        EXAMPLE 1:\n
        Voice Narration:\n
        "Unlock the power within you. Start your day with a positive affirmation and feel the energy surge through you. Every challenge is an opportunity to grow. Embrace your struggles and turn them into your strengths."\n
        
        Image_descriptions\n 
        Description 1: "Sunrise over serene lake",\n
        Description 2: "Person on mountaintop",\n
        Description 3: "Close-up smiling face",\n
        Description 4: "Notebook with positive affirmation",\n
        Description 5: "Tree silhouetted against sunrise",\n
        Description 6: "Runner pushing through fatigue",\n
        Description 7: "Seedling in sunlight",\n
        Description 8: "Stepping stones leading upwards",\n
        Description 9: "Person solving puzzle",\n
        Description 10: "Hands in applause" \n\n
        
        EXAMPLE 2:\n
        Voice Narration:\n
        "Embark on a culinary adventure. Let your taste buds travel the world as you savor the flavors of diverse cuisines. From spicy Thai curries to savory Italian pasta, each dish tells a story of culture and tradition, inviting you to a global feast of flavors."\n\n

        Image Descriptions:\n
        Description 1: "Steaming Bowl of Tom Yum Soup",\n
        Description 2: "Freshly Baked Margherita Pizza",\n
        Description 3: "Colorful Sushi Platter",\n
        Description 4: "Spices and Herbs at an Indian Market",\n
        Description 5: "Traditional Mexican Tacos",\n
        Description 6: "French Baguette with Cheese and Wine",\n
        Description 7: "Greek Salad with Feta Cheese",\n
        Description 8: "Chinese Dumplings on a Bamboo Steamer",\n
        Description 9: "Brazilian BBQ Skewers on Grill",\n
        Description 10: "Mouthwatering Chocolate Fondue Dessert"\n
        
       EXAMPLE3:\n
        Voice Narration:\n
        "Discover the latest tech gadgets that enhance your daily life. From smartwatches that keep you connected to fitness trackers that monitor your health, innovation is at your fingertips. Explore these cutting-edge devices and elevate your digital experience."\n

        Image Descriptions:
        Description 1: "Sleek Smartphone with High-Resolution Display",\n
        Description 2: "Smartwatch Showing Weather and Notifications",\n
        Description 3: "Wireless Earbuds in Charging Case",\n
        Description 4: "VR Headset for Immersive Gaming",\n
        Description 5: "Smart Home Hub Controlling Lights and Appliances",\n
        Description 6: "Laptop with Ultra-Fast Processor",\n
        Description 7: "Fitness Tracker Monitoring Heart Rate",\n
        Description 8: "High-Quality Noise-Canceling Headphones",\n
        Description 9: "Compact Drone for Aerial Photography",\n
        Description 10: "Gaming Console with Stunning Graphics"\n

        Now lets create another image descriptions list:\n
        Voice Narration:\n
        
        Image_descriptions:
        """
        
        lm += f"""Great! Now please find YOUR OWN short image descriptions (5 words) for 10 images,\n 
        that align with the voice narration without using any special characters or punctuation:\n\n
        Voicover Narration :\n
        "{lm['text']}"\n
        """

    with assistant():
        lm += gen(name='images', temperature=1.0, list_append=True, max_tokens=500)

    return lm

script = lm + video_script(topic,goal,paragraph_type,text_history)
voiceover_text =script['text']
print(f"\n\n<beginn voicover string>")
print(f"voiceover_text = {type(voiceover_text)}")
print(f"voiceover_text = {voiceover_text}")
print(f"<end voicover string>\n\n")

image_text = script['images']
print(f"\n\n<beginn image_text list>")
print(f"image_text = {type(image_text)}")
idx = 0
for element in image_text:
    print(f"image_text list element {str(idx)}: {element}")
print(f"<end voicover string>\n\n")
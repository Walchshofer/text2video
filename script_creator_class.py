import re
from guidance import gen, models, select, system, user, assistant, newline
import guidance


class ScriptCreator:
    def __init__(self, topic, goal, max_paragraphs):
        # Initialize parameters
        self.topic = topic
        self.goal = goal
        self.max_paragraphs = max_paragraphs
        self.text_history = ""

        # Initialize the LiteLLMChat model
        self.lm = models.LiteLLMChat(
            model="ollama/dolphin-mistral:v2.6",
            api_base="http://127.0.0.1:8000",
            api_key="NULL",  # Update with actual key
            temperature=1.0
        )
        self.lm.echo = False
        self.lm.caching = False

    def video_script(self, paragraph_type, i=None):
          
        @guidance(dedent=False)
        def script(lm, topic: str, goal: str, paragraph_type: str, text_history: str, i: int = None, max_paragraphs: int = None):
            with system():
                lm += "You are a video script creator. You do not introduce yourself. Your sole purpose is to create voice narrations."
                if paragraph_type == 'intro':
                    with user():
                        lm += self.construct_intro_prompt(paragraph_type)
                elif paragraph_type == 'body':
                    with user():
                        lm += self.construct_body_prompt(i,paragraph_type)
                elif paragraph_type == 'outro':
                    with user():
                        lm += self.construct_outro_prompt(paragraph_type)

            with assistant():
                lm += gen(name='text', temperature=1.0, stop=newline)
                voiceover_text = lm['text']

            with user():
                lm += self.construct_image_description_prompt(voiceover_text)

            with assistant():
                lm += gen(name='images', temperature=1.0, list_append=True, max_tokens=500)

            return lm
        
        lm = self.lm
        topic = self.topic
        text_history = self.text_history
        max_paragraphs = self.max_paragraphs
        script_result = lm + script(topic, goal, paragraph_type, text_history, i, max_paragraphs)
        voiceover_text = script_result['text']
        
        text_history += voiceover_text + "\n\n"  # Update text history with new text

        # Extract image descriptions
        img_list = script_result['images'][0] if script_result['images'] else ""
        parsed_descs = re.findall(r'\d+[.:] ([^\n]+)', img_list)

        return {"text": voiceover_text, "img_description": parsed_descs}

    def construct_intro_prompt(self,paragraph_type):
        return (
            f"I need a voice narration for the following topic:\n"
            f"{self.topic}\n"
            f"The video has the goal to {self.goal}\n\n"
            
            f"Generate a clear, engaging narration paragraph for a video with a word count between 80 and 120 words, "
            f"Ensure the paragraph welcomes the viewer and introduces the topic clearly, "
            f"setting the appropriate tone for the content that will follow in the video.\n\n"
            
            f"Few-shot examples:\n\n"

            f"1. paragraph_type: intro\n"
            f"text_history: \"\"\n"
            f"Result: \"Welcome to our journey through the artistic revolution of the Impressionist era. As we unveil each masterpiece, "
            f"you'll discover the unique brush strokes, vivid colors, and emotional depth that define this beloved period. Prepare to immerse yourself in the world of Monet, Degas, "
            f"and their contemporaries, as we celebrate the enduring legacy of Impressionist art.\"\n\n"

            f"2. paragraph_type: body\n"
            f"text_history: \"Previously, we introduced the concept of renewable energy.\"\n"
            f"Result: \"Now, let's delve deeper into the heart of the Impressionist movement. We'll examine the pivotal moments and key figures that propelled these artists to fame. "
            f"Discover how their innovative techniques and bold subject matter broke with tradition and opened up new avenues for artistic expression. "
            f"Join us as we continue our exploration of this captivating period in art history.\"\n\n"

            f"3. paragraph_type: outro\n"
            f"text_history: \"Throughout this video, we've witnessed the evolution and impact of Impressionist art.\"\n"
            f"Result: \"As we conclude our journey, let's reflect on the profound influence of the Impressionist era. The movement not only revolutionized art but also left an indelible mark on the cultural landscape. "
            f"Thank you for joining us in appreciating these masterpieces. Continue to explore and be inspired by the beauty and innovation that Impressionism has brought to the world of art.\"\n\n"

            f"Now I generate a text with 80 to 120 words for a paragraph_type = '{paragraph_type}'\n"
        )

    def construct_body_prompt(self, i, paragraph_type):
        return (
            f"Considering the context and previous content, please continue the narration for the body of the video. "
            f"This is paragraph {i + 1} out of {self.max_paragraphs}. Expand upon the existing text with an additional "
            f"paragraph of 80 to 120 words that further develops the topic '{self.topic}' with the goal of '{self.goal}' in mind.\n"
            f"Previous text for context: {self.text_history}\n"
            
            f"Now I generate a text with 80 to 120 words for a paragraph_type = '{paragraph_type}'\n"
        )

    def construct_outro_prompt(self, paragraph_type):
        return (
            f"Now, conclude the video with an engaging outro paragraph. "
            f"Please briefly summarize the main content provided in the following text history, reflect on the topic '{self.topic}', and reinforce the video's goal of '{self.goal}'. "
            f"Keep the word count between 80 and 120 words. Express gratitude to the viewer for watching and kindly invite them to subscribe for more content.\n\n"
            f"Text history for context: \"{self.text_history}\"\n\n"
            f"Ensure your summary is concise, touching upon key points and providing a meaningful conclusion to the topic. "
            f"Always end with a warm thank you to the viewers and an invitation to subscribe.\n"
                    
            f"Now I generate a text with 80 to 120 words for a paragraph_type = '{paragraph_type}'\n"
        )

    def construct_image_description_prompt(self, voiceover_text):
        return (
            f"Now please create a list with very short captivating titles for images that align with the voice narration:\n"
            f"Please provide one brief description (approximately 5 words) at a time.\n"
            f"Here is an example Voice Narration and its corresponding Image_descriptions list:\n"
            f"EXAMPLE 1:\n"
            f"Voice Narration:\n"
            f"\"Unlock the power within you. Start your day with a positive affirmation and feel the energy surge through you. Every challenge is an opportunity to grow. Embrace your struggles and turn them into your strengths.\"\n\n"
            
            f"Image_descriptions\n"
            f"Description 1: \"Sunrise over serene lake\",\n"
            f"Description 2: \"Person on mountaintop\",\n"
            f"Description 3: \"Close-up smiling face\",\n"
            f"Description 4: \"Notebook with positive affirmation\",\n"
            f"Description 5: \"Tree silhouetted against sunrise\",\n"
            f"Description 6: \"Runner pushing through fatigue\",\n"
            f"Description 7: \"Seedling in sunlight\",\n"
            f"Description 8: \"Stepping stones leading upwards\",\n"
            f"Description 9: \"Person solving puzzle\",\n"
            f"Description 10: \"Hands in applause\"\n\n"
            
            f"EXAMPLE 2:\n"
            f"Voice Narration:\n"
            f"\"Embark on a culinary adventure. Let your taste buds travel the world as you savor the flavors of diverse cuisines. From spicy Thai curries to savory Italian pasta, each dish tells a story of culture and tradition, inviting you to a global feast of flavors.\"\n\n"

            f"Image Descriptions:\n"
            f"Description 1: \"Steaming Bowl of Tom Yum Soup\",\n"
            f"Description 2: \"Freshly Baked Margherita Pizza\",\n"
            f"Description 3: \"Colorful Sushi Platter\",\n"
            f"Description 4: \"Spices and Herbs at an Indian Market\",\n"
            f"Description 5: \"Traditional Mexican Tacos\",\n"
            f"Description 6: \"French Baguette with Cheese and Wine\",\n"
            f"Description 7: \"Greek Salad with Feta Cheese\",\n"
            f"Description 8: \"Chinese Dumplings on a Bamboo Steamer\",\n"
            f"Description 9: \"Brazilian BBQ Skewers on Grill\",\n"
            f"Description 10: \"Mouthwatering Chocolate Fondue Dessert\"\n\n"
            
            f"EXAMPLE3:\n"
            f"Voice Narration:\n"
            f"\"Discover the latest tech gadgets that enhance your daily life. From smartwatches that keep you connected to fitness trackers that monitor your health, innovation is at your fingertips. Explore these cutting-edge devices and elevate your digital experience.\"\n\n"

            f"Image Descriptions:\n"
            f"Description 1: \"Sleek Smartphone with High-Resolution Display\",\n"
            f"Description 2: \"Smartwatch Showing Weather and Notifications\",\n"
            f"Description 3: \"Wireless Earbuds in Charging Case\",\n"
            f"Description 4: \"VR Headset for Immersive Gaming\",\n"
            f"Description 5: \"Smart Home Hub Controlling Lights and Appliances\",\n"
            f"Description 6: \"Laptop with Ultra-Fast Processor\",\n"
            f"Description 7: \"Fitness Tracker Monitoring Heart Rate\",\n"
            f"Description 8: \"High-Quality Noise-Canceling Headphones\",\n"
            f"Description 9: \"Compact Drone for Aerial Photography\",\n"
            f"Description 10: \"Gaming Console with Stunning Graphics\"\n\n"

            f"Great! Now please find YOUR OWN short image descriptions (5 words) for 10 images,\n"
            f"that align with the voice narration without using any special characters or punctuation:\n\n"
            f"Voiceover Narration :\n"
            f"\"{voiceover_text}\"\n"
        )

    def generate_script(self):
        # Loop to generate each paragraph and its image descriptions
        results = {"text": [], "img_description": []}
        for i in range(self.max_paragraphs):
            paragraph_type = 'intro' if i == 0 else 'outro' if i == self.max_paragraphs - 1 else 'body'
            script_output = self.video_script(paragraph_type, i)
            results["text"].append(script_output["text"])
            results["img_description"].append(script_output["img_description"])

        return results


# This is how you can use the ScriptCreator class
if __name__ == "__main__":
    topic = "The Joy of Unexpected Encounters"
    goal = "encourage viewers to embrace spontaneity and appreciate the unexpected encounters that enrich their lives."
    max_paragraphs = 5

    script_creator = ScriptCreator(topic, goal, max_paragraphs)
    script_results = script_creator.generate_script()

    # Print the results
    print(f"\n\n<begin voiceover string>")
    for i, (text, img_desc) in enumerate(zip(script_results["text"], script_results["img_description"])):
        print(f"Paragraph {i + 1} Voiceover Text: {text}")
        print("Image Descriptions: ", img_desc)
    print(f"<end voiceover string>\n\n")

import itertools
import json
import re
from tqdm import tqdm
import guidance
from guidance import gen, regex, newline, select

class RankingAssistant:
    def __init__(self, descriptions_gen, media_details):
        self.descriptions_cycle = itertools.cycle(descriptions_gen)  # Make an iterator
        self.media_details = media_details

        # Initialize the LiteLLMCompletion model with actual model details
        self.notus = guidance.models.LiteLLMCompletion(
            model="ollama/llama2-uncensored",
            api_base="http://127.0.0.1:8000",
            api_key="NULL",  # Replace with your actual API key
            temperature=1.0
        )
        self.notus.echo = False  # don't draw to notebook
       
    def create_ranking_prompt(self, paragraph, description_gen, media_list):
        #print("---------------- create ranking prompt ----------------------")
        lm = self.notus
        #print("Starting create_ranking_prompt")  # Confirm method is called
        #print(f"descriptions_gen = {description_gen}")
        # Initialize variables for formatted descriptions, options, and selection dictionary
        formatted_media_descriptions = ""
        options = []  # list to hold options for the model to select from
        selection_dict = {}  # dictionary mapping indices to media information

        # Create a cycle iterator for descriptions
        descriptions_cycle = itertools.cycle(description_gen)
        
        # Build formatted descriptions, options, and selection dictionary in a single loop
        for idx, media in enumerate(media_list):
            p_num = idx + 1  # 1-based indexing for user-friendly option numbers
            formatted_media_descriptions += f"{p_num}: {media['description']}\n"
            options.append(str(p_num))  # add index to options list
            selection_dict[str(p_num)] = {"url": media['url'], "description": media['description']}  # add media info to selection_dict

        # Debug print statement
        #print("Debugging create_ranking_prompt:")
        #print("Paragraph:", paragraph)
        #print("Formatted Media Descriptions:\n", formatted_media_descriptions)
        #print("Options:", options)
        
        # Get the next description from the cycle for alignment_bot
        next_description = next(descriptions_cycle)
        
        # Define the bots to use in the guidance language model
        @guidance
        def similarity_bot(lm, description, media_details):
            lm += f'''\
            Rank Image Similarity on a scale from 1 - 9,\n
            in terms of emotion, people, scenery, setting and look/feel but some imprecision.\n
            Here are the image descriptions:
            '''            
            for key in media_details.keys():
                # Check if the key starts with 'image' or 'video'
                if key.startswith('image') or key.startswith('video'):
                    for media in media_details[key]:                     
                        lm += f'''Target Image: "{description}"\n'''
                        lm += f'''Image to Rank: "{media['description']}"\n'''
                        lm += f'''{gen(stop=newline, name="rank", temperature=1.0, regex="[1-9]")}"\n'''
                        similarity_rank = str(lm['rank'])
                        media['similarity_rank'] = similarity_rank  # Add rank to the media item
                        media['target_desc'] = f'''{description}'''
            return lm
        
        
        @guidance
        def alignment_bot(lm, paragraph, formatted_media_descriptions, options, next_description):
            # Include the prompt for the model with the enumerated image descriptions
            lm += f'''
            As the director, my responsibility is to carefully select the top image for the storyboard, ensuring it aligns perfectly with the voiceover in terms of setting, feel, look, and emotional resonance.

            I understand that the co-director has suggested "{next_description}" for the scene.\n
            
            My task is to evaluate the image descriptions provided and identify the one that best complements the narrative
            and emotional continuity of the scene as described in the Voiceover text and the co-director's suggestion.

            When choosing the image, I must consider its ability to enhance the mood of the story and its seamless integration
            within the overall visual sequence. Precision is crucial in making this decision.

            Image List:
            {formatted_media_descriptions}

            Voiceover text: "{paragraph}"
            '''
            # Ask the model to select the best option
            lm += f'''After careful consideration, I believe that image description number {{{{select({options}, name="selected_number")}}}} that best aligns with the voiceover text and the co-director's suggestion:\n'''
            lm += select(options, name="selected_number")
            return lm
        

        # Call alignment_bot with the generated options
        alignment_result = lm + alignment_bot(paragraph, formatted_media_descriptions, options, next_description)
        #print(f"alignment_result = {str(alignment_result)}")
        
        # Retrieve the selected number and corresponding media
        selected_number = str(alignment_result['selected_number'])
        print(f"------------------ selected Number: {selected_number} --------------------------------")
        best_media = selection_dict[selected_number]        
        print(f"Target Description: {next_description}\n")
        print(f"Selcted Description: {best_media}\n")
               
        # Get the next description from the cycle for alignment_bot
        next_description = next(descriptions_cycle)
    
        return best_media

    def generate_ranking_with_retry(self, paragraph, description, media_list, max_retries=5):
        attempt = 0
        
        # Print all parameters for debugging
        #print('______________generate ranking with retry_________________')
        #print(f"I am in generate_ranking_with_retry")
        #print(f"Parameters:\nParagraph: {paragraph}\nDescription: {description}\nMedia List: {media_list}\nMax Retries: {max_retries}")
        
        while attempt < max_retries:
            try:
                best_media = self.create_ranking_prompt(paragraph, description, media_list)
                if best_media:
                    return best_media
            except Exception as e:
                print(f"Error during response generation attempt {attempt}: {e}")
            attempt += 1
        return None



    def rank(self):
        #print("-----------------------")
        #print("I am in rank")
        ranked_results = {}
        #print(f"self.media_details = {self.media_details}")
        for video_ids in self.media_details:
            video_id = video_ids
            #print(f"Found video ID: {video_id}")
            # Loop through each video_id and its paragraphs
            for video_id, paragraphs in self.media_details.items():
                #print(f"Working on Paragraph: {video_id}")
                ranked_results[video_id] = {}
                
                # Loop through each paragraph and its content
                for p_key, content in paragraphs.items():
                    #print(f"p_key: {p_key}")
                    #print(f"content: {content}")
                    
                    # Check that paragraph and image tags exist in content
                    if 'paragraph' in content and 'img_tags' in content:
                        paragraph = content['paragraph']
                        img_tags = content['img_tags']
                        # Initialize the entry for this paragraph
                        ranked_results[video_id][p_key] = {'paragraph': paragraph, 'img_tags': img_tags}

                        # Loop through each media item (image1, video1, etc.)
                        for media_key, media_list in content.items():
                            if media_key.startswith('image') or media_key.startswith('video'):
                                if isinstance(media_list, list) and all(isinstance(item, dict) for item in media_list):
                                    description = next(self.descriptions_cycle)  # This will cycle indefinitely
                                    #print(f"----------------- before ranking --------------")
                                    #print(f"paragraph = {paragraph}")
                                    #print(f"description = {description}")
                                    #print(f"media_list = {media_list}")

                                    # Function to generate ranking or select best media
                                    best_media = self.generate_ranking_with_retry(paragraph, description, media_list, 5)
                                    if best_media:
                                        # Assign the best media to the results
                                        ranked_results[video_id][p_key][media_key] = [best_media]
                                else:
                                    print(f"No more descriptions available for {media_key} in {p_key}")
                                    
        #print(f"ranked_results = {ranked_results}")
        return ranked_results  # Return the ranked results


    
    
# Sample data and usage
if __name__ == "__main__":
    media_tags_gen = ["dove", "nature", "subscribe", "celebration", "hands"]
    descriptions_gen = ["Hand releasing a dove", "Diversity in nature", "Subscribe button", "Celebratory fireworks", "Group of people holding hands"]
    video_id = "video123"
     # media_details structure
    media_details = {
    "video123": {
        "P1": {
        "paragraph": "This is the text of paragraph 1",
        "img_tags": ["nature", "outdoors"],
        "image1": [
            {
            "url": "https://images.pexels.com/photos/2529375/pexels-photo-2529375.jpeg",
            "description": "Woman Spreading Both Her Arms"
            },
            {
            "url": "https://images.pexels.com/photos/1051838/pexels-photo-1051838.jpeg",
            "description": "Silhouette of Man at Daytime"
            }
        ],
        "video1": [
            {
            "url": "https://player.vimeo.com/external/377100374.hd.mp4?s=9ec2ad7114635409a446a74c3321f715ecbdb0fe&profile_id=175&oauth2_token_id=57447761",
            "description": "Woman doing yoga"
            }
        ]
        },
        "P2": {
        "paragraph": "This is the text of paragraph 2",
        "img_tags": ["city", "nightlife"],
        "image1": [
            {
            "url": "https://images.pexels.com/photos/6740754/pexels-photo-6740754.jpeg",
            "description": "Woman in Black Leggings Unrolling A Yoga Mat"
            }
        ],
        "video1": [
            {
            "url": "https://player.vimeo.com/external/581023305.hd.mp4?s=e9ce35d2457b90a83c2bc106184b82ab5d45738e&profile_id=175&oauth2_token_id=57447761",
            "description": "A woman meditating outdoors"
            }
        ]
        },
        "P3": {
        "paragraph": "This is the text of paragraph 3",
        "img_tags": ["mountain", "adventure"],
        "image1": [
            {
            "url": "https://images.pexels.com/photos/2916820/pexels-photo-2916820.jpeg",
            "description": "A Woman Sits On A Rock Beside The Lake"
            }
        ],
        "video1": [
            {
            "url": "https://player.vimeo.com/external/581022595.hd.mp4?s=e0c3f760e3bd73fa7ab9af47a3864cc63c854527&profile_id=175&oauth2_token_id=57447761",
            "description": "A woman meditating outdoors"
            }
        ]
        }
    }
    }


    ra = RankingAssistant(descriptions_gen, media_details)
    ranked_results = ra.rank()
    print(f"Ranked Results: {json.dumps(ranked_results, indent=2)}")
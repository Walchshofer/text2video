import re
from guidance import gen, models, system, user, assistant
import guidance

# Initialize the LiteLLMCompletion model
lm = models.LiteLLMChat(
    model="ollama/notus:7b-v1-q6_K",
    api_base="http://127.0.0.1:8000",
    api_key="NULL",
    temperature=1.0
)
lm.echo = False


class ConversationAgent:
    def __init__(self, chat_model, name: str, instructions: str, context_turns: int = 2):
        self._chat_model = chat_model
        self._name = name
        self._instructions = instructions
        self._my_turns = []
        self._interlocutor_turns = []
        self._context_turns = context_turns

    def generate_prompt(self, interlocutor_reply: str | None = None, additional_context: str = "") -> str:
        # Get trimmed history
        my_hist = self._my_turns[-self._context_turns:]
        interlocutor_hist = self._interlocutor_turns[-self._context_turns:]

        # Set up the system prompt using the chat model
        prompt = f"Your name is {self._name}. {self._instructions}\n"
        prompt += additional_context
        prompt += "\n".join(interlocutor_hist + my_hist)
        prompt += interlocutor_reply or ""

        return prompt

    def reply(self, interlocutor_reply: str, additional_context: str = "") -> str:
        self._interlocutor_turns.append(interlocutor_reply)
        prompt = self.generate_prompt(interlocutor_reply, additional_context)

        # Ensure prompt is a string
        if not isinstance(prompt, str):
            raise TypeError(f"Prompt must be a string, but got {type(prompt)}")

        with system():
            response = self._chat_model(prompt)
            print(f"response = {str(response)}")

        # Add debugging to check the response type
        if isinstance(response, bytes):
            # Decode bytes to string if necessary
            response = response.decode('utf-8')
        
        if isinstance(response, str):
            self._my_turns.append(response)
        else:
            print(f"DEBUG: Unexpected response type: {type(response)}, value: {response}")
            raise TypeError(f"Expected response to be a string, got {type(response)}")

        return response

# Define ConversationAgents for Voice Over and Image paragraphs
voice_over_agent = ConversationAgent(lm, "Voice Over Bot", "You are creating voice-over scripts for the video presentation.")
image_bot_agent = ConversationAgent(lm, "Image Bot", "You are selecting images and writing alt text for the video presentation.")

# Initialize the script and user input
script = []
voice_over_history = ""
image_bot_history = ""
user_input = {
    "topic": "Boost Confidence",
    "goal": "help build self-confidence and self-esteem",
    "max_paragraphs": 3
}

# Generate script for the video
for paragraph_number in range(1, user_input['max_paragraphs'] + 1):
    paragraph_type = "intro" if paragraph_number == 1 else ("outro" if paragraph_number == user_input['max_paragraphs'] else "body")
    
    # Generate voice over text
    voice_over_context = f"{voice_over_history}\n--\n{paragraph_type.capitalize()} Paragraph:"
    voice_over_text = voice_over_agent.reply(f"Generate a {paragraph_type} paragraph for the topic of {user_input['topic']} with the goal to {user_input['goal']}.", voice_over_context)
    voice_over_history += f"\n{voice_over_text}"

    # Generate image descriptions
    image_bot_context = f"{image_bot_history}\n--\n{paragraph_type.capitalize()} Paragraph Images:"
    image_descriptions = image_bot_agent.reply(f"Generate images and alt text to accompany the following voice over text: {voice_over_text}", image_bot_context)
    image_bot_history += f"\n{image_descriptions}"

    # Append to script
    script.append({
        "paragraph_number": paragraph_number,
        "paragraph_type": paragraph_type,
        "voice_over_text": voice_over_text,
        "image_descriptions": image_descriptions
    })

# Display the generated script
print(script)
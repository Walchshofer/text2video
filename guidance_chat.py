from guidance import user, assistant, system, newline, gen
import guidance


chat_lm = guidance.models.LiteLLMChat(
            model="ollama/notus:7b-v1-q6_K",
            api_base="http://127.0.0.1:8000",
            api_key="NULL"  # Replace with your actual API key
        ) 

chat_lm.echo = False
chat_lm.get_role_start = ""
import re
from guidance import gen, select, system, user, assistant

@guidance
def plan_for_goal(lm, goal: str):
    
    # This is a helper function which we will use below
    def parse_best(prosandcons, options):
        best = re.search(r'Best=(\d+)', prosandcons)
        if not best:
            best =  re.search(r'Best.*?(\d+)', 'Best= option is 3')
        if best:
            best = int(best.group(1))
        else:
            best = 0
        return options[best]

    # Some general instruction to the model
    with system():
        lm += "You are a helpful assistant."

    # Simulate a simple request from the user
    # Note that we switch to using 'lm2' here, because these are intermediate steps (so we don't want to overwrite the current lm object)
    with user():
        lm2 = lm + f"""\
        I want to {goal}
        Can you please generate one option for how to accomplish this?
        Please make the option very short, at most one line."""

    # Generate several options. Note that this means several sequential generation requests
    n_options = 5
    with assistant():
        options = []
        for i in range(n_options):
            options.append((lm2 + gen(name='option', temperature=1.0, max_tokens=50))["option"])

    # Have the user request pros and cons
    with user():
        lm2 += f"""\
        I want to {goal}
        Can you please comment on the pros and cons of each of the following options, and then pick the best option?
        ---
        """
        for i, opt in enumerate(options):
            lm2 += f"Option {i}: {opt}\n"
        lm2 += f"""\
        ---
        Please discuss each option very briefly (one line for pros, one for cons), and end by saying Best=X, where X is the number of the best option."""

    # Get the pros and cons from the model
    with assistant():
        lm2 += gen(name='prosandcons', temperature=0.0, max_tokens=600, stop="Best=") + "Best=" + gen("best", regex="[0-9]+") 

    # The user now extracts the one selected as the best, and asks for a full plan
    # We switch back to 'lm' because this is the final result we want
    with user():
        lm += f"""\
        I want to {goal}
        Here is my plan: {options[int(lm2["best"])]}
        Please elaborate on this plan, and tell me how to best accomplish it."""

    # The plan is generated
    with assistant():
        lm += gen(name='plan', max_tokens=500)

    return lm


results = chat_lm + plan_for_goal(goal="read more books")
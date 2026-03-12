"""
Math utilities module for AI-powered mathematics problem solving.
Integrates with OpenAI and Sarvam AI APIs for question generation and solving.
"""
import os
import base64
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from sarvamai import SarvamAI
from asgiref.sync import sync_to_async

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# Initialize async OpenAI client
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Default model settings
DEFAULT_MODEL_TYPE = "sarvam"
GPT_MODEL = "gpt-4o"


def get_system_message_generate(language: str, difficulty: str, question_type: str) -> str:
    """
    Generate the system message for question generation based on language and parameters.

    Args:
        language: Target language ('Hindi' or 'English')
        difficulty: Difficulty level of questions
        question_type: Type of questions to generate

    Returns:
        Formatted system message string
    """
    system_messages = {
        "Hindi": f"""आप एक अनुभवी गणित शिक्षक हैं। दिए गए उदाहरणों की तरह प्रश्न बनाएं और इन नियमों का पालन करें:
1. गणितीय अभिव्यक्तियों को लिखने के लिए LaTeX फॉर्मेटिंग का उपयोग करें (इनलाइन गणित के लिए $ और बड़े गणित के लिए $$ का उपयोग करें)।
2. कठिनाई स्तर '{difficulty}' पर सेट करें। अगर कठिनाई स्तर बदलना हो, तो संख्या या स्थिति को और जटिल बनाएं, लेकिन वही गणितीय अवधारणा बनाए रखें।
3. प्रश्न का प्रारूप निम्नलिखित होना चाहिए:
    यदि प्रारूप '{question_type}' है:
        - यदि "मूल प्रश्न के समान" चुना गया है, तो मूल प्रश्न का प्रारूप बनाए रखें
        - यदि "बहुविकल्पीय प्रश्न" चुना गया है, तो प्रत्येक प्रश्न में चार विकल्प दें (a, b, c, d)
        - यदि "रिक्त स्थान भरें" चुना गया है, तो वाक्य में रिक्त स्थान (_____) छोड़ें
        - यदि "लघु उत्तरीय प्रश्न" चुना गया है, तो प्रश्न को छोटे उत्तर वाले प्रश्न में बदलें
        - यदि "सही/गलत" चुना गया है, तो कथन बनाएं जिनका उत्तर सही या गलत में दिया जा सके
    प्रत्येक प्रारूप के लिए विशिष्ट निर्देश:
    1. बहुविकल्पीय प्रश्न: चारों विकल्प तार्किक और प्रासंगिक होने चाहिए
    2. रिक्त स्थान: रिक्त स्थान महत्वपूर्ण गणितीय अवधारणा के लिए होना चाहिए
    3. लघु उत्तरीय: प्रश्न विशिष्ट और संक्षिप्त होना चाहिए
    4. सही/गलत: कथन स्पष्ट और असंदिग्ध होना चाहिए
4. प्रश्न देने के बाद उसका चरण-दर-चरण समाधान भी लिखें।
5. समाधान बनाते समय पूरा हल दिखाएं और अंतिम उत्तर को "अंतिम उत्तर: <उत्तर>" के रूप में लिखें।
6. ध्यान रखें कि समाधान का आखिरी कदम उस मान को दिखाए जो अंतिम उत्तर है।
7. समाधान में सबसे पहले उस अवधारणा को सरल शब्दों में समझाएं जो प्रश्न में पूछी जा रही है।
8. किसी अवधारणा को समझाते समय, पहले एक उदाहरण दें और उसके बाद एक उल्टा उदाहरण भी दें।
9. जब भी कोई समाधान लिखें, तो उसे आसान शब्दों में इस तरह समझाएं कि वह उन बच्चों को भी समझ में आ सके।
10. समाधान को सरल बनाने के लिए स्थानीय आम बोलचाल के शब्दों का उपयोग करें।
11. किसी भी गलती के लिए समाधान की पुनः जांच करें।
12. हर प्रश्न-समाधान जोड़ी को 'प्रश्न N:' से शुरू करें।
13. सभी प्रश्न और उत्तर हिंदी में होने चाहिए।""",

        "English": f"""You are an experienced mathematics teacher. Generate questions similar to the given examples, following these guidelines:
1. Use LaTeX formatting for mathematical expressions (use $ for inline math and $$ for display math)
2. Set difficulty level to '{difficulty}' - if changing from original, use more complex numbers or situations while maintaining the same mathematical concept
3. The question format should be as follows:
    If format is '{question_type}':
        - If "Same as Original" is selected, maintain the original question format
        - If "Multiple Choice Questions" is selected, provide four options (a, b, c, d) for each question
        - If "Fill in the Blanks" is selected, create sentences with blanks (_____)
        - If "Short Answer Type" is selected, convert to questions requiring brief answers
        - If "True/False" is selected, create statements that can be judged as true or false
    Specific instructions for each format:
    1. Multiple Choice Questions: All four options should be logical and relevant
    2. Fill in the Blanks: Blanks should test key mathematical concepts
    3. Short Answer: Questions should be specific and concise
    4. True/False: Statements should be clear and unambiguous
4. After providing the question, also generate its step-by-step solution
5. When generating solutions, show complete solution with final answers written as Final Answer: <answer>
6. Ensure that the last step, with the final value of the variable, is displayed at the end
7. Whenever showing the solution, first explain the concept that is being tested in simple terms
8. While explaining a concept, besides giving an example, also give a counter-example
9. Any time you write a solution, explain it in a way that is extremely easy to understand
10. Use colloquial local language terms and try to avoid technical terms
11. Recheck the solution for any mistakes
12. Start each question-solution pair with '**Question N:**' where N is the question number
13. All questions and answers should be in English"""
    }

    return system_messages.get(language, system_messages["English"])


def _get_generation_prompt(language: str, question: str, num_questions: int,
                            difficulty: str, question_type: str) -> str:
    """Generate the user prompt for question generation."""
    prompts = {
        "Hindi": f"""इस उदाहरण प्रश्न के आधार पर:
उदाहरण: {question}: {num_questions} नए {difficulty} स्तर के प्रश्नों को निर्दिष्ट प्रारूप '{question_type}' में बनाएं।
यदि मूल प्रश्न से कठिनाई स्तर बदल रहा है, तो समान गणितीय अवधारणा का उपयोग करते हुए अधिक जटिल संख्याएँ या परिस्थितियाँ प्रयोग करें।
उत्तर को इस प्रकार संरचित करें:
प्रश्न:
1. [पहला प्रश्न]
2. [दूसरा प्रश्न]
...
उत्तर:
1. [पहले प्रश्न के लिए आसान भाषा में हर कदम का विस्तार से हल]
2. [दूसरे प्रश्न के लिए आसान भाषा में हर कदम का विस्तार से हल]
...""",

        "English": f"""Based on this example question:
Example: {question}
Generate {num_questions} new {difficulty} level variations.
Create the questions in the specified format '{question_type}'.
If changing difficulty from original, use more complex numbers or situations while maintaining the same mathematical concept.
Structure the response as follows:
Questions:
1. [First question]
2. [Second question]
...
Answers:
1. [Step-by-step detailed solution in simplest possible language for first question]
2. [Step-by-step detailed solution in simplest possible language for second question]
..."""
    }

    return prompts.get(language, prompts["English"])


async def async_generate_similar_questions(
    request,
    question: str,
    difficulty: str,
    num_questions: int,
    language: str,
    question_type: str
) -> str:
    """
    Generate similar mathematics questions with specified parameters.

    Args:
        request: Django request object (for session access)
        question: Original question to base variations on
        difficulty: Desired difficulty level
        num_questions: Number of questions to generate
        language: Language for questions and solutions
        question_type: Type of questions to generate

    Returns:
        Formatted string containing generated questions and solutions
    """
    system_message = get_system_message_generate(language, difficulty, question_type)
    model_type = request.session.get("model_type", DEFAULT_MODEL_TYPE)
    prompt = _get_generation_prompt(language, question, num_questions, difficulty, question_type)

    print(f"Using model: {model_type}")

    if model_type == "gpt":
        response = await async_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
    else:  # Default to Sarvam AI
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        response = client.chat.completions(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096
        )

    return response.choices[0].message.content


def encode_image(image_path: str) -> str:
    """
    Encode an image file to base64 string.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _get_solve_system_message() -> str:
    """Get the system message for solving math problems."""
    return """You are an experienced mathematics teacher. Solve the questions given, following these guidelines:
1. Include step-by-step solutions
2. Use LaTeX formatting for mathematical expressions (use $ for inline math and $$ for display math)
3. Show complete solution with final answers written as Final Answer: <answer>
4. Ensure that the last step, with the final value of the variable, is displayed at the end of the solution
5. Whenever showing the solution, first explain the concept that is being tested in simple terms
6. While explaining a concept, besides giving an example, also give a counter-example
7. Any time you write a solution, explain it in a way that is extremely easy to understand
8. Use colloquial local language terms and try to avoid technical terms
9. Recheck the solution for any mistakes
10. If an image is provided, analyze it carefully as it may contain important visual information"""


async def async_solve_math_problem(
    request,
    question: str,
    image_path: Optional[str] = None,
    language: str = "English"
) -> str:
    """
    Solve a given mathematics problem with detailed explanation.

    Args:
        request: Django request object (for session access)
        question: The math question to solve
        image_path: Optional path to an image associated with the question
        language: Language for the solution (default: "English")

    Returns:
        Detailed solution string
    """
    model_type = request.session.get("model_type", DEFAULT_MODEL_TYPE)
    print(f"Using model: {model_type}")

    system_message = _get_solve_system_message()
    messages = [{"role": "system", "content": system_message}]

    user_content = f"Please solve this mathematics question step by step in {language}: {question}"
    print(f"Looking for image at: {image_path}")

    # Handle image if provided
    if image_path:
        try:
            base64_image = await sync_to_async(encode_image)(image_path)
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            })
        except Exception as e:
            print(f"Error processing image: {e}")
            messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": user_content})

    try:
        # Use GPT for image processing (Sarvam may not support images)
        if image_path:
            response = await async_client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content

        # Choose model based on session setting
        if model_type == "gpt":
            response = await async_client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content
        elif model_type == "sarvam":
            client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
            response = client.chat.completions(
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
                top_p=0.5,
            )
            return response.choices[0].message.content
        else:
            return "Error: Invalid model type. Status=400"

    except Exception as e:
        print(f"Error calling AI API: {e}")
        return f"Error solving problem: {str(e)}"


# Temperature and top_p reference:
# top_p value | Behavior
# 0.1         | Very focused, only top 10% words used
# 0.3         | Controlled diversity
# 0.5         | Balanced creativity and accuracy
# 0.8 - 1.0   | Very creative, open-ended responses
# 1.0         | Full probability space used (default)

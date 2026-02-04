from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from config import settings
from app.services.custom_model import get_custom_model


class ClassifierOutput(BaseModel):
    """Output schema for the classifier LLM."""
    save: bool = Field(
        description="Whether this conversation should be saved to the database"
    )
    extracted_facts: List[str] = Field(
        default_factory=list,
        description="List of factual information about the user extracted from the message"
    )
    mood: str = Field(
        description="Detected mood/emotion from the message (e.g., happy, sad, anxious, neutral, excited, stressed)"
    )


class ConversationClassifier:
    """
    LLM-based classifier to determine if conversations should be saved.
    
    Uses GPT-4o-mini to analyze conversations and decide:
    - Should this be saved to the database?
    - What facts can be extracted?
    - What is the user's mood?
    
    Saves only meaningful conversations to reduce database bloat.
    """
    
    def __init__(self, model: str = None):
        """
        Initialize the classifier.
        
        Args:
            model: Gemini model to use for classification (defaults to settings)
        """
        model_name = model or settings.gemini_model
        
        # Choose between custom model and Gemini based on configuration
        if settings.use_custom_model and settings.custom_model_url:
            print(f"Classifier: Using custom model from: {settings.custom_model_url}")
            self.llm = get_custom_model(
                base_url=settings.custom_model_url,
                temperature=0,
                max_tokens=1024
            )
        else:
            print(f"Classifier: Using Gemini model: {model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0,  # Deterministic for classification
                google_api_key=settings.gemini_api_key
            )
        
        # Output parser
        self.parser = JsonOutputParser(pydantic_object=ClassifierOutput)
        
        # Build the prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a conversation classifier for a mental wellness AI assistant.

Your task is to analyze user messages and determine:
1. Should this conversation be saved to the database?
2. What factual information can be extracted about the user?
3. What is the user's emotional state/mood?

**SAVE CRITERIA** - Save to database if the message contains:
✅ Emotional content (feelings, moods, mental state)
✅ Personal information or facts about the user
✅ Significant life events or experiences
✅ Health or wellness information
✅ Goals, challenges, or concerns
✅ Meaningful context for future conversations

❌ DO NOT SAVE if the message is:
- Simple greetings ("hi", "hello", "hey")
- Basic acknowledgments ("ok", "thanks", "got it")
- Small talk without substance
- Test messages or gibberish
- Simple questions without context
- Purely functional requests

**FACT EXTRACTION** - Extract facts like:
- Personal details (name, age, occupation, location)
- Relationships (family, friends, pets)
- Hobbies and interests
- Work or school information
- Health conditions or medications
- Important dates or events
- Preferences and dislikes

**MOOD DETECTION** - Identify the primary emotion:
- happy, joyful, excited, content
- sad, depressed, down, melancholic
- anxious, worried, nervous, stressed
- angry, frustrated, irritated
- calm, peaceful, relaxed
- neutral (no strong emotion)
- confused, uncertain
- hopeful, optimistic

{format_instructions}

Be conservative with saving - only save conversations that provide meaningful context or emotional insight."""),
            ("human", "User message: {user_message}")
        ])
        
        # Build the chain
        self.chain = (
            self.prompt
            | self.llm
            | self.parser
        )
    
    async def classify(self, user_message: str) -> Dict[str, Any]:
        """
        Classify a user message.
        
        Args:
            user_message: The user's message to classify
            
        Returns:
            Dict with keys: save, extracted_facts, mood
        """
        try:
            result = await self.chain.ainvoke({
                "user_message": user_message,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            return result
            
        except Exception as e:
            print(f"Error classifying message: {e}")
            # Default to not saving on error
            return {
                "save": False,
                "extracted_facts": [],
                "mood": "neutral"
            }
    
    def classify_sync(self, user_message: str) -> Dict[str, Any]:
        """
        Synchronous version of classify.
        
        Args:
            user_message: The user's message to classify
            
        Returns:
            Dict with keys: save, extracted_facts, mood
        """
        try:
            result = self.chain.invoke({
                "user_message": user_message,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            return result
            
        except Exception as e:
            print(f"Error classifying message: {e}")
            return {
                "save": False,
                "extracted_facts": [],
                "mood": "neutral"
            }


# Global classifier instance
_classifier: Optional[ConversationClassifier] = None


def get_classifier() -> ConversationClassifier:
    """
    Get or create the global classifier instance.
    
    Returns:
        ConversationClassifier: Classifier instance
    """
    global _classifier
    
    if _classifier is None:
        _classifier = ConversationClassifier()
    
    return _classifier

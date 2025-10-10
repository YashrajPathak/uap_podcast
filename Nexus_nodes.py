"""
nodes.py — Dynamic node-level logic for NexusAgent.

This includes:
- Topic introduction generation based on input context.
- Any dynamic conversational building blocks that Nexus executes during the session.
"""

import asyncio
from typing import Optional
from uap_podcast.agents.nexus_agent.utils.state import SYSTEM_NEXUS
from uap_podcast.models.podcast import llm  # <- using central llm() utility

async def generate_nexus_topic_intro(context: str) -> str:
    """
    Generate Nexus's introduction of the metrics and topics for discussion.

    This is the first dynamic message Nexus produces — it analyzes the data context
    and introduces 2–3 of the most interesting metrics trends to set the stage.
    """
    topic_system = (
        "You are Agent Nexus, the host of Optum MultiAgent Conversation. "
        "Your role is to introduce the key metrics and topics that Agents Reco and Stat will discuss. "
        "Review the provided data context and highlight 2-3 most interesting or important metric trends. "
        "Keep it concise (2-3 sentences), professional, and engaging. "
        "Focus on the most significant patterns that would spark an interesting discussion between metrics experts. "
        "Mention specific metrics like ASA, call duration, processing time, or volume changes when relevant. "
        "Set the stage for a productive conversation between our recommendation specialist and data integrity expert."
    )

    topic_user = f"""
    Data Context: {context}

    Based on this data, identify the 2-3 most interesting metric trends or patterns that would make for 
    a compelling discussion between a metrics recommendation specialist (Reco) and a data integrity expert (Stat).
    Provide a brief introduction that sets the stage for their conversation.
    """

    return await llm(topic_system, topic_user, max_tokens=120, temperature=0.4)


async def nexus_summary(context: Optional[str], highlights: Optional[str]) -> str:
    """
    Optionally generate a dynamic summary at the end of the conversation.

    This can be called after all agent turns are done to generate a concise summary.
    """
    system_prompt = SYSTEM_NEXUS
    user_prompt = (
        "Generate a closing summary for the podcast that highlights the key points "
        "from Reco and Stat, connects them to the business context, "
        "and thanks the listeners for tuning in."
    )

    if highlights:
        user_prompt += f"\nKey points discussed:\n{highlights}"

    if context:
        user_prompt += f"\nRelevant data context:\n{context}"

    return await llm(system_prompt, user_prompt, max_tokens=150, temperature=0.45)

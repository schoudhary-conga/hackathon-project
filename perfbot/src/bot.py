"""Teams Bot activity handler — processes messages and card actions."""

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, Attachment

from src.ai_brain import ai_brain
from src.handlers import handle_intent


class PerfBot(ActivityHandler):
    """Microsoft Teams bot that provides K6 performance insights."""

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages from users."""
        # Remove bot mention from Teams messages
        text = self._remove_mention(turn_context.activity)

        if not text.strip():
            await turn_context.send_activity(
                MessageFactory.text("Hi! Ask me about performance test results. "
                                    "Try: 'How did platform-data-api do in the last run?'")
            )
            return

        # Send typing indicator
        await turn_context.send_activity(Activity(type="typing"))

        # Parse intent via Azure OpenAI
        intent = await ai_brain.parse_intent(text)

        # Handle the intent — may return a card (dict) or text (str)
        response = await handle_intent(intent)

        # Send response based on type
        if isinstance(response, str):
            # Brief conversational response — plain text
            await turn_context.send_activity(MessageFactory.text(response))
        else:
            # Detailed response — Adaptive Card
            message = Activity(
                type="message",
                attachments=[Attachment(**response)] if isinstance(response, dict) else [],
            )
            await turn_context.send_activity(message)

    async def on_invoke_activity(self, turn_context: TurnContext):
        """Handle Adaptive Card action submissions (button clicks)."""
        if turn_context.activity.value:
            action_data = turn_context.activity.value

            # Re-route as a new intent
            card_attachment = await handle_intent(action_data)

            message = Activity(
                type="message",
                attachments=[Attachment(**card_attachment)],
            )
            await turn_context.send_activity(message)

        # Return invoke response
        from botbuilder.schema import InvokeResponse
        return InvokeResponse(status=200)

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        """Greet new members when bot is added to a conversation."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "👋 Hi! I'm **PerfBot** — your AI performance insights assistant.\n\n"
                        "Ask me things like:\n"
                        "- *How did platform-data-api do in the last run?*\n"
                        "- *Did last night's run pass?*\n"
                        "- *Any failures today?*\n"
                        "- *Which APIs are slowest?*\n"
                        "- *Is anything running right now?*\n"
                    )
                )

    def _remove_mention(self, activity: Activity) -> str:
        """Remove @mention of the bot from the message text."""
        text = activity.text or ""
        if activity.entities:
            for entity in activity.entities:
                if entity.type == "mention":
                    mention_text = entity.additional_properties.get("text", "")
                    text = text.replace(mention_text, "").strip()
        return text

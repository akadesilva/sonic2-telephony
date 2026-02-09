# LinkedIn Post

🎉 Excited to share my latest project: **Nova Sonic 2 Telephony Agent** 🚀

Built a voice-powered personal assistant that you can call on the phone! It uses Amazon's latest Nova Sonic 2 model to have natural conversations and help with daily tasks.

**What it does:** 📞
✅ Manages your Google Calendar - schedule meetings, check appointments
✅ Takes daily notes - timestamped entries stored in Google Drive
✅ Searches the web in real-time using Perplexity AI
✅ Understands natural language over phone calls

**Tech Stack:** 🛠️
🔹 Amazon Bedrock (Nova Sonic 2) - Real-time voice AI
🔹 Amazon Bedrock AgentCore - Serverless agent runtime
🔹 Vonage Voice API - Telephony integration
🔹 Google APIs - Calendar, Docs, Drive
🔹 AWS Lambda + API Gateway - Webhook handling
🔹 Python + FastAPI - WebSocket server

**Technical Challenges Solved:** 💡

🔊 **High-Jitter Telephony Networks**
The PSTN network introduces significant jitter compared to internet connections. This creates a tricky buffer management problem:
- Need LARGER buffers to prevent audio dropouts
- But larger buffers delay barge-in detection (user has to wait for queued audio to finish)
- Solution: Leverage Vonage's "clear buffer" API when Nova Sonic detects interruption
- Result: Responsive barge-in despite network jitter

🎙️ **Natural Conversation Flow**
Instead of awkward silence, the agent proactively greets you with "Hello! How can I help you today?" using a pre-recorded audio file. This eliminates the "dead air" moment and makes the interaction feel natural.

**Why it's cool:** ⚡
No screen needed! Just call a number and talk naturally. The agent:
- Keeps responses concise (2-3 sentences) for better listening
- Confirms important details by repeating them back
- Provides verbal updates when using tools
- Handles timezone-aware scheduling

**What's Next:** 🚀
- AgentCore Memory integration for persistent conversation context
- Async tool calls for parallel execution
- Multi-language support
- Custom voice personas

**Open Source:** 🌟
Released under MIT-0 license on GitHub. Includes:
📝 Complete setup guide with detailed learnings
🔧 Ready-to-deploy infrastructure
🧪 Test scripts for all tools
📚 Technical deep-dive on telephony challenges

Perfect for developers exploring:
- Voice AI applications
- Real-time streaming with Bedrock
- Telephony integrations
- Agentic workflows

Check it out and let me know what you think! Would love to hear ideas for additional capabilities. 🎯

[Link to GitHub Repository]

#AWS #AmazonBedrock #VoiceAI #AI #MachineLearning #Serverless #OpenSource #CloudComputing #Innovation #Telephony #RealtimeAI

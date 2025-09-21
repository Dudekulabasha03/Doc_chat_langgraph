#!/usr/bin/env python3
"""
ReAct Agent with LangGraph - Fixed Version
Uses Gemma2:9b + Tavily Search + Clean UI (No Deprecation Warnings)
"""

import os
import json
import gradio as gr
from typing import Annotated, Sequence, TypedDict

# LangChain and LangGraph imports
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

# Setup
os.environ["TAVILY_API_KEY"] = "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"

# Initialize tools
search = TavilySearchResults()

@tool
def search_tool(query: str):
    """Search the web for current information"""
    return search.invoke(query)

@tool
def recommend_clothing(weather: str) -> str:
    """Recommend clothing based on weather description"""
    weather = weather.lower()
    if "snow" in weather or "freezing" in weather:
        return "🧥 Heavy coat, gloves, and warm boots recommended"
    elif "rain" in weather or "wet" in weather:
        return "🌧️ Raincoat and waterproof shoes recommended"
    elif "hot" in weather or "sunny" in weather:
        return "☀️ Light clothing, t-shirt, shorts, and sunscreen"
    elif "cold" in weather:
        return "🧥 Warm jacket or sweater recommended"
    else:
        return "👕 Light jacket should be fine"

# Tool registry
tools = [search_tool, recommend_clothing]
tools_by_name = {tool.name: tool for tool in tools}

# Initialize Gemma2 model
model = ChatOllama(model="gemma2:9b")

# Create system prompt
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant using the ReAct framework.

When responding:
1. Think step-by-step about what information you need
2. Use tools when you need current data or specific capabilities
3. Provide clear, well-formatted responses

Be concise but comprehensive in your answers."""),
    MessagesPlaceholder(variable_name="messages")
])

# Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# LangGraph Functions
def call_model(state: AgentState):
    """Call the model to get next action"""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    
    # Check if we need to use tools
    if any(word in last_message.lower() for word in ["weather", "news", "current", "today", "latest"]):
        search_query = last_message
        
        try:
            search_results = search_tool.invoke(search_query)
            tool_message = ToolMessage(
                content=json.dumps(search_results),
                name="search_tool",
                tool_call_id="search_1"
            )
            
            # For weather + clothing questions
            if "weather" in last_message.lower() and "wear" in last_message.lower():
                clothing_advice = recommend_clothing.invoke(str(search_results))
                clothing_message = ToolMessage(
                    content=clothing_advice,
                    name="recommend_clothing", 
                    tool_call_id="clothing_1"
                )
                return {"messages": [tool_message, clothing_message]}
            else:
                return {"messages": [tool_message]}
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            return {"messages": [AIMessage(content=error_msg)]}
    
    # Generate response using model
    prompt = chat_prompt.format_messages(messages=messages)
    response = model.invoke(prompt)
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    """Determine if we should continue processing"""
    messages = state["messages"]
    if not messages:
        return "continue"
    
    last_message = messages[-1]
    
    # If it's a tool message, continue to get AI response
    if isinstance(last_message, ToolMessage):
        return "continue"
    
    # If it's an AI message, we're done
    return "end"

# Create LangGraph workflow
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "agent", "end": END}
)
workflow.set_entry_point("agent")
graph = workflow.compile()

def format_response(messages):
    """Format the response with beautiful structure"""
    sections = []
    thinking_steps = []
    
    for msg in messages:
        if isinstance(msg, ToolMessage):
            if msg.name == "search_tool":
                thinking_steps.append("🔍 Searching web for current information")
                try:
                    search_data = json.loads(msg.content)
                    if search_data:
                        search_section = "\n## 🔍 **Web Search Results**\n\n"
                        for i, result in enumerate(search_data[:3], 1):
                            title = result.get('title', 'Untitled')
                            content = result.get('content', '')[:180]
                            url = result.get('url', '')
                            
                            search_section += f"### {i}. {title}\n\n"
                            search_section += f"📄 {content}...\n\n"
                            if url:
                                search_section += f"🔗 [Read more]({url})\n\n"
                            search_section += "---\n\n"
                        sections.append(search_section)
                except Exception:
                    sections.append("\n## 🔍 **Web Search Results**\n\nFound relevant information.\n\n")
            
            elif msg.name == "recommend_clothing":
                thinking_steps.append("👕 Getting clothing recommendations")
                clothing_section = f"\n## 👕 **Clothing Recommendation**\n\n{msg.content}\n\n"
                sections.append(clothing_section)
        
        elif isinstance(msg, AIMessage) and msg.content:
            ai_section = f"\n## 💬 **AI Response**\n\n{msg.content}\n\n"
            sections.append(ai_section)
    
    # Build final response
    final_response = ""
    
    if thinking_steps:
        final_response += "## 🤔 **Agent Process**\n\n"
        for i, step in enumerate(thinking_steps, 1):
            final_response += f"**Step {i}:** {step}\n"
        final_response += "\n" + "="*50 + "\n"
    
    final_response += "".join(sections)
    return final_response

def react_chat(message, history):
    """Main chat function using LangGraph"""
    try:
        initial_state = {"messages": [HumanMessage(content=message)]}
        final_state = graph.invoke(initial_state)
        formatted_response = format_response(final_state["messages"])
        
        # Return proper format for Gradio
        history.append((message, formatted_response))
        return history, ""
    
    except Exception as e:
        error_response = f"❌ **Error:** {str(e)}\n\nPlease check if Ollama is running and Gemma2:9b is available."
        history.append((message, error_response))
        return history, ""

# Custom CSS for better styling
css = """
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto;
}
.chatbot {
    height: 600px !important;
}
"""

# Clean Gradio Interface
with gr.Blocks(title="ReAct Agent - Fixed", theme=gr.themes.Soft(), css=css) as demo:
    
    # Header
    gr.HTML("""
    <div style="text-align: center; padding: 25px; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 2.3em;">🤖 ReAct AI Agent</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 1.1em;">LangGraph + Gemma2:9b + Tavily Search</p>
    </div>
    """)
    
    # Main interface
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=600,
                show_copy_button=True,
                container=True,
                show_label=False
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask about weather, news, or any topic...",
                    container=False,
                    scale=8
                )
                send_btn = gr.Button("Send 🚀", variant="primary", scale=1)
            
            clear_btn = gr.Button("Clear Chat 🗑️", variant="secondary")
        
        with gr.Column(scale=1):
            gr.Markdown("""
            ### 📋 **Quick Examples**
            
            **Weather Queries:**
            - "Weather in London today and what to wear?"
            - "Tokyo weather forecast?"
            
            **News & Current Events:**
            - "Latest AI developments"
            - "Climate change news"
            
            **General Questions:**
            - "Capital of Japan?"
            - "Math: 15 × 8 = ?"
            
            ---
            
            ### 🔧 **How ReAct Works**
            
            1. **🤔 Reasoning** - Analyze your question
            2. **🔍 Acting** - Use web search tools
            3. **👀 Observing** - Process tool results  
            4. **💬 Responding** - Generate answer
            
            **Powered by LangGraph state machine!**
            
            ---
            
            ### ✨ **Features**
            - 🧠 **ReAct Framework**
            - 🔍 **Real-time Web Search**
            - 🌤️ **Weather + Clothing Advice**
            - 🤖 **Gemma2:9b Local Model**
            """)
    
    # Event handlers
    send_btn.click(react_chat, [msg, chatbot], [chatbot, msg])
    msg.submit(react_chat, [msg, chatbot], [chatbot, msg])
    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])

if __name__ == "__main__":
    print("🚀 Starting ReAct Agent (Fixed Version)...")
    print("📊 LangGraph + Gemma2:9b + Tavily Search")
    print("🌐 Interface: http://127.0.0.1:7860")
    demo.launch(share=True)

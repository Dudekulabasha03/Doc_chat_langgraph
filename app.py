import gradio as gr
import hashlib
from typing import List, Dict
import os
import json
from datetime import datetime

from document_processor.file_handler import DocumentProcessor
from retriever.builder import RetrieverBuilder
from agents.workflow import AgentWorkflow
from config import constants, settings
from utils.logging import logger

# 1) Define example data with detailed descriptions
EXAMPLES = {
    "Google 2024 Environmental Report": {
        "question": "Retrieve the data center PUE efficiency values in Singapore 2nd facility in 2019 and 2022. Also retrieve regional average CFE in Asia pacific in 2023",
        "description": "Environmental sustainability metrics and energy efficiency data from Google's 2024 report",
        "file_paths": ["examples/google-2024-environmental-report.pdf"],
        "tags": ["Environmental", "Data Centers", "Energy Efficiency"]
    },
    "DeepSeek-R1 Technical Report": {
        "question": "Summarize DeepSeek-R1 model's performance evaluation on all coding tasks against OpenAI o1-mini model",
        "description": "Technical analysis of AI model performance on coding benchmarks and comparisons",
        "file_paths": ["examples/DeepSeek Technical Report.pdf"],
        "tags": ["AI", "Machine Learning", "Coding", "Benchmarks"]
    }
}

def main():
    processor = DocumentProcessor()
    retriever_builder = RetrieverBuilder()
    workflow = AgentWorkflow()

    # Define custom CSS for modern dark theme
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-color: #6C5CE7;
        --secondary-color: #A29BFE;
        --accent-color: #00B894;
        --warning-color: #FDCB6E;
        --error-color: #E17055;
        --success-color: #00B894;
        --dark-bg: #1A1D23;
        --card-bg: #2D3748;
        --surface-bg: #374151;
        --text-primary: #F7FAFC;
        --text-secondary: #CBD5E0;
        --text-muted: #9CA3AF;
        --border-color: #4A5568;
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-accent: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --gradient-success: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --shadow-lg: 0 10px 25px rgba(0, 0, 0, 0.2);
        --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
        --border-radius: 12px;
    }

    /* Global theme overrides */
    .gradio-container {
        background: var(--dark-bg) !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        min-height: 100vh !important;
    }

    /* Header styling */
    .title {
        font-size: 2.5em !important; 
        text-align: center !important;
        background: var(--gradient-primary) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        font-weight: 700 !important;
        margin: 30px 0 20px 0 !important;
        text-shadow: none !important;
    }

    .subtitle {
        font-size: 1.3em !important; 
        text-align: center !important;
        color: var(--text-secondary) !important;
        margin: 10px 0 30px 0 !important;
        font-weight: 400 !important;
    }

    .section-header {
        font-size: 1.2em !important;
        font-weight: 600 !important;
        color: var(--primary-color) !important;
        border-bottom: 2px solid var(--primary-color) !important;
        padding-bottom: 8px !important;
        margin: 20px 0 15px 0 !important;
        position: relative !important;
    }

    .section-header::before {
        content: '' !important;
        position: absolute !important;
        bottom: -2px !important;
        left: 0 !important;
        width: 40px !important;
        height: 2px !important;
        background: var(--accent-color) !important;
    }

    .text {
        text-align: center !important;
        margin: 10px 0 !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
    }
    
    /* Container styling */
    .input-section {
        background: var(--card-bg) !important;
        padding: 25px !important;
        border-radius: var(--border-radius) !important;
        margin: 15px 0 !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--shadow-md) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .output-section {
        background: var(--surface-bg) !important;
        padding: 25px !important;
        border-radius: var(--border-radius) !important;
        margin: 15px 0 !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    /* File upload area */
    .file-upload {
        border: 2px dashed var(--primary-color) !important;
        border-radius: var(--border-radius) !important;
        padding: 30px !important;
        background: rgba(108, 92, 231, 0.05) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-align: center !important;
    }
    
    .file-upload:hover {
        border-color: var(--secondary-color) !important;
        background: rgba(108, 92, 231, 0.1) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Button styling */
    .btn-primary {
        background: var(--gradient-primary) !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 14px 32px !important;
        font-weight: 600 !important;
        font-size: 0.95em !important;
        color: white !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-md) !important;
        text-transform: none !important;
    }
    
    .btn-primary:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-lg) !important;
        filter: brightness(1.1) !important;
    }
    
    button[variant="secondary"] {
        background: var(--surface-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 20px !important;
        padding: 12px 24px !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    
    button[variant="secondary"]:hover {
        background: var(--border-color) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Input and textarea styling */
    .gradio-textbox, .gradio-dropdown {
        background: var(--surface-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }
    
    .gradio-textbox:focus, .gradio-dropdown:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1) !important;
    }
    
    /* Textarea specific styling */
    textarea {
        background: var(--surface-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        line-height: 1.6 !important;
        padding: 16px !important;
        resize: vertical !important;
    }
    
    textarea:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1) !important;
        outline: none !important;
    }
    
    /* Answer output styling */
    #answer_output {
        border: 1px solid var(--success-color) !important;
        border-radius: var(--border-radius) !important;
        background: var(--dark-bg) !important;
    }
    
    #answer_output textarea {
        max-height: 500px !important;
        overflow-y: auto !important;
        background: var(--dark-bg) !important;
        border: none !important;
        color: var(--text-primary) !important;
    }
    
    /* Verification report styling */
    #verification_output {
        border: 1px solid var(--warning-color) !important;
        border-radius: var(--border-radius) !important;
        background: var(--dark-bg) !important;
    }
    
    #verification_output textarea {
        max-height: 350px !important;
        overflow-y: auto !important;
        background: var(--dark-bg) !important;
        border: none !important;
        color: var(--text-primary) !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    }
    
    /* Status indicators */
    .status-indicator {
        padding: 10px 20px !important;
        border-radius: 25px !important;
        font-size: 0.9em !important;
        font-weight: 600 !important;
        margin: 8px 0 !important;
        display: inline-block !important;
    }
    
    .status-processing {
        background: rgba(253, 203, 110, 0.2) !important;
        color: var(--warning-color) !important;
        border: 1px solid rgba(253, 203, 110, 0.3) !important;
    }
    
    .status-complete {
        background: rgba(0, 184, 148, 0.2) !important;
        color: var(--success-color) !important;
        border: 1px solid rgba(0, 184, 148, 0.3) !important;
    }
    
    .status-error {
        background: rgba(225, 112, 85, 0.2) !important;
        color: var(--error-color) !important;
        border: 1px solid rgba(225, 112, 85, 0.3) !important;
    }
    
    /* Progress bar styling */
    .progress-bar {
        width: 100% !important;
        height: 6px !important;
        background: var(--surface-bg) !important;
        border-radius: 3px !important;
        overflow: hidden !important;
        margin: 10px 0 !important;
    }
    
    .progress-bar-fill {
        height: 100% !important;
        background: var(--gradient-success) !important;
        transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    /* Tab styling */
    .gradio-tabs {
        background: transparent !important;
    }
    
    .gradio-tab {
        background: var(--surface-bg) !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-secondary) !important;
        border-radius: 8px 8px 0 0 !important;
        font-weight: 500 !important;
    }
    
    .gradio-tab.selected {
        background: var(--primary-color) !important;
        color: white !important;
        border-color: var(--primary-color) !important;
    }
    
    /* Example styling */
    .example-card {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--border-radius) !important;
        padding: 20px !important;
        margin: 15px 0 !important;
        box-shadow: var(--shadow-md) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .example-card:hover {
        box-shadow: var(--shadow-lg) !important;
        transform: translateY(-4px) !important;
        border-color: var(--primary-color) !important;
    }
    
    .example-description {
        color: var(--text-secondary) !important;
        font-size: 0.95em !important;
        margin: 10px 0 !important;
        line-height: 1.5 !important;
    }
    
    .example-tags {
        margin-top: 15px !important;
    }
    
    .tag {
        display: inline-block !important;
        background: rgba(108, 92, 231, 0.2) !important;
        color: var(--primary-color) !important;
        padding: 4px 12px !important;
        border-radius: 16px !important;
        font-size: 0.8em !important;
        font-weight: 500 !important;
        margin: 3px 6px 3px 0 !important;
        border: 1px solid rgba(108, 92, 231, 0.3) !important;
    }
    
    /* Dropdown styling */
    .gradio-dropdown {
        background: var(--surface-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px !important;
        height: 8px !important;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--surface-bg) !important;
        border-radius: 4px !important;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--border-color) !important;
        border-radius: 4px !important;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-color) !important;
    }
    
    /* Label styling */
    label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        margin-bottom: 8px !important;
    }
    
    /* Info text styling */
    .gradio-info {
        color: var(--text-muted) !important;
        font-size: 0.85em !important;
    }
    
    /* Animation for smooth transitions */
    * {
        transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease !important;
    }
    
    /* Custom gradients for visual appeal */
    .gradient-bg-1 {
        background: var(--gradient-primary) !important;
    }
    
    .gradient-bg-2 {
        background: var(--gradient-accent) !important;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .input-section, .output-section {
            padding: 15px !important;
            margin: 10px 0 !important;
        }
        
        .title {
            font-size: 2em !important;
        }
        
        .subtitle {
            font-size: 1.1em !important;
        }
    }
    """

    js = """
    function createGradioAnimation() {
        var container = document.createElement('div');
        container.id = 'gradio-animation';
        container.style.fontSize = '2em';
        container.style.fontWeight = 'bold';
        container.style.textAlign = 'center';
        container.style.marginBottom = '20px';
        container.style.color = '#eba93f';

        var text = 'Welcome to DocChat 🐥!';
        for (var i = 0; i < text.length; i++) {
            (function(i){
                setTimeout(function(){
                    var letter = document.createElement('span');
                    letter.style.opacity = '0';
                    letter.style.transition = 'opacity 0.1s';
                    letter.innerText = text[i];

                    container.appendChild(letter);

                    setTimeout(function() {
                        letter.style.opacity = '0.9';
                    }, 50);
                }, i * 250);
            })(i);
        }

        var gradioContainer = document.querySelector('.gradio-container');
        gradioContainer.insertBefore(container, gradioContainer.firstChild);

        return 'Animation created';
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(), title="DocChat 🐥 - Enhanced Document Analysis", css=css, js=js) as demo:
        # Header Section
        gr.Markdown("# 🐥 DocChat: Advanced Document Analysis Platform", elem_classes="title")
        gr.Markdown("## Powered by Docling 📄 and LangGraph 🔗", elem_classes="subtitle")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("📤 **Upload** → 🤔 **Question** → 🚀 **Submit** → 📊 **Analysis**", elem_classes="text")
            with gr.Column(scale=1):
                gr.Markdown("💡 Try examples or upload: PDF, DOCX, TXT, MD files", elem_classes="text")

        # Main Layout
        with gr.Row():
            # Left Column - Input Section
            with gr.Column(scale=1, elem_classes="input-section"):
                gr.Markdown("### 📂 Examples Library", elem_classes="section-header")
                
                # Enhanced Examples Section
                with gr.Group():
                    example_dropdown = gr.Dropdown(
                        label="🎯 Select a Pre-loaded Example",
                        choices=list(EXAMPLES.keys()),
                        value=None,
                        info="Choose from curated examples with sample documents and questions"
                    )
                    
                    # Example description display
                    example_info = gr.Markdown(
                        "💡 **Select an example above to see its description and tags**",
                        elem_classes="example-description"
                    )
                    
                    with gr.Row():
                        load_example_btn = gr.Button("📥 Load Example", elem_classes="btn-primary")
                        clear_btn = gr.Button("🗑️ Clear All", variant="secondary")

                gr.Markdown("### 📄 Document Upload", elem_classes="section-header")
                
                # Enhanced File Upload Section
                with gr.Group():
                    files = gr.Files(
                        label="📎 Drop your documents here or click to browse",
                        file_types=constants.ALLOWED_TYPES,
                        file_count="multiple",
                        elem_classes="file-upload"
                    )
                    
                    # File status display
                    file_status = gr.Markdown(
                        "📁 **Ready to upload:** PDF, DOCX, TXT, MD files (Max: 200MB total)",
                        elem_classes="text"
                    )

                gr.Markdown("### ❓ Your Question", elem_classes="section-header")
                
                # Enhanced Question Input
                question = gr.Textbox(
                    label="✍️ What would you like to know about your documents?",
                    lines=4,
                    placeholder="Ask detailed questions about the content, request summaries, comparisons, or specific data extraction...",
                    info="Be specific for better results. Example: 'What are the key performance metrics mentioned in Q3 2023?'"
                )
                
                # Progress and Status Section
                gr.Markdown("### 📊 Processing Status", elem_classes="section-header")
                
                with gr.Group():
                    status_display = gr.Markdown(
                        "🟢 **Ready** - Upload documents and ask your question",
                        elem_classes="status-indicator"
                    )
                    
                    progress_bar = gr.HTML(
                        '<div class="progress-bar"><div class="progress-bar-fill" style="width: 0%"></div></div>',
                        visible=False
                    )
                
                # Submit Section
                with gr.Row():
                    submit_btn = gr.Button("🚀 Analyze Documents", elem_classes="btn-primary", variant="primary", scale=2)
                    reset_btn = gr.Button("🔄 Reset", variant="secondary", scale=1)
            
            # Right Column - Output Section  
            with gr.Column(scale=1, elem_classes="output-section"):
                gr.Markdown("### 🎯 Analysis Results", elem_classes="section-header")
                
                # Tabbed Output Interface
                with gr.Tabs():
                    with gr.TabItem("📝 Answer", elem_id="answer-tab"):
                        answer_output = gr.Textbox(
                            label="🐥 AI-Generated Response",
                            interactive=False,
                            elem_id="answer_output",
                            lines=25,
                            show_copy_button=True,
                            placeholder="Your detailed analysis will appear here..."
                        )
                        
                        # Answer actions
                        with gr.Row():
                            export_answer_btn = gr.Button("💾 Export Answer", size="sm")
                            rate_answer_btn = gr.Button("⭐ Rate Answer", size="sm")
                    
                    with gr.TabItem("✅ Verification Report", elem_id="verification-tab"):
                        verification_output = gr.Textbox(
                            label="🔍 Quality & Accuracy Assessment",
                            elem_id="verification_output",
                            lines=20,
                            show_copy_button=True,
                            placeholder="Verification analysis will appear here...",
                            info="This report evaluates the accuracy and relevance of the AI response"
                        )
                        
                        # Verification actions
                        with gr.Row():
                            export_verification_btn = gr.Button("📊 Export Report", size="sm")
                            view_sources_btn = gr.Button("📚 View Sources", size="sm")
                    
                    with gr.TabItem("📈 Session History", elem_id="history-tab"):
                        session_history = gr.Textbox(
                            label="🕒 Previous Queries and Results",
                            lines=15,
                            interactive=False,
                            placeholder="Your session history will be displayed here..."
                        )
                        
                        with gr.Row():
                            clear_history_btn = gr.Button("🗑️ Clear History", size="sm")
                            export_history_btn = gr.Button("💾 Export History", size="sm")

        # Session state management
        session_state = gr.State({
            "file_hashes": frozenset(),
            "retriever": None,
            "history": [],
            "current_files": []
        })

        # Enhanced helper functions
        def update_example_info(example_key: str):
            """Update example information display when selection changes."""
            if not example_key or example_key not in EXAMPLES:
                return "💡 **Select an example above to see its description and tags**"
            
            ex_data = EXAMPLES[example_key]
            description = ex_data.get("description", "No description available")
            tags = ex_data.get("tags", [])
            
            info_md = f"**📋 Description:** {description}\n\n"
            if tags:
                tags_str = " ".join([f"<span class='tag'>{tag}</span>" for tag in tags])
                info_md += f"**🏷️ Tags:** {tags_str}"
            
            return info_md
        
        def load_example(example_key: str):
            """Load example documents and question into the interface."""
            if not example_key or example_key not in EXAMPLES:
                return [], "", "⚠️ **No example selected**"

            ex_data = EXAMPLES[example_key]
            question = ex_data["question"]
            file_paths = ex_data["file_paths"]

            # Load files and validate existence
            loaded_files = []
            missing_files = []
            
            for path in file_paths:
                if os.path.exists(path):
                    loaded_files.append(path)
                else:
                    missing_files.append(path)
                    logger.warning(f"File not found: {path}")

            # Update status
            if missing_files:
                status = f"⚠️ **Warning:** {len(missing_files)} files not found: {', '.join(missing_files)}"
            elif loaded_files:
                status = f"✅ **Loaded:** {len(loaded_files)} files successfully loaded"
            else:
                status = "❌ **Error:** No files could be loaded"

            return loaded_files, question, status
        
        def clear_all():
            """Clear all inputs and reset interface."""
            return [], "", "🟢 **Ready** - Upload documents and ask your question", None
        
        def update_file_status(files):
            """Update file upload status display."""
            if not files:
                return "📁 **Ready to upload:** PDF, DOCX, TXT, MD files (Max: 200MB total)"
            
            file_count = len(files)
            total_size = sum(os.path.getsize(f.name) for f in files if hasattr(f, 'name') and os.path.exists(f.name))
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > constants.MAX_TOTAL_SIZE / (1024 * 1024):
                return f"❌ **Error:** {file_count} files ({size_mb:.1f}MB) exceed 200MB limit"
            else:
                return f"✅ **Uploaded:** {file_count} files ({size_mb:.1f}MB)"
        
        def reset_interface():
            """Reset the entire interface to initial state."""
            return (
                None,  # example_dropdown
                [],    # files
                "",    # question
                "💡 **Select an example above to see its description and tags**",  # example_info
                "📁 **Ready to upload:** PDF, DOCX, TXT, MD files (Max: 200MB total)",  # file_status
                "🟢 **Ready** - Upload documents and ask your question",  # status_display
                "",    # answer_output
                "",    # verification_output
                "Your session history will be displayed here...",  # session_history
                {"file_hashes": frozenset(), "retriever": None, "history": [], "current_files": []}  # session_state
            )

        load_example_btn.click(
            fn=load_example,
            inputs=[example_dropdown],
            outputs=[files, question]
        )

        # Enhanced processing function with progress tracking and history
        def process_question(question_text: str, uploaded_files: List, state: Dict):
            """Handle questions with enhanced progress tracking and history management."""
            try:
                # Initial validation
                if not question_text.strip():
                    raise ValueError("❌ Question cannot be empty")
                if not uploaded_files:
                    raise ValueError("❌ No documents uploaded")

                # Update processing status
                processing_status = "🔄 **Processing** - Analyzing documents..."
                
                current_hashes = _get_file_hashes(uploaded_files)
                file_names = [f.name.split('/')[-1] if hasattr(f, 'name') else str(f) for f in uploaded_files]
                
                # Process documents if needed
                if state["retriever"] is None or current_hashes != state["file_hashes"]:
                    logger.info("Processing new/changed documents...")
                    processing_status = "⚙️ **Processing Documents** - Extracting and indexing content..."
                    
                    # Process documents with better error handling
                    chunks = processor.process(uploaded_files)
                    
                    if not chunks:
                        error_msg = (
                            "⚠️ Unable to extract text from the uploaded documents.\n\n"
                            "🔍 **Possible causes:**\n"
                            "• Complex PDF formatting or scanned images\n"
                            "• Password-protected or corrupted files\n"
                            "• Unsupported file format\n\n"
                            "💡 **Try these solutions:**\n"
                            "• Use a different PDF or convert to TXT/MD\n"
                            "• Try the provided example documents\n"
                            "• Ensure files are not password-protected"
                        )
                        error_status = "❌ **Error** - Document processing failed"
                        return error_msg, "", error_status, state
                    
                    processing_status = "🔍 **Building Index** - Creating search index..."
                    
                    # Build retriever with validation
                    retriever = retriever_builder.build_hybrid_retriever(chunks)
                    
                    state.update({
                        "file_hashes": current_hashes,
                        "retriever": retriever,
                        "current_files": file_names
                    })
                    
                    logger.info(f"Successfully processed {len(chunks)} document chunks")
                
                processing_status = "🤖 **Generating Answer** - AI is analyzing your question..."
                
                # Run the workflow
                result = workflow.full_pipeline(
                    question=question_text,
                    retriever=state["retriever"]
                )
                
                # Update session history
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_entry = {
                    "timestamp": timestamp,
                    "question": question_text,
                    "files": file_names,
                    "answer_preview": result["draft_answer"][:200] + "..." if len(result["draft_answer"]) > 200 else result["draft_answer"]
                }
                
                state["history"].append(history_entry)
                
                # Format history display
                history_display = "\n\n".join([
                    f"**{entry['timestamp']}**\n"
                    f"**Q:** {entry['question']}\n"
                    f"**Files:** {', '.join(entry['files'])}\n"
                    f"**Answer:** {entry['answer_preview']}"
                    for entry in state["history"][-5:]  # Show last 5 entries
                ])
                
                if not history_display:
                    history_display = "Your session history will be displayed here..."
                
                success_status = f"✅ **Complete** - Analysis finished successfully ({timestamp})"
                
                return (
                    result["draft_answer"], 
                    result["verification_report"], 
                    success_status,
                    history_display,
                    state
                )
                    
            except ValueError as ve:
                logger.warning(f"Validation error: {str(ve)}")
                error_status = "⚠️ **Validation Error** - Please check your inputs"
                return str(ve), "", error_status, state.get("history", "Your session history will be displayed here..."), state
                
            except Exception as e:
                logger.error(f"Processing error: {str(e)}")
                error_msg = (
                    f"❌ **Processing Failed:** {str(e)}\n\n"
                    "🔧 **Troubleshooting Steps:**\n"
                    "• Check if Ollama is running: `ollama serve`\n"
                    "• Try with simpler text/markdown files\n"
                    "• Use the provided example documents\n"
                    "• Verify files are not corrupted or encrypted\n"
                    "• Restart the application if issues persist"
                )
                error_status = "❌ **Critical Error** - Processing failed"
                return error_msg, "", error_status, state.get("history", "Your session history will be displayed here..."), state

        # Export and utility functions
        def export_answer(answer_text):
            """Export answer to a downloadable file."""
            if not answer_text:
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"docchat_answer_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"DocChat AI Answer\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(answer_text)
            
            return filename
        
        def export_verification(verification_text):
            """Export verification report to a downloadable file."""
            if not verification_text:
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"docchat_verification_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"DocChat Verification Report\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(verification_text)
            
            return filename
        
        def export_history(history_text):
            """Export session history to a downloadable file."""
            if not history_text or history_text == "Your session history will be displayed here...":
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"docchat_history_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"DocChat Session History\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(history_text)
            
            return filename
        
        def clear_history():
            """Clear the session history."""
            return "Your session history will be displayed here..."
        
        # Event handlers
        
        # Example dropdown change
        example_dropdown.change(
            fn=update_example_info,
            inputs=[example_dropdown],
            outputs=[example_info]
        )
        
        # Load example button
        load_example_btn.click(
            fn=load_example,
            inputs=[example_dropdown],
            outputs=[files, question, status_display]
        )
        
        # Clear all button
        clear_btn.click(
            fn=clear_all,
            inputs=[],
            outputs=[files, question, status_display, example_dropdown]
        )
        
        # File upload change
        files.change(
            fn=update_file_status,
            inputs=[files],
            outputs=[file_status]
        )
        
        # Reset button
        reset_btn.click(
            fn=reset_interface,
            inputs=[],
            outputs=[
                example_dropdown, files, question, example_info, 
                file_status, status_display, answer_output, 
                verification_output, session_history, session_state
            ]
        )
        
        # Main submit button
        submit_btn.click(
            fn=process_question,
            inputs=[question, files, session_state],
            outputs=[answer_output, verification_output, status_display, session_history, session_state]
        )
        
        # Export buttons
        export_answer_btn.click(
            fn=export_answer,
            inputs=[answer_output],
            outputs=[]
        )
        
        export_verification_btn.click(
            fn=export_verification,
            inputs=[verification_output],
            outputs=[]
        )
        
        export_history_btn.click(
            fn=export_history,
            inputs=[session_history],
            outputs=[]
        )
        
        # Clear history button
        clear_history_btn.click(
            fn=clear_history,
            inputs=[],
            outputs=[session_history]
        )

    # Launch with enhanced configuration
    demo.launch(
        server_name="127.0.0.1", 
        server_port=5000, 
        share=True,
        show_api=True,
        show_error=True,
        quiet=False,
        favicon_path=None,
        app_kwargs={
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        }
    )

def _get_file_hashes(uploaded_files: List) -> frozenset:
    """Generate SHA-256 hashes for uploaded files."""
    hashes = set()
    for file in uploaded_files:
        with open(file.name, "rb") as f:
            hashes.add(hashlib.sha256(f.read()).hexdigest())
    return frozenset(hashes)

if __name__ == "__main__":
    main()

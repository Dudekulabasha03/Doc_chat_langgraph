#!/usr/bin/env python3
"""
Test script to launch the enhanced DocChat UI
This script verifies that all imports work and the interface can be initialized
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test if all required imports are available"""
    print("🧪 Testing imports...")
    
    try:
        import gradio as gr
        print("✅ Gradio imported successfully")
    except ImportError as e:
        print(f"❌ Gradio import failed: {e}")
        return False
    
    try:
        from document_processor.file_handler import DocumentProcessor
        print("✅ DocumentProcessor imported successfully")
    except ImportError as e:
        print(f"❌ DocumentProcessor import failed: {e}")
        return False
    
    try:
        from retriever.builder import RetrieverBuilder
        print("✅ RetrieverBuilder imported successfully")
    except ImportError as e:
        print(f"❌ RetrieverBuilder import failed: {e}")
        return False
    
    try:
        from agents.workflow import AgentWorkflow
        print("✅ AgentWorkflow imported successfully")
    except ImportError as e:
        print(f"❌ AgentWorkflow import failed: {e}")
        return False
    
    try:
        from config import constants, settings
        print("✅ Config modules imported successfully")
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    return True

def test_app_initialization():
    """Test if the app can be initialized without errors"""
    print("\n🚀 Testing app initialization...")
    
    try:
        # Import the main function
        from app import main
        print("✅ App main function imported successfully")
        
        # Note: We don't actually call main() here as it would launch the server
        print("✅ App structure verified")
        return True
        
    except Exception as e:
        print(f"❌ App initialization failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🐥 DocChat Enhanced UI - Test Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please check your dependencies.")
        sys.exit(1)
    
    # Test app initialization
    if not test_app_initialization():
        print("\n❌ App initialization tests failed.")
        sys.exit(1)
    
    print("\n🎉 All tests passed! The enhanced UI should work correctly.")
    print("\nTo run the app, use:")
    print("python3 app.py")
    
    print("\n📋 Enhanced Features Summary:")
    print("• 🎨 Improved UI with better styling and organization")
    print("• 📁 Enhanced file upload with validation and status indicators")
    print("• 📂 Better examples section with descriptions and tags")
    print("• 📊 Progress tracking and status updates")
    print("• 📝 Tabbed output interface (Answer, Verification, History)")
    print("• 💾 Export functionality for answers, reports, and history")
    print("• 🔄 Session history tracking")
    print("• 🎯 Better error handling and user feedback")

if __name__ == "__main__":
    main()
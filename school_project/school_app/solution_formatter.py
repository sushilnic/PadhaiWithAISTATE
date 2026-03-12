import re
import markdown
from bs4 import BeautifulSoup
import uuid

class SolutionFormatter:
    
    @staticmethod
    def format_solution(solution_text):
        """Format the solution text with proper markdown and LaTeX formatting."""
        if not solution_text:
            return ""
        
        text = solution_text
        
        # Store LaTeX expressions to protect them from markdown processing
        latex_store = {}
        
        def protect_latex(match):
            key = f"LATEX_{uuid.uuid4().hex[:8]}"
            latex_store[key] = match.group(0)
            return key
        
        # Protect display math \[ ... \] and $$ ... $$
        text = re.sub(r'\\\[[\s\S]*?\\\]', protect_latex, text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', protect_latex, text)
        
        # Protect inline math \( ... \) and $ ... $
        text = re.sub(r'\\\(.*?\\\)', protect_latex, text)
        text = re.sub(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)', protect_latex, text)
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            text,
            extensions=['extra', 'nl2br', 'sane_lists']
        )
        
        # Restore LaTeX expressions
        for key, latex in latex_store.items():
            html_content = html_content.replace(key, latex)
        
        # Clean up excessive line breaks
        html_content = re.sub(r'(<br\s*/?>){3,}', '<br><br>', html_content)
        html_content = re.sub(r'(<p>\s*</p>)+', '', html_content)
        
        # Wrap in a structured solution div
        return f'<div class="structured-solution">{html_content}</div>'
    
    @staticmethod
    def format_question(question_text):
        """Format the question text."""
        if not question_text:
            return ""
        
        # Store LaTeX expressions to protect them from markdown processing
        latex_store = {}
        
        def protect_latex(match):
            key = f"LATEX_{uuid.uuid4().hex[:8]}"
            latex_store[key] = match.group(0)
            return key
        
        # Protect display math and inline math
        text = re.sub(r'\\\[[\s\S]*?\\\]', protect_latex, question_text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', protect_latex, text)
        text = re.sub(r'\\\(.*?\\\)', protect_latex, text)
        text = re.sub(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)', protect_latex, text)
        
        # Convert markdown to HTML
        html_content = markdown.markdown(text, extensions=['extra'])
        
        # Restore LaTeX expressions
        for key, latex in latex_store.items():
            html_content = html_content.replace(key, latex)
        
        return html_content

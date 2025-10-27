import sys
import tty
import termios
import shutil
import os
from typing import List, Optional

class StoryWriterUI:
    def __init__(self):
        # Get terminal dimensions
        self.width, self.height = shutil.get_terminal_size()
        self.left_panel_expanded = True  # Start with panel open
        self.left_panel_width = max(17, self.width // 4 - 3)  # 25% of screen width minus 3, min 17
        self.main_content = ""
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.panel_selection = 0  # Track which item is selected in left panel
        self.panel_focused = False  # Track if panel has focus for navigation
        
        # Book management
        self.books_directory = "data"
        self.current_mode = "editor"  # "editor", "book_list"
        self.books_list = []
        self.book_selection = 0
        self.book_focused = False
        self.input_mode = False
        self.input_text = ""
        self.input_callback = None
        
        # Current book and chapters
        self.current_book = None
        self.chapters_list = []
        self.chapter_selection = 0
        self.chapter_focused = False
        self.current_chapter = None
        self.preview_mode = False
        self.preview_content = ""
        self.preview_chapter = None
        self.confirm_mode = False
        self.confirm_selection = False  # False = No, True = Yes
        self.unsaved_changes = False
        self.original_content = ""
        self.confirm_type = "save"  # "save" or "unsaved"
        self.pending_navigation = None  # Store pending navigation action
        self.help_mode = False
        
        # Load last book on startup
        self.load_last_book()
        
        # Terminal settings for raw input
        self.old_settings = None
        
    def enable_raw_mode(self):
        """Enable raw terminal mode for single character input"""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        
    def disable_raw_mode(self):
        """Restore normal terminal mode"""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            
    def get_key(self) -> str:
        """Get a single key press"""
        self.enable_raw_mode()
        try:
            key = sys.stdin.read(1)
            # Handle special keys
            if key == '\x1b':  # Escape sequence
                next_key = sys.stdin.read(2)
                if next_key == '[A':
                    return 'UP'
                elif next_key == '[B':
                    return 'DOWN'
                elif next_key == '[C':
                    return 'RIGHT'
                elif next_key == '[D':
                    return 'LEFT'
                else:
                    # Standalone escape key
                    return 'ESC'
            elif key == '\t':
                return 'TAB'
            elif key == '\r':
                return 'ENTER'
            elif key == '\x7f':  # Backspace
                return 'BACKSPACE'
            elif key == '\x03':  # Ctrl+C
                return 'CTRL_C'
            elif key == '\x11':  # Ctrl+Q
                return 'CTRL_Q'
            elif key == '\x02':  # Ctrl+B
                return 'CTRL_B'
            elif key == '\x0e':  # Ctrl+N
                return 'CTRL_N'
            elif key == '\x12':  # Ctrl+R
                return 'CTRL_R'
            elif key == '\x04':  # Ctrl+D
                return 'CTRL_D'
            elif key == '\x0f':  # Ctrl+O
                return 'CTRL_O'
            elif key == '\x13':  # Ctrl+S
                return 'CTRL_S'
            elif key == '\x08':  # Ctrl+H
                return 'CTRL_H'
            elif key == '\x1b':  # Escape
                return 'ESC'
            else:
                return key
        finally:
            self.disable_raw_mode()
    
    def load_books(self):
        """Load list of books from the books directory, sorted by recent order"""
        if not os.path.exists(self.books_directory):
            os.makedirs(self.books_directory)
            self.books_list = []
            return
        
        # Get all directories in the books folder
        try:
            items = os.listdir(self.books_directory)
            all_books = [item for item in items if os.path.isdir(os.path.join(self.books_directory, item))]
            
            # Read book order from .data file
            book_order = []
            if os.path.exists('.data'):
                with open('.data', 'r') as f:
                    book_order = [line.strip() for line in f.readlines() if line.strip()]
            
            # Sort books by order (recent first), then alphabetically for books not in order
            ordered_books = []
            unordered_books = []
            
            for book in book_order:
                if book in all_books:
                    ordered_books.append(book)
            
            for book in all_books:
                if book not in ordered_books:
                    unordered_books.append(book)
            
            unordered_books.sort()  # Sort alphabetically
            self.books_list = ordered_books + unordered_books
            
        except OSError:
            self.books_list = []
    
    def load_book(self, book_name: str):
        """Load a specific book and its chapters"""
        self.current_book = book_name
        self.current_chapter = None  # Clear current chapter when loading new book
        self.unsaved_changes = False  # Reset unsaved changes when loading new book
        self.save_last_book(book_name)  # Save the current book
        book_path = os.path.join(self.books_directory, book_name)
        
        if not os.path.exists(book_path):
            self.chapters_list = []
            return
        
        # Load chapter order from hidden file
        order_file = os.path.join(book_path, '.chapter_order')
        chapter_order = []
        
        if os.path.exists(order_file):
            try:
                with open(order_file, 'r') as f:
                    chapter_order = [line.strip() for line in f.readlines() if line.strip()]
            except OSError:
                pass
        
        # Get all files in the book directory (excluding hidden files)
        try:
            all_files = os.listdir(book_path)
            # Filter out hidden files and directories
            chapter_files = [f for f in all_files if not f.startswith('.') and os.path.isfile(os.path.join(book_path, f))]
            chapter_files.sort()
            
            # Merge ordered chapters with remaining files
            ordered_chapters = []
            for chapter in chapter_order:
                if chapter in chapter_files:
                    ordered_chapters.append(chapter)
                    chapter_files.remove(chapter)
            
            # Add remaining files
            ordered_chapters.extend(chapter_files)
            
            self.chapters_list = ordered_chapters
            
            # Set panel selection to current chapter if it exists
            if self.current_chapter and self.current_chapter in self.chapters_list:
                self.panel_selection = self.chapters_list.index(self.current_chapter)
            else:
                self.panel_selection = 0
            
            # Clear main content if no chapters exist
            if not self.chapters_list:
                self.main_content = ""
                self.cursor_pos = 0
                self.current_chapter = None
                self.preview_content = ""
                self.preview_mode = False
        except OSError:
            self.chapters_list = []
            # Clear main content on error
            self.main_content = ""
            self.cursor_pos = 0
            self.preview_content = ""
            self.preview_mode = False
            self.current_chapter = None
    
    def save_last_book(self, book_name: str):
        """Save the current book name to .data file and update order"""
        try:
            # Read existing order
            book_order = []
            if os.path.exists('.data'):
                with open('.data', 'r') as f:
                    book_order = [line.strip() for line in f.readlines() if line.strip()]
            
            # Remove book if it exists and add to front
            if book_name in book_order:
                book_order.remove(book_name)
            book_order.insert(0, book_name)
            
            # Keep only the last 10 books to avoid file getting too large
            book_order = book_order[:10]
            
            # Write updated order
            with open('.data', 'w') as f:
                for book in book_order:
                    f.write(book + '\n')
        except OSError:
            pass
    
    def load_last_book(self):
        """Load the last book from .data file or open book selection"""
        try:
            if os.path.exists('.data'):
                with open('.data', 'r') as f:
                    book_order = [line.strip() for line in f.readlines() if line.strip()]
                    # Get the first (most recent) book
                    if book_order and os.path.exists(os.path.join(self.books_directory, book_order[0])):
                        self.load_book(book_order[0])
                        self.panel_focused = True  # Focus panel when auto-loading book
                        self.left_panel_expanded = True  # Always open side panel when book is loaded
                        # Set panel selection to current chapter if it exists
                        if self.current_chapter and self.current_chapter in self.chapters_list:
                            self.panel_selection = self.chapters_list.index(self.current_chapter)
                        # Show preview of first chapter if available
                        if self.chapters_list:
                            first_chapter = self.chapters_list[0]
                            self.load_chapter_preview(first_chapter)
                            self.preview_mode = True
                        return
            
            # If no book found, automatically open book selection
            self.left_panel_expanded = False  # Close side panel
            self.current_mode = "book_list"
            self.load_books()
            self.book_selection = 0
            self.book_focused = True
        except OSError:
            # If error reading .data, open book selection
            self.left_panel_expanded = False  # Close side panel
            self.current_mode = "book_list"
            self.load_books()
            self.book_selection = 0
            self.book_focused = True
    
    def save_current_chapter(self):
        """Save the current chapter content to file"""
        if not self.current_book or not self.current_chapter:
            return False
        
        try:
            book_path = os.path.join(self.books_directory, self.current_book)
            chapter_path = os.path.join(book_path, self.current_chapter)
            
            with open(chapter_path, 'w') as f:
                f.write(self.main_content)
            # Update original content and reset unsaved changes
            self.original_content = self.main_content
            self.unsaved_changes = False
            return True
        except OSError:
            return False
    
    def load_chapter(self, chapter_name: str):
        """Load a specific chapter content"""
        if not self.current_book or not chapter_name:
            return False
        
        try:
            book_path = os.path.join(self.books_directory, self.current_book)
            chapter_path = os.path.join(book_path, chapter_name)
            
            if os.path.exists(chapter_path):
                with open(chapter_path, 'r') as f:
                    self.main_content = f.read()
                self.cursor_pos = len(self.main_content)
                # Store original content and reset unsaved changes
                self.original_content = self.main_content
                self.unsaved_changes = False
                self.current_chapter = chapter_name
                # Set panel selection to this chapter if side panel is open
                if self.left_panel_expanded and chapter_name in self.chapters_list:
                    self.panel_selection = self.chapters_list.index(chapter_name)
                return True
            else:
                # Chapter doesn't exist, create empty content
                self.main_content = ""
                self.cursor_pos = 0
                self.original_content = ""
                self.unsaved_changes = False
                self.current_chapter = chapter_name
                # Set panel selection to this chapter if side panel is open
                if self.left_panel_expanded and chapter_name in self.chapters_list:
                    self.panel_selection = self.chapters_list.index(chapter_name)
                return True
        except OSError:
            return False
    
    def load_chapter_preview(self, chapter_name: str):
        """Load a chapter preview without setting it as current"""
        if not self.current_book or not chapter_name:
            return False
        
        try:
            book_path = os.path.join(self.books_directory, self.current_book)
            chapter_path = os.path.join(book_path, chapter_name)
            
            if os.path.exists(chapter_path):
                with open(chapter_path, 'r') as f:
                    self.preview_content = f.read()
                self.preview_chapter = chapter_name
                return True
            else:
                self.preview_content = ""
                self.preview_chapter = chapter_name
                return True
        except OSError:
            self.preview_content = ""
            self.preview_chapter = None
            return False
    
    def create_new_book(self, book_name: str):
        """Create a new book directory"""
        if not book_name.strip():
            return False
        
        # Sanitize book name for filesystem
        safe_name = "".join(c for c in book_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            return False
        
        # Check if book already exists in current books list
        if safe_name in self.books_list:
            return False
        
        book_path = os.path.join(self.books_directory, safe_name)
        if os.path.exists(book_path):
            return False
        
        try:
            os.makedirs(book_path)
            # Create hidden chapter order file
            order_file = os.path.join(book_path, '.chapter_order')
            with open(order_file, 'w') as f:
                f.write('')
            # Add new book to the top of the order
            self.save_last_book(safe_name)
            return True
        except OSError:
            return False
    
    def delete_book(self, book_name: str):
        """Delete a book directory"""
        book_path = os.path.join(self.books_directory, book_name)
        if os.path.exists(book_path):
            try:
                import shutil
                shutil.rmtree(book_path)
                return True
            except OSError:
                return False
        return False
    
    def delete_chapter(self, chapter_name: str):
        """Delete a chapter file"""
        if not self.current_book or not chapter_name:
            return False
        
        book_path = os.path.join(self.books_directory, self.current_book)
        chapter_path = os.path.join(book_path, chapter_name)
        
        try:
            os.remove(chapter_path)
            # Update chapter order file
            self.update_chapter_order(chapter_name, None)  # Remove from order
            return True
        except OSError:
            return False
    
    def rename_book(self, old_name: str, new_name: str):
        """Rename a book directory"""
        if not new_name.strip():
            return False
        
        # Sanitize new name for filesystem
        safe_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            return False
        
        # Check if new name already exists in books list (and it's not the same as old name)
        if safe_name != old_name and safe_name in self.books_list:
            return False
        
        old_path = os.path.join(self.books_directory, old_name)
        new_path = os.path.join(self.books_directory, safe_name)
        
        if os.path.exists(new_path):
            return False
        
        try:
            os.rename(old_path, new_path)
            return True
        except OSError:
            return False
    
    def show_input_dialog(self, prompt: str, callback, old_name: str = None):
        """Show input dialog for book naming"""
        self.input_mode = True
        self.input_text = ""
        self.input_callback = callback
        self.input_prompt = prompt
        self.old_name = old_name
    
    def handle_input_dialog(self, key: str):
        """Handle input in dialog mode"""
        if key == 'ENTER':
            # Confirm input
            if self.input_callback:
                self.input_callback(self.input_text)
            self.input_mode = False
            self.input_text = ""
            self.input_callback = None
        elif key == 'ESC':  # Escape
            # Cancel input
            self.input_mode = False
            self.input_text = ""
            self.input_callback = None
        elif key == 'BACKSPACE':
            if self.input_text:
                self.input_text = self.input_text[:-1]
        elif len(key) == 1 and key.isprintable():
            self.input_text += key
        return True
    
    def handle_confirm_dialog(self, key: str):
        """Handle input in confirmation dialog"""
        if key == 'LEFT':
            # Move to Yes (leftmost option) - wrap around infinitely
            self.confirm_selection = True
        elif key == 'RIGHT':
            # Move to No (rightmost option) - wrap around infinitely
            self.confirm_selection = False
        elif key == 'ENTER':
            # Confirm selection
            if self.confirm_selection:
                # Yes - save the chapter
                if self.confirm_type == "unsaved":
                    self.save_current_chapter()
                    self.unsaved_changes = False
                else:
                    self.save_current_chapter()
            else:
                # No - for unsaved changes, allow navigation to continue
                if self.confirm_type == "unsaved":
                    self.unsaved_changes = False
                    # Execute pending navigation
                    if self.pending_navigation == "UP" and self.panel_selection > 0:
                        self.panel_selection -= 1
                        if self.panel_selection < len(self.chapters_list):
                            selected_chapter = self.chapters_list[self.panel_selection]
                            self.load_chapter_preview(selected_chapter)
                            self.preview_mode = True
                    elif self.pending_navigation == "DOWN" and self.panel_selection < len(self.chapters_list) - 1:
                        self.panel_selection += 1
                        if self.panel_selection < len(self.chapters_list):
                            selected_chapter = self.chapters_list[self.panel_selection]
                            self.load_chapter_preview(selected_chapter)
                            self.preview_mode = True
                    self.pending_navigation = None
            # No - do nothing
            self.confirm_mode = False
            self.confirm_selection = False
        elif key == 'ESC':  # Escape
            # Cancel - do nothing
            self.confirm_mode = False
            self.confirm_selection = False
        return True
    
    def draw_help_panel(self):
        """Draw the help panel overlay"""
        if not self.help_mode:
            return
        
        # Calculate panel dimensions
        panel_width = min(80, self.width - 4)
        panel_height = min(30, self.height - 4)
        x = (self.width - panel_width) // 2
        y = (self.height - panel_height) // 2
        
        # Draw help panel border
        self.draw_border(x, y, panel_width, panel_height, "Help")
        
        # Fill help panel background with solid color
        for row in range(y + 1, y + panel_height - 1):
            for col in range(x + 1, x + panel_width - 1):
                print(f"\033[{row};{col}H\033[7m ", end='')
        
        # Help content
        help_lines = [
            "GENERAL COMMANDS:",
            "  ^H    - Toggle this help panel",
            "  ^B    - Toggle side panel",
            "  ^O    - Open book selection",
            "  ^N    - New book/chapter",
            "  ^R    - Rename book",
            "  ^D    - Delete book",
            "  ^S    - Save current chapter",
            "  Enter - Select item",
            "  ESC   - Close dialogs/panels"
        ]
        
        # Draw help content
        content_y = y + 2
        for i, line in enumerate(help_lines):
            if content_y + i < y + panel_height - 1:
                print(f"\033[{content_y + i};{x + 2}H{line}", end='')
        
        # Draw close instruction at bottom
        close_y = y + panel_height - 2
        print(f"\033[{close_y};{x + 2}H\033[1mPress ESC or Ctrl+H to close\033[0m", end='')
    
    def clear_screen(self):
        """Clear the terminal screen with background color"""
        # Clear screen and set background color
        print('\033[2J\033[H\033[40m', end='')
        # Fill entire screen with background color
        for row in range(1, self.height + 1):
            print(f"\033[{row};1H{' ' * self.width}", end='')
        
    def draw_border(self, x: int, y: int, width: int, height: int, title: str = ""):
        """Draw a border box at the specified position"""
        if title:
            # Draw top border with integrated title
            title_len = len(title)
            if title_len >= width - 2:
                # Title too long, truncate it
                title = title[:width - 2]
                title_len = len(title)
            
            # Calculate padding to center title
            total_padding = width - 2 - title_len
            left_padding = total_padding // 2
            right_padding = total_padding - left_padding
            
            top_border = f"╔{'═' * left_padding}{title}{'═' * right_padding}╗"
            print(f"\033[{y};{x}H{top_border}", end='')
        else:
            # Top border without title
            print(f"\033[{y};{x}H╔{'═' * (width - 2)}╗", end='')
        
        # Side borders and content area
        for i in range(1, height - 1):
            print(f"\033[{y + i};{x}H║", end='')
            print(f"\033[{y + i};{x + width - 1}H║", end='')
        
        # Bottom border
        print(f"\033[{y + height - 1};{x}H╚{'═' * (width - 2)}╝", end='')
    
    def draw_left_panel(self):
        """Draw the expandable left panel"""
        if not self.left_panel_expanded:
            return
            
        panel_width = self.left_panel_width
        panel_height = self.height  # Use full height since no bottom bar
        
        # Draw panel background with color
        for row in range(2, panel_height):
            print(f"\033[{row};2H\033[7m{' ' * (panel_width - 2)}", end='')
        
        # Draw the left panel border with book title or "BOOKS"
        if self.current_book:
            title = self.current_book
        else:
            title = "BOOKS"
        self.draw_border(1, 1, panel_width, panel_height, title)
        
        # Add content to the left panel
        available_lines = panel_height - 2
        
        if self.current_book:
            # Show chapters when a book is loaded
            content_lines = []
            if not self.chapters_list:
                # Display "No Chapters" message at the top
                content_lines.append("No Chapters")
            else:
                for i, chapter in enumerate(self.chapters_list):
                    if i < available_lines - 3:  # Leave space for bottom items
                        # Display chapter name without extension
                        display_name = chapter
                        if chapter.endswith('.md'):
                            display_name = chapter[:-3]  # Remove .md extension
                        
                        if i == self.panel_selection and self.panel_focused:
                            content_lines.append(f"> {display_name}")
                        else:
                            content_lines.append(f"  {display_name}")
            
            # Fill remaining space
            while len(content_lines) < available_lines - 3:
                content_lines.append("")
            
            # No bottom items needed for book view
        else:
            # Show default content when no book is loaded
            content_lines = []
            
            # Fill with empty lines when no book is loaded
            while len(content_lines) < available_lines - 2:
                content_lines.append("")
        
        # Store selectable items for navigation
        self.selectable_items = []
        for i, line in enumerate(content_lines):
            if line.strip():
                self.selectable_items.append(i)
        
        # Set default selection to first selectable item if panel is open
        if self.left_panel_expanded and self.selectable_items and not self.panel_focused:
            self.panel_selection = self.selectable_items[0]
        
        for i, line in enumerate(content_lines):
            if i < panel_height - 2:
                # Highlight selected item with reversed colors
                if i == self.panel_selection and i in self.selectable_items:
                    print(f"\033[{2 + i};2H\033[7m {line} \033[0m", end='')  # Reversed colors
                else:
                    # Draw with reversed background for unselected items
                    print(f"\033[{2 + i};2H\033[7m {line} \033[0m", end='')
    
    def draw_main_content(self):
        """Draw the main writing area"""
        if self.left_panel_expanded:
            start_x = self.left_panel_width + 1
        else:
            start_x = 1
            
        content_width = self.width - start_x
        content_height = self.height  # Use full height since no bottom bar
        
        # Adjust content width to account for border
        display_width = content_width - 2  # Subtract 2 for left and right borders
        
        # Draw main content background with color
        for row in range(2, content_height):
            print(f"\033[{row};{start_x + 1}H\033[7m{' ' * (content_width - 2)}", end='')
        
        # Draw main content border
        if self.current_mode == "book_list":
            title = "BOOKS"
        elif self.preview_mode and self.preview_chapter:
            # Show preview chapter title without extension
            chapter_title = self.preview_chapter
            if chapter_title.endswith('.md'):
                chapter_title = chapter_title[:-3]  # Remove .md extension
            title = f"Preview: {chapter_title}"
        elif self.current_chapter:
            # Show chapter title without extension
            chapter_title = self.current_chapter
            if chapter_title.endswith('.md'):
                chapter_title = chapter_title[:-3]  # Remove .md extension
            title = chapter_title
        else:
            title = "STORY EDITOR" if not self.left_panel_expanded else ""
        self.draw_border(start_x, 1, content_width, content_height, title)
        
        if self.current_mode == "book_list":
            self.draw_book_list(start_x, content_width, content_height)
        else:
            # Display the story content or preview
            if self.preview_mode and self.preview_content:
                content_to_show = self.preview_content
            else:
                content_to_show = self.main_content
                
            lines = content_to_show.split('\n')
            display_start = max(0, self.scroll_offset)
            display_end = min(len(lines), display_start + content_height - 2)
            
            # Display lines with wrapping for display but keep original line structure
            display_lines = []
            for line in lines:
                if len(line) <= display_width:
                    display_lines.append(line)
                else:
                    # Wrap long lines for display
                    words = line.split(' ')
                    current_display_line = ''
                    for word in words:
                        if len(current_display_line + ' ' + word) <= display_width:
                            if current_display_line:
                                current_display_line += ' ' + word
                            else:
                                current_display_line = word
                        else:
                            if current_display_line:
                                display_lines.append(current_display_line)
                            current_display_line = word
                    if current_display_line:
                        display_lines.append(current_display_line)
            
            # Display wrapped lines
            display_start = max(0, self.scroll_offset)
            display_end = min(len(display_lines), display_start + content_height - 2)
            
            for i, line_idx in enumerate(range(display_start, display_end)):
                if line_idx < len(display_lines):
                    line = display_lines[line_idx]
                    print(f"\033[{2 + i};{start_x + 1}H{line}", end='')
    
    def draw_book_list(self, start_x: int, content_width: int, content_height: int):
        """Draw the book list in the main content area"""
        if not self.books_list:
            # Display "No Books" message at the top
            message = "No Books"
            print(f"\033[{2};{start_x + 2}H{message}", end='')
        else:
            # Display books list
            for i, book in enumerate(self.books_list):
                if i < content_height - 2:  # Leave room for border
                    # Show arrow for selected book
                    if i == self.book_selection and self.book_focused:
                        print(f"\033[{2 + i};{start_x + 2}H> {book}", end='')
                    else:
                        print(f"\033[{2 + i};{start_x + 2}H  {book}", end='')
    
    def draw_input_dialog(self):
        """Draw input dialog in the middle of the screen"""
        if not self.input_mode:
            return
        
        # Calculate dialog position (middle of screen)
        dialog_width = 40
        dialog_height = 3  # Reduced - no prompt needed for rename
        x = (self.width - dialog_width) // 2
        y = (self.height - dialog_height) // 2
        
        # Draw dialog background with color
        for row in range(y + 1, y + dialog_height - 1):
            print(f"\033[{row};{x + 1}H\033[7m{' ' * (dialog_width - 2)}", end='')
        
        # Determine title based on prompt and old name
        if hasattr(self, 'old_name') and self.old_name:
            title = f"Rename: {self.old_name}"
        elif "Chapter name:" in self.input_prompt:
            title = "Chapter name"
        elif "Book name:" in self.input_prompt:
            title = "Book name"
        elif "Rename" in self.input_prompt:
            title = "Rename"
        else:
            title = "Input"
        
        # Draw dialog border
        self.draw_border(x, y, dialog_width, dialog_height, title)
        
        # Draw prompt (only if it's not redundant with the title)
        if not ("Chapter name:" in self.input_prompt and title == "Chapter name"):
            if not (hasattr(self, 'old_name') and self.old_name):
                # Only show prompt for non-rename dialogs
                prompt = self.input_prompt[:dialog_width - 4]
                print(f"\033[{y + 1};{x + 2}H{prompt}", end='')
        
        # Draw input text
        input_display = self.input_text[:dialog_width - 4]
        print(f"\033[{y + 1};{x + 2}H{input_display}", end='')  # Input text on first content line
        
        # Draw cursor
        cursor_x = x + 2 + len(input_display)
        print(f"\033[{y + 1};{cursor_x}H_", end='')  # Cursor on input text line
    
    def draw_confirm_dialog(self):
        """Draw confirmation dialog in the middle of the screen"""
        if not self.confirm_mode:
            return
        
        # Calculate dialog position (middle of screen)
        dialog_width = 20
        dialog_height = 3
        x = (self.width - dialog_width) // 2
        y = (self.height - dialog_height) // 2
        
        # Draw dialog background with color
        for row in range(y + 1, y + dialog_height - 1):
            print(f"\033[{row};{x + 1}H\033[7m{' ' * (dialog_width - 2)}", end='')
        
        # Draw dialog border
        self.draw_border(x, y, dialog_width, dialog_height, "Save")
        
        # Draw options
        yes_text = "Yes"
        no_text = "No"
        
        # Calculate positions - Yes on left, No on right
        yes_x = x + 4
        no_x = x + 12
        option_y = y + 1
        
        # Draw Yes option (left) with arrow indicator
        if self.confirm_selection:
            print(f"\033[{option_y};{yes_x}H\033[7m> {yes_text} \033[0m", end='')
        else:
            print(f"\033[{option_y};{yes_x}H\033[7m  {yes_text} \033[0m", end='')
        
        # Draw No option (right) with arrow indicator
        if not self.confirm_selection:
            print(f"\033[{option_y};{no_x}H\033[7m> {no_text} \033[0m", end='')
        else:
            print(f"\033[{option_y};{no_x}H\033[7m  {no_text} \033[0m", end='')
    
    def draw_bottom_bar(self):
        """Draw the bottom status bar"""
        y = self.height
        if self.current_mode == "book_list":
            print(f"\033[{y};1H^B panel  ^N new book  ^R rename  ^D delete  ^Q quit", end='')
        elif self.current_book:
            print(f"\033[{y};1H^B panel  ^N new chapter  ^S save  ^O open book  ^Q quit", end='')
        else:
            print(f"\033[{y};1H^B panel  ^O open book  ^Q quit", end='')
    
    def render(self):
        """Render the entire UI"""
        self.clear_screen()
        self.draw_left_panel()
        self.draw_main_content()
        self.draw_input_dialog()
        self.draw_confirm_dialog()
        self.draw_help_panel()
        
        # Draw cursor in main content area
        if not self.input_mode and not self.confirm_mode and not self.help_mode:
            self.draw_cursor()
        
        sys.stdout.flush()
    
    def draw_cursor(self):
        """Draw cursor at the correct position"""
        # Only show cursor when side panel is closed (edit mode)
        if self.left_panel_expanded:
            return  # Don't draw cursor in view mode
        
        start_x = 2
        
        # Calculate display width
        if self.left_panel_expanded:
            content_width = self.width - (self.left_panel_width + 2)
        else:
            content_width = self.width - 1
        display_width = content_width - 2
        
        # Get content up to cursor position
        content_before_cursor = self.main_content[:self.cursor_pos]
        lines = content_before_cursor.split('\n')
        
        # Calculate which display line we're on
        display_line = 0
        for line in lines[:-1]:  # All lines except the current one
            display_line += self.calculate_wrapped_lines_for_display(line, display_width)
        
        # Calculate wrapped lines for current line up to cursor
        current_line_to_cursor = lines[-1] if lines else ""
        wrapped_lines = self.wrap_line_for_display(current_line_to_cursor, display_width)
        display_line += len(wrapped_lines) - 1  # -1 because we want the last line
        
        # Calculate cursor position within the current wrapped line
        if wrapped_lines:
            cursor_col = len(wrapped_lines[-1])
            cursor_x = start_x + cursor_col
        else:
            cursor_x = start_x
            
        cursor_y = 2 + display_line - self.scroll_offset
        
        # Position the terminal cursor
        print(f"\033[{cursor_y};{cursor_x}H", end='')
    
    def calculate_wrapped_lines_for_display(self, text, display_width):
        """Calculate how many display lines a text line will take when wrapped"""
        if not text:
            return 1
        wrapped = self.wrap_line_for_display(text, display_width)
        return len(wrapped)
    
    def wrap_line_for_display(self, line, display_width):
        """Wrap a single line - word-based wrapping to match display logic"""
        if len(line) <= display_width:
            return [line]
        else:
            # Word-based wrapping - same logic as in draw_main_content
            words = line.split(' ')
            wrapped_lines = []
            current_line = ''
            for word in words:
                if len(current_line + ' ' + word) <= display_width:
                    if current_line:
                        current_line += ' ' + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = word
            if current_line:
                wrapped_lines.append(current_line)
            return wrapped_lines
    
    def calculate_chars_before_wrapped_line(self, line, wrapped_line_idx, display_width):
        """Calculate how many characters come before a specific wrapped line"""
        if wrapped_line_idx == 0:
            return 0
        
        wrapped_lines = self.wrap_line_for_display(line, display_width)
        if wrapped_line_idx >= len(wrapped_lines):
            return len(line)
        
        # Count characters in all previous wrapped lines
        chars_before = 0
        for i in range(wrapped_line_idx):
            wrapped_line = wrapped_lines[i]
            chars_before += len(wrapped_line)
            # Add 1 for the space that was removed when splitting (except for the last line)
            if i < len(wrapped_lines) - 1:
                chars_before += 1
        
        return chars_before
    
    def handle_input(self, key: str):
        """Handle keyboard input"""
        # Handle help panel first
        if self.help_mode:
            if key == 'ESC' or key == 'CTRL_H':
                self.help_mode = False
            return True
        
        # Handle input dialog first
        if self.input_mode:
            return self.handle_input_dialog(key)
        
        # Handle confirmation dialog
        if self.confirm_mode:
            return self.handle_confirm_dialog(key)
        
        if key == 'CTRL_Q':
            return False  # Quit
        elif key == 'CTRL_B':
            self.left_panel_expanded = not self.left_panel_expanded
            # Recalculate panel width when toggling
            self.left_panel_width = max(17, self.width // 4 - 3)
            # Set panel focus when opening side panel
            if self.left_panel_expanded:
                self.panel_focused = True
                # Set panel selection to current chapter when opening side panel
                if self.current_chapter and self.current_chapter in self.chapters_list:
                    self.panel_selection = self.chapters_list.index(self.current_chapter)
            else:
                self.panel_focused = False
        elif key == 'CTRL_N' and self.current_mode == "book_list":
            # Create new book
            self.show_input_dialog("Book name:", lambda name: self.create_new_book_callback(name))
        elif key == 'CTRL_R':
            if self.current_mode == "book_list":
                # Rename book
                if self.books_list and self.book_selection < len(self.books_list):
                    selected_book = self.books_list[self.book_selection]
                    self.show_input_dialog("New name:", lambda name: self.rename_book_callback(name), old_name=selected_book)
            elif not self.left_panel_expanded and self.current_book and self.current_chapter:
                # Rename current chapter (only when side panel is closed)
                chapter_name = self.current_chapter.replace('.md', '')
                self.show_input_dialog("New name:", lambda name: self.rename_chapter_callback(self.current_chapter, name), old_name=chapter_name)
        elif key == 'CTRL_D':
            if self.current_mode == "book_list":
                # Delete book
                if self.books_list and self.book_selection < len(self.books_list):
                    self.delete_book_callback()
            elif self.left_panel_expanded and self.current_book and self.chapters_list:
                # Delete chapter from side panel
                if self.panel_selection < len(self.chapters_list):
                    self.delete_chapter_callback()
            elif not self.left_panel_expanded and self.current_book and self.current_chapter:
                # Delete current chapter from main editor
                self.delete_chapter_callback()
        elif key == 'CTRL_O' and self.current_mode != "book_list":
            # Open book list
            self.left_panel_expanded = False  # Close side panel
            self.current_mode = "book_list"
            self.load_books()
            self.book_selection = 0
            self.book_focused = True
        elif key == 'CTRL_N' and self.current_book:
            # Create new chapter
            self.show_input_dialog("Chapter name:", lambda name: self.create_new_chapter_callback(name))
        elif key == 'CTRL_S':
            # Show save confirmation dialog
            if self.current_book and self.current_chapter:
                self.confirm_mode = True
                self.confirm_selection = False  # Default to No
                self.confirm_type = "save"
        elif key == 'CTRL_H':
            # Toggle help panel
            self.help_mode = not self.help_mode
        elif key == 'ESC' and self.current_mode == "book_list":
            # Go back to editor mode
            self.current_mode = "editor"
            self.book_focused = False
        elif key == 'BACKSPACE':
            if self.current_mode == "book_list":
                # Exit book list mode and return to side panel
                self.current_mode = "editor"
                self.book_focused = False
            elif self.left_panel_expanded:
                # When side panel is open, backspace exits to main editor
                self.panel_focused = False
                self.preview_mode = False  # Exit preview mode
            elif self.cursor_pos > 0:
                self.main_content = self.main_content[:self.cursor_pos - 1] + self.main_content[self.cursor_pos:]
                self.cursor_pos -= 1
                # Mark as having unsaved changes
                self.unsaved_changes = True
        elif key == 'ENTER':
            if self.current_mode == "book_list":
                # Handle book selection
                if self.books_list and self.book_selection < len(self.books_list):
                    # Load selected book
                    selected_book = self.books_list[self.book_selection]
                    self.load_book(selected_book)
                    self.current_mode = "editor"
                    self.book_focused = False
                    # Set panel selection to current chapter if it exists, otherwise first chapter
                    if self.current_chapter and self.current_chapter in self.chapters_list:
                        self.panel_selection = self.chapters_list.index(self.current_chapter)
                    else:
                        self.panel_selection = 0
                    self.panel_focused = True  # Focus the panel when book is loaded
                    self.left_panel_expanded = True  # Always open side panel when book is loaded
                    # Show preview of first chapter if available
                    if self.chapters_list:
                        first_chapter = self.chapters_list[0]
                        self.load_chapter_preview(first_chapter)
                        self.preview_mode = True
            elif self.left_panel_expanded and self.panel_focused and self.panel_selection in self.selectable_items:
                # Handle panel item selection
                if self.current_book:
                    # Handle chapter selection
                    if self.panel_selection < len(self.chapters_list):
                        # Chapter selected
                        selected_chapter = self.chapters_list[self.panel_selection]
                        self.current_chapter = selected_chapter
                        # Load chapter content and exit preview mode
                        self.load_chapter(selected_chapter)
                        self.preview_mode = False
                        # Close side panel and return control to main editor
                        self.left_panel_expanded = False
                        self.panel_focused = False
                # Return focus to editor after selection
                self.panel_focused = False
            elif not self.left_panel_expanded:
                # Only allow editing when side panel is closed
                self.main_content = self.main_content[:self.cursor_pos] + '\n' + self.main_content[self.cursor_pos:]
                self.cursor_pos += 1
                # Mark as having unsaved changes
                self.unsaved_changes = True
        elif key == 'UP':
            if self.current_mode == "book_list" and self.books_list:
                # Navigate book list
                self.book_focused = True
                if self.book_selection > 0:
                    self.book_selection -= 1
            elif self.left_panel_expanded and self.selectable_items:
                # Navigate left panel (chapters only)
                self.panel_focused = True
                if self.current_book and self.panel_selection > 0:
                    # Check for unsaved changes before navigating
                    if self.unsaved_changes:
                        self.confirm_mode = True
                        self.confirm_selection = False  # Default to No
                        self.confirm_type = "unsaved"
                        self.pending_navigation = "UP"
                        return True
                    # Navigate chapters
                    self.panel_selection -= 1
                    # Load preview of selected chapter
                    if self.panel_selection < len(self.chapters_list):
                        selected_chapter = self.chapters_list[self.panel_selection]
                        self.load_chapter_preview(selected_chapter)
                        self.preview_mode = True
            else:
                # Move cursor up in main content
                if not self.left_panel_expanded:
                    self.move_cursor_up()
        elif key == 'DOWN':
            if self.current_mode == "book_list" and self.books_list:
                # Navigate book list
                self.book_focused = True
                if self.book_selection < len(self.books_list) - 1:
                    self.book_selection += 1
            elif self.left_panel_expanded and self.selectable_items:
                # Navigate left panel (chapters only)
                self.panel_focused = True
                if self.current_book:
                    # Navigate chapters
                    if self.panel_selection < len(self.chapters_list) - 1:
                        # Check for unsaved changes before navigating
                        if self.unsaved_changes:
                            self.confirm_mode = True
                            self.confirm_selection = False  # Default to No
                            self.confirm_type = "unsaved"
                            self.pending_navigation = "DOWN"
                            return True
                        self.panel_selection += 1
                        # Load preview of selected chapter
                        if self.panel_selection < len(self.chapters_list):
                            selected_chapter = self.chapters_list[self.panel_selection]
                            self.load_chapter_preview(selected_chapter)
                            self.preview_mode = True
            else:
                # Move cursor down in main content
                if not self.left_panel_expanded:
                    self.move_cursor_down()
        elif key == 'LEFT':
            if not self.left_panel_expanded or not self.panel_focused:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
        elif key == 'RIGHT':
            if not self.left_panel_expanded or not self.panel_focused:
                if self.cursor_pos < len(self.main_content):
                    self.cursor_pos += 1
        elif len(key) == 1 and key.isprintable():
            # Insert character - only when side panel is closed
            if not self.left_panel_expanded:
                self.main_content = self.main_content[:self.cursor_pos] + key + self.main_content[self.cursor_pos:]
                self.cursor_pos += 1
                # Mark as having unsaved changes
                self.unsaved_changes = True
            # Return focus to editor when typing
            self.panel_focused = False
            
        return True
    
    def move_cursor_up(self):
        """Move cursor up one virtual line"""
        if not self.main_content or self.cursor_pos == 0:
            return
        
        # Calculate display width
        if self.left_panel_expanded:
            content_width = self.width - (self.left_panel_width + 2)
        else:
            content_width = self.width - 1
        display_width = content_width - 2
        
        # Get content up to cursor position
        content_before_cursor = self.main_content[:self.cursor_pos]
        lines = content_before_cursor.split('\n')
        
        # Calculate which virtual line we're currently on
        current_virtual_line = 0
        for line in lines[:-1]:  # All lines except the current one
            current_virtual_line += self.calculate_wrapped_lines_for_display(line, display_width)
        
        # Calculate wrapped lines for current line up to cursor
        current_line_to_cursor = lines[-1] if lines else ""
        wrapped_lines = self.wrap_line_for_display(current_line_to_cursor, display_width)
        current_virtual_line += len(wrapped_lines) - 1  # -1 because we want the last line
        
        # If we're on the first virtual line, move to beginning of content
        if current_virtual_line == 0:
            self.cursor_pos = 0
            return
        
        # Find the previous virtual line
        target_virtual_line = current_virtual_line - 1
        
        # Calculate cursor position within the current wrapped line
        current_col = len(wrapped_lines[-1]) if wrapped_lines else 0
        
        # Work backwards through lines to find the target virtual line
        virtual_line_count = 0
        target_line_idx = 0
        target_col = 0
        
        for line_idx, line in enumerate(lines):
            line_wrapped = self.wrap_line_for_display(line, display_width)
            line_virtual_lines = len(line_wrapped)
            
            if virtual_line_count + line_virtual_lines > target_virtual_line:
                # Target virtual line is within this actual line
                target_line_idx = line_idx
                target_wrapped_line_idx = target_virtual_line - virtual_line_count
                target_wrapped_line = line_wrapped[target_wrapped_line_idx]
                
                # Calculate column position within the target wrapped line
                target_col = min(current_col, len(target_wrapped_line))
                break
            
            virtual_line_count += line_virtual_lines
        
        # Calculate the actual cursor position
        if target_line_idx == 0:
            line_start = 0
        else:
            line_start = len('\n'.join(lines[:target_line_idx])) + 1
        
        target_line = lines[target_line_idx]
        target_wrapped = self.wrap_line_for_display(target_line, display_width)
        target_wrapped_line_idx = target_virtual_line - virtual_line_count
        
        if target_wrapped_line_idx < len(target_wrapped):
            target_wrapped_line = target_wrapped[target_wrapped_line_idx]
            # Calculate position within the actual line using word-based positioning
            chars_before_wrapped_line = self.calculate_chars_before_wrapped_line(target_line, target_wrapped_line_idx, display_width)
            self.cursor_pos = line_start + chars_before_wrapped_line + target_col
        else:
            # Fallback to end of line
            self.cursor_pos = line_start + len(target_line)
    
    def move_cursor_down(self):
        """Move cursor down one virtual line"""
        if not self.main_content:
            return
        
        # Calculate display width
        if self.left_panel_expanded:
            content_width = self.width - (self.left_panel_width + 2)
        else:
            content_width = self.width - 1
        display_width = content_width - 2
        
        # Get content up to cursor position
        content_before_cursor = self.main_content[:self.cursor_pos]
        lines = content_before_cursor.split('\n')
        
        # Calculate which virtual line we're currently on
        current_virtual_line = 0
        for line in lines[:-1]:  # All lines except the current one
            current_virtual_line += self.calculate_wrapped_lines_for_display(line, display_width)
        
        # Calculate wrapped lines for current line up to cursor
        current_line_to_cursor = lines[-1] if lines else ""
        wrapped_lines = self.wrap_line_for_display(current_line_to_cursor, display_width)
        current_virtual_line += len(wrapped_lines) - 1  # -1 because we want the last line
        
        # Calculate total virtual lines in the entire content
        all_lines = self.main_content.split('\n')
        total_virtual_lines = 0
        for line in all_lines:
            total_virtual_lines += self.calculate_wrapped_lines_for_display(line, display_width)
        
        # If we're on the last virtual line, don't move
        if current_virtual_line >= total_virtual_lines - 1:
            return
        
        # Find the next virtual line
        target_virtual_line = current_virtual_line + 1
        
        # Calculate cursor position within the current wrapped line
        current_col = len(wrapped_lines[-1]) if wrapped_lines else 0
        
        # Work forwards through lines to find the target virtual line
        virtual_line_count = 0
        target_line_idx = 0
        target_col = 0
        
        for line_idx, line in enumerate(all_lines):
            line_wrapped = self.wrap_line_for_display(line, display_width)
            line_virtual_lines = len(line_wrapped)
            
            if virtual_line_count + line_virtual_lines > target_virtual_line:
                # Target virtual line is within this actual line
                target_line_idx = line_idx
                target_wrapped_line_idx = target_virtual_line - virtual_line_count
                target_wrapped_line = line_wrapped[target_wrapped_line_idx]
                
                # Calculate column position within the target wrapped line
                target_col = min(current_col, len(target_wrapped_line))
                break
            
            virtual_line_count += line_virtual_lines
        
        # Calculate the actual cursor position
        if target_line_idx == 0:
            line_start = 0
        else:
            line_start = len('\n'.join(all_lines[:target_line_idx])) + 1
        
        target_line = all_lines[target_line_idx]
        target_wrapped = self.wrap_line_for_display(target_line, display_width)
        target_wrapped_line_idx = target_virtual_line - virtual_line_count
        
        if target_wrapped_line_idx < len(target_wrapped):
            target_wrapped_line = target_wrapped[target_wrapped_line_idx]
            # Calculate position within the actual line using word-based positioning
            chars_before_wrapped_line = self.calculate_chars_before_wrapped_line(target_line, target_wrapped_line_idx, display_width)
            self.cursor_pos = line_start + chars_before_wrapped_line + target_col
        else:
            # Fallback to end of line
            self.cursor_pos = line_start + len(target_line)
    
    
    def create_new_book_callback(self, name: str):
        """Callback for creating a new book"""
        if self.create_new_book(name):
            self.load_books()
    
    def rename_book_callback(self, new_name: str):
        """Callback for renaming a book"""
        if self.books_list and self.book_selection < len(self.books_list):
            old_name = self.books_list[self.book_selection]
            if self.rename_book(old_name, new_name):
                self.load_books()
                # Adjust selection if needed
                if self.book_selection >= len(self.books_list):
                    self.book_selection = max(0, len(self.books_list) - 1)
    
    def delete_book_callback(self):
        """Callback for deleting a book"""
        if self.books_list and self.book_selection < len(self.books_list):
            book_name = self.books_list[self.book_selection]
            if self.delete_book(book_name):
                self.load_books()
                # Adjust selection if needed
                if self.book_selection >= len(self.books_list):
                    self.book_selection = max(0, len(self.books_list) - 1)
    
    def delete_chapter_callback(self):
        """Callback for deleting a chapter"""
        chapter_name = None
        
        if self.left_panel_expanded and self.chapters_list and self.panel_selection < len(self.chapters_list):
            # Delete from side panel
            chapter_name = self.chapters_list[self.panel_selection]
        elif not self.left_panel_expanded and self.current_chapter:
            # Delete current chapter from main editor
            chapter_name = self.current_chapter
        
        if chapter_name and self.delete_chapter(chapter_name):
            # Reload the book to refresh the chapter list
            self.load_book(self.current_book)
            # Adjust selection if needed (only for side panel)
            if self.left_panel_expanded and self.panel_selection >= len(self.chapters_list):
                self.panel_selection = max(0, len(self.chapters_list) - 1)
            # If we deleted the current chapter, clear the editor
            if self.current_chapter == chapter_name:
                self.main_content = ""
                self.cursor_pos = 0
                self.current_chapter = None
                self.unsaved_changes = False
    
    def rename_chapter_callback(self, old_chapter: str, new_name: str):
        """Callback for renaming a chapter"""
        if not new_name.strip():
            return
        
        # Sanitize the new name
        safe_name = "".join(c for c in new_name.strip() if c.isalnum() or c in " -_")
        if not safe_name:
            return
        
        # Add .md extension if not present
        if not safe_name.endswith('.md'):
            safe_name += '.md'
        
        # Check if new chapter name already exists (and it's not the same as old name)
        if safe_name != old_chapter and safe_name in self.chapters_list:
            return
        
        try:
            book_path = os.path.join(self.books_directory, self.current_book)
            old_path = os.path.join(book_path, old_chapter)
            new_path = os.path.join(book_path, safe_name)
            
            # Rename the file
            os.rename(old_path, new_path)
            
            # Update chapter order file
            self.update_chapter_order(old_chapter, safe_name)
            
            # Reload the book to refresh the chapter list
            self.load_book(self.current_book)
            
            # If we renamed the current chapter, update current_chapter
            if self.current_chapter == old_chapter:
                self.current_chapter = safe_name
                
        except OSError:
            pass  # Handle rename errors silently
    
    def update_chapter_order(self, old_name: str, new_name: str):
        """Update the chapter order file when a chapter is renamed"""
        if not self.current_book:
            return
        
        try:
            book_path = os.path.join(self.books_directory, self.current_book)
            order_file = os.path.join(book_path, '.chapter_order')
            
            if os.path.exists(order_file):
                with open(order_file, 'r') as f:
                    chapters = [line.strip() for line in f.readlines() if line.strip()]
                
                # Replace old name with new name
                if old_name in chapters:
                    chapters[chapters.index(old_name)] = new_name
                    
                    with open(order_file, 'w') as f:
                        for chapter in chapters:
                            f.write(chapter + '\n')
        except OSError:
            pass  # Handle file errors silently
    
    def create_new_chapter_callback(self, name: str):
        """Callback for creating a new chapter"""
        if not self.current_book or not name.strip():
            return
        
        # Sanitize chapter name
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        if not safe_name:
            return
        
        # Add .md extension if not present
        if not safe_name.endswith('.md'):
            safe_name += '.md'
        
        # Check if chapter already exists
        if safe_name in self.chapters_list:
            # Chapter already exists, don't create duplicate
            return
        
        # Create chapter file
        book_path = os.path.join(self.books_directory, self.current_book)
        chapter_path = os.path.join(book_path, safe_name)
        
        try:
            with open(chapter_path, 'w') as f:
                f.write('')  # Create empty chapter
            # Reload chapters
            self.load_book(self.current_book)
            # Clear main content and set new chapter
            self.main_content = ""
            self.cursor_pos = 0
            self.current_chapter = safe_name
            # Exit preview mode and close side panel
            self.preview_mode = False
            self.left_panel_expanded = False
            self.panel_focused = False
        except OSError:
            pass
    
    def run(self):
        """Main application loop"""
        try:
            while True:
                self.render()
                key = self.get_key()
                if not self.handle_input(key):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.disable_raw_mode()
            self.clear_screen()
            print("Goodbye!")

if __name__ == "__main__":
    ui = StoryWriterUI()
    ui.run()

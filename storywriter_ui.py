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
        self.left_panel_width = max(20, self.width // 4)  # 25% of screen width, min 20
        self.main_content = ""
        self.cursor_pos = 0
        self.scroll_offset = 0
        self.panel_selection = 0  # Track which item is selected in left panel
        self.panel_focused = False  # Track if panel has focus for navigation
        
        # Book management
        self.books_directory = "@data"
        self.current_mode = "editor"  # "editor", "book_list"
        self.books_list = []
        self.book_selection = 0
        self.book_focused = False
        self.input_mode = False
        self.input_text = ""
        self.input_callback = None
        
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
            elif key == '\x1b':  # Escape
                return 'ESC'
            return key
        finally:
            self.disable_raw_mode()
    
    def load_books(self):
        """Load list of books from the books directory"""
        if not os.path.exists(self.books_directory):
            os.makedirs(self.books_directory)
            self.books_list = []
            return
        
        # Get all directories in the books folder
        try:
            items = os.listdir(self.books_directory)
            self.books_list = [item for item in items if os.path.isdir(os.path.join(self.books_directory, item))]
            self.books_list.sort()
        except OSError:
            self.books_list = []
    
    def create_new_book(self, book_name: str):
        """Create a new book directory"""
        if not book_name.strip():
            return False
        
        # Sanitize book name for filesystem
        safe_name = "".join(c for c in book_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
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
    
    def rename_book(self, old_name: str, new_name: str):
        """Rename a book directory"""
        if not new_name.strip():
            return False
        
        # Sanitize new name for filesystem
        safe_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
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
    
    def show_input_dialog(self, prompt: str, callback):
        """Show input dialog for book naming"""
        self.input_mode = True
        self.input_text = ""
        self.input_callback = callback
        self.input_prompt = prompt
    
    def handle_input_dialog(self, key: str):
        """Handle input in dialog mode"""
        if key == 'ENTER':
            # Confirm input
            if self.input_callback:
                self.input_callback(self.input_text)
            self.input_mode = False
            self.input_text = ""
            self.input_callback = None
        elif key == '\x1b':  # Escape
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
    
    def clear_screen(self):
        """Clear the terminal screen"""
        print('\033[2J\033[H', end='')
        
    def draw_border(self, x: int, y: int, width: int, height: int, title: str = ""):
        """Draw a border box at the specified position"""
        # Top border
        print(f"\033[{y};{x}H╔{'═' * (width - 2)}╗", end='')
        
        # Title if provided
        if title:
            title_x = x + 2
            title_y = y
            print(f"\033[{title_y};{title_x}H{title}", end='')
        
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
        panel_height = self.height - 1  # Leave room for bottom bar
        
        # Draw the left panel border
        self.draw_border(1, 1, panel_width, panel_height, "=BOOKS=")
        
        # Add some sample content to the left panel
        content_lines = []
        
        # Add New Story and Settings at the bottom
        available_lines = panel_height - 2
        if len(content_lines) < available_lines - 3:  # Leave space for bottom items
            # Fill with empty lines if needed
            while len(content_lines) < available_lines - 3:
                content_lines.append("")
            
            # Add bottom items
            content_lines.append("")
            content_lines.append("Open Book")
            content_lines.append("Settings")
        
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
                    print(f"\033[{2 + i};3H\033[7m {line} \033[0m", end='')  # Reversed colors
                else:
                    print(f"\033[{2 + i};3H{line}", end='')
    
    def draw_main_content(self):
        """Draw the main writing area"""
        if self.left_panel_expanded:
            start_x = self.left_panel_width + 2
        else:
            start_x = 1
            
        content_width = self.width - start_x
        content_height = self.height - 1  # Leave room for bottom bar
        
        # Draw main content border
        if self.current_mode == "book_list":
            title = "BOOKS"
        else:
            title = "STORY EDITOR" if not self.left_panel_expanded else ""
        self.draw_border(start_x, 1, content_width, content_height, title)
        
        if self.current_mode == "book_list":
            self.draw_book_list(start_x, content_width, content_height)
        else:
            # Display the story content
            lines = self.main_content.split('\n')
            display_start = max(0, self.scroll_offset)
            display_end = min(len(lines), display_start + content_height - 2)
            
            for i, line_idx in enumerate(range(display_start, display_end)):
                if line_idx < len(lines):
                    line = lines[line_idx]
                    # Truncate line if too long
                    if len(line) > content_width - 2:
                        line = line[:content_width - 5] + "..."
                    print(f"\033[{2 + i};{start_x + 1}H{line}", end='')
    
    def draw_book_list(self, start_x: int, content_width: int, content_height: int):
        """Draw the book list in the main content area"""
        if not self.books_list:
            # Display "No Books" message
            message = "No Books"
            x_pos = start_x + (content_width - len(message)) // 2
            y_pos = content_height // 2
            print(f"\033[{y_pos};{x_pos}H{message}", end='')
        else:
            # Display books list
            for i, book in enumerate(self.books_list):
                if i < content_height - 2:  # Leave room for border
                    # Show arrow for selected book
                    if i == self.book_selection and self.book_focused:
                        print(f"\033[{2 + i};{start_x + 1}H> {book}", end='')
                    else:
                        print(f"\033[{2 + i};{start_x + 1}H  {book}", end='')
    
    def draw_input_dialog(self):
        """Draw input dialog in the middle of the screen"""
        if not self.input_mode:
            return
        
        # Calculate dialog position (middle of screen)
        dialog_width = 40
        dialog_height = 5
        x = (self.width - dialog_width) // 2
        y = (self.height - dialog_height) // 2
        
        # Draw dialog border
        self.draw_border(x, y, dialog_width, dialog_height, "Input")
        
        # Draw prompt
        prompt = self.input_prompt[:dialog_width - 4]
        print(f"\033[{y + 1};{x + 2}H{prompt}", end='')
        
        # Draw input text
        input_display = self.input_text[:dialog_width - 4]
        print(f"\033[{y + 3};{x + 2}H{input_display}", end='')
        
        # Draw cursor
        cursor_x = x + 2 + len(input_display)
        print(f"\033[{y + 3};{cursor_x}H_", end='')
    
    def draw_bottom_bar(self):
        """Draw the bottom status bar"""
        y = self.height
        if self.current_mode == "book_list":
            print(f"\033[{y};1H^B panel  ^N new book  ^R rename  ^D delete  ^Q quit", end='')
        else:
            print(f"\033[{y};1H^B panel  ^Q quit", end='')
    
    def render(self):
        """Render the entire UI"""
        self.clear_screen()
        self.draw_left_panel()
        self.draw_main_content()
        self.draw_input_dialog()
        self.draw_bottom_bar()
        
        # Position cursor in main content area
        if self.left_panel_expanded:
            cursor_x = self.left_panel_width + 3
        else:
            cursor_x = 2
            
        # Calculate cursor position based on content
        lines = self.main_content[:self.cursor_pos].split('\n')
        cursor_y = 2 + len(lines) - 1
        cursor_x += len(lines[-1]) if lines else 0
        
        print(f"\033[{cursor_y};{cursor_x}H", end='')
        sys.stdout.flush()
    
    def handle_input(self, key: str):
        """Handle keyboard input"""
        # Handle input dialog first
        if self.input_mode:
            return self.handle_input_dialog(key)
        
        if key == 'CTRL_Q':
            return False  # Quit
        elif key == 'CTRL_B':
            self.left_panel_expanded = not self.left_panel_expanded
            # Recalculate panel width when toggling
            self.left_panel_width = max(20, self.width // 4)
            # Reset panel focus when toggling
            self.panel_focused = False
        elif key == 'CTRL_N' and self.current_mode == "book_list":
            # Create new book
            self.show_input_dialog("Book name:", lambda name: self.create_new_book_callback(name))
        elif key == 'CTRL_R' and self.current_mode == "book_list":
            # Rename book
            if self.books_list and self.book_selection < len(self.books_list):
                self.show_input_dialog("New name:", lambda name: self.rename_book_callback(name))
        elif key == 'CTRL_D' and self.current_mode == "book_list":
            # Delete book
            if self.books_list and self.book_selection < len(self.books_list):
                self.delete_book_callback()
        elif key == 'ESC' and self.current_mode == "book_list":
            # Go back to editor mode
            self.current_mode = "editor"
            self.book_focused = False
        elif key == 'BACKSPACE':
            if self.current_mode == "book_list":
                # Exit book list mode and return to side panel
                self.current_mode = "editor"
                self.book_focused = False
            elif self.cursor_pos > 0:
                self.main_content = self.main_content[:self.cursor_pos - 1] + self.main_content[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key == 'ENTER':
            if self.current_mode == "book_list":
                # Handle book selection
                if self.books_list and self.book_selection < len(self.books_list):
                    # TODO: Open selected book
                    pass
            elif self.left_panel_expanded and self.panel_focused and self.panel_selection in self.selectable_items:
                # Handle panel item selection
                content_lines = []
                
                # Add bottom items
                available_lines = self.height - 3
                if len(content_lines) < available_lines - 3:
                    while len(content_lines) < available_lines - 3:
                        content_lines.append("")
                    content_lines.append("")
                    content_lines.append("Open Book")
                    content_lines.append("Settings")
                
                selected_item = content_lines[self.panel_selection]
                if selected_item == "Open Book":
                    # Switch to book list mode
                    self.current_mode = "book_list"
                    self.load_books()
                    self.book_selection = 0
                    self.book_focused = True
                elif selected_item == "Settings":
                    # TODO: Implement settings
                    pass
                # Return focus to editor after selection
                self.panel_focused = False
            else:
                self.main_content = self.main_content[:self.cursor_pos] + '\n' + self.main_content[self.cursor_pos:]
                self.cursor_pos += 1
        elif key == 'UP':
            if self.current_mode == "book_list" and self.books_list:
                # Navigate book list
                self.book_focused = True
                if self.book_selection > 0:
                    self.book_selection -= 1
            elif self.left_panel_expanded and self.selectable_items:
                # Navigate left panel
                self.panel_focused = True
                current_index = self.selectable_items.index(self.panel_selection) if self.panel_selection in self.selectable_items else 0
                if current_index > 0:
                    self.panel_selection = self.selectable_items[current_index - 1]
            else:
                # Move cursor up in main content (simplified)
                pass
        elif key == 'DOWN':
            if self.current_mode == "book_list" and self.books_list:
                # Navigate book list
                self.book_focused = True
                if self.book_selection < len(self.books_list) - 1:
                    self.book_selection += 1
            elif self.left_panel_expanded and self.selectable_items:
                # Navigate left panel
                self.panel_focused = True
                current_index = self.selectable_items.index(self.panel_selection) if self.panel_selection in self.selectable_items else 0
                if current_index < len(self.selectable_items) - 1:
                    self.panel_selection = self.selectable_items[current_index + 1]
            else:
                # Move cursor down in main content (simplified)
                pass
        elif key == 'LEFT':
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
        elif key == 'RIGHT':
            if self.cursor_pos < len(self.main_content):
                self.cursor_pos += 1
        elif len(key) == 1 and key.isprintable():
            # Insert character - always goes to story editor
            self.main_content = self.main_content[:self.cursor_pos] + key + self.main_content[self.cursor_pos:]
            self.cursor_pos += 1
            # Return focus to editor when typing
            self.panel_focused = False
            
        return True
    
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

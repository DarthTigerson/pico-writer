import sys
import tty
import termios
import shutil
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
            return key
        finally:
            self.disable_raw_mode()
    
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
        content_lines = [
            "Recent Stories:",
            "",
            "• Adventure Tale",
            "• Mystery Story", 
            "• Sci-Fi Novel"
        ]
        
        # Add New Story and Settings at the bottom
        available_lines = panel_height - 2
        if len(content_lines) < available_lines - 3:  # Leave space for bottom items
            # Fill with empty lines if needed
            while len(content_lines) < available_lines - 3:
                content_lines.append("")
            
            # Add bottom items
            content_lines.append("")
            content_lines.append("New Story")
            content_lines.append("Settings")
        
        # Store selectable items for navigation
        self.selectable_items = []
        for i, line in enumerate(content_lines):
            if line.strip() and not line.startswith("Recent Stories:") and not line.startswith("•"):
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
        title = "STORY EDITOR" if not self.left_panel_expanded else ""
        self.draw_border(start_x, 1, content_width, content_height, title)
        
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
    
    def draw_bottom_bar(self):
        """Draw the bottom status bar"""
        y = self.height
        print(f"\033[{y};1H^B panel  ^Q quit", end='')
    
    def render(self):
        """Render the entire UI"""
        self.clear_screen()
        self.draw_left_panel()
        self.draw_main_content()
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
        if key == 'CTRL_Q':
            return False  # Quit
        elif key == 'CTRL_B':
            self.left_panel_expanded = not self.left_panel_expanded
            # Recalculate panel width when toggling
            self.left_panel_width = max(20, self.width // 4)
            # Reset panel focus when toggling
            self.panel_focused = False
        elif key == 'BACKSPACE':
            if self.cursor_pos > 0:
                self.main_content = self.main_content[:self.cursor_pos - 1] + self.main_content[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key == 'ENTER':
            if self.left_panel_expanded and self.panel_focused and self.panel_selection in self.selectable_items:
                # Handle panel item selection
                content_lines = [
                    "Recent Stories:",
                    "",
                    "• Adventure Tale",
                    "• Mystery Story", 
                    "• Sci-Fi Novel"
                ]
                
                # Add bottom items
                available_lines = self.height - 3
                if len(content_lines) < available_lines - 3:
                    while len(content_lines) < available_lines - 3:
                        content_lines.append("")
                    content_lines.append("")
                    content_lines.append("New Story")
                    content_lines.append("Settings")
                
                selected_item = content_lines[self.panel_selection]
                if selected_item == "New Story":
                    self.main_content = ""
                    self.cursor_pos = 0
                elif selected_item == "Settings":
                    # TODO: Implement settings
                    pass
                # Return focus to editor after selection
                self.panel_focused = False
            else:
                self.main_content = self.main_content[:self.cursor_pos] + '\n' + self.main_content[self.cursor_pos:]
                self.cursor_pos += 1
        elif key == 'UP':
            if self.left_panel_expanded and self.selectable_items:
                # Navigate left panel
                self.panel_focused = True
                current_index = self.selectable_items.index(self.panel_selection) if self.panel_selection in self.selectable_items else 0
                if current_index > 0:
                    self.panel_selection = self.selectable_items[current_index - 1]
            else:
                # Move cursor up in main content (simplified)
                pass
        elif key == 'DOWN':
            if self.left_panel_expanded and self.selectable_items:
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

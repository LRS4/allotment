import sys
import random
import time
import pyautogui
from PyQt5 import QtWidgets, QtCore
from pynput import keyboard


class MouseJiggler(QtCore.QThread):
    """Mouse Jiggler that runs in a QThread."""

    log_message = QtCore.pyqtSignal(str)  # Custom signal for logging messages

    def __init__(self, sleep_time, min_switches, max_switches, min_wiggles, max_wiggles):
        super().__init__()
        self._is_running = True  # Control flag to stop the jiggler
        self.sleep_time = sleep_time
        self.min_switches = min_switches
        self.max_switches = max_switches
        self.min_wiggles = min_wiggles
        self.max_wiggles = max_wiggles

    def run(self):
        self.log_message.emit('Mouse jiggler started.')
        try:
            while self._is_running:
                self.switch_screens()
                self.wiggle_mouse()
                self.log_message.emit(f"Sleeping for {self.sleep_time} seconds...")
                # Needed to sleep for shorter intervals to check stop flag more frequently
                for _ in range(self.sleep_time):
                    if not self._is_running:
                        break
                    time.sleep(1)
        except Exception as e:
            self.log_message.emit(f"Error in MouseJiggler: {e}")

    def stop(self):
        """This will stop the jiggler."""
        self._is_running = False
        self.quit()
        self.wait()  # Wait for the thread to finish

    def switch_screens(self):
        if not self._is_running:
            return
        max_switches = random.randint(self.min_switches, self.max_switches)
        self.log_message.emit(f"Switching active screen {max_switches} times...")
        pyautogui.keyDown('alt')
        for _ in range(max_switches):
            if not self._is_running:
                pyautogui.keyUp('alt')
                return
            pyautogui.press('tab')
            time.sleep(0.5)
        pyautogui.keyUp('alt')

    def wiggle_mouse(self):
        if not self._is_running:
            return
        max_wiggles = random.randint(self.min_wiggles, self.max_wiggles)
        self.log_message.emit(f"Moving mouse {max_wiggles} times...")
        for i in range(max_wiggles):
            if not self._is_running:
                return
            coords = self.get_random_coords()
            self.log_message.emit(f"{i + 1}/{max_wiggles}: Moving to coordinates: {coords[0]}, {coords[1]}")
            pyautogui.moveTo(x=coords[0], y=coords[1], duration=1)  # Shorter duration for responsiveness
            if not self._is_running:
                return

    def get_random_coords(self):
        screen = pyautogui.size()
        return [random.randint(100, screen[0] - 200),
                random.randint(100, screen[1] - 200)]


class KeyListenerThread(QtCore.QThread):
    """Global Key Listener Thread using pynput."""

    escape_pressed = QtCore.pyqtSignal()  # Signal to notify when ESC is pressed

    def run(self):
        def on_press(key):
            if key == keyboard.Key.esc:
                print("Escape key pressed.")
                self.escape_pressed.emit()  # Emit the signal when ESC is pressed
                return False  # Stop the listener

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()


class AppWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Layout and widgets
        self.setWindowTitle('MausMove')

        self.layout = QtWidgets.QVBoxLayout()

        # Input fields for configuration
        self.sleep_time_input = QtWidgets.QSpinBox()
        self.sleep_time_input.setRange(1, 60)  # Set range from 1 to 60 seconds
        self.sleep_time_input.setValue(10)
        self.min_switches_input = QtWidgets.QSpinBox()
        self.min_switches_input.setRange(0, 10)
        self.min_switches_input.setValue(1)
        self.max_switches_input = QtWidgets.QSpinBox()
        self.max_switches_input.setRange(0, 10)
        self.max_switches_input.setValue(5)
        self.min_wiggles_input = QtWidgets.QSpinBox()
        self.min_wiggles_input.setRange(1, 20)
        self.min_wiggles_input.setValue(4)
        self.max_wiggles_input = QtWidgets.QSpinBox()
        self.max_wiggles_input.setRange(1, 20)
        self.max_wiggles_input.setValue(9)

        # Labels
        self.layout.addWidget(QtWidgets.QLabel("Sleep Time (seconds):"))
        self.layout.addWidget(self.sleep_time_input)
        self.layout.addWidget(QtWidgets.QLabel("Min Switches:"))
        self.layout.addWidget(self.min_switches_input)
        self.layout.addWidget(QtWidgets.QLabel("Max Switches:"))
        self.layout.addWidget(self.max_switches_input)
        self.layout.addWidget(QtWidgets.QLabel("Min Wiggles:"))
        self.layout.addWidget(self.min_wiggles_input)
        self.layout.addWidget(QtWidgets.QLabel("Max Wiggles:"))
        self.layout.addWidget(self.max_wiggles_input)

        # Buttons
        self.start_jiggler_button = QtWidgets.QPushButton('Start Jiggler')
        self.start_jiggler_button.clicked.connect(self.start_jiggler)

        self.stop_jiggler_button = QtWidgets.QPushButton('Stop Jiggler')
        self.stop_jiggler_button.clicked.connect(self.stop_jiggler)

        # Logging area (QTextEdit)
        self.log_area = QtWidgets.QTextEdit()
        self.log_area.setReadOnly(True)  # Make it non-editable

        # Add widgets to layout
        self.layout.addWidget(self.start_jiggler_button)
        self.layout.addWidget(self.stop_jiggler_button)
        self.layout.addWidget(self.log_area)  # Add log area to the layout
        self.setLayout(self.layout)

        # Threads
        self.jiggler_thread = None
        self.key_listener_thread = KeyListenerThread()

        # Connect the escape key press signal to stop the jiggler
        self.key_listener_thread.escape_pressed.connect(self.handle_escape_press)

        # Start the key listener
        self.start_key_listener()

    def start_jiggler(self):
        if self.jiggler_thread and self.jiggler_thread.isRunning():
            self.update_log("Jiggler is already running.")
            return

        # Get user input values
        sleep_time = self.sleep_time_input.value()
        min_switches = self.min_switches_input.value()
        max_switches = self.max_switches_input.value()
        min_wiggles = self.min_wiggles_input.value()
        max_wiggles = self.max_wiggles_input.value()

        # Create and start the jiggler thread with user settings
        self.jiggler_thread = MouseJiggler(sleep_time, min_switches, max_switches, min_wiggles, max_wiggles)
        self.jiggler_thread.log_message.connect(self.update_log)  # Reconnect signal
        self.jiggler_thread.start()
        self.clear_log()
        self.update_log("Started the mouse jiggler.")

    def stop_jiggler(self):
        if self.jiggler_thread:
            if self.jiggler_thread.isRunning():
                self.jiggler_thread.stop()  # Send the stop signal to the jiggler
                self.jiggler_thread = None  # Clear the thread reference
                self.update_log("Stopped the mouse jiggler.")
                self.start_key_listener()

    def handle_escape_press(self):
        """Handle the ESC key press to stop the jiggler."""
        self.update_log("ESC key pressed. Stopping the mouse jiggler...")
        self.stop_jiggler()

    def start_key_listener(self):
        """Start the global key listener."""
        if not self.key_listener_thread.isRunning():
            self.key_listener_thread.start()
            print("Started the key listener.")

    def update_log(self, message):
        """Update the log area with new messages."""
        message_includes_esc = "ESC" in message
        log_already_includes_esc = "ESC" in self.log_area.toPlainText()

        if (
            message_includes_esc and \
            log_already_includes_esc
        ):
            return
        
        self.log_area.append(message)

    def clear_log(self):
        """Clear the log area."""        
        self.log_area.clear()

    def closeEvent(self, event):
        """Ensure the listener thread is cleaned up on app close."""
        if self.key_listener_thread.isRunning():
            self.key_listener_thread.quit()
        if self.jiggler_thread:
            if self.jiggler_thread.isRunning():
                self.jiggler_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec_())

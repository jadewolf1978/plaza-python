import logging
from colorama import Fore, Style, init
from datetime import datetime

init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'DEBUG': Fore.BLUE,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        # Add timestamp with cyan color
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        colored_timestamp = f"{Fore.CYAN}{timestamp}{Style.RESET_ALL}"
        
        # Color the log level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        
        # Format the message
        return f"[{colored_timestamp}] [{record.levelname}]: {record.getMessage()}"

# Create logger
logger = logging.getLogger('plaza')
logger.setLevel(logging.INFO)

# Create console handler and set formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

def get_logger():
    return logger
